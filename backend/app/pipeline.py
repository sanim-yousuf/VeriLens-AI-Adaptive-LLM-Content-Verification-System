import hashlib
import logging
import re
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic
from urllib.parse import urlparse

from app.openai_client import OpenAIClient
from app.schemas import (
    AgentFinding,
    AnalysisMode,
    AnalysisRequest,
    AnalysisResponse,
    ClaimCheck,
    ClaimVerdict,
    CommunitySignal,
    CostMetadata,
    EvidenceItem,
    ExplainResponse,
    HighlightSpan,
    InputType,
    LanguageCode,
    ModerationResult,
    RecommendedAction,
    RegionalContext,
    RiskFactor,
    RiskLevel,
    ScoreBreakdown,
    TimelineEvent,
    Topic,
    TrustAnalysis,
    VisualAuthenticity,
)
from app.settings import Settings
from app.store import AnalysisStore

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are VeriLens AI, an explainable multilingual trust-analysis engine.
Return only schema-compliant JSON. Separate evidence from inference. Preserve Bangla,
Banglish, and English nuance. Be cautious with health, finance, politics, public safety,
and regional conflict. Do not overclaim falsehood when evidence is incomplete.
Produce claim checks, risk factors, regional context, multi-agent findings, and a trust timeline.
""".strip()

BANGLA_RE = re.compile(r"[\u0980-\u09FF]")
LATIN_RE = re.compile(r"[A-Za-z]")
URL_RE = re.compile(r"https?://[^\s]+")
HIGH_STAKES_TOPICS = {Topic.HEALTH, Topic.FINANCE, Topic.POLITICS, Topic.PUBLIC_SAFETY}
URGENCY_TERMS = (
    "share now",
    "urgent",
    "breaking",
    "forward this",
    "do not ignore",
    "guaranteed",
    "miracle",
    "secret cure",
    "100% true",
)
TOPIC_TERMS = {
    Topic.HEALTH: ("vaccine", "medicine", "cure", "doctor", "hospital", "virus", "disease"),
    Topic.FINANCE: ("bank", "loan", "investment", "crypto", "money", "bkash", "nagad", "profit"),
    Topic.POLITICS: ("election", "minister", "government", "party", "vote", "protest"),
    Topic.EDUCATION: ("exam", "admission", "university", "school", "result"),
    Topic.PUBLIC_SAFETY: ("attack", "fire", "police", "army", "alert", "danger"),
    Topic.INTERNATIONAL: ("india", "china", "usa", "united states", "border", "global"),
}
TRUSTED_DOMAINS = {
    "who.int": 92,
    "un.org": 90,
    "worldbank.org": 88,
    "reuters.com": 86,
    "apnews.com": 84,
    "bbc.com": 82,
    "thedailystar.net": 76,
    "prothomalo.com": 76,
    "bdnews24.com": 74,
}
LOW_REPUTATION_HINTS = ("blogspot.", "wordpress.", "free-news", "viral", "click", "truth-now")


@dataclass(slots=True)
class PreprocessedInput:
    original: str
    normalized: str
    language: LanguageCode
    urls: list[str]
    domains: list[str]
    cache_key: str


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = monotonic()
        bucket = self._buckets[key]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True


class AnalysisService:
    def __init__(self, settings: Settings, store: AnalysisStore) -> None:
        self.settings = settings
        self.store = store
        self.openai = OpenAIClient(settings)

    async def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        if len(request.content) > self.settings.max_input_chars:
            raise ValueError(f"Input is too large. Maximum allowed size is {self.settings.max_input_chars} characters.")

        data = preprocess(request)
        cached = self.store.get_by_cache_key(data.cache_key)
        if cached and request.analysis_mode != AnalysisMode.DEEP:
            cached_copy = cached.model_copy(
                update={
                    "analysis_id": str(uuid.uuid4()),
                    "cost": cached.cost.model_copy(update={"cache_hit": True}),
                }
            )
            cached_copy.trust_timeline = timeline_for(
                mode=request.analysis_mode,
                openai_used=cached_copy.cost.openai_used,
                cache_hit=True,
                fallback_reason=None,
            )
            return self.store.save(cached_copy)

        source_score, source_notes = score_source(data.domains)
        moderation = await self._moderate(request.content)
        baseline = offline_analysis(request, data, source_score, source_notes)
        model = choose_model(self.settings, request.analysis_mode, baseline.topic, request.input_type, baseline.trust_score)

        analysis = baseline
        usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
        openai_used = False
        fallback_reason: str | None = None

        if request.analysis_mode != AnalysisMode.OFFLINE and self.openai.enabled:
            try:
                prompt = build_prompt(request, data, source_score, source_notes, moderation, baseline)
                analysis, usage = await self.openai.analyze(model=model, instructions=SYSTEM_PROMPT, prompt=prompt)
                openai_used = True
            except Exception as exc:
                logger.warning("OpenAI trust analysis failed; using offline fallback. reason=%s", exc)
                fallback_reason = f"OpenAI analysis failed ({type(exc).__name__}): {safe_error(exc)}"
                model = "offline-heuristics"
                analysis = baseline
        elif request.analysis_mode != AnalysisMode.OFFLINE:
            fallback_reason = self.openai.unavailable_reason or "OpenAI client is unavailable; local fallback was used."
            model = "offline-heuristics"

        analysis = reconcile_scores(analysis, baseline, moderation)
        analysis = apply_runtime_fields(
            analysis=analysis,
            request=request,
            openai_used=openai_used,
            fallback_reason=fallback_reason,
            cache_hit=False,
            store=self.store,
            analysis_id=None,
        )
        response = AnalysisResponse(
            **analysis.model_dump(),
            analysis_id=str(uuid.uuid4()),
            input_type=request.input_type,
            moderation=moderation,
            cost=CostMetadata(
                model_used=model,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                cached_tokens=usage["cached_tokens"],
                analysis_mode=request.analysis_mode,
                cache_hit=False,
                openai_used=openai_used,
            ),
            source_url=request.source_url or (data.urls[0] if data.urls else None),
            region=request.user_context.region,
            evidence_vs_inference=[
                item
                for item in analysis.reasoning
                if item.signal_type in {"fact", "inference", "heuristic", "source", "uncertainty"}
            ],
            raw_signals={
                "cache_key": data.cache_key,
                "domains": data.domains,
                "source_notes": source_notes,
                "offline_baseline_score": baseline.trust_score,
                "analysis_mode": request.analysis_mode.value,
                "openai_fallback_reason": fallback_reason,
            },
        )
        response.community_signal = self.store.community_signal(response.analysis_id)
        return self.store.save(response)

    async def _moderate(self, content: str) -> ModerationResult:
        try:
            return await self.openai.moderate(content)
        except Exception:
            return ModerationResult(reason="Moderation unavailable; local safeguards continued.")

    async def explain(self, analysis: AnalysisResponse, question: str) -> ExplainResponse:
        clean_question = question.strip()
        if self.openai.enabled:
            try:
                answer = await self.openai.answer(
                    model=self.settings.standard_model,
                    instructions=(
                        "You are the VeriLens report assistant. Explain only the existing report. "
                        "Do not invent external facts. Be concise and practical."
                    ),
                    prompt=f"""
Question:
{clean_question}

Report JSON:
{analysis.model_dump_json()}
""".strip(),
                )
                return ExplainResponse(
                    analysis_id=analysis.analysis_id,
                    answer=answer,
                    openai_used=True,
                    model_used=self.settings.standard_model,
                )
            except Exception:
                pass

        return ExplainResponse(
            analysis_id=analysis.analysis_id,
            answer=offline_explanation(analysis, clean_question),
            openai_used=False,
            model_used="offline-explainer",
        )


def preprocess(request: AnalysisRequest) -> PreprocessedInput:
    original = request.content.strip()
    normalized = re.sub(r"\s+", " ", original).strip().lower()

    urls = URL_RE.findall(original)
    if request.source_url:
        urls.append(request.source_url)
    if request.input_type == InputType.URL and original.startswith("http"):
        urls.append(original)

    domains = sorted(
        {
            parsed.netloc.lower().replace("www.", "")
            for parsed in (urlparse(url) for url in urls)
            if parsed.netloc
        }
    )
    cache_key = hashlib.sha256(
        "|".join(
            [
                request.input_type.value,
                request.analysis_mode.value,
                request.user_context.region,
                normalized,
                ",".join(domains),
            ]
        ).encode("utf-8")
    ).hexdigest()

    return PreprocessedInput(
        original=original,
        normalized=normalized,
        language=detect_language(original),
        urls=sorted(set(urls)),
        domains=domains,
        cache_key=cache_key,
    )


def detect_language(text: str) -> LanguageCode:
    has_bangla = bool(BANGLA_RE.search(text))
    has_latin = bool(LATIN_RE.search(text))
    if has_bangla and has_latin:
        return LanguageCode.MIXED
    if has_bangla:
        return LanguageCode.BN
    if has_latin:
        return LanguageCode.EN
    return LanguageCode.UNKNOWN


def score_source(domains: list[str]) -> tuple[int, list[str]]:
    if not domains:
        return 45, ["No source domain was provided."]

    scores: list[int] = []
    notes: list[str] = []
    for domain in domains:
        if domain in TRUSTED_DOMAINS:
            scores.append(TRUSTED_DOMAINS[domain])
            notes.append(f"{domain} is in the curated trusted-source list.")
        elif any(hint in domain for hint in LOW_REPUTATION_HINTS):
            scores.append(25)
            notes.append(f"{domain} has low-reputation or viral-site naming patterns.")
        else:
            scores.append(55)
            notes.append(f"{domain} is not yet in the curated source list.")
    return round(sum(scores) / len(scores)), notes


def offline_analysis(
    request: AnalysisRequest,
    data: PreprocessedInput,
    source_score: int,
    source_notes: list[str],
) -> TrustAnalysis:
    topic = detect_topic(data.normalized)
    manipulation_score = manipulation_risk(data.normalized, data.original)
    patterns = manipulation_patterns(data.normalized)
    evidence_quality = evidence_score(data.normalized, source_score)
    context_risk = context_score(topic)
    viral_risk = viral_score(data.normalized)
    visual_risk = 55 if request.input_type in {InputType.IMAGE, InputType.SCREENSHOT} else 0
    ai_likelihood = ai_generated_score(data.normalized, data.original)

    trust_score = round(
        source_score * 0.25
        + evidence_quality * 0.25
        + (100 - manipulation_score) * 0.15
        + 70 * 0.10
        + (100 - context_risk) * 0.10
        + (100 - visual_risk) * 0.10
        + (100 - viral_risk) * 0.05
    )
    trust_score = clamp(trust_score)
    risk_level = risk_from_score(trust_score)

    reasoning = [
        EvidenceItem(
            label="source_signal",
            evidence="; ".join(source_notes),
            signal_type="source",
            confidence=0.7 if source_score >= 70 else 0.5,
        ),
        EvidenceItem(
            label="manipulation_signal",
            evidence=f"Local heuristics estimated manipulation intensity at {manipulation_score}/100.",
            signal_type="heuristic",
            confidence=0.58,
        ),
        EvidenceItem(
            label="evidence_signal",
            evidence=f"Evidence quality was estimated at {evidence_quality}/100 from source, citations, and specificity.",
            signal_type="heuristic",
            confidence=0.52,
        ),
    ]
    highlights = [
        HighlightSpan(text=term, type="urgency_or_emotion_bait", severity=RiskLevel.HIGH)
        for term in URGENCY_TERMS
        if term in data.normalized
    ][:6]

    return TrustAnalysis(
        topic=topic,
        language=data.language if data.language != LanguageCode.UNKNOWN else LanguageCode.EN,
        trust_score=trust_score,
        risk_level=risk_level,
        confidence=0.5,
        misinformation_probability=clamp(100 - trust_score + manipulation_score // 5),
        manipulation_score=manipulation_score,
        source_score=source_score,
        evidence_quality=evidence_quality,
        score_breakdown=ScoreBreakdown(
            source_credibility=source_score,
            evidence_consistency=evidence_quality,
            manipulation_intensity=manipulation_score,
            language_patterns=max(0, 100 - manipulation_score),
            context_risk=context_risk,
            visual_authenticity=max(0, 100 - visual_risk),
            viral_risk=viral_risk,
        ),
        reasoning=reasoning,
        highlight_spans=highlights,
        agent_findings=[
            AgentFinding(
                agent="Local Trust Agent",
                score=trust_score,
                summary="Fast offline baseline using source, evidence, manipulation, topic, and viral-risk signals.",
                evidence=reasoning,
            ),
            AgentFinding(
                agent="Emotion Agent",
                score=max(0, 100 - manipulation_score),
                summary=f"Detected {len(patterns)} manipulation pattern(s).",
                evidence=[
                    EvidenceItem(
                        label="emotion_patterns",
                        evidence=", ".join(patterns) if patterns else "No strong manipulation pattern was detected.",
                        signal_type="heuristic",
                        confidence=0.56,
                    )
                ],
            ),
            AgentFinding(
                agent="Source Agent",
                score=source_score,
                summary="Assessed domain reputation and source availability.",
                evidence=[
                    EvidenceItem(
                        label="source_notes",
                        evidence="; ".join(source_notes),
                        signal_type="source",
                        confidence=0.62,
                    )
                ],
            ),
            AgentFinding(
                agent="Evidence Agent",
                score=evidence_quality,
                summary="Estimated how much verifiable evidence is present in the submission.",
                evidence=[
                    EvidenceItem(
                        label="evidence_quality",
                        evidence=f"Evidence score is {evidence_quality}/100.",
                        signal_type="heuristic",
                        confidence=0.52,
                    )
                ],
            ),
        ],
        visual_authenticity=VisualAuthenticity(
            deepfake_risk=visual_risk,
            tampering_risk=visual_risk,
            notes="Dedicated visual forensics is not enabled in the local baseline.",
        ),
        risk_factors=risk_factors_for(
            source_score=source_score,
            evidence_quality=evidence_quality,
            manipulation_score=manipulation_score,
            context_risk=context_risk,
            viral_risk=viral_risk,
            ai_likelihood=ai_likelihood,
            visual_risk=visual_risk,
        ),
        claim_checks=claim_checks_for(data.original, evidence_quality, source_score),
        manipulation_patterns=patterns,
        ai_generated_likelihood=ai_likelihood,
        viral_risk=viral_risk,
        regional_context=regional_context_for(request.user_context.region, topic, context_risk),
        community_signal=CommunitySignal(
            report_count=0,
            consensus="not_enough_reports",
            note="Community verification is ready for feedback data but has no reports for this item yet.",
        ),
        trust_timeline=[
            TimelineEvent(stage="input_received", status="complete", note="Content accepted and normalized."),
            TimelineEvent(stage="local_baseline", status="complete", note="Offline trust signals were calculated."),
            TimelineEvent(
                stage="openai_analysis",
                status="pending" if request.analysis_mode != AnalysisMode.OFFLINE else "skipped",
                note="OpenAI Structured Output analysis runs when an API key is configured and mode is not offline.",
            ),
            TimelineEvent(stage="score_reconciliation", status="complete", note="Weighted trust score was produced."),
        ],
        expert_notes=expert_notes_for(topic, risk_level, evidence_quality),
        recommended_action=action_for(risk_level, topic),
        summary=f"{request.input_type.value.title()} content is {risk_level.value} risk with a primary topic of {topic.value}.",
        uncertainty="Offline baseline is heuristic-only; standard or deep mode improves reasoning when an API key is configured.",
    )


def choose_model(settings: Settings, mode: AnalysisMode, topic: Topic, input_type: InputType, baseline_score: int) -> str:
    if mode == AnalysisMode.OFFLINE:
        return "offline-heuristics"
    if mode == AnalysisMode.QUICK:
        return settings.triage_model
    if mode == AnalysisMode.DEEP:
        return settings.premium_model if topic in HIGH_STAKES_TOPICS or input_type != InputType.TEXT else settings.advanced_model
    return settings.advanced_model if topic in HIGH_STAKES_TOPICS or baseline_score < 45 else settings.standard_model


def build_prompt(
    request: AnalysisRequest,
    data: PreprocessedInput,
    source_score: int,
    source_notes: list[str],
    moderation: ModerationResult,
    baseline: TrustAnalysis,
) -> str:
    return f"""
Analyze this content using the VeriLens trust rubric.

Context:
- input_type: {request.input_type.value}
- analysis_mode: {request.analysis_mode.value}
- region: {request.user_context.region}
- locale: {request.locale}
- detected_language: {data.language.value}
- domains: {data.domains}
- source_score: {source_score}
- source_notes: {source_notes}
- moderation: {moderation.model_dump()}
- local_baseline: {baseline.model_dump()}

Content:
{data.original}
""".strip()


def apply_runtime_fields(
    analysis: TrustAnalysis,
    request: AnalysisRequest,
    openai_used: bool,
    fallback_reason: str | None,
    cache_hit: bool,
    store: AnalysisStore,
    analysis_id: str | None,
) -> TrustAnalysis:
    updated_notes = list(analysis.expert_notes)
    if fallback_reason:
        updated_notes.append(fallback_reason)

    return analysis.model_copy(
        update={
            "community_signal": store.community_signal(analysis_id) if analysis_id else analysis.community_signal,
            "trust_timeline": timeline_for(
                mode=request.analysis_mode,
                openai_used=openai_used,
                cache_hit=cache_hit,
                fallback_reason=fallback_reason,
            ),
            "expert_notes": dedupe_strings(updated_notes),
        }
    )


def timeline_for(
    mode: AnalysisMode,
    openai_used: bool,
    cache_hit: bool,
    fallback_reason: str | None,
) -> list[TimelineEvent]:
    if cache_hit:
        openai_status = "cached"
        openai_note = "A previous matching report was reused to reduce latency and API cost."
    elif mode == AnalysisMode.OFFLINE:
        openai_status = "skipped"
        openai_note = "Offline mode was selected, so no OpenAI request was made."
    elif openai_used:
        openai_status = "complete"
        openai_note = "OpenAI Structured Output analysis completed successfully."
    else:
        openai_status = "fallback"
        openai_note = fallback_reason or "OpenAI was unavailable, so local fallback analysis was used."

    return [
        TimelineEvent(stage="input_received", status="complete", note="Content accepted and normalized."),
        TimelineEvent(stage="source_reputation", status="complete", note="Source and domain signals were scored."),
        TimelineEvent(stage="moderation", status="complete", note="Safety moderation gate was evaluated or safely skipped."),
        TimelineEvent(stage="local_baseline", status="complete", note="Local trust signals were calculated."),
        TimelineEvent(stage="openai_analysis", status=openai_status, note=openai_note),
        TimelineEvent(stage="score_reconciliation", status="complete", note="Weighted trust score was produced."),
    ]


def reconcile_scores(analysis: TrustAnalysis, baseline: TrustAnalysis, moderation: ModerationResult) -> TrustAnalysis:
    weighted = round(
        analysis.source_score * 0.25
        + analysis.evidence_quality * 0.25
        + (100 - analysis.manipulation_score) * 0.15
        + analysis.score_breakdown.language_patterns * 0.10
        + (100 - analysis.score_breakdown.context_risk) * 0.10
        + analysis.score_breakdown.visual_authenticity * 0.10
        + (100 - analysis.score_breakdown.viral_risk) * 0.05
    )
    if moderation.flagged:
        weighted -= 10
    if analysis.topic in {Topic.HEALTH, Topic.FINANCE} and analysis.evidence_quality < 45:
        weighted -= 12

    trust_score = clamp(round(weighted * 0.8 + baseline.trust_score * 0.2))
    risk_level = risk_from_score(trust_score)
    return analysis.model_copy(
        update={
            "trust_score": trust_score,
            "risk_level": risk_level,
            "misinformation_probability": clamp(100 - trust_score + analysis.manipulation_score // 6),
            "recommended_action": action_for(risk_level, analysis.topic),
        }
    )


def detect_topic(text: str) -> Topic:
    topic, score = max(
        ((topic, sum(1 for term in terms if term in text)) for topic, terms in TOPIC_TERMS.items()),
        key=lambda item: item[1],
    )
    return topic if score > 0 else Topic.OTHER


def manipulation_risk(text: str, original_text: str) -> int:
    score = sum(12 for term in URGENCY_TERMS if term in text)
    score += min(25, text.count("!") * 5)
    score += 15 if re.search(r"\b\d{2,3}%\b", text) else 0
    score += 10 if len(re.findall(r"\b[A-Z]{4,}\b", original_text)) >= 3 else 0
    return clamp(score)


def manipulation_patterns(text: str) -> list[str]:
    patterns: list[str] = []
    if any(term in text for term in ("urgent", "breaking", "do not ignore")):
        patterns.append("urgency_pressure")
    if "share" in text or "forward" in text:
        patterns.append("share_pressure")
    if any(term in text for term in ("guaranteed", "100% true", "miracle")):
        patterns.append("absolute_certainty")
    if any(term in text for term in ("secret", "they do not want you to know")):
        patterns.append("conspiracy_framing")
    if text.count("!") >= 3:
        patterns.append("excessive_punctuation")
    return patterns


def evidence_score(text: str, source_score: int) -> int:
    score = 35
    score += 20 if "http://" in text or "https://" in text else 0
    score += 15 if any(term in text for term in ("study", "report", "official", "source", "according to")) else 0
    score += 5 if re.search(r"\b(20\d{2}|19\d{2})\b", text) else 0
    score += 20 if source_score >= 75 else 0
    score -= 15 if source_score <= 35 else 0
    return clamp(score)


def context_score(topic: Topic) -> int:
    return {
        Topic.HEALTH: 75,
        Topic.FINANCE: 72,
        Topic.POLITICS: 70,
        Topic.PUBLIC_SAFETY: 68,
        Topic.INTERNATIONAL: 55,
        Topic.EDUCATION: 45,
        Topic.OTHER: 35,
    }[topic]


def viral_score(text: str) -> int:
    score = 25 if "share" in text or "forward" in text else 0
    score += 20 if "breaking" in text or "urgent" in text else 0
    score += 15 if len(text) < 280 else 0
    score += min(25, text.count("!") * 5)
    return clamp(score)


def ai_generated_score(text: str, original_text: str) -> int:
    score = 8
    if "as an ai language model" in text:
        score += 60
    if len(re.findall(r"\b(furthermore|moreover|in conclusion|it is important to note)\b", text)) >= 2:
        score += 18
    if len(original_text) > 700 and original_text.count("\n") <= 1:
        score += 10
    if re.search(r"\b\d+\.\s+\w+", original_text) and len(re.findall(r"\b(firstly|secondly|thirdly)\b", text)) >= 1:
        score += 8
    return clamp(score)


def claim_checks_for(text: str, evidence_quality: int, source_score: int) -> list[ClaimCheck]:
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if len(sentence.strip()) >= 24
    ]
    ranked = sorted(sentences, key=lambda item: claim_weight(item), reverse=True)[:4]

    if not ranked:
        ranked = [text[:180].strip()] if text.strip() else ["No explicit claim found."]

    checks: list[ClaimCheck] = []
    for sentence in ranked:
        verdict = ClaimVerdict.UNCERTAIN
        missing = "More independent source evidence is needed."
        confidence = 0.45

        if evidence_quality >= 75 and source_score >= 70:
            verdict = ClaimVerdict.SUPPORTED
            missing = "No major missing evidence detected from local signals."
            confidence = 0.66
        elif evidence_quality < 45:
            verdict = ClaimVerdict.NEEDS_EXTERNAL_VERIFICATION
            confidence = 0.58

        checks.append(
            ClaimCheck(
                claim=sentence[:260],
                verdict=verdict,
                confidence=confidence,
                evidence=f"Local evidence quality={evidence_quality}/100; source score={source_score}/100.",
                missing_evidence=missing,
            )
        )
    return checks


def claim_weight(sentence: str) -> int:
    lowered = sentence.lower()
    score = 0
    score += 8 if re.search(r"\b(19\d{2}|20\d{2}|\d+%)\b", lowered) else 0
    score += 6 if any(term in lowered for term in ("said", "announced", "confirmed", "according to", "report")) else 0
    score += 5 if any(term in lowered for term in ("will", "must", "never", "always", "guaranteed")) else 0
    score += min(5, len(sentence) // 60)
    return score


def risk_factors_for(
    source_score: int,
    evidence_quality: int,
    manipulation_score: int,
    context_risk: int,
    viral_risk: int,
    ai_likelihood: int,
    visual_risk: int,
) -> list[RiskFactor]:
    factors = [
        RiskFactor(
            label="source_credibility",
            score=source_score,
            impact=RiskLevel.HIGH if source_score < 40 else RiskLevel.MEDIUM if source_score < 65 else RiskLevel.LOW,
            explanation="Measures whether the source is known, unknown, or uses risky naming patterns.",
        ),
        RiskFactor(
            label="evidence_consistency",
            score=evidence_quality,
            impact=RiskLevel.HIGH if evidence_quality < 45 else RiskLevel.MEDIUM if evidence_quality < 70 else RiskLevel.LOW,
            explanation="Measures the presence of citations, dates, official references, and source specificity.",
        ),
        RiskFactor(
            label="emotional_manipulation",
            score=manipulation_score,
            impact=RiskLevel.HIGH if manipulation_score > 60 else RiskLevel.MEDIUM if manipulation_score > 25 else RiskLevel.LOW,
            explanation="Detects urgency, certainty, pressure to share, and sensational wording.",
        ),
        RiskFactor(
            label="context_sensitivity",
            score=context_risk,
            impact=RiskLevel.HIGH if context_risk > 65 else RiskLevel.MEDIUM if context_risk > 45 else RiskLevel.LOW,
            explanation="Raises caution for health, finance, politics, and public safety claims.",
        ),
        RiskFactor(
            label="viral_risk",
            score=viral_risk,
            impact=RiskLevel.HIGH if viral_risk > 60 else RiskLevel.MEDIUM if viral_risk > 30 else RiskLevel.LOW,
            explanation="Estimates whether the wording is optimized for fast sharing.",
        ),
        RiskFactor(
            label="ai_generated_likelihood",
            score=ai_likelihood,
            impact=RiskLevel.MEDIUM if ai_likelihood > 45 else RiskLevel.LOW,
            explanation="Flags generic AI-writing patterns without treating them as proof of misinformation.",
        ),
    ]
    if visual_risk:
        factors.append(
            RiskFactor(
                label="visual_authenticity",
                score=visual_risk,
                impact=RiskLevel.MEDIUM,
                explanation="Image or screenshot content needs dedicated visual/OCR verification.",
            )
        )
    return factors


def regional_context_for(region: str, topic: Topic, context_risk: int) -> RegionalContext:
    if region.upper() == "BD":
        note = "Bangladesh context is applied with extra caution for Bangla/Banglish, public safety, politics, education, and finance claims."
    else:
        note = "Regional context is applied from the submitted locale and topic sensitivity."
    return RegionalContext(region=region, sensitivity=context_risk, note=note)


def expert_notes_for(topic: Topic, risk: RiskLevel, evidence_quality: int) -> list[str]:
    notes: list[str] = []
    if topic in {Topic.HEALTH, Topic.FINANCE} and evidence_quality < 60:
        notes.append("Use expert or official-source review before acting on this claim.")
    if risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        notes.append("Avoid resharing until at least one independent credible source confirms the claim.")
    if topic == Topic.POLITICS:
        notes.append("Check publication time, original source, and whether the quote/image has been reused out of context.")
    return notes or ["No expert escalation note was triggered by the local baseline."]


def dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item not in seen:
            output.append(item)
            seen.add(item)
    return output


def offline_explanation(analysis: AnalysisResponse, question: str) -> str:
    lowered = question.lower()
    if "why" in lowered or "score" in lowered:
        return (
            f"The score is {analysis.trust_score}/100 because source credibility is "
            f"{analysis.source_score}/100, evidence quality is {analysis.evidence_quality}/100, "
            f"and manipulation intensity is {analysis.manipulation_score}/100. "
            f"The recommended action is {analysis.recommended_action.value}."
        )
    if "claim" in lowered:
        first_claim = analysis.claim_checks[0] if analysis.claim_checks else None
        if first_claim:
            return (
                f"The strongest extracted claim is: \"{first_claim.claim}\". "
                f"I marked it {first_claim.verdict.value} with confidence {first_claim.confidence:.2f}. "
                f"Missing evidence: {first_claim.missing_evidence}"
            )
    if "source" in lowered:
        return (
            f"The source score is {analysis.source_score}/100. "
            f"Source notes: {analysis.raw_signals.get('source_notes', 'No source notes available')}."
        )
    return (
        f"This report is {analysis.risk_level.value} risk. "
        f"Main uncertainty: {analysis.uncertainty} "
        f"Best next step: {analysis.recommended_action.value}."
    )


def safe_error(exc: Exception) -> str:
    message = str(exc).replace("\n", " ").strip()
    if not message:
        return "No error message was returned."
    redacted = re.sub(r"sk-[A-Za-z0-9_\-]+", "sk-...redacted", message)
    return redacted[:240]


def risk_from_score(score: int) -> RiskLevel:
    if score >= 80:
        return RiskLevel.LOW
    if score >= 60:
        return RiskLevel.MEDIUM
    if score >= 35:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def action_for(risk: RiskLevel, topic: Topic) -> RecommendedAction:
    if risk in {RiskLevel.CRITICAL, RiskLevel.HIGH} and topic in {Topic.HEALTH, Topic.FINANCE}:
        return RecommendedAction.SEEK_EXPERT_REVIEW
    if risk in {RiskLevel.CRITICAL, RiskLevel.HIGH}:
        return RecommendedAction.DO_NOT_SHARE
    if risk == RiskLevel.MEDIUM:
        return RecommendedAction.VERIFY_BEFORE_SHARING
    return RecommendedAction.SAFE_TO_SHARE


def clamp(value: int) -> int:
    return max(0, min(100, value))

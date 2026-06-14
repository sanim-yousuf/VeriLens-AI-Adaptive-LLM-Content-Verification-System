from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InputType(str, Enum):
    TEXT = "text"
    URL = "url"
    IMAGE = "image"
    SCREENSHOT = "screenshot"


class AnalysisMode(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"
    OFFLINE = "offline"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Topic(str, Enum):
    POLITICS = "politics"
    EDUCATION = "education"
    HEALTH = "health"
    FINANCE = "finance"
    INTERNATIONAL = "international"
    PUBLIC_SAFETY = "public_safety"
    OTHER = "other"


class LanguageCode(str, Enum):
    BN = "bn"
    EN = "en"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class RecommendedAction(str, Enum):
    SAFE_TO_SHARE = "safe_to_share"
    VERIFY_BEFORE_SHARING = "verify_before_sharing"
    DO_NOT_SHARE = "do_not_share"
    SEEK_EXPERT_REVIEW = "seek_expert_review"


class ClaimVerdict(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNCERTAIN = "uncertain"
    NEEDS_EXTERNAL_VERIFICATION = "needs_external_verification"


class UserContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region: str = "BD"
    audience: str = "general"
    notes: str | None = None


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    input_type: InputType = Field(default=InputType.TEXT, alias="type")
    content: str = Field(..., min_length=1, max_length=120000)
    analysis_mode: AnalysisMode = AnalysisMode.STANDARD
    source_url: str | None = None
    locale: str = "bn-BD"
    user_context: UserContext = Field(default_factory=UserContext)


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    evidence: str
    signal_type: str
    confidence: float = Field(ge=0, le=1)


class HighlightSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    type: str
    severity: RiskLevel = RiskLevel.MEDIUM


class ScoreBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_credibility: int = Field(ge=0, le=100)
    evidence_consistency: int = Field(ge=0, le=100)
    manipulation_intensity: int = Field(ge=0, le=100)
    language_patterns: int = Field(ge=0, le=100)
    context_risk: int = Field(ge=0, le=100)
    visual_authenticity: int = Field(ge=0, le=100)
    viral_risk: int = Field(ge=0, le=100)


class AgentFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: str
    score: int = Field(ge=0, le=100)
    summary: str
    evidence: list[EvidenceItem] = Field(default_factory=list)


class VisualAuthenticity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deepfake_risk: int = Field(ge=0, le=100)
    tampering_risk: int = Field(ge=0, le=100)
    notes: str


class RiskFactor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    score: int = Field(ge=0, le=100)
    impact: RiskLevel
    explanation: str


class ClaimCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str
    verdict: ClaimVerdict
    confidence: float = Field(ge=0, le=1)
    evidence: str
    missing_evidence: str


class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    status: str
    note: str


class RegionalContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region: str
    sensitivity: int = Field(ge=0, le=100)
    note: str


class CommunitySignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_count: int = Field(ge=0)
    consensus: str
    note: str


class ModerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flagged: bool = False
    categories: list[str] = Field(default_factory=list)
    reason: str | None = None


class CostMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_used: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    analysis_mode: AnalysisMode
    cache_hit: bool = False
    openai_used: bool = False


class TrustAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: Topic
    language: LanguageCode
    trust_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    confidence: float = Field(ge=0, le=1)
    misinformation_probability: int = Field(ge=0, le=100)
    manipulation_score: int = Field(ge=0, le=100)
    source_score: int = Field(ge=0, le=100)
    evidence_quality: int = Field(ge=0, le=100)
    score_breakdown: ScoreBreakdown
    reasoning: list[EvidenceItem]
    highlight_spans: list[HighlightSpan]
    agent_findings: list[AgentFinding]
    visual_authenticity: VisualAuthenticity
    risk_factors: list[RiskFactor]
    claim_checks: list[ClaimCheck]
    manipulation_patterns: list[str]
    ai_generated_likelihood: int = Field(ge=0, le=100)
    viral_risk: int = Field(ge=0, le=100)
    regional_context: RegionalContext
    community_signal: CommunitySignal
    trust_timeline: list[TimelineEvent]
    expert_notes: list[str]
    recommended_action: RecommendedAction
    summary: str
    uncertainty: str


class AnalysisResponse(TrustAnalysis):
    analysis_id: str
    schema_version: str = "2026-05-26"
    input_type: InputType
    moderation: ModerationResult
    cost: CostMetadata
    source_url: str | None = None
    region: str = "BD"
    evidence_vs_inference: list[EvidenceItem] = Field(default_factory=list)
    raw_signals: dict[str, Any] = Field(default_factory=dict)


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    user_rating: int = Field(ge=1, le=5)
    corrected_risk_level: str | None = None
    notes: str | None = None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: bool
    message: str
    analysis_id: str
    report_count: int = 0
    consensus: str = "not_enough_reports"


class ExplainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=2, max_length=1200)


class ExplainResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    answer: str
    openai_used: bool = False
    model_used: str = "offline-explainer"

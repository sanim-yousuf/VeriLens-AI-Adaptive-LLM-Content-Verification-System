import time
from collections import Counter

from app.schemas import AnalysisResponse, CommunitySignal, FeedbackRequest


class AnalysisStore:
    def __init__(self, ttl_seconds: int = 86400) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, tuple[float, AnalysisResponse]] = {}
        self._feedback: dict[str, list[FeedbackRequest]] = {}

    def save(self, analysis: AnalysisResponse) -> AnalysisResponse:
        self._items[analysis.analysis_id] = (time.time(), analysis)
        self._purge_expired()
        return analysis

    def get(self, analysis_id: str) -> AnalysisResponse | None:
        item = self._items.get(analysis_id)
        if item is None:
            return None

        created_at, analysis = item
        if time.time() - created_at > self.ttl_seconds:
            self._items.pop(analysis_id, None)
            return None
        return analysis

    def get_by_cache_key(self, cache_key: str) -> AnalysisResponse | None:
        self._purge_expired()
        for _, analysis in self._items.values():
            if analysis.raw_signals.get("cache_key") == cache_key:
                return analysis
        return None

    def save_feedback(self, feedback: FeedbackRequest) -> CommunitySignal:
        self._feedback.setdefault(feedback.analysis_id, []).append(feedback)
        signal = self.community_signal(feedback.analysis_id)
        item = self._items.get(feedback.analysis_id)
        if item:
            created_at, analysis = item
            self._items[feedback.analysis_id] = (created_at, analysis.model_copy(update={"community_signal": signal}))
        return signal

    def community_signal(self, analysis_id: str) -> CommunitySignal:
        feedback_items = self._feedback.get(analysis_id, [])
        if not feedback_items:
            return CommunitySignal(
                report_count=0,
                consensus="not_enough_reports",
                note="Community verification is ready for feedback data but has no reports for this item yet.",
            )

        corrected = [item.corrected_risk_level for item in feedback_items if item.corrected_risk_level]
        consensus = Counter(corrected).most_common(1)[0][0] if corrected else "user_feedback_received"
        return CommunitySignal(
            report_count=len(feedback_items),
            consensus=consensus,
            note=f"{len(feedback_items)} community feedback item(s) have been recorded for this report.",
        )

    def _purge_expired(self) -> None:
        now = time.time()
        for analysis_id, (created_at, _) in list(self._items.items()):
            if now - created_at > self.ttl_seconds:
                self._items.pop(analysis_id, None)

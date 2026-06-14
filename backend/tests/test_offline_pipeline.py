import pytest

from app.pipeline import AnalysisService
from app.schemas import AnalysisMode, AnalysisRequest
from app.settings import Settings
from app.store import AnalysisStore


@pytest.mark.asyncio
async def test_offline_pipeline_scores_urgent_claim_as_risky() -> None:
    settings = Settings(OPENAI_API_KEY=None)
    service = AnalysisService(settings=settings, store=AnalysisStore())
    response = await service.analyze(
        AnalysisRequest(
            content="URGENT share now! Secret cure guaranteed 100% true. Forward this to everyone.",
            analysis_mode=AnalysisMode.OFFLINE,
        )
    )

    assert response.trust_score < 70
    assert response.manipulation_score > 20
    assert response.cost.openai_used is False


@pytest.mark.asyncio
async def test_cache_marks_repeat_analysis() -> None:
    settings = Settings(OPENAI_API_KEY=None)
    service = AnalysisService(settings=settings, store=AnalysisStore())
    payload = AnalysisRequest(content="According to an official report in 2025, school results were published.")

    first = await service.analyze(payload)
    second = await service.analyze(payload)

    assert first.analysis_id != second.analysis_id
    assert second.cost.cache_hit is True

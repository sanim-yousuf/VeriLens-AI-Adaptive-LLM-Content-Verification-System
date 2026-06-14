import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from app.pipeline import AnalysisService, RateLimiter
from app.schemas import (
    AnalysisMode,
    AnalysisRequest,
    AnalysisResponse,
    ExplainRequest,
    ExplainResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from app.settings import get_settings
from app.store import AnalysisStore


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    app = FastAPI(
        title="VeriLens AI",
        description="Explainable multilingual trust intelligence for digital content verification.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = AnalysisStore(ttl_seconds=settings.cache_ttl_seconds)
    service = AnalysisService(settings=settings, store=store)
    limiter = RateLimiter(settings.rate_limit_per_minute)

    @app.get("/health")
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "verilens-ai",
            "openai_configured": bool(settings.openai_api_key),
            "offline_mode_available": True,
            "default_model": settings.standard_model,
        }

    @app.post("/v1/analyses", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
    async def create_analysis(payload: AnalysisRequest, request: Request) -> AnalysisResponse:
        client_host = request.client.host if request.client else "unknown"
        if not limiter.allow(client_host):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait before running another analysis.",
            )
        try:
            return await service.analyze(payload)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.get("/v1/analyses/{analysis_id}", response_model=AnalysisResponse)
    async def get_analysis(analysis_id: str) -> AnalysisResponse:
        analysis = store.get(analysis_id)
        if analysis is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")
        return analysis

    @app.post("/v1/analyses/{analysis_id}/deep-review", response_model=AnalysisResponse)
    async def deep_review(analysis_id: str, payload: AnalysisRequest) -> AnalysisResponse:
        if store.get(analysis_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")
        return await service.analyze(payload.model_copy(update={"analysis_mode": AnalysisMode.DEEP}))

    @app.post("/v1/feedback", response_model=FeedbackResponse, status_code=status.HTTP_202_ACCEPTED)
    async def feedback(payload: FeedbackRequest) -> FeedbackResponse:
        signal = store.save_feedback(payload)
        return FeedbackResponse(
            accepted=True,
            message="Feedback received. It will be used for evaluation and calibration.",
            analysis_id=payload.analysis_id,
            report_count=signal.report_count,
            consensus=signal.consensus,
        )

    @app.post("/v1/analyses/{analysis_id}/explain", response_model=ExplainResponse)
    async def explain_report(analysis_id: str, payload: ExplainRequest) -> ExplainResponse:
        analysis = store.get(analysis_id)
        if analysis is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")
        return await service.explain(analysis, payload.question)

    return app


app = create_app()

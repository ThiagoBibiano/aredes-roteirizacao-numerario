from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from roteirizacao.api.schemas import (
    DatasetPlanningRunRequest,
    ErrorResponse,
    HealthResponse,
    InlinePlanningRunRequest,
    PlanningRunResponse,
    SnapshotMaterializeRequest,
    SnapshotMaterializeResponse,
)
from roteirizacao.api.service import ApiPlanningService, ApiSettings


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    resolved_settings = settings or ApiSettings.from_env()
    service = ApiPlanningService(resolved_settings)

    app = FastAPI(
        title="Roteirizacao Numerario API",
        version="0.1.0",
        description="Backend HTTP para o motor de planejamento de transporte de numerario.",
    )
    app.state.settings = resolved_settings
    app.state.service = service

    @app.exception_handler(FileNotFoundError)
    async def handle_not_found(_: Request, exc: FileNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(detail=str(exc), error_type="file_not_found").model_dump(),
        )

    @app.exception_handler(ValueError)
    async def handle_value_error(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(detail=str(exc), error_type="validation_error").model_dump(),
        )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", application="roteirizacao-numerario-api")

    @app.post(
        "/api/v1/snapshots/materialize",
        response_model=SnapshotMaterializeResponse,
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def materialize_snapshot(payload: SnapshotMaterializeRequest) -> SnapshotMaterializeResponse:
        response = service.materialize_snapshot(
            data_operacao=payload.data_operacao,
            source_dir=payload.source_dir,
            snapshot_dir=payload.snapshot_dir,
        )
        return SnapshotMaterializeResponse(**response)

    @app.post(
        "/api/v1/planning/run-dataset",
        response_model=PlanningRunResponse,
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def run_dataset(payload: DatasetPlanningRunRequest) -> PlanningRunResponse:
        response = service.run_dataset(**payload.model_dump())
        return PlanningRunResponse(**response)

    @app.post(
        "/api/v1/planning/run",
        response_model=PlanningRunResponse,
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def run_inline(payload: InlinePlanningRunRequest) -> PlanningRunResponse:
        response = service.run_inline(**payload.model_dump())
        return PlanningRunResponse(**response)

    return app


def run() -> None:
    import uvicorn

    settings = ApiSettings.from_env()
    uvicorn.run(
        "roteirizacao.api.main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )


if __name__ == "__main__":
    run()

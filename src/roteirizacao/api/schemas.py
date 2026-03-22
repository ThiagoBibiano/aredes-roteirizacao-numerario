from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    application: str


class SnapshotMaterializeRequest(BaseModel):
    data_operacao: str
    source_dir: str = "data/logistics_sources"
    snapshot_dir: str = "data/logistics_snapshots"


class SnapshotMaterializeResponse(BaseModel):
    data_operacao: str
    snapshot_id: str
    content_hash: str
    snapshot_path: str
    version_path: str
    manifest_path: str


class DatasetPlanningRunRequest(BaseModel):
    dataset_dir: str
    output_path: str | None = None
    snapshot_dir: str | None = None
    source_dir: str | None = None
    state_dir: str | None = None
    materialize_snapshot: bool = False
    max_iterations: int = 100
    seed: int = 1
    collect_stats: bool = False
    display: bool = False


class InlinePlanningRunRequest(BaseModel):
    contexto: dict[str, Any]
    bases: list[dict[str, Any]] = Field(default_factory=list)
    pontos: list[dict[str, Any]] = Field(default_factory=list)
    viaturas: list[dict[str, Any]] = Field(default_factory=list)
    ordens: list[dict[str, Any]] = Field(default_factory=list)
    snapshot_source: dict[str, Any] | None = None
    materialize_snapshot: bool = False
    max_iterations: int = 100
    seed: int = 1
    collect_stats: bool = False
    display: bool = False


class PlanningRunResponse(BaseModel):
    id_execucao: str
    hash_cenario: str
    status_final: str
    reused_cached_result: bool
    recovered_previous_context: bool
    attempt_number: int
    output_path: str
    result_path: str
    state_path: str
    scenario_path: str
    manifest_path: str
    snapshot_materialization: dict[str, Any] | None = None
    result: dict[str, Any]


class ErrorResponse(BaseModel):
    detail: str
    error_type: str

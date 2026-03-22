"""Casos de uso e pipeline da aplicacao."""

from roteirizacao.application.audit import AuditTrailResult, PlanningAuditTrailBuilder
from roteirizacao.application.instance_builder import InstanceBuildResult, OptimizationInstanceBuilder
from roteirizacao.application.logistics_matrix import LogisticsMatrixBuilder
from roteirizacao.application.logistics_provider import (
    FallbackLogisticsMatrixProvider,
    LogisticsMatrixProvider,
    PersistedSnapshotLogisticsMatrixProvider,
    SnapshotCoverageError,
    SnapshotUnavailableError,
)
from roteirizacao.application.orchestration import (
    DailyPlanningOrchestrator,
    DatasetPlanningRequest,
    FileSystemExecutionRepository,
    LoadedDatasetPayloads,
    OrchestrationResult,
    PlanningDatasetLoader,
)
from roteirizacao.application.planning import PlanningExecutor
from roteirizacao.application.post_processing import (
    ClassPostProcessingResult,
    PostProcessingResult,
    RoutePostProcessor,
    SolverExecutionArtifact,
)
from roteirizacao.application.preparation import PreparationPipeline, PreparationResult
from roteirizacao.application.reporting import PlanningReportingBuilder, ReportingResult
from roteirizacao.application.snapshot_materializer import (
    FileSystemSnapshotRepository,
    JsonFileLogisticsSnapshotSource,
    LogisticsSnapshotMaterializer,
    LogisticsSnapshotSource,
    SnapshotMaterializationResult,
)

__all__ = [
    "AuditTrailResult",
    "ClassPostProcessingResult",
    "DailyPlanningOrchestrator",
    "DatasetPlanningRequest",
    "FallbackLogisticsMatrixProvider",
    "FileSystemExecutionRepository",
    "FileSystemSnapshotRepository",
    "InstanceBuildResult",
    "JsonFileLogisticsSnapshotSource",
    "LoadedDatasetPayloads",
    "LogisticsMatrixBuilder",
    "LogisticsMatrixProvider",
    "LogisticsSnapshotMaterializer",
    "LogisticsSnapshotSource",
    "OptimizationInstanceBuilder",
    "OrchestrationResult",
    "PersistedSnapshotLogisticsMatrixProvider",
    "PlanningAuditTrailBuilder",
    "PlanningDatasetLoader",
    "PlanningExecutor",
    "PlanningReportingBuilder",
    "PostProcessingResult",
    "PreparationPipeline",
    "PreparationResult",
    "ReportingResult",
    "RoutePostProcessor",
    "SnapshotCoverageError",
    "SnapshotMaterializationResult",
    "SnapshotUnavailableError",
    "SolverExecutionArtifact",
]

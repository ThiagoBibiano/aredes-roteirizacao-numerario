"""Pacote principal do projeto de roteirizacao de numerario."""

from roteirizacao.application import (
    FallbackLogisticsMatrixProvider,
    FileSystemSnapshotRepository,
    InstanceBuildResult,
    JsonFileLogisticsSnapshotSource,
    LogisticsMatrixBuilder,
    LogisticsMatrixProvider,
    LogisticsSnapshotMaterializer,
    LogisticsSnapshotSource,
    OptimizationInstanceBuilder,
    PersistedSnapshotLogisticsMatrixProvider,
    PlanningExecutor,
    PreparationPipeline,
    PreparationResult,
    SnapshotCoverageError,
    SnapshotMaterializationResult,
    SnapshotUnavailableError,
)
from roteirizacao.optimization import PyVRPAdapter, SolverAdapter

__all__ = [
    "FallbackLogisticsMatrixProvider",
    "FileSystemSnapshotRepository",
    "InstanceBuildResult",
    "JsonFileLogisticsSnapshotSource",
    "LogisticsMatrixBuilder",
    "LogisticsMatrixProvider",
    "LogisticsSnapshotMaterializer",
    "LogisticsSnapshotSource",
    "OptimizationInstanceBuilder",
    "PersistedSnapshotLogisticsMatrixProvider",
    "PlanningExecutor",
    "PreparationPipeline",
    "PreparationResult",
    "PyVRPAdapter",
    "SnapshotCoverageError",
    "SnapshotMaterializationResult",
    "SnapshotUnavailableError",
    "SolverAdapter",
]

"""Pacote principal do projeto de roteirizacao de numerario."""

from roteirizacao.application import (
    FallbackLogisticsMatrixProvider,
    InstanceBuildResult,
    LogisticsMatrixBuilder,
    LogisticsMatrixProvider,
    OptimizationInstanceBuilder,
    PersistedSnapshotLogisticsMatrixProvider,
    PlanningExecutor,
    PreparationPipeline,
    PreparationResult,
    SnapshotCoverageError,
    SnapshotUnavailableError,
)
from roteirizacao.optimization import PyVRPAdapter, SolverAdapter

__all__ = [
    "FallbackLogisticsMatrixProvider",
    "InstanceBuildResult",
    "LogisticsMatrixBuilder",
    "LogisticsMatrixProvider",
    "OptimizationInstanceBuilder",
    "PersistedSnapshotLogisticsMatrixProvider",
    "PlanningExecutor",
    "PreparationPipeline",
    "PreparationResult",
    "PyVRPAdapter",
    "SnapshotCoverageError",
    "SnapshotUnavailableError",
    "SolverAdapter",
]

"""Casos de uso e pipeline da aplicacao."""

from roteirizacao.application.instance_builder import InstanceBuildResult, OptimizationInstanceBuilder
from roteirizacao.application.logistics_matrix import LogisticsMatrixBuilder
from roteirizacao.application.logistics_provider import (
    FallbackLogisticsMatrixProvider,
    LogisticsMatrixProvider,
    PersistedSnapshotLogisticsMatrixProvider,
    SnapshotCoverageError,
    SnapshotUnavailableError,
)
from roteirizacao.application.planning import PlanningExecutor
from roteirizacao.application.preparation import PreparationPipeline, PreparationResult

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
    "SnapshotCoverageError",
    "SnapshotUnavailableError",
]

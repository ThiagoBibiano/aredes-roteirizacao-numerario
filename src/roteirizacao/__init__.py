"""Pacote principal do projeto de roteirizacao de numerario."""

from roteirizacao.application import (
    InstanceBuildResult,
    LogisticsMatrixBuilder,
    OptimizationInstanceBuilder,
    PlanningExecutor,
    PreparationPipeline,
    PreparationResult,
)
from roteirizacao.optimization import PyVRPAdapter, SolverAdapter

__all__ = [
    "InstanceBuildResult",
    "LogisticsMatrixBuilder",
    "OptimizationInstanceBuilder",
    "PlanningExecutor",
    "PreparationPipeline",
    "PreparationResult",
    "PyVRPAdapter",
    "SolverAdapter",
]

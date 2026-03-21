"""Pacote principal do projeto de roteirizacao de numerario."""

from roteirizacao.application.instance_builder import InstanceBuildResult, OptimizationInstanceBuilder
from roteirizacao.application.preparation import PreparationPipeline, PreparationResult
from roteirizacao.optimization import PyVRPAdapter, SolverAdapter

__all__ = [
    "InstanceBuildResult",
    "OptimizationInstanceBuilder",
    "PreparationPipeline",
    "PreparationResult",
    "PyVRPAdapter",
    "SolverAdapter",
]

"""Adapters e contratos para integracao com solvers."""

from roteirizacao.optimization.pyvrp_adapter import (
    PyVRPAdapter,
    PyVRPClientData,
    PyVRPDepotData,
    PyVRPEdgeData,
    PyVRPModelPayload,
    PyVRPVehicleTypeData,
)
from roteirizacao.optimization.solver_adapter import SolverAdapter

__all__ = [
    "PyVRPAdapter",
    "PyVRPClientData",
    "PyVRPDepotData",
    "PyVRPEdgeData",
    "PyVRPModelPayload",
    "PyVRPVehicleTypeData",
    "SolverAdapter",
]

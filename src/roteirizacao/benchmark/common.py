from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from roteirizacao.domain.optimization import InstanciaRoteirizacaoBase


ZERO = Decimal("0")
TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")


@dataclass(slots=True, frozen=True)
class BenchmarkRoute:
    vehicle_id: str
    depot_id: str
    location_sequence: tuple[str, ...]
    visited_node_ids: tuple[str, ...]
    distance_total_m: int
    duration_total_s: int


@dataclass(slots=True, frozen=True)
class BenchmarkSolution:
    solver: str
    status: str
    runtime_s: float
    feasible: bool
    routes: tuple[BenchmarkRoute, ...]
    served_node_ids: tuple[str, ...]
    missing_node_ids: tuple[str, ...]
    best_bound: Decimal | None = None
    gap_pct: Decimal | None = None
    notes: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class BenchmarkResultRecord:
    scenario_id: str
    family: str
    layer: str
    seed: int
    n_orders: int
    n_vehicles: int
    solver: str
    classe_operacional: str
    status: str
    runtime_s: Decimal
    objective_common: Decimal
    service_rate: Decimal
    vehicles_used: int
    distance_total_m: int
    duration_total_s: int
    feasible: bool
    best_bound: Decimal | None = None
    gap_pct: Decimal | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "family": self.family,
            "layer": self.layer,
            "seed": self.seed,
            "n_orders": self.n_orders,
            "n_vehicles": self.n_vehicles,
            "solver": self.solver,
            "classe_operacional": self.classe_operacional,
            "status": self.status,
            "runtime_s": _format_decimal(self.runtime_s, FOUR_PLACES),
            "objective_common": _format_decimal(self.objective_common),
            "service_rate": _format_decimal(self.service_rate, FOUR_PLACES),
            "vehicles_used": self.vehicles_used,
            "distance_total_m": self.distance_total_m,
            "duration_total_s": self.duration_total_s,
            "feasible": self.feasible,
            "best_bound": None if self.best_bound is None else _format_decimal(self.best_bound),
            "gap_pct": None if self.gap_pct is None else _format_decimal(self.gap_pct, FOUR_PLACES),
            "notes": self.notes,
        }


def build_result_record(spec, instance: InstanciaRoteirizacaoBase, solution: BenchmarkSolution) -> BenchmarkResultRecord:
    penalty_by_node = {
        penalty.id_alvo: penalty.valor
        for penalty in instance.penalidades
        if penalty.tipo_penalidade == "nao_atendimento"
    }
    vehicle_by_id = {vehicle.id_veiculo: vehicle for vehicle in instance.veiculos}

    fixed_total = ZERO
    arc_cost_total = ZERO
    distance_total = 0
    duration_total = 0

    for route in solution.routes:
        vehicle = vehicle_by_id[route.vehicle_id]
        fixed_total += vehicle.custo_fixo
        distance_total += route.distance_total_m
        duration_total += route.duration_total_s
        for origin_id, destination_id in zip(route.location_sequence, route.location_sequence[1:]):
            trecho = instance.matriz_logistica.trecho(origin_id, destination_id)
            if trecho.custo is not None:
                arc_cost_total += trecho.custo

    miss_penalty_total = sum((penalty_by_node[node_id] for node_id in solution.missing_node_ids), start=ZERO)
    objective_common = (fixed_total + arc_cost_total + Decimal(duration_total) + miss_penalty_total).quantize(TWO_PLACES)
    total_nodes = len(instance.nos_atendimento)
    service_rate = (
        (Decimal(len(solution.served_node_ids)) / Decimal(total_nodes)).quantize(FOUR_PLACES)
        if total_nodes
        else ZERO
    )

    return BenchmarkResultRecord(
        scenario_id=spec.scenario_id,
        family=spec.family,
        layer=spec.layer,
        seed=spec.seed,
        n_orders=spec.n_orders,
        n_vehicles=spec.n_vehicles,
        solver=solution.solver,
        classe_operacional=spec.classe_operacional,
        status=solution.status,
        runtime_s=Decimal(str(solution.runtime_s)).quantize(FOUR_PLACES),
        objective_common=objective_common,
        service_rate=service_rate,
        vehicles_used=len(solution.routes),
        distance_total_m=distance_total,
        duration_total_s=duration_total,
        feasible=solution.feasible,
        best_bound=None if solution.best_bound is None else solution.best_bound.quantize(TWO_PLACES),
        gap_pct=None if solution.gap_pct is None else solution.gap_pct.quantize(FOUR_PLACES),
        notes=" | ".join(note for note in solution.notes if note),
    )


def _format_decimal(value: Decimal, quantizer: Decimal = TWO_PLACES) -> str:
    return str(value.quantize(quantizer))

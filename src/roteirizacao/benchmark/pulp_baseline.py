from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from time import perf_counter

from roteirizacao.benchmark.common import BenchmarkRoute, BenchmarkSolution
from roteirizacao.domain.optimization import InstanciaRoteirizacaoBase


@dataclass(slots=True, frozen=True)
class PuLPBaselineConfig:
    time_limit_seconds: int
    gap_pct_target: float = 0.01
    msg: bool = False


class PuLPBaselineSolver:
    def __init__(self, config: PuLPBaselineConfig) -> None:
        self.config = config

    def solve(self, instance: InstanciaRoteirizacaoBase) -> BenchmarkSolution:
        try:
            import pulp
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "pulp nao esta instalado no ambiente. Instale o extra de benchmark para executar o baseline."
            ) from exc

        start_clock = perf_counter()
        node_by_id = {node.id_no: node for node in instance.nos_atendimento}
        depot_by_vehicle = {vehicle.id_veiculo: f"dep-{vehicle.id_base_origem}" for vehicle in instance.veiculos}
        eligibility = {(item.id_veiculo, item.id_no): item.elegivel for item in instance.elegibilidade_veiculo_no}
        penalty_by_node = {
            penalty.id_alvo: penalty.valor
            for penalty in instance.penalidades
            if penalty.tipo_penalidade == "nao_atendimento"
        }

        problem = pulp.LpProblem(f"baseline_{instance.id_cenario}", pulp.LpMinimize)
        x: dict[tuple[str, str, str], pulp.LpVariable] = {}
        y: dict[tuple[str, str], pulp.LpVariable] = {}
        z: dict[str, pulp.LpVariable] = {}
        miss: dict[str, pulp.LpVariable] = {}
        service_time: dict[tuple[str, str], pulp.LpVariable] = {}
        cumulative: dict[tuple[str, str, str], pulp.LpVariable] = {}

        virtual_start = {}
        virtual_end = {}
        max_window = max(
            [
                *[vehicle.janela_operacao.fim for vehicle in instance.veiculos],
                *[node.janela_tempo.fim for node in instance.nos_atendimento],
            ]
        )
        min_window = min(
            [
                *[vehicle.janela_operacao.inicio for vehicle in instance.veiculos],
                *[node.janela_tempo.inicio for node in instance.nos_atendimento],
            ]
        )
        horizon_seconds = int((max_window - min_window).total_seconds()) + 86400

        for vehicle in instance.veiculos:
            vehicle_id = vehicle.id_veiculo
            z[vehicle_id] = pulp.LpVariable(f"z_{vehicle_id}", lowBound=0, upBound=1, cat="Binary")
            virtual_start[vehicle_id] = f"start::{vehicle_id}"
            virtual_end[vehicle_id] = f"end::{vehicle_id}"
            service_time[(vehicle_id, virtual_start[vehicle_id])] = pulp.LpVariable(
                f"t_{vehicle_id}_start",
                lowBound=0,
                upBound=horizon_seconds,
                cat="Continuous",
            )
            service_time[(vehicle_id, virtual_end[vehicle_id])] = pulp.LpVariable(
                f"t_{vehicle_id}_end",
                lowBound=0,
                upBound=horizon_seconds,
                cat="Continuous",
            )

            for node in instance.nos_atendimento:
                eligible = 1 if eligibility.get((vehicle_id, node.id_no), False) else 0
                y[(vehicle_id, node.id_no)] = pulp.LpVariable(
                    f"y_{vehicle_id}_{node.id_no}",
                    lowBound=0,
                    upBound=eligible,
                    cat="Binary",
                )
                service_time[(vehicle_id, node.id_no)] = pulp.LpVariable(
                    f"t_{vehicle_id}_{node.id_no}",
                    lowBound=0,
                    upBound=horizon_seconds,
                    cat="Continuous",
                )
                for dimension in instance.dimensoes_capacidade:
                    capacity = float(vehicle.capacidades[dimension])
                    cumulative[(vehicle_id, node.id_no, dimension)] = pulp.LpVariable(
                        f"load_{vehicle_id}_{node.id_no}_{dimension}",
                        lowBound=0,
                        upBound=capacity,
                        cat="Continuous",
                    )

        for node in instance.nos_atendimento:
            miss[node.id_no] = pulp.LpVariable(f"miss_{node.id_no}", lowBound=0, upBound=1, cat="Binary")

        for vehicle in instance.veiculos:
            vehicle_id = vehicle.id_veiculo
            start_node = virtual_start[vehicle_id]
            end_node = virtual_end[vehicle_id]
            depot_id = depot_by_vehicle[vehicle_id]

            for node in instance.nos_atendimento:
                if not eligibility.get((vehicle_id, node.id_no), False):
                    continue
                if instance.matriz_logistica.trecho(depot_id, node.id_no).disponivel:
                    x[(vehicle_id, start_node, node.id_no)] = pulp.LpVariable(
                        f"x_{vehicle_id}_start_{node.id_no}",
                        lowBound=0,
                        upBound=1,
                        cat="Binary",
                    )
                if instance.matriz_logistica.trecho(node.id_no, depot_id).disponivel:
                    x[(vehicle_id, node.id_no, end_node)] = pulp.LpVariable(
                        f"x_{vehicle_id}_{node.id_no}_end",
                        lowBound=0,
                        upBound=1,
                        cat="Binary",
                    )

            for origin in instance.nos_atendimento:
                if not eligibility.get((vehicle_id, origin.id_no), False):
                    continue
                for destination in instance.nos_atendimento:
                    if origin.id_no == destination.id_no:
                        continue
                    if not eligibility.get((vehicle_id, destination.id_no), False):
                        continue
                    trecho = instance.matriz_logistica.trecho(origin.id_no, destination.id_no)
                    if trecho.disponivel:
                        x[(vehicle_id, origin.id_no, destination.id_no)] = pulp.LpVariable(
                            f"x_{vehicle_id}_{origin.id_no}_{destination.id_no}",
                            lowBound=0,
                            upBound=1,
                            cat="Binary",
                        )

        objective_terms: list[object] = []
        for vehicle in instance.veiculos:
            objective_terms.append(float(vehicle.custo_fixo) * z[vehicle.id_veiculo])
        for (vehicle_id, origin_id, destination_id), variable in x.items():
            real_origin = depot_by_vehicle[vehicle_id] if origin_id.startswith("start::") else origin_id
            real_destination = depot_by_vehicle[vehicle_id] if destination_id.startswith("end::") else destination_id
            trecho = instance.matriz_logistica.trecho(real_origin, real_destination)
            objective_terms.append(float(trecho.custo or Decimal("0")) * variable)
            objective_terms.append(float(trecho.tempo_segundos or 0) * variable)
        for node_id, variable in miss.items():
            objective_terms.append(float(penalty_by_node[node_id]) * variable)
        problem += pulp.lpSum(objective_terms)

        for node in instance.nos_atendimento:
            problem += (
                pulp.lpSum(y[(vehicle.id_veiculo, node.id_no)] for vehicle in instance.veiculos) + miss[node.id_no] == 1
            ), f"serve_or_miss_{node.id_no}"

        for vehicle in instance.veiculos:
            vehicle_id = vehicle.id_veiculo
            start_node = virtual_start[vehicle_id]
            end_node = virtual_end[vehicle_id]
            start_edges = [x[key] for key in x if key[0] == vehicle_id and key[1] == start_node]
            end_edges = [x[key] for key in x if key[0] == vehicle_id and key[2] == end_node]
            problem += pulp.lpSum(start_edges) == z[vehicle_id], f"vehicle_start_{vehicle_id}"
            problem += pulp.lpSum(end_edges) == z[vehicle_id], f"vehicle_end_{vehicle_id}"

            open_seconds = int((vehicle.janela_operacao.inicio - min_window).total_seconds())
            close_seconds = int((vehicle.janela_operacao.fim - min_window).total_seconds())
            problem += service_time[(vehicle_id, start_node)] >= open_seconds * z[vehicle_id], f"start_open_{vehicle_id}"
            problem += service_time[(vehicle_id, start_node)] <= close_seconds, f"start_close_{vehicle_id}"
            problem += service_time[(vehicle_id, end_node)] <= close_seconds + horizon_seconds * (1 - z[vehicle_id]), f"end_close_{vehicle_id}"

            for node in instance.nos_atendimento:
                inbound = [x[key] for key in x if key[0] == vehicle_id and key[2] == node.id_no]
                outbound = [x[key] for key in x if key[0] == vehicle_id and key[1] == node.id_no]
                problem += pulp.lpSum(inbound) == y[(vehicle_id, node.id_no)], f"inbound_{vehicle_id}_{node.id_no}"
                problem += pulp.lpSum(outbound) == y[(vehicle_id, node.id_no)], f"outbound_{vehicle_id}_{node.id_no}"

                open_seconds = int((node.janela_tempo.inicio - min_window).total_seconds())
                close_seconds = int((node.janela_tempo.fim - min_window).total_seconds())
                problem += service_time[(vehicle_id, node.id_no)] >= open_seconds * y[(vehicle_id, node.id_no)], f"node_open_{vehicle_id}_{node.id_no}"
                problem += service_time[(vehicle_id, node.id_no)] <= close_seconds + horizon_seconds * (1 - y[(vehicle_id, node.id_no)]), f"node_close_{vehicle_id}_{node.id_no}"

                for dimension in instance.dimensoes_capacidade:
                    demand = float(node.demandas[dimension])
                    capacity = float(vehicle.capacidades[dimension])
                    load_var = cumulative[(vehicle_id, node.id_no, dimension)]
                    problem += load_var >= demand * y[(vehicle_id, node.id_no)], f"load_lb_{vehicle_id}_{node.id_no}_{dimension}"
                    problem += load_var <= capacity * y[(vehicle_id, node.id_no)], f"load_ub_{vehicle_id}_{node.id_no}_{dimension}"

            for (solver_vehicle_id, origin_id, destination_id), arc_var in x.items():
                if solver_vehicle_id != vehicle_id:
                    continue
                real_origin = depot_by_vehicle[vehicle_id] if origin_id.startswith("start::") else origin_id
                real_destination = depot_by_vehicle[vehicle_id] if destination_id.startswith("end::") else destination_id
                trecho = instance.matriz_logistica.trecho(real_origin, real_destination)
                travel_seconds = int(trecho.tempo_segundos or 0)
                service_origin = 0 if origin_id.startswith("start::") else instance.tempos_servico[origin_id] * 60
                problem += (
                    service_time[(vehicle_id, destination_id)] >= service_time[(vehicle_id, origin_id)] + service_origin + travel_seconds - horizon_seconds * (1 - arc_var)
                ), f"time_{vehicle_id}_{origin_id}_{destination_id}"

                if destination_id.startswith("end::"):
                    continue
                for dimension in instance.dimensoes_capacidade:
                    demand = float(node_by_id[destination_id].demandas[dimension])
                    capacity = float(vehicle.capacidades[dimension])
                    relax_capacity = capacity + demand
                    destination_load = cumulative[(vehicle_id, destination_id, dimension)]
                    if origin_id.startswith("start::"):
                        problem += destination_load >= demand - relax_capacity * (1 - arc_var), f"start_load_lb_{vehicle_id}_{destination_id}_{dimension}"
                        problem += destination_load <= demand + relax_capacity * (1 - arc_var), f"start_load_ub_{vehicle_id}_{destination_id}_{dimension}"
                    else:
                        origin_load = cumulative[(vehicle_id, origin_id, dimension)]
                        problem += destination_load >= origin_load + demand - relax_capacity * (1 - arc_var), f"flow_load_lb_{vehicle_id}_{origin_id}_{destination_id}_{dimension}"
                        problem += destination_load <= origin_load + demand + relax_capacity * (1 - arc_var), f"flow_load_ub_{vehicle_id}_{origin_id}_{destination_id}_{dimension}"

        solver = pulp.PULP_CBC_CMD(
            msg=self.config.msg,
            timeLimit=self.config.time_limit_seconds,
            gapRel=self.config.gap_pct_target,
        )
        problem.solve(solver)
        runtime_s = perf_counter() - start_clock

        solution_status = getattr(pulp, "LpStatus", {}).get(problem.status, str(problem.status))
        incumbent_exists = any(variable.varValue not in (None, 0) for variable in y.values())
        feasible = solution_status == "Optimal" or incumbent_exists

        routes: list[BenchmarkRoute] = []
        served_node_ids = sorted(
            node_id
            for (vehicle_id, node_id), variable in y.items()
            if variable.varValue is not None and variable.varValue > 0.5
        )
        missing_node_ids = sorted(node_id for node_id, variable in miss.items() if variable.varValue is not None and variable.varValue > 0.5)

        if feasible:
            for vehicle in instance.veiculos:
                vehicle_id = vehicle.id_veiculo
                if z[vehicle_id].varValue is None or z[vehicle_id].varValue < 0.5:
                    continue
                start_node = virtual_start[vehicle_id]
                end_node = virtual_end[vehicle_id]
                successors = {
                    origin_id: destination_id
                    for (solver_vehicle_id, origin_id, destination_id), variable in x.items()
                    if solver_vehicle_id == vehicle_id and variable.varValue is not None and variable.varValue > 0.5
                }
                sequence = [depot_by_vehicle[vehicle_id]]
                visited_node_ids: list[str] = []
                current = start_node
                while current in successors:
                    current = successors[current]
                    if current == end_node:
                        sequence.append(depot_by_vehicle[vehicle_id])
                        break
                    sequence.append(current)
                    visited_node_ids.append(current)
                distance_total = 0
                duration_total = 0
                for origin_id, destination_id in zip(sequence, sequence[1:]):
                    trecho = instance.matriz_logistica.trecho(origin_id, destination_id)
                    distance_total += int(trecho.distancia_metros or 0)
                    duration_total += int(trecho.tempo_segundos or 0)
                routes.append(
                    BenchmarkRoute(
                        vehicle_id=vehicle_id,
                        depot_id=vehicle.id_base_origem,
                        location_sequence=tuple(sequence),
                        visited_node_ids=tuple(visited_node_ids),
                        distance_total_m=distance_total,
                        duration_total_s=duration_total,
                    )
                )

        return BenchmarkSolution(
            solver="pulp",
            status=solution_status,
            runtime_s=runtime_s,
            feasible=feasible,
            routes=tuple(routes),
            served_node_ids=tuple(served_node_ids),
            missing_node_ids=tuple(missing_node_ids),
            best_bound=None,
            gap_pct=None,
            notes=(f"time_limit_s={self.config.time_limit_seconds}",),
            metadata={"model_name": problem.name},
        )

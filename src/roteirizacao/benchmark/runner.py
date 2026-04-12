from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

from roteirizacao.application.instance_builder import OptimizationInstanceBuilder
from roteirizacao.application.orchestration import PlanningDatasetLoader
from roteirizacao.application.preparation import PreparationPipeline
from roteirizacao.benchmark.common import BenchmarkResultRecord, BenchmarkRoute, BenchmarkSolution, build_result_record
from roteirizacao.benchmark.pulp_baseline import PuLPBaselineConfig, PuLPBaselineSolver
from roteirizacao.benchmark.scenario_catalog import DEFAULT_SCENARIO_CATALOG_PATH, load_scenario_catalog
from roteirizacao.benchmark.scenario_generator import materialize_scenarios_from_catalog
from roteirizacao.domain import BaseBruta, OrdemBruta, PontoBruto, ViaturaBruta
from roteirizacao.domain.enums import ClasseOperacional
from roteirizacao.optimization.pyvrp_adapter import PyVRPAdapter


PROJECT_ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")
DEFAULT_BENCHMARK_OUTPUT_DIR = Path("data/benchmarks")
PULP_TIME_LIMIT_BY_LAYER = {
    "didatica": 120,
    "benchmark": 300,
    "estresse": 600,
}
PYVRP_ITERATIONS_BY_LAYER = {
    "didatica": 50,
    "benchmark": 100,
    "estresse": 150,
}


@dataclass(slots=True, frozen=True)
class BenchmarkExecutionArtifacts:
    results_path: Path
    summary_path: Path
    plots_dir: Path
    records: tuple[BenchmarkResultRecord, ...]


class PyVRPBenchmarkSolver:
    def __init__(self, *, max_iterations: int, seed: int, collect_stats: bool = False, display: bool = False) -> None:
        self.max_iterations = max_iterations
        self.seed = seed
        self.collect_stats = collect_stats
        self.display = display
        self.adapter = PyVRPAdapter()

    def solve(self, instance) -> BenchmarkSolution:
        import pyvrp

        model = self.adapter.build_model(instance)
        payload = self.adapter.build_payload(instance)
        start_clock = perf_counter()
        solver_result = model.solve(
            pyvrp.stop.MaxIterations(self.max_iterations),
            seed=self.seed,
            collect_stats=self.collect_stats,
            display=self.display,
        )
        runtime_s = perf_counter() - start_clock
        solution = solver_result.best
        location_ids = [depot.name for depot in payload.depots] + [client.name for client in payload.clients]

        routes: list[BenchmarkRoute] = []
        served_node_ids: list[str] = []
        for route in solution.routes():
            depot_id = payload.depots[int(route.start_depot())].name
            visit_locations = [location_ids[int(location)] for location in route.visits()]
            served_node_ids.extend(visit_locations)
            sequence = [depot_id, *visit_locations, payload.depots[int(route.end_depot())].name]
            distance_total = 0
            duration_total = 0
            for origin_id, destination_id in zip(sequence, sequence[1:]):
                trecho = instance.matriz_logistica.trecho(origin_id, destination_id)
                distance_total += int(trecho.distancia_metros or 0)
                duration_total += int(trecho.tempo_segundos or 0)
            routes.append(
                BenchmarkRoute(
                    vehicle_id=instance.veiculos[int(route.vehicle_type())].id_veiculo,
                    depot_id=depot_id.replace("dep-", ""),
                    location_sequence=tuple(sequence),
                    visited_node_ids=tuple(visit_locations),
                    distance_total_m=distance_total,
                    duration_total_s=duration_total,
                )
            )

        served = tuple(sorted(set(served_node_ids)))
        missing = tuple(sorted(node.id_no for node in instance.nos_atendimento if node.id_no not in served))
        notes = (
            f"internal_cost={solver_result.cost()}",
            f"num_routes={solution.num_routes()}",
            f"num_missing_clients={solution.num_missing_clients()}",
        )
        return BenchmarkSolution(
            solver="pyvrp",
            status="feasible" if solver_result.is_feasible() else "infeasible",
            runtime_s=runtime_s,
            feasible=bool(solver_result.is_feasible()),
            routes=tuple(routes),
            served_node_ids=served,
            missing_node_ids=missing,
            best_bound=None,
            gap_pct=None,
            notes=notes,
            metadata={"summary": solver_result.summary()},
        )


class BenchmarkRunner:
    def __init__(
        self,
        *,
        catalog_path: Path | str = DEFAULT_SCENARIO_CATALOG_PATH,
        output_dir: Path | str = DEFAULT_BENCHMARK_OUTPUT_DIR,
    ) -> None:
        self.catalog_path = Path(catalog_path)
        if not self.catalog_path.is_absolute():
            self.catalog_path = PROJECT_ROOT / self.catalog_path

        self.output_dir = Path(output_dir)
        if not self.output_dir.is_absolute():
            self.output_dir = PROJECT_ROOT / self.output_dir

    def run(
        self,
        *,
        scenario_ids: set[str] | None = None,
        overwrite_scenarios: bool = False,
    ) -> BenchmarkExecutionArtifacts:
        specs = [spec for spec in load_scenario_catalog(self.catalog_path) if scenario_ids is None or spec.scenario_id in scenario_ids]
        materialize_scenarios_from_catalog(catalog_path=self.catalog_path, scenario_ids=scenario_ids, overwrite=overwrite_scenarios)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        records: list[BenchmarkResultRecord] = []

        for spec in specs:
            instances = load_instances_from_dataset(spec.dataset_dir)
            instance = instances[ClasseOperacional(spec.classe_operacional)]

            pyvrp_solver = PyVRPBenchmarkSolver(
                max_iterations=PYVRP_ITERATIONS_BY_LAYER[spec.layer],
                seed=spec.seed,
            )
            pyvrp_solution = pyvrp_solver.solve(instance)
            records.append(build_result_record(spec, instance, pyvrp_solution))

            pulp_solver = PuLPBaselineSolver(
                PuLPBaselineConfig(
                    time_limit_seconds=PULP_TIME_LIMIT_BY_LAYER[spec.layer],
                    gap_pct_target=0.01,
                    msg=False,
                )
            )
            pulp_solution = pulp_solver.solve(instance)
            records.append(build_result_record(spec, instance, pulp_solution))

        results_path = self.output_dir / "results.csv"
        self._write_results_csv(results_path, records)

        plots_dir = self.output_dir / "plots"
        plots_dir.mkdir(parents=True, exist_ok=True)
        self._write_plots(plots_dir, records)

        summary_path = self.output_dir / "summary.json"
        summary_payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "catalog_path": str(self.catalog_path),
            "records": [record.to_dict() for record in records],
            "aggregates": self._aggregate(records),
        }
        summary_path.write_text(json.dumps(summary_payload, indent=2, ensure_ascii=False) + "\n")
        return BenchmarkExecutionArtifacts(
            results_path=results_path,
            summary_path=summary_path,
            plots_dir=plots_dir,
            records=tuple(records),
        )

    def _write_results_csv(self, path: Path, records: list[BenchmarkResultRecord]) -> None:
        if not records:
            raise ValueError("benchmark sem registros")
        fieldnames = list(records[0].to_dict().keys())
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(record.to_dict())

    def _aggregate(self, records: list[BenchmarkResultRecord]) -> dict[str, Any]:
        aggregates: dict[str, dict[str, float]] = {}
        grouped: dict[tuple[str, int], list[BenchmarkResultRecord]] = defaultdict(list)
        for record in records:
            grouped[(record.solver, record.n_orders)].append(record)
        for (solver, key), rows in grouped.items():
            aggregates[f"{solver}:{key}"] = {
                "avg_runtime_s": mean(float(row.runtime_s) for row in rows),
                "avg_objective_common": mean(float(row.objective_common) for row in rows),
                "avg_service_rate": mean(float(row.service_rate) for row in rows),
            }
        return aggregates

    def _write_plots(self, plots_dir: Path, records: list[BenchmarkResultRecord]) -> None:
        import matplotlib.pyplot as plt

        for metric in ("runtime_s", "objective_common", "service_rate", "vehicles_used"):
            figure, axis = plt.subplots(figsize=(9, 5))
            by_solver: dict[str, list[tuple[int, float]]] = defaultdict(list)
            for record in records:
                value = getattr(record, metric)
                x_value = record.n_orders
                by_solver[record.solver].append((x_value, float(value)))
            for solver, pairs in sorted(by_solver.items()):
                pairs.sort(key=lambda item: item[0])
                axis.plot([item[0] for item in pairs], [item[1] for item in pairs], marker="o", label=solver)
            axis.set_xlabel("n_orders")
            axis.set_ylabel(metric)
            axis.set_title(f"{metric} x n_orders")
            axis.grid(alpha=0.2)
            axis.legend()
            figure.tight_layout()
            figure.savefig(plots_dir / f"{metric}_x_orders.png", dpi=160)
            plt.close(figure)

        figure, axis = plt.subplots(figsize=(9, 5))
        failures = defaultdict(list)
        for record in records:
            if record.solver != "pulp":
                continue
            failures[record.n_orders].append(0 if record.feasible else 1)
        x_values = sorted(failures)
        failure_rate = [mean(failures[x_value]) for x_value in x_values]
        axis.plot(x_values, failure_rate, marker="o", color="#bc3908")
        axis.set_xlabel("n_orders")
        axis.set_ylabel("failure_rate")
        axis.set_title("fronteira_timeout_ou_falha_pulp")
        axis.grid(alpha=0.2)
        figure.tight_layout()
        figure.savefig(plots_dir / "pulp_failure_frontier.png", dpi=160)
        plt.close(figure)

def load_instances_from_dataset(dataset_dir: Path | str) -> dict[ClasseOperacional, object]:
    loader = PlanningDatasetLoader()
    dataset_dir = Path(dataset_dir)
    if not dataset_dir.is_absolute():
        dataset_dir = PROJECT_ROOT / dataset_dir
    payloads = loader.load_payloads(dataset_dir)
    context = loader.load_context(payloads.contexto_payload)
    preparation = PreparationPipeline(context).run(
        bases_brutas=loader.load_raw_records(payloads.bases_payload, raw_cls=BaseBruta, default_origin="dataset:bases", id_field="id_base", contexto=context),
        pontos_brutos=loader.load_raw_records(payloads.pontos_payload, raw_cls=PontoBruto, default_origin="dataset:pontos", id_field="id_ponto", contexto=context),
        viaturas_brutas=loader.load_raw_records(payloads.viaturas_payload, raw_cls=ViaturaBruta, default_origin="dataset:viaturas", id_field="id_viatura", contexto=context),
        ordens_brutas=loader.load_raw_records(payloads.ordens_payload, raw_cls=OrdemBruta, default_origin="dataset:ordens", id_field="id_ordem", contexto=context),
    )
    return OptimizationInstanceBuilder(context).build(preparation).instancias

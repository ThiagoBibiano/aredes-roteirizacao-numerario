from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from random import Random
from statistics import mean, median, stdev
from types import SimpleNamespace
from typing import Any

from roteirizacao.benchmark.common import BenchmarkResultRecord, BenchmarkRoute, BenchmarkSolution, build_result_record
from roteirizacao.benchmark.pulp_baseline import PuLPBaselineConfig, PuLPBaselineSolver
from roteirizacao.benchmark.runner import PyVRPBenchmarkSolver, load_instances_from_dataset
from roteirizacao.domain.enums import ClasseOperacional

from solver_workbench_support import (
    _maybe_add_basemap,
    _require_network_stack,
    _service_style,
    _set_axis_extent,
    compile_scenario,
    load_scenario_artifacts,
    resolve_dataset_dir,
    scenario_public_label,
)


PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists())
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")

DEFAULT_BASE_SCENARIO = "operacao_sob_pressao"
DEFAULT_ORDER_SHARES = (0.20, 0.40, 0.60, 0.80)
DEFAULT_REPETITIONS = 5
DEFAULT_BASE_SEED = 20260411
DEFAULT_PYVRP_MAX_ITERATIONS = 100
DEFAULT_PULP_TIME_LIMIT_SECONDS = 60
DEFAULT_FULL_RUN_PULP_TIME_LIMIT_SECONDS = 300
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "operacao_sob_pressao_subsample"

SOLVER_ORDER = ("pyvrp", "pulp")
SOLVER_LABELS = {
    "pyvrp": "PyVRP",
    "pulp": "PuLP",
}
SOLVER_COLORS = {
    "pyvrp": "#2563eb",
    "pulp": "#f97316",
}
SOLVER_OFFSETS = {
    "pyvrp": -2.4,
    "pulp": 2.4,
}

METRIC_SPECS = (
    {
        "key": "runtime_s",
        "label": "Tempo de solucao (s)",
        "title": "Tempo de solucao por percentual de ordens",
        "summary_key": "runtime_s",
        "transform": lambda value: value,
        "ylim": None,
    },
    {
        "key": "objective_common",
        "label": "Funcao objetivo comum",
        "title": "Funcao objetivo comum por percentual de ordens",
        "summary_key": "objective_common",
        "transform": lambda value: value,
        "ylim": None,
    },
    {
        "key": "service_rate",
        "label": "Taxa de atendimento (%)",
        "title": "Taxa de atendimento por percentual de ordens",
        "summary_key": "service_rate",
        "transform": lambda value: value * 100.0,
        "ylim": (0, 105),
    },
    {
        "key": "vehicles_used",
        "label": "Viaturas acionadas",
        "title": "Uso de frota por percentual de ordens",
        "summary_key": "vehicles_used",
        "transform": lambda value: value,
        "ylim": None,
    },
)


@dataclass(slots=True, frozen=True)
class PressureSubsetBenchmarkArtifacts:
    output_dir: Path
    datasets_dir: Path
    results_path: Path
    summary_path: Path
    plots_dir: Path
    records: tuple[dict[str, Any], ...]
    full_run: dict[str, Any]


@dataclass(slots=True, frozen=True)
class _SolvedSubsetBundle:
    scenario_records: tuple[dict[str, Any], ...]
    class_records: tuple[dict[str, Any], ...]
    solutions_by_solver: dict[str, dict[str, BenchmarkSolution]] | None = None


def load_benchmark_summary(path: str | Path) -> dict[str, Any]:
    summary_path = Path(path)
    if not summary_path.is_absolute():
        summary_path = PROJECT_ROOT / summary_path
    return json.loads(summary_path.read_text())


def rows_to_markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_Nenhum dado disponivel._"

    headers = list(rows[0].keys())
    lines = [
        "| " + " | ".join(_markdown_escape(str(header)) for header in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append(
            "| " + " | ".join(_markdown_escape(_stringify_cell(row.get(header))) for header in headers) + " |"
        )
    return "\n".join(lines)


def run_randomized_pressure_benchmark(
    *,
    base_scenario: str = DEFAULT_BASE_SCENARIO,
    order_shares: tuple[float, ...] = DEFAULT_ORDER_SHARES,
    repetitions: int = DEFAULT_REPETITIONS,
    pyvrp_max_iterations: int = DEFAULT_PYVRP_MAX_ITERATIONS,
    pulp_time_limit_seconds: int = DEFAULT_PULP_TIME_LIMIT_SECONDS,
    full_run_pulp_time_limit_seconds: int = DEFAULT_FULL_RUN_PULP_TIME_LIMIT_SECONDS,
    base_seed: int = DEFAULT_BASE_SEED,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    overwrite_datasets: bool = True,
    with_basemap: bool = False,
) -> PressureSubsetBenchmarkArtifacts:
    output_path = Path(output_dir)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.mkdir(parents=True, exist_ok=True)

    datasets_dir = output_path / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)

    all_records: list[dict[str, Any]] = []
    all_class_records: list[dict[str, Any]] = []
    dataset_manifests: list[dict[str, Any]] = []

    for order_share in order_shares:
        for repetition in range(1, repetitions + 1):
            dataset_manifest = materialize_pressure_subset_dataset(
                base_scenario=base_scenario,
                order_share=order_share,
                repetition=repetition,
                base_seed=base_seed,
                output_root=datasets_dir,
                overwrite=overwrite_datasets,
            )
            dataset_manifests.append(dataset_manifest)
            solved_subset = _run_single_subset_benchmark(
                dataset_manifest=dataset_manifest,
                pyvrp_max_iterations=pyvrp_max_iterations,
                pulp_time_limit_seconds=pulp_time_limit_seconds,
            )
            all_records.extend(solved_subset.scenario_records)
            all_class_records.extend(solved_subset.class_records)

    results_path = output_path / "results.csv"
    _write_results_csv(results_path, all_records)

    full_run = _run_full_benchmark(
        base_scenario=base_scenario,
        datasets_dir=datasets_dir,
        pyvrp_max_iterations=pyvrp_max_iterations,
        pulp_time_limit_seconds=full_run_pulp_time_limit_seconds,
        base_seed=base_seed,
        overwrite_datasets=overwrite_datasets,
    )

    aggregates = aggregate_records(all_records)
    relative_error_records = compute_relative_objective_error_records(all_records)
    relative_error_aggregates = aggregate_relative_objective_errors(relative_error_records, records=all_records)

    plots_dir = output_path / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    plot_paths = _write_plots(
        plots_dir=plots_dir,
        records=all_records,
        aggregates=aggregates,
        relative_error_records=relative_error_records,
        full_run=full_run,
        with_basemap=with_basemap,
    )
    full_run["plots"] = {**full_run.get("plots", {}), **plot_paths.get("full_run", {})}

    summary_path = output_path / "summary.json"
    summary_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_scenario": base_scenario,
        "base_scenario_label": scenario_public_label(base_scenario),
        "order_shares": [int(round(item * 100)) for item in order_shares],
        "repetitions": repetitions,
        "pyvrp_max_iterations": pyvrp_max_iterations,
        "pulp_time_limit_seconds": pulp_time_limit_seconds,
        "full_run_pulp_time_limit_seconds": full_run_pulp_time_limit_seconds,
        "dataset_manifests": dataset_manifests,
        "records": all_records,
        "class_records": all_class_records,
        "aggregates": aggregates,
        "relative_objective_error_records": relative_error_records,
        "relative_objective_error_aggregates": relative_error_aggregates,
        "full_run": _serialize_full_run(full_run),
        "plot_paths": plot_paths.get("sample", {}),
    }
    summary_path.write_text(json.dumps(summary_payload, indent=2, ensure_ascii=False) + "\n")

    return PressureSubsetBenchmarkArtifacts(
        output_dir=output_path,
        datasets_dir=datasets_dir,
        results_path=results_path,
        summary_path=summary_path,
        plots_dir=plots_dir,
        records=tuple(all_records),
        full_run=full_run,
    )


def materialize_pressure_subset_dataset(
    *,
    base_scenario: str,
    order_share: float,
    repetition: int,
    base_seed: int,
    output_root: Path | str,
    overwrite: bool = True,
) -> dict[str, Any]:
    base_scenario_name, base_dataset_dir = resolve_dataset_dir(base_scenario)
    output_root = Path(output_root)
    if not output_root.is_absolute():
        output_root = PROJECT_ROOT / output_root

    payload = _load_dataset_payload(base_dataset_dir)
    share_pct = int(round(order_share * 100))
    sample_seed = base_seed + share_pct * 100 + repetition
    scenario_id = f"{base_scenario_name}_pct{share_pct:02d}_rep{repetition:02d}"
    dataset_dir = output_root / scenario_id
    dataset_dir.mkdir(parents=True, exist_ok=True)

    rng = Random(sample_seed)
    selected_orders, per_class_counts = _sample_orders(
        payload["ordens"],
        order_share=order_share,
        rng=rng,
    )

    contexto = dict(payload["contexto"])
    contexto["id_execucao"] = f"exec-{scenario_id}-{contexto['data_operacao']}"
    contexto["timestamp_referencia"] = datetime.now(timezone.utc).isoformat()

    _write_json(dataset_dir / "contexto.json", contexto)
    _write_json(dataset_dir / "bases.json", payload["bases"])
    _write_json(dataset_dir / "pontos.json", payload["pontos"])
    _write_json(dataset_dir / "viaturas.json", payload["viaturas"])
    _write_json(dataset_dir / "ordens.json", selected_orders)

    manifest = {
        "scenario_id": scenario_id,
        "base_scenario": base_scenario_name,
        "base_dataset_dir": str(base_dataset_dir),
        "dataset_dir": str(dataset_dir),
        "order_share_pct": share_pct,
        "repetition": repetition,
        "sample_seed": sample_seed,
        "n_orders": len(selected_orders),
        "n_vehicles": len(payload["viaturas"]),
        "per_class_counts": per_class_counts,
        "selected_order_ids": [str(item["id_ordem"]) for item in selected_orders],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(dataset_dir / "subset_manifest.json", manifest)

    if overwrite or not (dataset_dir / "logistics_sources" / f"{contexto['data_operacao']}.json").exists():
        compile_scenario(dataset_dir)

    return manifest


def aggregate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not records:
        return []

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[(str(record["solver"]), int(record["order_share_pct"]))].append(record)

    rows: list[dict[str, Any]] = []
    for share_pct in sorted({int(record["order_share_pct"]) for record in records}):
        for solver in SOLVER_ORDER:
            items = grouped.get((solver, share_pct), [])
            if not items:
                continue
            row = {
                "solver": solver,
                "solver_label": SOLVER_LABELS.get(solver, solver),
                "order_share_pct": share_pct,
                "order_share_label": _share_label(share_pct),
                "repetitions": len(items),
                "repetitions_feasible": sum(1 for item in items if bool(item["feasible"])),
                "mean_n_orders": _safe_mean(_as_float(item["n_orders"]) for item in items),
                "mean_runtime_s": _safe_mean(_as_float(item["runtime_s"]) for item in items),
                "std_runtime_s": _safe_stdev(_as_float(item["runtime_s"]) for item in items),
                "median_runtime_s": _safe_median(_as_float(item["runtime_s"]) for item in items),
                "min_runtime_s": min(_as_float(item["runtime_s"]) for item in items),
                "max_runtime_s": max(_as_float(item["runtime_s"]) for item in items),
                "mean_objective_common": _safe_mean(_as_float(item["objective_common"]) for item in items),
                "std_objective_common": _safe_stdev(_as_float(item["objective_common"]) for item in items),
                "median_objective_common": _safe_median(_as_float(item["objective_common"]) for item in items),
                "min_objective_common": min(_as_float(item["objective_common"]) for item in items),
                "max_objective_common": max(_as_float(item["objective_common"]) for item in items),
                "mean_service_rate": _safe_mean(_as_float(item["service_rate"]) for item in items),
                "std_service_rate": _safe_stdev(_as_float(item["service_rate"]) for item in items),
                "median_service_rate": _safe_median(_as_float(item["service_rate"]) for item in items),
                "min_service_rate": min(_as_float(item["service_rate"]) for item in items),
                "max_service_rate": max(_as_float(item["service_rate"]) for item in items),
                "mean_vehicles_used": _safe_mean(_as_float(item["vehicles_used"]) for item in items),
                "std_vehicles_used": _safe_stdev(_as_float(item["vehicles_used"]) for item in items),
                "median_vehicles_used": _safe_median(_as_float(item["vehicles_used"]) for item in items),
                "min_vehicles_used": min(_as_float(item["vehicles_used"]) for item in items),
                "max_vehicles_used": max(_as_float(item["vehicles_used"]) for item in items),
                "mean_distance_total_m": _safe_mean(_as_float(item["distance_total_m"]) for item in items),
                "std_distance_total_m": _safe_stdev(_as_float(item["distance_total_m"]) for item in items),
                "median_distance_total_m": _safe_median(_as_float(item["distance_total_m"]) for item in items),
                "mean_duration_total_s": _safe_mean(_as_float(item["duration_total_s"]) for item in items),
                "std_duration_total_s": _safe_stdev(_as_float(item["duration_total_s"]) for item in items),
                "median_duration_total_s": _safe_median(_as_float(item["duration_total_s"]) for item in items),
                "feasible_rate": _safe_mean(1.0 if item["feasible"] else 0.0 for item in items),
            }
            rows.append(row)
    return rows


def summarize_records(records_or_aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregates = _coerce_aggregates(records_or_aggregates)
    rows: list[dict[str, Any]] = []
    for item in aggregates:
        rows.append(
            {
                "Solver": item["solver_label"],
                "Escala": item["order_share_label"],
                "Repeticoes": item["repetitions"],
                "Tempo medio (s)": _fmt(item["mean_runtime_s"], 4),
                "DP tempo (s)": _fmt(item["std_runtime_s"], 4),
                "FO media": _fmt(item["mean_objective_common"], 2),
                "DP FO": _fmt(item["std_objective_common"], 2),
                "Atendimento medio (%)": _fmt(item["mean_service_rate"] * 100.0, 2),
                "Viaturas medias": _fmt(item["mean_vehicles_used"], 2),
                "Viabilidade (%)": _fmt(item["feasible_rate"] * 100.0, 1),
            }
        )
    return rows


def compute_relative_objective_error_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not records:
        return []

    grouped: dict[tuple[int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for record in records:
        grouped[(int(record["order_share_pct"]), int(record["repetition"]))][str(record["solver"])] = record

    rows: list[dict[str, Any]] = []
    for (share_pct, repetition), record_map in sorted(grouped.items()):
        pulp_record = record_map.get("pulp")
        reference_available = pulp_record is not None and bool(pulp_record.get("feasible"))
        reference_objective = _as_float(pulp_record["objective_common"]) if reference_available and pulp_record is not None else None

        for solver in SOLVER_ORDER:
            solver_record = record_map.get(solver)
            if solver_record is None:
                continue
            objective_value = _as_float(solver_record["objective_common"])
            relative_error_pct = None
            if reference_available and reference_objective is not None and reference_objective > 0:
                if solver == "pulp":
                    relative_error_pct = 0.0
                else:
                    relative_error_pct = max(0.0, ((objective_value - reference_objective) / reference_objective) * 100.0)
            rows.append(
                {
                    "solver": solver,
                    "solver_label": SOLVER_LABELS.get(solver, solver),
                    "order_share_pct": share_pct,
                    "order_share_label": _share_label(share_pct),
                    "repetition": repetition,
                    "reference_available": reference_available,
                    "reference_solver": "pulp" if reference_available else None,
                    "reference_objective_common": reference_objective,
                    "objective_common": objective_value,
                    "feasible": bool(solver_record.get("feasible")),
                    "relative_objective_error_pct": relative_error_pct,
                }
            )
    return rows


def aggregate_relative_objective_errors(
    relative_error_records: list[dict[str, Any]],
    *,
    records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    shares = sorted({int(item["order_share_pct"]) for item in relative_error_records} or {int(item["order_share_pct"]) for item in records or []})
    repetitions_by_share: dict[int, int] = defaultdict(int)
    if records is not None:
        seen_repetitions: dict[int, set[int]] = defaultdict(set)
        for record in records:
            seen_repetitions[int(record["order_share_pct"])].add(int(record["repetition"]))
        repetitions_by_share = {share_pct: len(repetitions) for share_pct, repetitions in seen_repetitions.items()}

    rows: list[dict[str, Any]] = []
    for share_pct in shares:
        for solver in SOLVER_ORDER:
            items = [
                item
                for item in relative_error_records
                if int(item["order_share_pct"]) == share_pct and str(item["solver"]) == solver
            ]
            valid_items = [item for item in items if item["relative_objective_error_pct"] is not None]
            values = [float(item["relative_objective_error_pct"]) for item in valid_items]
            rows.append(
                {
                    "solver": solver,
                    "solver_label": SOLVER_LABELS.get(solver, solver),
                    "order_share_pct": share_pct,
                    "order_share_label": _share_label(share_pct),
                    "repetitions": repetitions_by_share.get(share_pct, len(items)),
                    "valid_reference_count": len(valid_items),
                    "mean_relative_objective_error_pct": None if not values else _safe_mean(values),
                    "median_relative_objective_error_pct": None if not values else _safe_median(values),
                    "max_relative_objective_error_pct": None if not values else max(values),
                }
            )
    return rows


def summarize_relative_objective_errors(relative_error_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregates = aggregate_relative_objective_errors(relative_error_records)
    rows: list[dict[str, Any]] = []
    for item in aggregates:
        if item["solver"] != "pyvrp":
            continue
        rows.append(
            {
                "Escala": item["order_share_label"],
                "Referencias PuLP validas": f"{item['valid_reference_count']}/{item['repetitions']}",
                "Erro relativo medio da FO (%)": _fmt_nullable(item["mean_relative_objective_error_pct"], 4),
                "Erro relativo mediano (%)": _fmt_nullable(item["median_relative_objective_error_pct"], 4),
                "Erro relativo maximo (%)": _fmt_nullable(item["max_relative_objective_error_pct"], 4),
            }
        )
    return rows


def summarize_pulp_viability(summary_or_aggregates: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(summary_or_aggregates, dict):
        aggregates = summary_or_aggregates.get("aggregates", [])
        relative_error_records = summary_or_aggregates.get("relative_objective_error_records", [])
    else:
        aggregates = _coerce_aggregates(summary_or_aggregates)
        relative_error_records = []

    reference_counts: dict[int, int] = defaultdict(int)
    repetitions: dict[int, int] = defaultdict(int)
    for item in relative_error_records:
        share_pct = int(item["order_share_pct"])
        if item["solver"] != "pyvrp":
            continue
        repetitions[share_pct] += 1
        if item["reference_available"]:
            reference_counts[share_pct] += 1

    rows: list[dict[str, Any]] = []
    for item in aggregates:
        if item["solver"] != "pulp":
            continue
        share_pct = int(item["order_share_pct"])
        rows.append(
            {
                "Escala": item["order_share_label"],
                "Repeticoes": item["repetitions"],
                "PuLP viavel": item["repetitions_feasible"],
                "Taxa de viabilidade do PuLP (%)": _fmt(item["feasible_rate"] * 100.0, 1),
                "Referencias validas para erro de FO": f"{reference_counts.get(share_pct, 0)}/{repetitions.get(share_pct, item['repetitions'])}",
            }
        )
    return rows


def summarize_full_run(full_run: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for solver in SOLVER_ORDER:
        solver_payload = full_run.get("solvers", {}).get(solver)
        if not solver_payload:
            continue
        record = solver_payload["scenario_record"]
        rows.append(
            {
                "Solver": SOLVER_LABELS.get(solver, solver),
                "Status": str(record["status"]),
                "FO": _fmt(_as_float(record["objective_common"]), 2),
                "Atendimento (%)": _fmt(_as_float(record["service_rate"]) * 100.0, 2),
                "Viaturas": int(record["vehicles_used"]),
                "Distancia total (km)": _fmt(_as_float(record["distance_total_m"]) / 1000.0, 2),
                "Duracao total (min)": _fmt(_as_float(record["duration_total_s"]) / 60.0, 1),
                "Escopo": "saldo agregado de duas execucoes isoladas por classe operacional",
            }
        )
    return rows


def summarize_full_run_by_class(full_run: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for solver in SOLVER_ORDER:
        solver_payload = full_run.get("solvers", {}).get(solver)
        if not solver_payload:
            continue
        class_records = {
            str(item["classe_operacional"]): item
            for item in solver_payload.get("class_records", [])
        }
        for classe_operacional in ("suprimento", "recolhimento"):
            record = class_records.get(classe_operacional)
            if not record:
                continue
            rows.append(
                {
                    "Solver": SOLVER_LABELS.get(solver, solver),
                    "Classe operacional": classe_operacional,
                    "Status": str(record["status"]),
                    "FO": _fmt(_as_float(record["objective_common"]), 2),
                    "Atendimento (%)": _fmt(_as_float(record["service_rate"]) * 100.0, 2),
                    "Viaturas": int(record["vehicles_used"]),
                    "Distancia total (km)": _fmt(_as_float(record["distance_total_m"]) / 1000.0, 2),
                    "Duracao total (min)": _fmt(_as_float(record["duration_total_s"]) / 60.0, 1),
                }
            )
    return rows


def full_run_route_sequences(
    full_run: dict[str, Any],
    *,
    solver: str,
    classe_operacional: str | None = None,
    include_return_to_base: bool = True,
) -> list[dict[str, Any]]:
    solver_payload = full_run.get("solvers", {}).get(solver)
    if not solver_payload or "solutions_by_class" not in solver_payload:
        return []

    dataset_dir = Path(str(full_run["manifest"]["dataset_dir"]))
    artifacts = load_scenario_artifacts(dataset_dir)

    rows: list[dict[str, Any]] = []
    requested_class = classe_operacional
    for class_name in sorted(solver_payload["solutions_by_class"]):
        if requested_class is not None and class_name != requested_class:
            continue
        solution = solver_payload["solutions_by_class"][class_name]
        for route_index, route in enumerate(solution.routes, start=1):
            sequence = list(route.location_sequence)
            if not include_return_to_base and len(sequence) >= 2:
                sequence = sequence[:-1]
            rows.append(
                {
                    "Classe operacional": class_name,
                    "Rota": f"R{route_index:02d}",
                    "Viatura": route.vehicle_id,
                    "Base": route.depot_id,
                    "Paradas": len(route.visited_node_ids),
                    "Sequencia": " -> ".join(_route_display_label(artifacts, node_id) for node_id in sequence),
                    "Leitura correta": "execucao isolada desta classe operacional",
                    "Distancia (km)": _fmt(route.distance_total_m / 1000.0, 2),
                    "Duracao (min)": _fmt(route.duration_total_s / 60.0, 1),
                }
            )
    return rows


def build_benchmark_takeaway(summary_or_records: dict[str, Any] | list[dict[str, Any]]) -> str:
    if isinstance(summary_or_records, dict):
        records = summary_or_records.get("records", [])
        relative_error_records = summary_or_records.get("relative_objective_error_records", [])
        full_run = summary_or_records.get("full_run")
    else:
        records = summary_or_records
        relative_error_records = compute_relative_objective_error_records(records)
        full_run = None

    aggregates = aggregate_records(records)
    if not aggregates:
        return "Nenhum registro de benchmark foi carregado."

    largest_share = max(int(item["order_share_pct"]) for item in aggregates)
    pyvrp_row = next(item for item in aggregates if item["solver"] == "pyvrp" and int(item["order_share_pct"]) == largest_share)
    pulp_row = next(item for item in aggregates if item["solver"] == "pulp" and int(item["order_share_pct"]) == largest_share)

    pyvrp_error_rows = [
        item
        for item in aggregate_relative_objective_errors(relative_error_records, records=records)
        if item["solver"] == "pyvrp" and int(item["order_share_pct"]) == largest_share
    ]
    error_line = ""
    if pyvrp_error_rows:
        error_row = pyvrp_error_rows[0]
        error_line = (
            f" Nas repeticoes com referencia valida do PuLP em {largest_share}% das ordens, "
            f"o erro relativo mediano da FO do PyVRP foi { _fmt_nullable(error_row['median_relative_objective_error_pct'], 4) }%."
        )

    full_run_line = ""
    if isinstance(full_run, dict) and full_run.get("solvers"):
        pyvrp_full = full_run["solvers"].get("pyvrp", {}).get("scenario_record")
        pulp_full = full_run["solvers"].get("pulp", {}).get("scenario_record")
        if pyvrp_full and pulp_full:
            full_run_line = (
                f" Na rodada exaustiva de 100% das ordens, o PyVRP fechou com status {pyvrp_full['status']} "
                f"e o PuLP com status {pulp_full['status']}."
            )

    return (
        "O benchmark amostral confirma o trade-off esperado entre controle de otimalidade e escalabilidade. "
        f"No recorte de {largest_share}% das ordens, o PyVRP teve tempo medio de {pyvrp_row['mean_runtime_s']:.4f}s, "
        f"enquanto o PuLP exigiu {pulp_row['mean_runtime_s']:.4f}s. "
        f"A taxa media de atendimento permaneceu em {pyvrp_row['mean_service_rate'] * 100.0:.2f}% para o PyVRP "
        f"e {pulp_row['mean_service_rate'] * 100.0:.2f}% para o PuLP."
        f"{error_line}{full_run_line}"
    )


def _run_single_subset_benchmark(
    *,
    dataset_manifest: dict[str, Any],
    pyvrp_max_iterations: int,
    pulp_time_limit_seconds: int,
    include_solutions: bool = False,
) -> _SolvedSubsetBundle:
    dataset_dir = Path(str(dataset_manifest["dataset_dir"]))
    instances = load_instances_from_dataset(dataset_dir)

    class_results_by_solver: dict[str, list[BenchmarkResultRecord]] = {"pyvrp": [], "pulp": []}
    solutions_by_solver: dict[str, dict[str, BenchmarkSolution]] | None = {"pyvrp": {}, "pulp": {}} if include_solutions else None

    for classe_operacional in sorted(instances, key=lambda item: item.value):
        instance = instances[classe_operacional]
        spec = _build_class_spec(dataset_manifest, classe_operacional, instance)

        pyvrp_solution = PyVRPBenchmarkSolver(
            max_iterations=pyvrp_max_iterations,
            seed=int(dataset_manifest["sample_seed"]),
        ).solve(instance)
        class_results_by_solver["pyvrp"].append(build_result_record(spec, instance, pyvrp_solution))
        if include_solutions and solutions_by_solver is not None:
            solutions_by_solver["pyvrp"][classe_operacional.value] = pyvrp_solution

        pulp_solution = PuLPBaselineSolver(
            PuLPBaselineConfig(
                time_limit_seconds=pulp_time_limit_seconds,
                gap_pct_target=0.01,
                msg=False,
            )
        ).solve(instance)
        class_results_by_solver["pulp"].append(build_result_record(spec, instance, pulp_solution))
        if include_solutions and solutions_by_solver is not None:
            solutions_by_solver["pulp"][classe_operacional.value] = pulp_solution

    scenario_records = tuple(
        _aggregate_solver_records(
            dataset_manifest=dataset_manifest,
            solver=solver_name,
            class_records=records,
        )
        for solver_name, records in sorted(class_results_by_solver.items())
    )
    raw_class_records = tuple(
        record.to_dict()
        for records in class_results_by_solver.values()
        for record in records
    )
    return _SolvedSubsetBundle(
        scenario_records=scenario_records,
        class_records=raw_class_records,
        solutions_by_solver=solutions_by_solver,
    )


def _run_full_benchmark(
    *,
    base_scenario: str,
    datasets_dir: Path,
    pyvrp_max_iterations: int,
    pulp_time_limit_seconds: int,
    base_seed: int,
    overwrite_datasets: bool,
) -> dict[str, Any]:
    full_manifest = materialize_pressure_subset_dataset(
        base_scenario=base_scenario,
        order_share=1.0,
        repetition=1,
        base_seed=base_seed,
        output_root=datasets_dir,
        overwrite=overwrite_datasets,
    )
    solved_subset = _run_single_subset_benchmark(
        dataset_manifest=full_manifest,
        pyvrp_max_iterations=pyvrp_max_iterations,
        pulp_time_limit_seconds=pulp_time_limit_seconds,
        include_solutions=True,
    )

    solver_payloads: dict[str, dict[str, Any]] = {}
    for scenario_record in solved_subset.scenario_records:
        solver_name = str(scenario_record["solver"])
        solver_payloads[solver_name] = {
            "scenario_record": scenario_record,
            "class_records": [
                item for item in solved_subset.class_records if str(item["solver"]) == solver_name
            ],
            "solutions_by_class": (solved_subset.solutions_by_solver or {}).get(solver_name, {}),
        }

    return {
        "manifest": full_manifest,
        "scenario_records": list(solved_subset.scenario_records),
        "class_records": list(solved_subset.class_records),
        "solvers": solver_payloads,
        "plots": {},
    }


def _build_class_spec(
    dataset_manifest: dict[str, Any],
    classe_operacional: ClasseOperacional,
    instance,
) -> SimpleNamespace:
    return SimpleNamespace(
        scenario_id=f"{dataset_manifest['scenario_id']}_{classe_operacional.value}",
        family="operacao_sob_pressao_subsample",
        layer="subsample",
        seed=int(dataset_manifest["sample_seed"]),
        n_orders=len(instance.nos_atendimento),
        n_vehicles=len(instance.veiculos),
        classe_operacional=classe_operacional.value,
    )


def _aggregate_solver_records(
    *,
    dataset_manifest: dict[str, Any],
    solver: str,
    class_records: list[BenchmarkResultRecord],
) -> dict[str, Any]:
    total_orders = sum(int(record.n_orders) for record in class_records)
    served_orders = sum(
        int(round(Decimal(str(record.service_rate)) * Decimal(record.n_orders)))
        for record in class_records
    )
    feasible = all(record.feasible for record in class_records)
    status = "feasible" if feasible else "partial"

    class_statuses = ", ".join(f"{record.classe_operacional}:{record.status}" for record in class_records)
    class_notes = " | ".join(record.notes for record in class_records if record.notes)
    aggregate_notes = " | ".join(part for part in (f"class_statuses={class_statuses}", class_notes) if part)

    return {
        "scenario_id": str(dataset_manifest["scenario_id"]),
        "base_scenario": str(dataset_manifest["base_scenario"]),
        "base_scenario_label": scenario_public_label(str(dataset_manifest["base_scenario"])),
        "order_share_pct": int(dataset_manifest["order_share_pct"]),
        "order_share_label": _share_label(int(dataset_manifest["order_share_pct"])),
        "repetition": int(dataset_manifest["repetition"]),
        "sample_seed": int(dataset_manifest["sample_seed"]),
        "n_orders": total_orders,
        "n_orders_suprimento": int(dataset_manifest["per_class_counts"].get("suprimento", 0)),
        "n_orders_recolhimento": int(dataset_manifest["per_class_counts"].get("recolhimento", 0)),
        "n_vehicles": int(dataset_manifest["n_vehicles"]),
        "solver": solver,
        "solver_label": SOLVER_LABELS.get(solver, solver),
        "status": status,
        "runtime_s": f"{sum(float(record.runtime_s) for record in class_records):.4f}",
        "objective_common": f"{sum(float(record.objective_common) for record in class_records):.2f}",
        "service_rate": f"{(served_orders / total_orders) if total_orders else 0.0:.4f}",
        "vehicles_used": sum(int(record.vehicles_used) for record in class_records),
        "distance_total_m": sum(int(record.distance_total_m) for record in class_records),
        "duration_total_s": sum(int(record.duration_total_s) for record in class_records),
        "feasible": feasible,
        "best_bound": None,
        "gap_pct": None,
        "notes": aggregate_notes,
    }


def _load_dataset_payload(dataset_dir: Path) -> dict[str, Any]:
    return {
        "contexto": json.loads((dataset_dir / "contexto.json").read_text()),
        "bases": json.loads((dataset_dir / "bases.json").read_text()),
        "pontos": json.loads((dataset_dir / "pontos.json").read_text()),
        "viaturas": json.loads((dataset_dir / "viaturas.json").read_text()),
        "ordens": json.loads((dataset_dir / "ordens.json").read_text()),
    }


def _sample_orders(
    orders: list[dict[str, Any]],
    *,
    order_share: float,
    rng: Random,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    orders_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for order in orders:
        class_token = str(order.get("classe_operacional") or order.get("tipo_servico"))
        orders_by_class[class_token].append(dict(order))

    selected_orders: list[dict[str, Any]] = []
    per_class_counts: dict[str, int] = {}
    for class_token, class_orders in sorted(orders_by_class.items()):
        if not class_orders:
            continue
        target_count = min(len(class_orders), max(1, int(round(len(class_orders) * order_share))))
        chosen = rng.sample(class_orders, target_count)
        chosen.sort(key=lambda item: (str(item.get("inicio_janela", "")), str(item["id_ordem"])))
        selected_orders.extend(chosen)
        per_class_counts[class_token] = target_count

    selected_orders.sort(
        key=lambda item: (
            str(item.get("classe_operacional", "")),
            str(item.get("inicio_janela", "")),
            str(item["id_ordem"]),
        )
    )
    return selected_orders, per_class_counts


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _write_results_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        raise ValueError("benchmark sem registros")
    fieldnames = list(records[0].keys())
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def _write_plots(
    *,
    plots_dir: Path,
    records: list[dict[str, Any]],
    aggregates: list[dict[str, Any]],
    relative_error_records: list[dict[str, Any]],
    full_run: dict[str, Any],
    with_basemap: bool,
) -> dict[str, dict[str, str]]:
    sample_paths = {
        "trend_panel": str(_plot_trend_panel(plots_dir, records, aggregates)),
        "dispersion_panel": str(_plot_dispersion_panel(plots_dir, records)),
        "relative_error_panel": str(_plot_relative_error_panel(plots_dir, relative_error_records, records)),
        "pulp_viability_panel": str(_plot_pulp_viability_panel(plots_dir, aggregates, relative_error_records)),
    }
    full_run_path = _plot_full_run_route_panel(plots_dir, full_run, with_basemap=with_basemap)
    return {
        "sample": sample_paths,
        "full_run": {"route_panel": str(full_run_path)},
    }


def _plot_trend_panel(
    plots_dir: Path,
    records: list[dict[str, Any]],
    aggregates: list[dict[str, Any]],
) -> Path:
    _, plt = _require_network_stack()
    share_values = sorted({int(record["order_share_pct"]) for record in records})
    figure, axes = plt.subplots(2, 2, figsize=(15, 10), constrained_layout=True)

    for axis, metric in zip(axes.flat, METRIC_SPECS):
        for solver in SOLVER_ORDER:
            color = SOLVER_COLORS[solver]
            solver_records = [
                record
                for record in records
                if str(record["solver"]) == solver
            ]
            solver_aggregates = [
                record
                for record in aggregates
                if str(record["solver"]) == solver
            ]
            solver_aggregates.sort(key=lambda item: int(item["order_share_pct"]))

            scatter_x: list[float] = []
            scatter_y: list[float] = []
            for record in solver_records:
                jitter = _repetition_jitter(int(record["repetition"]))
                scatter_x.append(float(int(record["order_share_pct"]) + SOLVER_OFFSETS[solver] + jitter))
                scatter_y.append(metric["transform"](_as_float(record[metric["key"]])))
            axis.scatter(scatter_x, scatter_y, color=color, alpha=0.35, s=38, edgecolor="white", linewidth=0.5)

            if solver_aggregates:
                x_values = [float(int(item["order_share_pct"]) + SOLVER_OFFSETS[solver]) for item in solver_aggregates]
                y_values = [metric["transform"](float(item[f"mean_{metric['summary_key']}"])) for item in solver_aggregates]
                std_values = [metric["transform"](float(item[f"std_{metric['summary_key']}"])) for item in solver_aggregates]
                axis.plot(x_values, y_values, color=color, linewidth=2.2, marker="o", label=SOLVER_LABELS[solver])
                axis.errorbar(
                    x_values,
                    y_values,
                    yerr=std_values,
                    fmt="none",
                    ecolor=color,
                    elinewidth=1.2,
                    capsize=4,
                    alpha=0.65,
                )

        axis.set_title(metric["title"])
        axis.set_ylabel(metric["label"])
        axis.set_xticks(share_values)
        axis.set_xticklabels([_share_label(item) for item in share_values])
        axis.set_xlabel("Escala do experimento")
        axis.grid(alpha=0.18)
        if metric["ylim"] is not None:
            axis.set_ylim(*metric["ylim"])

    axes[0, 0].legend(loc="upper left")
    output_path = plots_dir / "painel_tendencias.png"
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output_path


def _plot_dispersion_panel(plots_dir: Path, records: list[dict[str, Any]]) -> Path:
    _, plt = _require_network_stack()
    from matplotlib.lines import Line2D

    share_values = sorted({int(record["order_share_pct"]) for record in records})
    figure, axes = plt.subplots(2, 2, figsize=(15, 10), constrained_layout=True)

    for axis, metric in zip(axes.flat, METRIC_SPECS):
        box_data: list[list[float]] = []
        box_positions: list[float] = []
        box_colors: list[str] = []

        for share_pct in share_values:
            for solver in SOLVER_ORDER:
                values = [
                    metric["transform"](_as_float(record[metric["key"]]))
                    for record in records
                    if int(record["order_share_pct"]) == share_pct and str(record["solver"]) == solver
                ]
                if not values:
                    continue
                box_data.append(values)
                box_positions.append(float(share_pct + SOLVER_OFFSETS[solver]))
                box_colors.append(SOLVER_COLORS[solver])

                axis.scatter(
                    [share_pct + SOLVER_OFFSETS[solver] + _repetition_jitter(index + 1) for index, _ in enumerate(values)],
                    values,
                    color=SOLVER_COLORS[solver],
                    alpha=0.35,
                    s=34,
                    edgecolor="white",
                    linewidth=0.5,
                    zorder=3,
                )

        if box_data:
            boxplot = axis.boxplot(
                box_data,
                positions=box_positions,
                widths=3.6,
                patch_artist=True,
                manage_ticks=False,
                medianprops={"color": "#0f172a", "linewidth": 1.6},
            )
            for patch, color in zip(boxplot["boxes"], box_colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.24)
                patch.set_edgecolor(color)
                patch.set_linewidth(1.4)
            for whisker, color in zip(boxplot["whiskers"], [item for color in box_colors for item in (color, color)]):
                whisker.set_color(color)
                whisker.set_alpha(0.65)
            for cap, color in zip(boxplot["caps"], [item for color in box_colors for item in (color, color)]):
                cap.set_color(color)
                cap.set_alpha(0.65)

        axis.set_title(f"Dispersao - {metric['label']}")
        axis.set_ylabel(metric["label"])
        axis.set_xticks(share_values)
        axis.set_xticklabels([_share_label(item) for item in share_values])
        axis.set_xlabel("Escala do experimento")
        axis.grid(alpha=0.18)
        if metric["ylim"] is not None:
            axis.set_ylim(*metric["ylim"])

    handles = [
        Line2D([0], [0], color=SOLVER_COLORS[solver], marker="o", linestyle="-", linewidth=2.0, label=SOLVER_LABELS[solver])
        for solver in SOLVER_ORDER
    ]
    axes[0, 0].legend(handles=handles, loc="upper left")
    output_path = plots_dir / "painel_dispersao.png"
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output_path


def _plot_relative_error_panel(
    plots_dir: Path,
    relative_error_records: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> Path:
    _, plt = _require_network_stack()
    figure, axis = plt.subplots(figsize=(12, 6), constrained_layout=True)
    share_values = sorted({int(record["order_share_pct"]) for record in records})

    pyvrp_records = [
        item for item in relative_error_records
        if item["solver"] == "pyvrp"
    ]
    box_data: list[list[float]] = []
    box_positions: list[float] = []
    for share_pct in share_values:
        values = [
            float(item["relative_objective_error_pct"])
            for item in pyvrp_records
            if int(item["order_share_pct"]) == share_pct and item["relative_objective_error_pct"] is not None
        ]
        if values:
            box_data.append(values)
            box_positions.append(float(share_pct))
            axis.scatter(
                [share_pct + _repetition_jitter(index + 1) for index, _ in enumerate(values)],
                values,
                color=SOLVER_COLORS["pyvrp"],
                alpha=0.5,
                s=44,
                edgecolor="white",
                linewidth=0.6,
                zorder=3,
            )

    if box_data:
        boxplot = axis.boxplot(
            box_data,
            positions=box_positions,
            widths=5.8,
            patch_artist=True,
            manage_ticks=False,
            medianprops={"color": "#0f172a", "linewidth": 1.7},
        )
        for patch in boxplot["boxes"]:
            patch.set_facecolor(SOLVER_COLORS["pyvrp"])
            patch.set_alpha(0.22)
            patch.set_edgecolor(SOLVER_COLORS["pyvrp"])
            patch.set_linewidth(1.4)
        for line in (*boxplot["whiskers"], *boxplot["caps"]):
            line.set_color(SOLVER_COLORS["pyvrp"])
            line.set_alpha(0.65)
    else:
        axis.text(
            0.5,
            0.5,
            "Nao houve repeticoes com referencia valida do PuLP para calcular o erro relativo da FO.",
            ha="center",
            va="center",
            transform=axis.transAxes,
            fontsize=11,
            color="#475569",
        )

    reference_counts = aggregate_relative_objective_errors(relative_error_records, records=records)
    for item in reference_counts:
        if item["solver"] != "pyvrp":
            continue
        axis.text(
            float(item["order_share_pct"]),
            axis.get_ylim()[1] * 0.94 if axis.get_ylim()[1] > 0 else 1.0,
            f"refs PuLP: {item['valid_reference_count']}/{item['repetitions']}",
            ha="center",
            va="top",
            fontsize=8.8,
            color="#334155",
        )

    axis.axhline(0.0, color=SOLVER_COLORS["pulp"], linestyle="--", linewidth=1.6, label="PuLP = referencia global")
    axis.set_title("Erro relativo da funcao objetivo em relacao ao PuLP (%)")
    axis.set_xlabel("Escala do experimento")
    axis.set_ylabel("Erro relativo da FO (%)")
    axis.set_xticks(share_values)
    axis.set_xticklabels([_share_label(item) for item in share_values])
    axis.grid(alpha=0.18)
    axis.legend(loc="upper left")
    output_path = plots_dir / "erro_relativo_fo_pct.png"
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output_path


def _plot_pulp_viability_panel(
    plots_dir: Path,
    aggregates: list[dict[str, Any]],
    relative_error_records: list[dict[str, Any]],
) -> Path:
    _, plt = _require_network_stack()
    figure, axis = plt.subplots(figsize=(12, 6), constrained_layout=True)

    pulp_rows = [item for item in aggregates if item["solver"] == "pulp"]
    pulp_rows.sort(key=lambda item: int(item["order_share_pct"]))
    share_values = [int(item["order_share_pct"]) for item in pulp_rows]
    viability_pct = [float(item["feasible_rate"]) * 100.0 for item in pulp_rows]
    axis.bar(share_values, viability_pct, width=7.5, color=SOLVER_COLORS["pulp"], alpha=0.82)

    reference_counts = {
        int(item["order_share_pct"]): item["valid_reference_count"]
        for item in aggregate_relative_objective_errors(relative_error_records)
        if item["solver"] == "pyvrp"
    }
    for item, pct_value in zip(pulp_rows, viability_pct):
        share_pct = int(item["order_share_pct"])
        axis.text(
            share_pct,
            min(pct_value + 2.5, 102.0),
            f"{item['repetitions_feasible']}/{item['repetitions']} viavel\nrefs FO: {reference_counts.get(share_pct, 0)}/{item['repetitions']}",
            ha="center",
            va="bottom",
            fontsize=8.8,
            color="#334155",
        )

    axis.set_title("Taxa de viabilidade do PuLP por percentual de ordens")
    axis.set_xlabel("Escala do experimento")
    axis.set_ylabel("Taxa de viabilidade do PuLP (%)")
    axis.set_xticks(share_values)
    axis.set_xticklabels([_share_label(item) for item in share_values])
    axis.set_ylim(0, 110)
    axis.grid(alpha=0.18, axis="y")
    output_path = plots_dir / "taxa_viabilidade_pulp.png"
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output_path


def _plot_full_run_route_panel(plots_dir: Path, full_run: dict[str, Any], *, with_basemap: bool) -> Path:
    nx, plt = _require_network_stack()

    dataset_dir = Path(str(full_run["manifest"]["dataset_dir"]))
    artifacts = load_scenario_artifacts(dataset_dir)

    figure, axes = plt.subplots(2, 2, figsize=(18, 12), constrained_layout=True)
    figure.suptitle(
        "Rodada exaustiva de 100% das ordens\nCada painel representa uma execucao isolada por classe operacional",
        fontsize=14,
        fontweight="bold",
    )
    for row_index, classe_operacional in enumerate(("suprimento", "recolhimento")):
        for col_index, solver in enumerate(SOLVER_ORDER):
            axis = axes[row_index, col_index]
            solver_payload = full_run.get("solvers", {}).get(solver)
            _draw_full_run_solver_panel(
                axis=axis,
                solver=solver,
                solver_payload=solver_payload,
                classe_operacional=classe_operacional,
                artifacts=artifacts,
                nx=nx,
                with_basemap=with_basemap,
            )

    output_path = plots_dir / "rodada_exaustiva_100_rotas.png"
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output_path


def _draw_full_run_solver_panel(axis, *, solver: str, solver_payload: dict[str, Any] | None, classe_operacional: str, artifacts, nx, with_basemap: bool) -> None:
    positions = artifacts.positions
    base_nodes = [node_id for node_id, kind in artifacts.node_kind.items() if kind == "base"]
    order_nodes = [node_id for node_id, kind in artifacts.node_kind.items() if kind == "ordem"]

    basemap_added = _maybe_add_basemap(axis, positions) if with_basemap else False
    title_suffix = " com basemap" if basemap_added else ""
    axis.set_title(f"{SOLVER_LABELS[solver]} - {classe_operacional}{title_suffix}", loc="left")

    base_graph = nx.DiGraph()
    for node_id, position in positions.items():
        base_graph.add_node(node_id, pos=position)
    for arc in artifacts.matrix_payload.get("arcs", []):
        origem = arc["id_origem"]
        destino = arc["id_destino"]
        if origem in positions and destino in positions:
            base_graph.add_edge(origem, destino)

    nx.draw_networkx_edges(
        base_graph,
        pos=positions,
        ax=axis,
        arrows=False,
        edge_color="#d9dee5",
        alpha=0.16,
        width=0.8,
    )
    nx.draw_networkx_nodes(
        base_graph,
        pos=positions,
        nodelist=base_nodes,
        ax=axis,
        node_color="#12355b",
        node_shape="s",
        node_size=380,
        edgecolors="white",
        linewidths=1.2,
    )

    if not solver_payload:
        axis.text(0.5, 0.5, "Solver sem dados nesta rodada.", transform=axis.transAxes, ha="center", va="center")
        return

    class_records = {
        str(item["classe_operacional"]): item
        for item in solver_payload.get("class_records", [])
    }
    scenario_record = class_records.get(classe_operacional)
    solutions_by_class: dict[str, BenchmarkSolution] = solver_payload.get("solutions_by_class", {})
    solution = solutions_by_class.get(classe_operacional)
    if scenario_record is None or solution is None:
        axis.text(
            0.5,
            0.5,
            f"Nao ha resultado para {classe_operacional} neste solver.",
            transform=axis.transAxes,
            ha="center",
            va="center",
        )
        return

    served_nodes: set[str] = set()

    for route_index, route in enumerate(solution.routes, start=1):
        served_nodes.update(route.visited_node_ids)
        style = _service_style(classe_operacional)
        route_color = SOLVER_COLORS[solver]
        edge_list = list(zip(route.location_sequence, route.location_sequence[1:]))
        connection_rad = _route_connection_rad(route_index)
        nx.draw_networkx_edges(
            base_graph,
            pos=positions,
            ax=axis,
            edgelist=edge_list,
            arrows=True,
            arrowsize=16,
            width=5.0,
            edge_color="#ffffff",
            alpha=0.92,
            style=style["line_style"],
            connectionstyle=f"arc3,rad={connection_rad}",
        )
        nx.draw_networkx_edges(
            base_graph,
            pos=positions,
            ax=axis,
            edgelist=edge_list,
            arrows=True,
            arrowsize=14,
            width=2.8,
            edge_color=route_color,
            alpha=0.94,
            style=style["line_style"],
            connectionstyle=f"arc3,rad={connection_rad}",
        )
        _annotate_benchmark_route_label(
            axis=axis,
            positions=positions,
            route=route,
            route_index=route_index,
            route_color=route_color,
        )

    unserved_nodes = sorted(set(solution.missing_node_ids))

    served_by_service: dict[str, list[str]] = {"suprimento": [], "recolhimento": []}
    for ordem in artifacts.ordens:
        node_id = f"no-{ordem['id_ordem']}"
        if node_id not in served_nodes:
            continue
        served_by_service[str(ordem.get("classe_operacional", ordem.get("tipo_servico", ""))).lower()].append(node_id)

    for classe_operacional, node_ids in served_by_service.items():
        if not node_ids:
            continue
        style = _service_style(classe_operacional)
        nx.draw_networkx_nodes(
            base_graph,
            pos=positions,
            nodelist=node_ids,
            ax=axis,
            node_color=style["fill"],
            node_shape=style["marker"],
            node_size=300,
            edgecolors="white",
            linewidths=0.9,
            alpha=0.98,
        )

    if unserved_nodes:
        nx.draw_networkx_nodes(
            base_graph,
            pos=positions,
            nodelist=unserved_nodes,
            ax=axis,
            node_color="#cbd5e1",
            node_shape="X",
            node_size=280,
            edgecolors="#475569",
            linewidths=1.0,
            alpha=0.94,
        )

    base_labels = {node_id: artifacts.labels[node_id].split(" - ")[0] for node_id in base_nodes}
    nx.draw_networkx_labels(base_graph, pos=positions, labels=base_labels, ax=axis, font_size=8, font_color="#102a43")

    _set_axis_extent(axis, positions)
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.grid(alpha=0.18)
    _draw_full_run_legend(axis, solver)

    summary_text = (
        f"Status: {scenario_record['status']}\n"
        f"FO: {scenario_record['objective_common']}\n"
        f"Atendimento: {float(scenario_record['service_rate']) * 100.0:.2f}%\n"
        f"Viaturas: {scenario_record['vehicles_used']}\n"
        f"Distancia: {int(scenario_record['distance_total_m']) / 1000.0:.2f} km\n"
        f"Duracao: {int(scenario_record['duration_total_s']) / 60.0:.1f} min"
    )
    axis.text(
        0.02,
        0.98,
        summary_text,
        transform=axis.transAxes,
        va="top",
        fontsize=9,
        color="#102a43",
        bbox={"facecolor": "white", "alpha": 0.92, "edgecolor": "#cbd5e1", "boxstyle": "round,pad=0.35"},
    )

    if not bool(scenario_record.get("feasible")):
        axis.text(
            0.5,
            0.08,
            "Nao houve solucao viavel completa neste solver.\nA visualizacao mostra apenas o que foi efetivamente roteirizado.",
            transform=axis.transAxes,
            ha="center",
            va="bottom",
            fontsize=9,
            color="#7c2d12",
            bbox={"facecolor": "#fff7ed", "alpha": 0.95, "edgecolor": "#fdba74", "boxstyle": "round,pad=0.35"},
        )


def _draw_full_run_legend(axis, solver: str) -> None:
    from matplotlib.lines import Line2D

    handles = [
        Line2D([0], [0], marker="s", linestyle="None", markerfacecolor="#12355b", markeredgecolor="white", markeredgewidth=1.2, markersize=9, label="Base"),
        Line2D([0], [0], marker="^", linestyle="None", markerfacecolor=_service_style("suprimento")["fill"], markeredgecolor="white", markeredgewidth=1.0, markersize=9, label="Ordem atendida - suprimento"),
        Line2D([0], [0], marker="v", linestyle="None", markerfacecolor=_service_style("recolhimento")["fill"], markeredgecolor="white", markeredgewidth=1.0, markersize=9, label="Ordem atendida - recolhimento"),
        Line2D([0], [0], marker="X", linestyle="None", markerfacecolor="#cbd5e1", markeredgecolor="#475569", markeredgewidth=1.0, markersize=9, label="Ordem nao atendida"),
        Line2D([0, 1], [0, 0], color=SOLVER_COLORS[solver], linewidth=2.6, linestyle="solid", label="Rota de suprimento"),
        Line2D([0, 1], [0, 0], color=SOLVER_COLORS[solver], linewidth=2.6, linestyle=(0, (6, 4)), label="Rota de recolhimento"),
    ]
    axis.legend(handles=handles, loc="lower left", frameon=True, fontsize=8.2)


def _route_connection_rad(route_index: int) -> float:
    magnitude = 0.035 + (0.012 * ((route_index - 1) % 3))
    return magnitude if route_index % 2 else -magnitude


def _annotate_benchmark_route_label(axis, *, positions: dict[str, tuple[float, float]], route: BenchmarkRoute, route_index: int, route_color) -> None:
    anchor_node = None
    for node_id in route.location_sequence:
        if node_id.startswith("no-"):
            anchor_node = node_id
            break
    if anchor_node is None:
        anchor_node = route.location_sequence[0] if route.location_sequence else None
    if anchor_node is None or anchor_node not in positions:
        return

    x_coord, y_coord = positions[anchor_node]
    axis.text(
        x_coord,
        y_coord,
        f"R{route_index:02d}",
        ha="center",
        va="center",
        fontsize=7.5,
        color="white",
        fontweight="bold",
        zorder=7,
        bbox={
            "facecolor": route_color,
            "edgecolor": "white",
            "boxstyle": "round,pad=0.18",
            "linewidth": 0.9,
        },
    )


def _serialize_full_run(full_run: dict[str, Any]) -> dict[str, Any]:
    serialized_solvers: dict[str, Any] = {}
    for solver, payload in full_run.get("solvers", {}).items():
        serialized_solvers[solver] = {
            "scenario_record": payload["scenario_record"],
            "class_records": payload["class_records"],
            "solutions_by_class": {
                classe_operacional: _serialize_solution(solution)
                for classe_operacional, solution in payload.get("solutions_by_class", {}).items()
            },
        }
    return {
        "manifest": full_run.get("manifest"),
        "scenario_records": full_run.get("scenario_records", []),
        "class_records": full_run.get("class_records", []),
        "solvers": serialized_solvers,
        "plots": full_run.get("plots", {}),
    }


def _serialize_solution(solution: BenchmarkSolution) -> dict[str, Any]:
    return {
        "solver": solution.solver,
        "status": solution.status,
        "runtime_s": round(float(solution.runtime_s), 4),
        "feasible": bool(solution.feasible),
        "routes": [_serialize_route(route) for route in solution.routes],
        "served_node_ids": list(solution.served_node_ids),
        "missing_node_ids": list(solution.missing_node_ids),
        "best_bound": None if solution.best_bound is None else str(solution.best_bound),
        "gap_pct": None if solution.gap_pct is None else str(solution.gap_pct),
        "notes": list(solution.notes),
    }


def _serialize_route(route: BenchmarkRoute) -> dict[str, Any]:
    return {
        "vehicle_id": route.vehicle_id,
        "depot_id": route.depot_id,
        "location_sequence": list(route.location_sequence),
        "visited_node_ids": list(route.visited_node_ids),
        "distance_total_m": int(route.distance_total_m),
        "duration_total_s": int(route.duration_total_s),
    }


def _route_display_label(artifacts, node_id: str) -> str:
    if node_id.startswith("dep-"):
        return artifacts.labels.get(node_id, node_id)
    if node_id.startswith("no-"):
        return artifacts.labels.get(node_id, node_id)
    return node_id


def _repetition_jitter(repetition: int) -> float:
    return float((repetition - 3) * 0.45)


def _coerce_aggregates(records_or_aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not records_or_aggregates:
        return []
    if "mean_runtime_s" in records_or_aggregates[0]:
        return records_or_aggregates
    return aggregate_records(records_or_aggregates)


def _share_label(share_pct: int) -> str:
    return f"{share_pct}% das ordens"


def _fmt(value: float, decimals: int) -> str:
    return f"{float(value):.{decimals}f}"


def _fmt_nullable(value: float | None, decimals: int) -> str:
    if value is None:
        return "indisponivel"
    return _fmt(value, decimals)


def _as_float(value: Any) -> float:
    return float(value)


def _safe_mean(values) -> float:
    sequence = list(values)
    return float(mean(sequence)) if sequence else 0.0


def _safe_median(values) -> float:
    sequence = list(values)
    return float(median(sequence)) if sequence else 0.0


def _safe_stdev(values) -> float:
    sequence = list(values)
    if len(sequence) < 2:
        return 0.0
    return float(stdev(sequence))


def _stringify_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return _fmt(value, 4)
    return str(value)


def _markdown_escape(value: str) -> str:
    return value.replace("|", "\\|")


def cycle_palette():
    _, plt = _require_network_stack()
    while True:
        for color in plt.cm.tab10.colors:
            yield color

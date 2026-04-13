from __future__ import annotations

import importlib.util
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from random import Random
from typing import Any

from roteirizacao.application.snapshot_materializer import (
    FileSystemSnapshotRepository,
    JsonFileLogisticsSnapshotSource,
    LogisticsSnapshotMaterializer,
)
from roteirizacao.benchmark.scenario_catalog import (
    DEFAULT_SCENARIO_CATALOG_PATH,
    BenchmarkScenarioSpec,
    group_specs_by_dataset_dir,
    load_scenario_catalog,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = PROJECT_ROOT / "data"
TEMPLATE_BY_LAYER = {
    "didatica": DATA_ROOT / "fake_solution",
    "benchmark": DATA_ROOT / "fake_smoke",
    "estresse": DATA_ROOT / "fake_smoke",
}
GEO_DENSITY_FACTOR = {
    "clustered": Decimal("0.78"),
    "balanced": Decimal("1.00"),
    "dispersed": Decimal("1.35"),
}
PRESSURE_FACTOR = {
    "balanced": Decimal("1.00"),
    "high": Decimal("1.55"),
}
WINDOW_FACTOR = {
    "balanced": Decimal("1.00"),
    "tight": Decimal("0.45"),
}


def materialize_scenarios_from_catalog(
    *,
    catalog_path: Path | str = DEFAULT_SCENARIO_CATALOG_PATH,
    scenario_ids: set[str] | None = None,
    overwrite: bool = False,
) -> list[Path]:
    specs = load_scenario_catalog(catalog_path)
    grouped_specs = group_specs_by_dataset_dir(tuple(_expand_specs_to_full_dataset(specs, scenario_ids)))
    materialized: list[Path] = []
    for dataset_dir, dataset_specs in sorted(grouped_specs.items(), key=lambda item: str(item[0])):
        materialized.append(materialize_dataset_from_specs(dataset_dir, dataset_specs, overwrite=overwrite))
    return materialized


def materialize_dataset_from_specs(
    dataset_dir: Path,
    specs: list[BenchmarkScenarioSpec],
    *,
    overwrite: bool = False,
) -> Path:
    if not specs:
        raise ValueError("materialize_dataset_from_specs requer ao menos um spec")

    dataset_dir = dataset_dir if dataset_dir.is_absolute() else PROJECT_ROOT / dataset_dir
    representative = specs[0]
    _validate_group(specs)

    manifest_path = dataset_dir / "scenario_manifest.json"
    if manifest_path.exists() and not overwrite:
        return dataset_dir

    template_dir = TEMPLATE_BY_LAYER[representative.layer]
    template_payload = _load_dataset_payload(template_dir)
    rng = Random(representative.seed)
    per_class_counts = {spec.classe_operacional: spec.n_orders for spec in specs}

    bases = template_payload["bases"]
    pontos = _transform_points(template_payload["pontos"], geo_density=representative.geo_density)
    viaturas = _select_vehicles(template_payload["viaturas"], representative.n_vehicles, rng)
    ordens = _build_orders(
        template_payload["ordens"],
        pontos=pontos,
        data_operacao=str(template_payload["contexto"]["data_operacao"]),
        per_class_counts=per_class_counts,
        window_profile=representative.window_profile,
        volume_pressure=representative.volume_pressure,
        cash_pressure=representative.cash_pressure,
        priority_ratio=representative.priority_ratio,
        family=representative.family,
        layer=representative.layer,
        seed=representative.seed,
    )
    contexto = dict(template_payload["contexto"])
    contexto["id_execucao"] = f"exec-{dataset_dir.name}-{contexto['data_operacao']}"
    contexto["timestamp_referencia"] = datetime.now(timezone.utc).isoformat()

    dataset_dir.mkdir(parents=True, exist_ok=True)
    _write_json(dataset_dir / "contexto.json", contexto)
    _write_json(dataset_dir / "bases.json", bases)
    _write_json(dataset_dir / "pontos.json", pontos)
    _write_json(dataset_dir / "viaturas.json", viaturas)
    _write_json(dataset_dir / "ordens.json", ordens)
    _write_json(
        manifest_path,
        {
            "dataset_dir": str(dataset_dir.relative_to(PROJECT_ROOT)),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "family": representative.family,
            "layer": representative.layer,
            "seed": representative.seed,
            "window_profile": representative.window_profile,
            "volume_pressure": representative.volume_pressure,
            "cash_pressure": representative.cash_pressure,
            "priority_ratio": representative.priority_ratio,
            "geo_density": representative.geo_density,
            "n_vehicles": representative.n_vehicles,
            "n_orders_por_classe": per_class_counts,
            "scenario_ids": [spec.scenario_id for spec in specs],
            "pedagogical_hypothesis": [spec.pedagogical_hypothesis for spec in specs],
        },
    )
    _write_readme(dataset_dir, representative, per_class_counts)
    _materialize_logistics_snapshot(dataset_dir, str(contexto["data_operacao"]))
    return dataset_dir


def _expand_specs_to_full_dataset(specs: tuple[BenchmarkScenarioSpec, ...], scenario_ids: set[str] | None) -> list[BenchmarkScenarioSpec]:
    if scenario_ids is None:
        return list(specs)
    selected_dataset_dirs = {spec.dataset_dir for spec in specs if spec.scenario_id in scenario_ids}
    return [spec for spec in specs if spec.dataset_dir in selected_dataset_dirs]


def _validate_group(specs: list[BenchmarkScenarioSpec]) -> None:
    first = specs[0]
    for spec in specs[1:]:
        comparable = (
            spec.family == first.family
            and spec.layer == first.layer
            and spec.seed == first.seed
            and spec.n_vehicles == first.n_vehicles
            and spec.window_profile == first.window_profile
            and spec.volume_pressure == first.volume_pressure
            and spec.cash_pressure == first.cash_pressure
            and spec.priority_ratio == first.priority_ratio
            and spec.geo_density == first.geo_density
        )
        if not comparable:
            raise ValueError(f"dataset_dir {first.dataset_dir} possui specs incompativeis")


def _load_dataset_payload(dataset_dir: Path) -> dict[str, Any]:
    return {
        "contexto": json.loads((dataset_dir / "contexto.json").read_text()),
        "bases": json.loads((dataset_dir / "bases.json").read_text()),
        "pontos": json.loads((dataset_dir / "pontos.json").read_text()),
        "viaturas": json.loads((dataset_dir / "viaturas.json").read_text()),
        "ordens": json.loads((dataset_dir / "ordens.json").read_text()),
    }


def _transform_points(points: list[dict[str, Any]], *, geo_density: str) -> list[dict[str, Any]]:
    factor = GEO_DENSITY_FACTOR[geo_density]
    centroid_lat = sum(Decimal(str(point["latitude"])) for point in points) / Decimal(len(points))
    centroid_lon = sum(Decimal(str(point["longitude"])) for point in points) / Decimal(len(points))
    transformed: list[dict[str, Any]] = []
    for point in points:
        latitude = Decimal(str(point["latitude"]))
        longitude = Decimal(str(point["longitude"]))
        adjusted = dict(point)
        adjusted["latitude"] = float((centroid_lat + (latitude - centroid_lat) * factor).quantize(Decimal("0.0000001")))
        adjusted["longitude"] = float((centroid_lon + (longitude - centroid_lon) * factor).quantize(Decimal("0.0000001")))
        transformed.append(adjusted)
    return transformed


def _select_vehicles(vehicles: list[dict[str, Any]], target_count: int, rng: Random) -> list[dict[str, Any]]:
    if target_count > len(vehicles):
        raise ValueError("catalogo requer mais viaturas do que o template possui")
    selected = rng.sample(list(vehicles), target_count)
    return sorted(selected, key=lambda item: str(item["id_viatura"]))


def _build_orders(
    orders: list[dict[str, Any]],
    *,
    pontos: list[dict[str, Any]],
    data_operacao: str,
    per_class_counts: dict[str, int],
    window_profile: str,
    volume_pressure: str,
    cash_pressure: str,
    priority_ratio: float,
    family: str,
    layer: str,
    seed: int,
) -> list[dict[str, Any]]:
    rng = Random(seed)
    point_ids = [str(point["id_ponto"]) for point in pontos]
    orders_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for order in orders:
        class_token = str(order.get("classe_operacional") or order.get("tipo_servico"))
        orders_by_class[class_token].append(order)

    generated: list[dict[str, Any]] = []
    for class_token, count in sorted(per_class_counts.items()):
        source_pool = list(orders_by_class[class_token])
        rng.shuffle(source_pool)
        special_cutoff = int(round(count * priority_ratio))
        for index in range(count):
            source = source_pool[index % len(source_pool)]
            point_id = point_ids[(index + (0 if class_token == "suprimento" else 3)) % len(point_ids)]
            generated.append(
                _build_order_record(
                    source=source,
                    class_token=class_token,
                    point_id=point_id,
                    data_operacao=data_operacao,
                    order_index=index + 1,
                    is_special=index < special_cutoff,
                    window_profile=window_profile,
                    volume_pressure=volume_pressure,
                    cash_pressure=cash_pressure,
                    family=family,
                    layer=layer,
                    seed=seed,
                )
            )

    generated.sort(key=lambda item: (str(item["tipo_servico"]), str(item["inicio_janela"]), str(item["id_ordem"])))
    return generated


def _build_order_record(
    *,
    source: dict[str, Any],
    class_token: str,
    point_id: str,
    data_operacao: str,
    order_index: int,
    is_special: bool,
    window_profile: str,
    volume_pressure: str,
    cash_pressure: str,
    family: str,
    layer: str,
    seed: int,
) -> dict[str, Any]:
    record = dict(source)
    start_dt = datetime.fromisoformat(str(source["inicio_janela"]))
    end_dt = datetime.fromisoformat(str(source["fim_janela"]))
    adjusted_window = _adjust_window(start_dt, end_dt, window_profile=window_profile, is_special=is_special)
    volume_scale = PRESSURE_FACTOR[volume_pressure]
    cash_scale = PRESSURE_FACTOR[cash_pressure]
    if layer == "estresse":
        volume_scale *= Decimal("1.10")
        cash_scale *= Decimal("1.10")

    record["id_ordem"] = f"ORD-{family[:3].upper()}-{layer[:3].upper()}-{seed:02d}-{class_token[:3].upper()}-{order_index:03d}"
    record["origem_ordem"] = f"benchmark_{family}_{layer}"
    record["data_operacao"] = data_operacao
    record["id_ponto"] = point_id
    record["tipo_servico"] = class_token
    record["classe_operacional"] = class_token
    record["classe_planejamento"] = "especial" if is_special else "eventual"
    record["criticidade"] = "alta" if is_special else "media"
    record["timestamp_criacao"] = (adjusted_window[0] - timedelta(hours=8 if is_special else 18)).isoformat()
    record["inicio_janela"] = adjusted_window[0].isoformat()
    record["fim_janela"] = adjusted_window[1].isoformat()
    record["valor_estimado"] = _scaled_decimal_str(source["valor_estimado"], cash_scale)
    record["volume_estimado"] = _scaled_decimal_str(source["volume_estimado"], volume_scale)
    record["penalidade_nao_atendimento"] = _scaled_decimal_str(
        source["penalidade_nao_atendimento"],
        Decimal("1.35") if is_special else Decimal("1.00"),
    )
    record["penalidade_atraso"] = _scaled_decimal_str(
        source["penalidade_atraso"],
        Decimal("1.20") if window_profile == "tight" else Decimal("1.00"),
    )
    record["status_cancelamento"] = "nao_cancelada"
    record["taxa_improdutiva"] = str(source.get("taxa_improdutiva", "0"))
    return record


def _adjust_window(
    start_dt: datetime,
    end_dt: datetime,
    *,
    window_profile: str,
    is_special: bool,
) -> tuple[datetime, datetime]:
    factor = WINDOW_FACTOR[window_profile]
    span = end_dt - start_dt
    target_span = span * float(factor)
    if is_special and window_profile == "tight":
        target_span = max(target_span, timedelta(hours=2))
    if target_span <= timedelta():
        target_span = timedelta(hours=1)
    center = start_dt + (span / 2)
    new_start = center - (target_span / 2)
    new_end = center + (target_span / 2)
    if new_end <= new_start:
        new_end = new_start + timedelta(hours=1)
    return new_start, new_end


def _scaled_decimal_str(value: Any, factor: Decimal) -> str:
    amount = Decimal(str(value))
    return str((amount * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _write_readme(dataset_dir: Path, representative: BenchmarkScenarioSpec, per_class_counts: dict[str, int]) -> None:
    readme = "\n".join(
        [
            f"# Dataset benchmark {dataset_dir.name}",
            "",
            f"- familia: `{representative.family}`",
            f"- camada: `{representative.layer}`",
            f"- seed: `{representative.seed}`",
            f"- ordens por classe: `{per_class_counts}`",
            f"- viaturas: `{representative.n_vehicles}`",
            f"- janela: `{representative.window_profile}`",
            f"- pressao de volume: `{representative.volume_pressure}`",
            f"- pressao financeira: `{representative.cash_pressure}`",
            f"- densidade geografica: `{representative.geo_density}`",
            f"- hipoteses: `{representative.pedagogical_hypothesis}`",
            "",
            "Dataset gerado automaticamente a partir do catalogo declarativo em `data/scenarios/catalog_v1.json`.",
            "",
        ]
    )
    (dataset_dir / "README.md").write_text(readme)


def _materialize_logistics_snapshot(dataset_dir: Path, operation_date: str) -> None:
    matrix_module = _load_matrix_script_module()
    config = matrix_module.MatrixBuildConfig(
        dataset_dir=dataset_dir,
        date=operation_date,
        detour_factor=1.25,
        average_speed_mps=8.5,
        cost_per_km=Decimal("3.00"),
    )
    locations = matrix_module.build_locations(dataset_dir)
    arcs = matrix_module.build_arcs(locations, config)
    payload = {
        "snapshot_id": f"snap-{dataset_dir.name}-{operation_date}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy_name": "synthetic_geodesic_v1",
        "source_name": f"{dataset_dir.name}_source",
        "arcs": arcs,
    }
    source_dir = dataset_dir / "logistics_sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_path = source_dir / f"{operation_date}.json"
    source_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    materializer = LogisticsSnapshotMaterializer(
        JsonFileLogisticsSnapshotSource(source_dir),
        FileSystemSnapshotRepository(dataset_dir / "logistics_snapshots"),
    )
    materializer.materialize(datetime.fromisoformat(operation_date).date())


def _load_matrix_script_module():
    script_path = PROJECT_ROOT / "scripts" / "build_fake_smoke_matrix.py"
    spec = importlib.util.spec_from_file_location("build_fake_smoke_matrix_module", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"nao foi possivel carregar o script de matriz: {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

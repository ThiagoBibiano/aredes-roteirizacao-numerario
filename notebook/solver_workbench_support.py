from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from itertools import cycle
from pathlib import Path
from typing import Any

from roteirizacao import (
    DailyPlanningOrchestrator,
    DatasetPlanningRequest,
    FileSystemSnapshotRepository,
    JsonFileLogisticsSnapshotSource,
    LogisticsSnapshotMaterializer,
)
from roteirizacao.domain.serialization import serialize_value

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DATASETS = {
    "operacao_controlada": PROJECT_ROOT / "data" / "fake_solution",
    "operacao_sob_pressao": PROJECT_ROOT / "data" / "fake_smoke",
}
LEGACY_SCENARIO_ALIASES = {
    "fake_solution": "operacao_controlada",
    "fake_smoke": "operacao_sob_pressao",
}
DEFAULT_SCENARIO = "operacao_controlada"
SCENARIO_LABELS = {
    "operacao_controlada": "Operação Controlada",
    "operacao_sob_pressao": "Operação Sob Pressão",
}


@dataclass(frozen=True)
class ScenarioArtifacts:
    scenario_name: str
    dataset_dir: Path
    contexto: dict[str, Any]
    bases: list[dict[str, Any]]
    pontos: list[dict[str, Any]]
    viaturas: list[dict[str, Any]]
    ordens: list[dict[str, Any]]
    matrix_payload: dict[str, Any]
    positions: dict[str, tuple[float, float]]
    labels: dict[str, str]
    node_kind: dict[str, str]


def scenario_public_label(scenario_name: str) -> str:
    canonical = LEGACY_SCENARIO_ALIASES.get(scenario_name, scenario_name)
    return SCENARIO_LABELS.get(canonical, canonical.replace("_", " ").title())


def resolve_dataset_dir(scenario: str | Path = DEFAULT_SCENARIO) -> tuple[str, Path]:
    if isinstance(scenario, Path):
        resolved = scenario
        scenario_name = scenario.name
    else:
        raw_name = str(scenario)
        canonical_name = LEGACY_SCENARIO_ALIASES.get(raw_name, raw_name)
        resolved = SCENARIO_DATASETS.get(canonical_name, PROJECT_ROOT / raw_name)
        scenario_name = canonical_name

    if not resolved.is_absolute():
        resolved = PROJECT_ROOT / resolved

    for canonical_name, dataset_path in SCENARIO_DATASETS.items():
        if resolved == dataset_path:
            scenario_name = canonical_name
            break

    if not resolved.exists():
        raise FileNotFoundError(f"dataset nao encontrado: {resolved}")

    return scenario_name, resolved


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _load_matrix_script_module():
    script_path = PROJECT_ROOT / "scripts" / "build_fake_smoke_matrix.py"
    spec = importlib.util.spec_from_file_location("build_fake_smoke_matrix_module", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"nao foi possivel carregar o script de matriz: {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def compile_scenario(
    scenario: str | Path = DEFAULT_SCENARIO,
    *,
    detour_factor: float = 1.25,
    average_speed_mps: float = 8.5,
    cost_per_km: str = "3.00",
) -> dict[str, Any]:
    scenario_name, dataset_dir = resolve_dataset_dir(scenario)
    contexto = _read_json(dataset_dir / "contexto.json")
    data_operacao = contexto["data_operacao"]
    matrix_module = _load_matrix_script_module()
    config = matrix_module.MatrixBuildConfig(
        dataset_dir=dataset_dir,
        date=data_operacao,
        detour_factor=detour_factor,
        average_speed_mps=average_speed_mps,
        cost_per_km=Decimal(str(cost_per_km)),
    )
    locations = matrix_module.build_locations(dataset_dir)
    arcs = matrix_module.build_arcs(locations, config)
    dataset_token = scenario_name.strip() or dataset_dir.name.strip() or "cenario"
    payload = {
        "snapshot_id": f"snap-{dataset_token}-{data_operacao}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy_name": "synthetic_geodesic_v1",
        "source_name": f"{dataset_token}_source",
        "arcs": arcs,
    }
    source_path = dataset_dir / "logistics_sources" / f"{data_operacao}.json"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    materializer = LogisticsSnapshotMaterializer(
        JsonFileLogisticsSnapshotSource(dataset_dir / "logistics_sources"),
        FileSystemSnapshotRepository(dataset_dir / "logistics_snapshots"),
    )
    snapshot_result = materializer.materialize(date.fromisoformat(data_operacao))
    return {
        "cenario": scenario_name,
        "dataset_dir": str(dataset_dir),
        "data_operacao": data_operacao,
        "locations": len(locations),
        "arcs": len(arcs),
        "source_path": str(source_path),
        "snapshot_id": snapshot_result.snapshot_id,
        "snapshot_path": str(snapshot_result.snapshot_path),
        "version_path": str(snapshot_result.version_path),
        "manifest_path": str(snapshot_result.manifest_path),
    }


def compile_default_scenarios() -> list[dict[str, Any]]:
    return [
        compile_scenario("operacao_controlada"),
        compile_scenario("operacao_sob_pressao"),
    ]


def load_scenario_artifacts(scenario: str | Path = DEFAULT_SCENARIO) -> ScenarioArtifacts:
    scenario_name, dataset_dir = resolve_dataset_dir(scenario)
    contexto = _read_json(dataset_dir / "contexto.json")
    bases = _read_json(dataset_dir / "bases.json")
    pontos = _read_json(dataset_dir / "pontos.json")
    viaturas = _read_json(dataset_dir / "viaturas.json")
    ordens = _read_json(dataset_dir / "ordens.json")
    data_operacao = contexto["data_operacao"]

    source_path = dataset_dir / "logistics_sources" / f"{data_operacao}.json"
    snapshot_path = dataset_dir / "logistics_snapshots" / f"{data_operacao}.json"
    if source_path.exists():
        matrix_payload = _read_json(source_path)
    elif snapshot_path.exists():
        matrix_payload = _read_json(snapshot_path)
    else:
        raise FileNotFoundError(
            "matriz logistica nao encontrada; gere logistics_sources/<data>.json "
            "ou materialize um snapshot antes de abrir o notebook"
        )

    points_by_id = {item["id_ponto"]: item for item in pontos}
    positions: dict[str, tuple[float, float]] = {}
    labels: dict[str, str] = {}
    node_kind: dict[str, str] = {}

    for base in bases:
        node_id = f"dep-{base['id_base']}"
        positions[node_id] = (float(base["longitude"]), float(base["latitude"]))
        labels[node_id] = str(base.get("nome", base["id_base"]))
        node_kind[node_id] = "base"

    for ordem in ordens:
        ponto = points_by_id[ordem["id_ponto"]]
        node_id = f"no-{ordem['id_ordem']}"
        positions[node_id] = (float(ponto["longitude"]), float(ponto["latitude"]))
        labels[node_id] = str(ponto.get("nome", ordem["id_ponto"]))
        node_kind[node_id] = "ordem"

    return ScenarioArtifacts(
        scenario_name=scenario_name,
        dataset_dir=dataset_dir,
        contexto=contexto,
        bases=bases,
        pontos=pontos,
        viaturas=viaturas,
        ordens=ordens,
        matrix_payload=matrix_payload,
        positions=positions,
        labels=labels,
        node_kind=node_kind,
    )


def summarize_dataset(artifacts: ScenarioArtifacts) -> dict[str, Any]:
    return {
        "cenario": artifacts.scenario_name,
        "cenario_legivel": scenario_public_label(artifacts.scenario_name),
        "dataset_dir": str(artifacts.dataset_dir),
        "data_operacao": artifacts.contexto["data_operacao"],
        "bases": len(artifacts.bases),
        "pontos_catalogados": len(artifacts.pontos),
        "viaturas": len(artifacts.viaturas),
        "ordens_do_dia": len(artifacts.ordens),
        "arcos_matriz": len(artifacts.matrix_payload.get("arcs", [])),
        "estrategia_matriz": artifacts.matrix_payload.get("strategy_name"),
        "fonte_matriz": artifacts.matrix_payload.get("source_name"),
    }


def analyze_scenario(artifacts: ScenarioArtifacts) -> dict[str, Any]:
    ordens = artifacts.ordens
    viaturas = artifacts.viaturas
    total_ordens = len(ordens)
    total_viaturas = len(viaturas)
    total_especiais = sum(1 for ordem in ordens if str(ordem.get("classe_planejamento", "")).lower() == "especial")
    avg_window_hours = (
        round(
            sum(
                (
                    datetime.fromisoformat(str(ordem["fim_janela"]))
                    - datetime.fromisoformat(str(ordem["inicio_janela"]))
                ).total_seconds()
                for ordem in ordens
            )
            / max(total_ordens, 1)
            / 3600,
            2,
        )
        if ordens
        else 0.0
    )
    avg_value = (
        float(sum(Decimal(str(ordem.get("valor_estimado", "0"))) for ordem in ordens) / Decimal(max(total_ordens, 1)))
        if ordens
        else 0.0
    )
    avg_volume = (
        float(sum(Decimal(str(ordem.get("volume_estimado", "0"))) for ordem in ordens) / Decimal(max(total_ordens, 1)))
        if ordens
        else 0.0
    )
    avg_cash_capacity = (
        float(sum(Decimal(str(viatura.get("capacidade_financeira", "0"))) for viatura in viaturas) / Decimal(max(total_viaturas, 1)))
        if viaturas
        else 0.0
    )
    avg_volume_capacity = (
        float(sum(Decimal(str(viatura.get("capacidade_volumetrica", "0"))) for viatura in viaturas) / Decimal(max(total_viaturas, 1)))
        if viaturas
        else 0.0
    )
    cash_pressure_ratio = round(avg_value / avg_cash_capacity, 3) if avg_cash_capacity else 0.0
    volume_pressure_ratio = round(avg_volume / avg_volume_capacity, 3) if avg_volume_capacity else 0.0
    longitudes = [point[0] for point in artifacts.positions.values()]
    latitudes = [point[1] for point in artifacts.positions.values()]
    geo_span = {
        "longitude": round(max(longitudes) - min(longitudes), 4) if longitudes else 0.0,
        "latitude": round(max(latitudes) - min(latitudes), 4) if latitudes else 0.0,
    }
    dominant_bottleneck = "cobertura_balanceada"
    if avg_window_hours <= 3.0:
        dominant_bottleneck = "janela_tempo"
    elif cash_pressure_ratio >= 0.55:
        dominant_bottleneck = "limite_financeiro"
    elif volume_pressure_ratio >= 0.55:
        dominant_bottleneck = "capacidade_volumetrica"
    elif geo_span["longitude"] >= 0.18 or geo_span["latitude"] >= 0.18:
        dominant_bottleneck = "dispersao_geografica"

    return {
        "cenario": artifacts.scenario_name,
        "total_ordens": total_ordens,
        "total_viaturas": total_viaturas,
        "total_especiais": total_especiais,
        "priority_ratio": round(total_especiais / max(total_ordens, 1), 3),
        "avg_window_hours": avg_window_hours,
        "avg_value": round(avg_value, 2),
        "avg_volume": round(avg_volume, 2),
        "cash_pressure_ratio": cash_pressure_ratio,
        "volume_pressure_ratio": volume_pressure_ratio,
        "geo_span_longitude": geo_span["longitude"],
        "geo_span_latitude": geo_span["latitude"],
        "dominant_bottleneck": dominant_bottleneck,
    }


def _require_network_stack():
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - dependency guidance only
        raise RuntimeError(
            "matplotlib nao esta instalado. Rode `.venv/bin/pip install -e '.[dev,notebook]'`."
        ) from exc

    try:
        import networkx as nx
    except ImportError as exc:  # pragma: no cover - dependency guidance only
        raise RuntimeError(
            "networkx nao esta instalado. Rode `.venv/bin/pip install -e '.[dev,notebook]'`."
        ) from exc

    return nx, plt


def _try_import_contextily():
    try:
        import contextily as cx
    except ImportError:  # pragma: no cover - optional rendering dependency
        return None
    return cx


def _set_axis_extent(axis, positions: dict[str, tuple[float, float]], *, pad_ratio: float = 0.10) -> None:
    if not positions:
        return
    longitudes = [point[0] for point in positions.values()]
    latitudes = [point[1] for point in positions.values()]
    min_x = min(longitudes)
    max_x = max(longitudes)
    min_y = min(latitudes)
    max_y = max(latitudes)
    span_x = max(max_x - min_x, 0.01)
    span_y = max(max_y - min_y, 0.01)
    axis.set_xlim(min_x - span_x * pad_ratio, max_x + span_x * pad_ratio)
    axis.set_ylim(min_y - span_y * pad_ratio, max_y + span_y * pad_ratio)


def _maybe_add_basemap(axis, positions: dict[str, tuple[float, float]]) -> bool:
    cx = _try_import_contextily()
    if cx is None:
        return False
    _set_axis_extent(axis, positions)
    try:
        cx.add_basemap(
            axis,
            crs="EPSG:4326",
            source=cx.providers.CartoDB.PositronNoLabels,
            attribution=False,
        )
    except Exception:  # pragma: no cover - tile/network/runtime dependent
        return False
    return True


def build_base_graph(artifacts: ScenarioArtifacts):
    nx, _ = _require_network_stack()
    graph = nx.DiGraph()
    for node_id, position in artifacts.positions.items():
        graph.add_node(
            node_id,
            pos=position,
            label=artifacts.labels.get(node_id, node_id),
            kind=artifacts.node_kind.get(node_id, "ordem"),
        )

    for arc in artifacts.matrix_payload.get("arcs", []):
        origem = arc["id_origem"]
        destino = arc["id_destino"]
        if origem not in artifacts.positions or destino not in artifacts.positions:
            continue
        graph.add_edge(
            origem,
            destino,
            distancia_metros=int(arc["distancia_metros"]),
            tempo_segundos=int(arc["tempo_segundos"]),
            custo=float(arc["custo"]),
        )
    return graph


def run_scenario(
    scenario: str | Path = DEFAULT_SCENARIO,
    *,
    max_iterations: int = 50,
    seed: int = 1,
    materialize_snapshot: bool = True,
    collect_stats: bool = False,
    display: bool = False,
):
    _, dataset_dir = resolve_dataset_dir(scenario)
    orchestrator = DailyPlanningOrchestrator()
    return orchestrator.run(
        DatasetPlanningRequest(
            dataset_dir=dataset_dir,
            materialize_snapshot=materialize_snapshot,
            max_iterations=max_iterations,
            seed=seed,
            collect_stats=collect_stats,
            display=display,
        )
    )


def summarize_orchestration(orchestration) -> dict[str, Any]:
    result = orchestration.resultado_planejamento
    fleet_summary = summarize_fleet_usage(orchestration)
    return {
        "id_execucao": result.id_execucao,
        "status_final": result.status_final.value,
        "hash_cenario": orchestration.hash_cenario,
        "reused_cached_result": orchestration.reused_cached_result,
        "recovered_previous_context": orchestration.recovered_previous_context,
        "attempt_number": orchestration.attempt_number,
        "total_rotas": result.resumo_operacional.total_rotas,
        "rotas_suprimento": result.resumo_operacional.total_rotas_suprimento,
        "rotas_recolhimento": result.resumo_operacional.total_rotas_recolhimento,
        "ordens_planejadas": result.resumo_operacional.total_ordens_planejadas,
        "ordens_nao_atendidas": result.resumo_operacional.total_ordens_nao_atendidas,
        "taxa_atendimento": str(result.kpi_operacional.taxa_atendimento),
        "utilizacao_frota": str(result.kpi_operacional.utilizacao_frota),
        "viaturas_acionadas_unicas": result.kpi_operacional.viaturas_acionadas,
        "alocacoes_viatura_rota": fleet_summary["alocacoes_viatura_rota"],
        "viaturas_reutilizadas": fleet_summary["viaturas_reutilizadas"],
        "viaturas_reutilizadas_entre_classes": fleet_summary["viaturas_reutilizadas_entre_classes"],
        "ids_viaturas_reutilizadas_entre_classes": fleet_summary["ids_viaturas_reutilizadas_entre_classes"],
        "custo_total_estimado": str(result.kpi_gerencial.custo_total_estimado),
        "resultado_json": str(orchestration.result_path),
        "observacao_frota": fleet_summary["leitura_correta"],
    }


def run_and_summarize(
    scenario: str | Path,
    *,
    max_iterations: int = 50,
    seed: int = 1,
    materialize_snapshot: bool = True,
) -> dict[str, Any]:
    summary = summarize_orchestration(
        run_scenario(
            scenario,
            max_iterations=max_iterations,
            seed=seed,
            materialize_snapshot=materialize_snapshot,
        )
    )
    summary["cenario"] = resolve_dataset_dir(scenario)[0]
    return summary


def compare_default_scenarios(
    *,
    max_iterations: int = 50,
    seed: int = 1,
    materialize_snapshot: bool = True,
) -> list[dict[str, Any]]:
    return [
        run_and_summarize(
            "operacao_controlada",
            max_iterations=max_iterations,
            seed=seed,
            materialize_snapshot=materialize_snapshot,
        ),
        run_and_summarize(
            "operacao_sob_pressao",
            max_iterations=max_iterations,
            seed=seed,
            materialize_snapshot=materialize_snapshot,
        ),
    ]


def _iter_routes(orchestration):
    result = orchestration.resultado_planejamento
    yield from result.rotas_suprimento
    yield from result.rotas_recolhimento


def summarize_fleet_usage(orchestration) -> dict[str, Any]:
    route_rows = route_sequences(orchestration)
    vehicle_counter = Counter(row["id_viatura"] for row in route_rows)
    classes_by_vehicle: dict[str, set[str]] = {}
    for row in route_rows:
        classes_by_vehicle.setdefault(row["id_viatura"], set()).add(row["classe_operacional"])

    reused_vehicle_ids = sorted(vehicle_id for vehicle_id, count in vehicle_counter.items() if count > 1)
    reused_between_classes = sorted(
        vehicle_id for vehicle_id, classes in classes_by_vehicle.items()
        if len(classes) > 1
    )
    unique_vehicles = len(vehicle_counter)
    total_routes = len(route_rows)
    return {
        "alocacoes_viatura_rota": total_routes,
        "viaturas_unicas": unique_vehicles,
        "viaturas_reutilizadas": len(reused_vehicle_ids),
        "viaturas_reutilizadas_entre_classes": len(reused_between_classes),
        "ids_viaturas_reutilizadas": reused_vehicle_ids,
        "ids_viaturas_reutilizadas_entre_classes": reused_between_classes,
        "rotas_por_viatura_unica": 0.0 if unique_vehicles == 0 else round(total_routes / unique_vehicles, 2),
        "leitura_correta": (
            "Suprimento e recolhimento são resolvidos em instâncias separadas. "
            "Por isso, o mesmo ID de viatura pode aparecer em mais de uma rota e "
            "`viaturas_acionadas_unicas` pode ser menor que `total_rotas`."
        ),
    }


def fleet_assignment_rows(orchestration, *, only_reused: bool = True) -> list[dict[str, Any]]:
    route_rows = route_sequences(orchestration)
    by_vehicle: dict[str, dict[str, Any]] = {}
    for row in route_rows:
        vehicle_id = row["id_viatura"]
        entry = by_vehicle.setdefault(
            vehicle_id,
            {"Viatura": vehicle_id, "Classes": set(), "Rotas": [], "Total de rotas": 0},
        )
        entry["Classes"].add(row["classe_operacional"])
        entry["Rotas"].append(row["id_rota"])
        entry["Total de rotas"] += 1

    rows: list[dict[str, Any]] = []
    for vehicle_id in sorted(by_vehicle):
        entry = by_vehicle[vehicle_id]
        if only_reused and entry["Total de rotas"] <= 1:
            continue
        classes = sorted(entry["Classes"])
        rows.append(
            {
                "Viatura": vehicle_id,
                "Classes": " + ".join(classes),
                "Total de rotas": entry["Total de rotas"],
                "Rotas": ", ".join(entry["Rotas"]),
                "Reuso entre classes": "sim" if len(classes) > 1 else "não",
            }
        )
    return rows


def _route_color_map(orchestration) -> dict[str, tuple[float, float, float, float]]:
    _, plt = _require_network_stack()
    palette = cycle(plt.cm.tab10.colors)
    return {route.id_rota: next(palette) for route in _iter_routes(orchestration)}


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _order_metadata_map(artifacts: ScenarioArtifacts) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for ordem in artifacts.ordens:
        ordem_id = str(ordem["id_ordem"])
        node_id = f"no-{ordem_id}"
        label = artifacts.labels.get(node_id, ordem_id)
        metadata[ordem_id] = {
            "id_ordem": ordem_id,
            "id_ponto": str(ordem.get("id_ponto", "")),
            "node_id": node_id,
            "label": label,
            "label_short": label.split(" - ")[0],
            "tipo_servico": str(ordem.get("tipo_servico", "desconhecido")).lower(),
            "classe_planejamento": str(ordem.get("classe_planejamento", "nao_informada")).lower(),
            "criticidade": str(ordem.get("criticidade", "nao_informada")).lower(),
            "valor_estimado": str(ordem.get("valor_estimado", "0")),
            "volume_estimado": str(ordem.get("volume_estimado", "0")),
        }
    return metadata


def _service_style(tipo_servico: str) -> dict[str, Any]:
    normalized = tipo_servico.lower()
    if normalized == "suprimento":
        return {
            "marker": "^",
            "fill": "#2a9d8f",
            "line_style": "solid",
            "service_label": "SUP",
        }
    if normalized == "recolhimento":
        return {
            "marker": "v",
            "fill": "#e76f51",
            "line_style": (0, (6, 4)),
            "service_label": "REC",
        }
    return {
        "marker": "o",
        "fill": "#7d8597",
        "line_style": "solid",
        "service_label": normalized[:3].upper(),
    }


def _route_short_label(route_id: str) -> str:
    suffix = route_id.rsplit("-", 1)[-1]
    if suffix.isdigit():
        return f"R{int(suffix):02d}"
    return route_id[-8:]


def _format_brl(value: Any) -> str:
    amount = Decimal(str(value))
    formatted = f"{amount:,.0f}"
    return formatted.replace(",", ".")


def _planning_label(classe_planejamento: str) -> str:
    normalized = classe_planejamento.lower()
    if normalized == "especial":
        return "ESP"
    if normalized == "eventual":
        return "EVT"
    if normalized == "padrao":
        return "PAD"
    if normalized == "nao_informada":
        return "N/I"
    return normalized[:3].upper()


def _build_solution_node_state(orchestration, artifacts: ScenarioArtifacts) -> dict[str, dict[str, Any]]:
    node_state: dict[str, dict[str, Any]] = {}
    order_metadata = _order_metadata_map(artifacts)

    for route_index, route in enumerate(_iter_routes(orchestration), start=1):
        route_label = _route_short_label(route.id_rota)
        route_class = _enum_value(route.classe_operacional).lower()
        style = _service_style(route_class)
        for parada in route.paradas:
            metadata = order_metadata.get(parada.id_ordem, {}).copy()
            metadata.update(
                {
                    "id_rota": route.id_rota,
                    "route_label": route_label,
                    "route_index": route_index,
                    "vehicle_id": route.id_viatura,
                    "sequence": parada.sequencia,
                    "tipo_servico": _enum_value(parada.tipo_servico).lower(),
                    "criticidade": _enum_value(parada.criticidade).lower(),
                    "line_style": style["line_style"],
                    "service_label": style["service_label"],
                    "served": True,
                }
            )
            node_state[parada.id_no] = metadata

    result = orchestration.resultado_planejamento
    for ordem in result.ordens_nao_atendidas:
        node_id = ordem.id_no
        metadata = order_metadata.get(ordem.id_ordem, {}).copy()
        metadata.update(
            {
                "id_ordem": ordem.id_ordem,
                "node_id": node_id,
                "tipo_servico": _enum_value(ordem.tipo_servico).lower(),
                "criticidade": _enum_value(ordem.criticidade).lower(),
                "served": False,
                "service_label": _service_style(_enum_value(ordem.tipo_servico))["service_label"],
            }
        )
        node_state[node_id] = metadata

    return node_state


def _draw_semantic_legend(axis, *, include_unserved: bool, include_routes: bool) -> None:
    from matplotlib.lines import Line2D

    handles = [
        Line2D(
            [0],
            [0],
            marker="s",
            linestyle="None",
            markerfacecolor="#12355b",
            markeredgecolor="white",
            markeredgewidth=1.2,
            markersize=10,
            label="Base",
        ),
        Line2D(
            [0],
            [0],
            marker="^",
            linestyle="None",
            markerfacecolor="#2a9d8f",
            markeredgecolor="white",
            markeredgewidth=1.0,
            markersize=10,
            label="Suprimento",
        ),
        Line2D(
            [0],
            [0],
            marker="v",
            linestyle="None",
            markerfacecolor="#e76f51",
            markeredgecolor="white",
            markeredgewidth=1.0,
            markersize=10,
            label="Recolhimento",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="None",
            markerfacecolor="#ffffff",
            markeredgecolor="#d4a017",
            markeredgewidth=2.0,
            markersize=10,
            label="Especial",
        ),
    ]

    if include_unserved:
        handles.append(
            Line2D(
                [0],
                [0],
                marker="X",
                linestyle="None",
                markerfacecolor="#cbd5e1",
                markeredgecolor="#475569",
                markeredgewidth=1.0,
                markersize=9,
                label="Não atendida",
            )
        )
    if include_routes:
        handles.extend(
            [
                Line2D(
                    [0, 1],
                    [0, 0],
                    color="#64748b",
                    linewidth=2.4,
                    linestyle="solid",
                    label="Rota de suprimento",
                ),
                Line2D(
                    [0, 1],
                    [0, 0],
                    color="#64748b",
                    linewidth=2.4,
                    linestyle=(0, (6, 4)),
                    label="Rota de recolhimento",
                ),
            ]
        )
    axis.legend(handles=handles, loc="upper left", frameon=True, fontsize=8.5)


def _draw_solution_semantic_legend(axis) -> None:
    _draw_semantic_legend(axis, include_unserved=True, include_routes=True)


def _draw_base_semantic_legend(axis) -> None:
    _draw_semantic_legend(axis, include_unserved=False, include_routes=False)


def _draw_route_summary_panel(axis, orchestration, node_state: dict[str, dict[str, Any]], colors) -> None:
    axis.axis("off")

    routes = list(_iter_routes(orchestration))
    served_nodes = [item for item in node_state.values() if item.get("served")]
    special_served = sum(1 for item in served_nodes if item.get("classe_planejamento") == "especial")
    unserved_count = sum(1 for item in node_state.values() if item.get("served") is False)
    services = Counter(item.get("tipo_servico", "desconhecido") for item in served_nodes)

    header = (
        f"Rotas: {len(routes)}\n"
        f"Atendidas: {len(served_nodes)} | Especiais: {special_served}\n"
        f"SUP: {services.get('suprimento', 0)} | REC: {services.get('recolhimento', 0)}\n"
        f"Não atendidas: {unserved_count}"
    )
    axis.text(
        0.0,
        1.0,
        header,
        va="top",
        fontsize=9,
        color="#243b53",
        bbox={"facecolor": "#f8fafc", "edgecolor": "#cbd5e1", "boxstyle": "round,pad=0.45"},
    )

    y_position = 0.78
    displayed_routes = 0
    for route in routes:
        route_nodes = [item for item in node_state.values() if item.get("id_rota") == route.id_rota]
        if not route_nodes:
            continue
        special_count = sum(1 for item in route_nodes if item.get("classe_planejamento") == "especial")
        route_class = _enum_value(route.classe_operacional).lower()
        summary = (
            f"{_route_short_label(route.id_rota)} | {route.id_viatura}\n"
            f"{route_class} | {len(route.paradas)} parada(s) | {special_count} especial(is)\n"
            f"R$ {_format_brl(route.custo_estimado)} | {route.distancia_estimada / 1000:.1f} km"
        )
        axis.text(
            0.0,
            y_position,
            summary,
            va="top",
            fontsize=8.4,
            color="#102a43",
            bbox={
                "facecolor": (*colors[route.id_rota][:3], 0.12),
                "edgecolor": colors[route.id_rota],
                "boxstyle": "round,pad=0.4",
            },
        )
        displayed_routes += 1
        y_position -= 0.145
        if y_position < 0.05:
            break

    hidden_routes = len(routes) - displayed_routes
    if hidden_routes > 0:
        axis.text(0.0, max(y_position, 0.03), f"+ {hidden_routes} rota(s) fora do painel", fontsize=8.2, color="#52606d")


def build_solution_graph(orchestration, artifacts: ScenarioArtifacts, *, include_return_to_base: bool = True):
    nx, _ = _require_network_stack()
    graph = nx.MultiDiGraph()

    for node_id, position in artifacts.positions.items():
        graph.add_node(
            node_id,
            pos=position,
            label=artifacts.labels.get(node_id, node_id),
            kind=artifacts.node_kind.get(node_id, "ordem"),
        )

    colors = _route_color_map(orchestration)
    for route in _iter_routes(orchestration):
        route_nodes = [f"dep-{route.id_base}", *[parada.id_no for parada in route.paradas]]
        if include_return_to_base:
            route_nodes.append(f"dep-{route.id_base}")

        for sequence, (origem, destino) in enumerate(zip(route_nodes, route_nodes[1:]), start=1):
            if origem not in artifacts.positions or destino not in artifacts.positions:
                continue
            graph.add_edge(
                origem,
                destino,
                key=f"{route.id_rota}:{sequence}",
                route_id=route.id_rota,
                vehicle_id=route.id_viatura,
                classe_operacional=route.classe_operacional.value,
                sequence=sequence,
                color=colors[route.id_rota],
            )

    return graph


def route_sequences(orchestration, *, include_return_to_base: bool = True) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for route in _iter_routes(orchestration):
        point_chain = [route.id_base, *[parada.id_ponto for parada in route.paradas]]
        if include_return_to_base:
            point_chain.append(route.id_base)
        rows.append(
            {
                "id_rota": route.id_rota,
                "id_viatura": route.id_viatura,
                "classe_operacional": route.classe_operacional.value,
                "quantidade_paradas": len(route.paradas),
                "inicio_previsto": route.inicio_previsto.isoformat(),
                "fim_previsto": route.fim_previsto.isoformat(),
                "sequencia": " -> ".join(point_chain),
                "ordens": [parada.id_ordem for parada in route.paradas],
            }
        )
    return rows


def serialize_orchestration(orchestration) -> dict[str, Any]:
    return {
        "hash_cenario": orchestration.hash_cenario,
        "reused_cached_result": orchestration.reused_cached_result,
        "recovered_previous_context": orchestration.recovered_previous_context,
        "attempt_number": orchestration.attempt_number,
        "output_path": str(orchestration.output_path),
        "result_path": str(orchestration.result_path),
        "state_path": str(orchestration.state_path),
        "scenario_path": str(orchestration.scenario_path),
        "manifest_path": str(orchestration.manifest_path),
        "snapshot_materialization": None
        if orchestration.snapshot_materialization is None
        else serialize_value(orchestration.snapshot_materialization),
        "result": serialize_value(orchestration.resultado_planejamento),
    }


def build_takeaway(orchestration, artifacts: ScenarioArtifacts) -> str:
    analysis = analyze_scenario(artifacts)
    summary = summarize_orchestration(orchestration)
    bottleneck = {
        "cobertura_balanceada": "cobertura balanceada",
        "janela_tempo": "janela de tempo",
        "limite_financeiro": "limite financeiro",
        "capacidade_volumetrica": "capacidade volumétrica",
        "dispersao_geografica": "dispersão geográfica",
    }.get(analysis["dominant_bottleneck"], analysis["dominant_bottleneck"].replace("_", " "))
    scenario_label = scenario_public_label(analysis["cenario"])
    status_label = {
        "concluida": "concluída",
        "concluida_com_ressalvas": "concluída com ressalvas",
        "inviavel": "inviável",
        "erro": "erro",
    }.get(summary["status_final"], str(summary["status_final"]).replace("_", " "))
    return (
        f"No cenário {scenario_label}, o gargalo dominante é {bottleneck}. "
        f"O solver encerrou com status {status_label}, planejou {summary['ordens_planejadas']} ordem(ns), "
        f"deixou {summary['ordens_nao_atendidas']} não atendida(s) e acionou {summary['total_rotas']} rota(s). "
        f"A leitura principal para apresentação é comparar cobertura e custo com esse gargalo em mente, "
        f"sem tratar a sequência exata de visitas como critério científico principal."
    )


def plot_base_graph(
    artifacts: ScenarioArtifacts,
    *,
    figsize: tuple[int, int] = (12, 8),
    edge_alpha: float = 0.08,
    with_labels: bool = True,
    with_basemap: bool = False,
):
    nx, plt = _require_network_stack()
    graph = build_base_graph(artifacts)
    positions = nx.get_node_attributes(graph, "pos")

    figure, axis = plt.subplots(figsize=figsize)
    basemap_added = _maybe_add_basemap(axis, positions) if with_basemap else False
    title_suffix = " com basemap" if basemap_added else ""
    axis.set_title(f"Rede-base do cenário {scenario_public_label(artifacts.scenario_name)}{title_suffix}")

    base_nodes = [node for node, kind in artifacts.node_kind.items() if kind == "base"]
    order_metadata = _order_metadata_map(artifacts)

    nx.draw_networkx_edges(
        graph,
        pos=positions,
        ax=axis,
        arrows=False,
        edge_color="#9aa5b1",
        alpha=0.22 if basemap_added else edge_alpha,
        width=0.8,
    )
    nx.draw_networkx_nodes(
        graph,
        pos=positions,
        nodelist=base_nodes,
        ax=axis,
        node_color="#12355b",
        node_size=420,
        node_shape="s",
        edgecolors="white",
        linewidths=1.2,
    )

    grouped_order_nodes: dict[tuple[str, str], list[str]] = {}
    for ordem_id, metadata in order_metadata.items():
        key = (
            metadata.get("tipo_servico", "desconhecido"),
            metadata.get("classe_planejamento", "nao_informada"),
        )
        grouped_order_nodes.setdefault(key, []).append(f"no-{ordem_id}")

    for (tipo_servico, classe_planejamento), node_ids in grouped_order_nodes.items():
        style = _service_style(tipo_servico)
        edge_color = "#d4a017" if classe_planejamento == "especial" else "white"
        line_width = 2.2 if classe_planejamento == "especial" else 0.9
        node_size = 360 if classe_planejamento == "especial" else 300
        nx.draw_networkx_nodes(
            graph,
            pos=positions,
            nodelist=node_ids,
            ax=axis,
            node_color=style["fill"],
            node_size=node_size,
            node_shape=style["marker"],
            edgecolors=edge_color,
            linewidths=line_width,
        )

    if with_labels:
        label_map = {
            node_id: artifacts.labels[node_id].split(" - ")[0]
            for node_id in positions
        }
        nx.draw_networkx_labels(graph, pos=positions, labels=label_map, ax=axis, font_size=7)

    _set_axis_extent(axis, positions)
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    if with_basemap and not basemap_added:
        axis.text(
            0.02,
            0.98,
            "Basemap indisponível; renderização mantida em networkx puro.",
            transform=axis.transAxes,
            va="top",
            fontsize=9,
            bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "#cccccc"},
        )
    _draw_base_semantic_legend(axis)
    axis.grid(alpha=0.2)
    figure.tight_layout()
    return figure, axis


def plot_solution_graph(
    orchestration,
    artifacts: ScenarioArtifacts,
    *,
    include_return_to_base: bool = True,
    include_base_graph: bool = True,
    figsize: tuple[int, int] = (12, 8),
    with_basemap: bool = False,
    show_order_details: bool = True,
    show_route_summary: bool = True,
    show_unserved_orders: bool = True,
):
    nx, plt = _require_network_stack()
    base_graph = build_base_graph(artifacts)
    solution_graph = build_solution_graph(
        orchestration,
        artifacts,
        include_return_to_base=include_return_to_base,
    )
    positions = nx.get_node_attributes(base_graph, "pos")
    colors = _route_color_map(orchestration)
    node_state = _build_solution_node_state(orchestration, artifacts)
    result = orchestration.resultado_planejamento

    if show_route_summary:
        figure = plt.figure(figsize=figsize, constrained_layout=True)
        grid = figure.add_gridspec(1, 2, width_ratios=(4.8, 1.7))
        axis = figure.add_subplot(grid[0, 0])
        summary_axis = figure.add_subplot(grid[0, 1])
    else:
        figure, axis = plt.subplots(figsize=figsize, constrained_layout=True)
        summary_axis = None

    basemap_added = _maybe_add_basemap(axis, positions) if with_basemap else False
    title_suffix = " com basemap" if basemap_added else ""
    subtitle = (
        f"{result.resumo_operacional.total_ordens_planejadas} ordem(ns) planejada(s)"
        f" | {result.resumo_operacional.total_ordens_nao_atendidas} não atendida(s)"
    )
    axis.set_title(f"Rede escolhida pelo solver{title_suffix}\n{subtitle}", loc="left")

    if include_base_graph:
        nx.draw_networkx_edges(
            base_graph,
            pos=positions,
            ax=axis,
            arrows=False,
            edge_color="#d9dee5",
            alpha=0.22 if basemap_added else 0.12,
            width=0.8,
        )

    base_nodes = [node for node, kind in artifacts.node_kind.items() if kind == "base"]
    nx.draw_networkx_nodes(
        base_graph,
        pos=positions,
        nodelist=base_nodes,
        ax=axis,
        node_color="#12355b",
        node_size=420,
        node_shape="s",
        edgecolors="white",
        linewidths=1.2,
    )

    for route_id, color in colors.items():
        route_edges = [
            (origem, destino, key)
            for origem, destino, key, attrs in solution_graph.edges(keys=True, data=True)
            if attrs["route_id"] == route_id
        ]
        route_style = "solid"
        for _, _, _, attrs in solution_graph.edges(keys=True, data=True):
            if attrs["route_id"] == route_id:
                route_style = _service_style(attrs["classe_operacional"])["line_style"]
                break
        nx.draw_networkx_edges(
            solution_graph,
            pos=positions,
            ax=axis,
            edgelist=route_edges,
            edge_color=["#ffffff"],
            alpha=0.85,
            width=5.6,
            arrows=True,
            arrowsize=18,
            style=route_style,
            connectionstyle="arc3,rad=0.06",
        )
        nx.draw_networkx_edges(
            solution_graph,
            pos=positions,
            ax=axis,
            edgelist=route_edges,
            edge_color=[color],
            alpha=0.95,
            width=2.8,
            arrows=True,
            arrowsize=16,
            style=route_style,
            connectionstyle="arc3,rad=0.06",
        )

    grouped_order_nodes: dict[tuple[str, str, bool], list[str]] = {}
    for node_id, metadata in node_state.items():
        if metadata.get("served") is False and not show_unserved_orders:
            continue
        key = (
            metadata.get("tipo_servico", "desconhecido"),
            metadata.get("classe_planejamento", "nao_informada"),
            bool(metadata.get("served")),
        )
        grouped_order_nodes.setdefault(key, []).append(node_id)

    for (tipo_servico, classe_planejamento, served), node_ids in grouped_order_nodes.items():
        style = _service_style(tipo_servico)
        if served:
            edge_color = "#d4a017" if classe_planejamento == "especial" else "white"
            line_width = 2.2 if classe_planejamento == "especial" else 0.9
            node_size = 380 if classe_planejamento == "especial" else 310
            node_color = style["fill"]
            node_shape = style["marker"]
        else:
            edge_color = "#475569"
            line_width = 1.1
            node_size = 300
            node_color = "#cbd5e1"
            node_shape = "X"

        nx.draw_networkx_nodes(
            base_graph,
            pos=positions,
            nodelist=node_ids,
            ax=axis,
            node_color=node_color,
            node_size=node_size,
            node_shape=node_shape,
            edgecolors=edge_color,
            linewidths=line_width,
            alpha=0.98 if served else 0.92,
        )

    for node_id, metadata in node_state.items():
        if metadata.get("served") is False and not show_unserved_orders:
            continue
        position = positions.get(node_id)
        if position is None:
            continue
        x_coord, y_coord = position
        sequence_label = "X" if metadata.get("served") is False else str(metadata.get("sequence", "?"))
        axis.text(
            x_coord,
            y_coord,
            sequence_label,
            ha="center",
            va="center",
            fontsize=7.5,
            color="white" if metadata.get("served") else "#102a43",
            fontweight="bold",
            zorder=6,
        )

    base_label_map = {node_id: artifacts.labels[node_id].split(" - ")[0] for node_id in base_nodes}
    nx.draw_networkx_labels(base_graph, pos=positions, labels=base_label_map, ax=axis, font_size=8, font_color="#102a43")

    if show_order_details:
        longitude_span = max(point[0] for point in positions.values()) - min(point[0] for point in positions.values())
        latitude_span = max(point[1] for point in positions.values()) - min(point[1] for point in positions.values())
        offset_x = max(longitude_span * 0.012, 0.0035)
        offset_y = max(latitude_span * 0.010, 0.0025)
        for index, (node_id, metadata) in enumerate(node_state.items()):
            if metadata.get("served") is False and not show_unserved_orders:
                continue
            position = positions.get(node_id)
            if position is None:
                continue
            x_coord, y_coord = position
            label_prefix = metadata.get("label_short", metadata.get("id_ordem", node_id))
            planning_label = _planning_label(metadata.get("classe_planejamento", "nao_informada"))
            status_label = "NÃO ATENDIDA" if metadata.get("served") is False else metadata.get("route_label", "")
            detail_label = (
                f"{metadata.get('service_label', '---')} | {planning_label} | {metadata.get('criticidade', '--').upper()}\n"
                f"{status_label} | R$ {_format_brl(metadata.get('valor_estimado', '0'))}"
            )
            vertical_sign = 1 if index % 2 == 0 else -1
            axis.text(
                x_coord + offset_x,
                y_coord + (offset_y * vertical_sign),
                f"{label_prefix}\n{detail_label}",
                ha="left",
                va="center",
                fontsize=7.4,
                color="#102a43",
                zorder=7,
                bbox={
                    "facecolor": (1, 1, 1, 0.9),
                    "edgecolor": "#d9e2ec",
                    "boxstyle": "round,pad=0.28",
                },
            )

    _set_axis_extent(axis, positions)
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    if with_basemap and not basemap_added:
        axis.text(
            0.02,
            0.98,
            "Basemap indisponível; renderização mantida em networkx puro.",
            transform=axis.transAxes,
            va="top",
            fontsize=9,
            bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "#cccccc"},
        )
    _draw_solution_semantic_legend(axis)
    if summary_axis is not None:
        _draw_route_summary_panel(summary_axis, orchestration, node_state, colors)
    axis.grid(alpha=0.2)
    return figure, axis


def plot_kpi_dashboard(orchestration, *, figsize: tuple[int, int] = (12, 4)):
    _, plt = _require_network_stack()
    result = orchestration.resultado_planejamento
    fleet_summary = summarize_fleet_usage(orchestration)
    figure, axes = plt.subplots(1, 4, figsize=figsize, constrained_layout=True)
    cards = [
        ("Taxa de atendimento", f"{Decimal(str(result.kpi_operacional.taxa_atendimento)) * 100:.1f}%"),
        ("Rotas / viaturas únicas", f"{fleet_summary['alocacoes_viatura_rota']} / {fleet_summary['viaturas_unicas']}"),
        ("Distância total", f"{result.kpi_operacional.distancia_total_estimada / 1000:.1f} km"),
        ("Custo estimado", f"R$ {_format_brl(result.kpi_gerencial.custo_total_estimado)}"),
    ]
    palette = ["#12355b", "#2a9d8f", "#f4a261", "#bc3908"]
    for axis, (title, value), color in zip(axes, cards, palette):
        axis.axis("off")
        axis.add_patch(plt.Rectangle((0, 0), 1, 1, color=color, alpha=0.92, transform=axis.transAxes))
        axis.text(0.08, 0.68, title, color="white", fontsize=11, fontweight="bold", transform=axis.transAxes)
        axis.text(0.08, 0.32, value, color="white", fontsize=22, fontweight="bold", transform=axis.transAxes)
    if fleet_summary["viaturas_reutilizadas_entre_classes"] > 0:
        figure.text(
            0.5,
            0.01,
            "Leitura correta: o mesmo ID de viatura pode reaparecer porque suprimento e recolhimento são resolvidos separadamente.",
            ha="center",
            va="bottom",
            fontsize=8.8,
            color="#475569",
        )
    return figure, axes


def export_presentation_bundle(
    orchestration,
    artifacts: ScenarioArtifacts,
    *,
    output_dir: str | Path,
    with_basemap: bool = False,
    show_order_details: bool = True,
) -> dict[str, str]:
    _, plt = _require_network_stack()
    output_path = Path(output_dir)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.mkdir(parents=True, exist_ok=True)

    base_figure, _ = plot_base_graph(artifacts, with_basemap=with_basemap)
    base_path = output_path / f"{artifacts.scenario_name}_rede_base.png"
    base_figure.savefig(base_path, dpi=180, bbox_inches="tight")
    plt.close(base_figure)

    solution_figure, _ = plot_solution_graph(
        orchestration,
        artifacts,
        with_basemap=with_basemap,
        show_order_details=show_order_details,
    )
    solution_path = output_path / f"{artifacts.scenario_name}_solucao.png"
    solution_figure.savefig(solution_path, dpi=180, bbox_inches="tight")
    plt.close(solution_figure)

    kpi_figure, _ = plot_kpi_dashboard(orchestration)
    kpi_path = output_path / f"{artifacts.scenario_name}_kpis.png"
    kpi_figure.savefig(kpi_path, dpi=180, bbox_inches="tight")
    plt.close(kpi_figure)

    takeaway_path = output_path / f"{artifacts.scenario_name}_takeaway.txt"
    takeaway_path.write_text(build_takeaway(orchestration, artifacts) + "\n")
    return {
        "base_map": str(base_path),
        "solution_map": str(solution_path),
        "kpi_panel": str(kpi_path),
        "takeaway": str(takeaway_path),
    }

from __future__ import annotations

import importlib.util
import json
import sys
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
DEFAULT_SCENARIOS = {
    "fake_solution": PROJECT_ROOT / "data" / "fake_solution",
    "fake_smoke": PROJECT_ROOT / "data" / "fake_smoke",
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


def resolve_dataset_dir(scenario: str | Path = "fake_solution") -> tuple[str, Path]:
    if isinstance(scenario, Path):
        resolved = scenario
        scenario_name = scenario.name
    else:
        resolved = DEFAULT_SCENARIOS.get(scenario, PROJECT_ROOT / str(scenario))
        scenario_name = Path(str(scenario)).name

    if not resolved.is_absolute():
        resolved = PROJECT_ROOT / resolved

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
    scenario: str | Path = "fake_solution",
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
    dataset_token = dataset_dir.name.strip() or "fake"
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
        compile_scenario("fake_solution"),
        compile_scenario("fake_smoke"),
    ]


def load_scenario_artifacts(scenario: str | Path = "fake_solution") -> ScenarioArtifacts:
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
    scenario: str | Path = "fake_solution",
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
        "custo_total_estimado": str(result.kpi_gerencial.custo_total_estimado),
        "resultado_json": str(orchestration.result_path),
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
            "fake_solution",
            max_iterations=max_iterations,
            seed=seed,
            materialize_snapshot=materialize_snapshot,
        ),
        run_and_summarize(
            "fake_smoke",
            max_iterations=max_iterations,
            seed=seed,
            materialize_snapshot=materialize_snapshot,
        ),
    ]


def _iter_routes(orchestration):
    result = orchestration.resultado_planejamento
    yield from result.rotas_suprimento
    yield from result.rotas_recolhimento


def _route_color_map(orchestration) -> dict[str, tuple[float, float, float, float]]:
    _, plt = _require_network_stack()
    palette = cycle(plt.cm.tab10.colors)
    return {route.id_rota: next(palette) for route in _iter_routes(orchestration)}


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
    axis.set_title(f"Rede-base do cenario {artifacts.scenario_name}{title_suffix}")

    base_nodes = [node for node, kind in artifacts.node_kind.items() if kind == "base"]
    order_nodes = [node for node, kind in artifacts.node_kind.items() if kind == "ordem"]

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
        edgecolors="white",
        linewidths=1.2,
        label="Bases",
    )
    nx.draw_networkx_nodes(
        graph,
        pos=positions,
        nodelist=order_nodes,
        ax=axis,
        node_color="#f8961e",
        node_size=260,
        edgecolors="white",
        linewidths=0.8,
        label="Ordens do dia",
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
            "Basemap indisponivel; renderizacao mantida em networkx puro.",
            transform=axis.transAxes,
            va="top",
            fontsize=9,
            bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "#cccccc"},
        )
    axis.legend(loc="best")
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

    figure, axis = plt.subplots(figsize=figsize)
    basemap_added = _maybe_add_basemap(axis, positions) if with_basemap else False
    title_suffix = " com basemap" if basemap_added else ""
    axis.set_title(f"Rede escolhida pelo solver{title_suffix}")

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
    order_nodes = [node for node, kind in artifacts.node_kind.items() if kind == "ordem"]
    nx.draw_networkx_nodes(
        base_graph,
        pos=positions,
        nodelist=base_nodes,
        ax=axis,
        node_color="#12355b",
        node_size=420,
        edgecolors="white",
        linewidths=1.2,
        label="Bases",
    )
    nx.draw_networkx_nodes(
        base_graph,
        pos=positions,
        nodelist=order_nodes,
        ax=axis,
        node_color="#f8d7a3",
        node_size=240,
        edgecolors="white",
        linewidths=0.7,
        label="Ordens do dia",
    )

    for route_id, color in colors.items():
        route_edges = [
            (origem, destino, key)
            for origem, destino, key, attrs in solution_graph.edges(keys=True, data=True)
            if attrs["route_id"] == route_id
        ]
        route_data = solution_graph.edges(keys=True, data=True)
        route_label = None
        for _, _, _, attrs in route_data:
            if attrs["route_id"] == route_id:
                route_label = f"{route_id} | {attrs['vehicle_id']}"
                break
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
            connectionstyle="arc3,rad=0.04",
            label=route_label,
        )

    label_map = {
        node_id: artifacts.labels[node_id].split(" - ")[0]
        for node_id in positions
    }
    nx.draw_networkx_labels(base_graph, pos=positions, labels=label_map, ax=axis, font_size=7)

    _set_axis_extent(axis, positions)
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    if with_basemap and not basemap_added:
        axis.text(
            0.02,
            0.98,
            "Basemap indisponivel; renderizacao mantida em networkx puro.",
            transform=axis.transAxes,
            va="top",
            fontsize=9,
            bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "#cccccc"},
        )
    axis.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0))
    axis.grid(alpha=0.2)
    figure.tight_layout()
    return figure, axis

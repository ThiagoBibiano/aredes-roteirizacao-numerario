from __future__ import annotations

from typing import Any

import streamlit as st

from apps.ui_streamlit.services.timeline import TimelineSnapshotViewModel, resolve_route_state, resolve_vehicle_positions
from apps.ui_streamlit.services.view_models import InspectionSnapshotViewModel, MapNodeViewModel, MapSegmentViewModel

try:
    import pydeck as pdk
except Exception:  # pragma: no cover - optional dependency at runtime
    pdk = None


def render_route_map(
    snapshot: InspectionSnapshotViewModel,
    *,
    nodes: tuple[MapNodeViewModel, ...],
    segments: tuple[MapSegmentViewModel, ...],
    selected_route_id: str | None,
    timeline: TimelineSnapshotViewModel | None = None,
    current_at: str | None = None,
) -> str | None:
    st.subheader("Mapa operacional")
    if not snapshot.map_available:
        st.info(snapshot.map_warnings[0] if snapshot.map_warnings else "Mapa indisponivel para o cenario atual.")
        return None
    if pdk is None:
        st.error("pydeck nao esta instalado no ambiente da UI.")
        return None

    route_states = {}
    if timeline is not None and timeline.available:
        route_states = {
            route.id_rota: resolve_route_state(route, current_at)
            for route in timeline.routes
        }

    node_records = [_node_record(node, selected_route_id, route_states) for node in nodes]
    segment_records = [_segment_record(segment, selected_route_id, route_states) for segment in segments]
    vehicle_records = _vehicle_records(timeline, current_at, selected_route_id)
    if not node_records and not segment_records and not vehicle_records:
        st.info("Sem elementos para exibir no mapa com os filtros atuais.")
        return None
    if snapshot.map_warnings:
        with st.expander("Avisos de cruzamento do mapa", expanded=False):
            for warning in snapshot.map_warnings:
                st.write(f"- {warning}")

    latitudes = [record["latitude"] for record in node_records] + [record["from_latitude"] for record in segment_records] + [record["to_latitude"] for record in segment_records] + [record["latitude"] for record in vehicle_records]
    longitudes = [record["longitude"] for record in node_records] + [record["from_longitude"] for record in segment_records] + [record["to_longitude"] for record in segment_records] + [record["longitude"] for record in vehicle_records]
    initial_view = pdk.ViewState(
        latitude=sum(latitudes) / len(latitudes),
        longitude=sum(longitudes) / len(longitudes),
        zoom=10,
        pitch=0,
    )
    layers = []
    if segment_records:
        layers.append(
            pdk.Layer(
                "LineLayer",
                id="route_segments",
                data=segment_records,
                get_source_position="[from_longitude, from_latitude]",
                get_target_position="[to_longitude, to_latitude]",
                get_width="width",
                get_color="color",
                pickable=True,
            )
        )
    if node_records:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="route_nodes",
                data=node_records,
                get_position="[longitude, latitude]",
                get_radius="radius",
                get_color="color",
                pickable=True,
            )
        )
    if vehicle_records:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="route_vehicles",
                data=vehicle_records,
                get_position="[longitude, latitude]",
                get_radius="radius",
                get_color="color",
                pickable=True,
            )
        )
    deck = pdk.Deck(
        map_style=None,
        initial_view_state=initial_view,
        layers=layers,
        tooltip={"html": "{tooltip_html}"},
    )
    selection = st.pydeck_chart(
        deck,
        width="stretch",
        on_select="rerun",
        selection_mode="single-object",
        key="route_map_selection",
    )
    return _extract_selected_route_id(selection)


def _node_record(
    node: MapNodeViewModel,
    selected_route_id: str | None,
    route_states: dict[str, Any],
) -> dict[str, Any]:
    return {
        "node_id": node.node_id,
        "id_rota": node.id_rota,
        "latitude": node.latitude,
        "longitude": node.longitude,
        "radius": _node_radius(node, route_states),
        "color": _node_color(node, selected_route_id, route_states),
        "tooltip_html": _tooltip_html(node.label, node.tooltip_fields),
    }


def _segment_record(
    segment: MapSegmentViewModel,
    selected_route_id: str | None,
    route_states: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id_rota": segment.id_rota,
        "id_viatura": segment.id_viatura,
        "from_latitude": segment.from_latitude,
        "from_longitude": segment.from_longitude,
        "to_latitude": segment.to_latitude,
        "to_longitude": segment.to_longitude,
        "width": _segment_width(segment, selected_route_id, route_states),
        "color": _segment_color(segment, selected_route_id, route_states),
        "tooltip_html": _tooltip_html(
            f"Rota {segment.id_rota}",
            {
                "viatura": segment.id_viatura,
                "classe_operacional": segment.classe_operacional,
                "ordem_segmento": segment.ordem_segmento,
            },
        ),
    }


def _vehicle_records(
    timeline: TimelineSnapshotViewModel | None,
    current_at: str | None,
    selected_route_id: str | None,
) -> list[dict[str, Any]]:
    if timeline is None or not timeline.available:
        return []
    records: list[dict[str, Any]] = []
    for position in resolve_vehicle_positions(timeline, current_at):
        if position.latitude is None or position.longitude is None:
            continue
        opacity = 240
        if selected_route_id and position.id_rota != selected_route_id:
            opacity = 90
        records.append(
            {
                "id_rota": position.id_rota,
                "latitude": position.latitude,
                "longitude": position.longitude,
                "radius": 110,
                "color": [244, 162, 97, opacity],
                "tooltip_html": _tooltip_html(
                    f"Viatura {position.id_viatura}",
                    {
                        "rota": position.id_rota,
                        "fase": position.phase,
                        "segmento_ativo": position.active_segment,
                        "parada_ativa": position.active_stop,
                    },
                ),
            }
        )
    return records


def _node_radius(node: MapNodeViewModel, route_states: dict[str, Any]) -> int:
    if node.kind == "base":
        return 90
    stop_sequence = _stop_sequence_from_node(node)
    route_state = route_states.get(node.id_rota or "")
    if route_state is not None and stop_sequence is not None and route_state.active_stop_sequence == stop_sequence:
        return 95
    return 55


def _node_color(
    node: MapNodeViewModel,
    selected_route_id: str | None,
    route_states: dict[str, Any],
) -> list[int]:
    opacity = 220
    if selected_route_id and node.id_rota and node.id_rota != selected_route_id:
        opacity = 70
    palette = {
        "base": [33, 37, 41, opacity],
        "ponto_nao_atendido": [214, 40, 40, opacity],
        "ponto_excluido": [128, 128, 128, opacity],
        "ponto_cancelado": [229, 152, 0, opacity],
    }
    if node.kind != "ponto_atendido":
        return palette.get(node.kind, [31, 119, 180, opacity])

    route_state = route_states.get(node.id_rota or "")
    stop_sequence = _stop_sequence_from_node(node)
    if route_state is None or stop_sequence is None:
        return [38, 70, 83, opacity]
    if route_state.active_stop_sequence == stop_sequence:
        return [42, 157, 143, opacity]
    if stop_sequence in route_state.completed_stop_sequences:
        return [38, 70, 83, opacity]
    if stop_sequence in route_state.future_stop_sequences:
        return [168, 181, 187, 110 if not selected_route_id or node.id_rota == selected_route_id else 60]
    return [38, 70, 83, opacity]


def _segment_width(
    segment: MapSegmentViewModel,
    selected_route_id: str | None,
    route_states: dict[str, Any],
) -> int:
    route_state = route_states.get(segment.id_rota)
    if route_state is not None and route_state.active_segment_sequence == segment.ordem_segmento:
        return 6
    if selected_route_id and segment.id_rota == selected_route_id:
        return 5
    return 3


def _segment_color(
    segment: MapSegmentViewModel,
    selected_route_id: str | None,
    route_states: dict[str, Any],
) -> list[int]:
    if selected_route_id and segment.id_rota != selected_route_id:
        return [150, 150, 150, 80]
    route_state = route_states.get(segment.id_rota)
    if route_state is not None:
        if route_state.active_segment_sequence == segment.ordem_segmento:
            return [244, 162, 97, 240]
        if segment.ordem_segmento in route_state.completed_segment_sequences:
            return [42, 157, 143, 220]
        if segment.ordem_segmento in route_state.future_segment_sequences:
            return [168, 181, 187, 90]
    if segment.classe_operacional == "recolhimento":
        return [231, 111, 81, 220]
    return [29, 53, 87, 220]


def _stop_sequence_from_node(node: MapNodeViewModel) -> int | None:
    if node.kind != "ponto_atendido":
        return None
    try:
        return int(str(node.node_id).split(":")[-1])
    except (TypeError, ValueError):
        return None


def _tooltip_html(title: str, fields: dict[str, Any]) -> str:
    lines = [f"<b>{title}</b>"]
    for key, value in fields.items():
        if value in (None, "", {}):
            continue
        lines.append(f"{key}: {value}")
    return "<br/>".join(lines)


def _extract_selected_route_id(selection: Any) -> str | None:
    if selection is None:
        return None
    if isinstance(selection, dict):
        if selection.get("id_rota"):
            return str(selection["id_rota"])
        for value in selection.values():
            resolved = _extract_selected_route_id(value)
            if resolved:
                return resolved
    if isinstance(selection, list):
        for item in selection:
            resolved = _extract_selected_route_id(item)
            if resolved:
                return resolved
    return None

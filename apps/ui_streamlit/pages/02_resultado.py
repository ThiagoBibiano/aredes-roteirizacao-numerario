from __future__ import annotations

import sys
from pathlib import Path

_CURRENT_PATH = Path(__file__).resolve()
_REPO_ROOT = next(parent for parent in _CURRENT_PATH.parents if (parent / "pyproject.toml").exists())
for _candidate in (_REPO_ROOT, _REPO_ROOT / "src"):
    _candidate_str = str(_candidate)
    if _candidate_str not in sys.path:
        sys.path.insert(0, _candidate_str)

import streamlit as st

from apps.ui_streamlit.components.execution_summary import render_execution_summary
from apps.ui_streamlit.components.kpi_cards import render_kpi_cards, render_route_charts
from apps.ui_streamlit.components.route_detail import render_route_detail
from apps.ui_streamlit.components.route_map import render_route_map
from apps.ui_streamlit.components.route_table import render_route_table
from apps.ui_streamlit.components.sidebar import render_global_sidebar
from apps.ui_streamlit.services.filters import apply_filters
from apps.ui_streamlit.services.timeline import (
    advance_timeline_current_at,
    build_timeline_snapshot,
    clamp_timeline_current_at,
    derive_stop_temporal_status,
    find_neighbor_event_at,
    find_timeline_route,
    format_timeline_label,
    minute_marks,
    resolve_route_state,
    resolve_selected_step_index,
)
from apps.ui_streamlit.state.session_state import (
    TIMELINE_CURRENT_AT_WIDGET_KEY,
    TIMELINE_INCLUDE_RETURN_KEY,
    TIMELINE_STEP_SECONDS_KEY,
    ensure_session_state,
    get_filter_criteria,
    get_last_message,
    get_raw_response,
    get_selected_route_id,
    get_timeline_current_at,
    get_timeline_current_at_widget,
    get_timeline_frame_interval_ms,
    get_timeline_include_return_to_base,
    get_timeline_step_seconds,
    is_timeline_playing,
    prime_timeline_current_at_widget,
    refresh_snapshot_if_needed,
    set_selected_route_id,
    set_timeline_current_at,
    set_timeline_playing,
)


AUTOPLAY_STEP_OPTIONS = (60, 300, 900)


def main() -> None:
    st.set_page_config(page_title="Resultado", layout="wide")
    ensure_session_state()
    render_global_sidebar()
    snapshot = refresh_snapshot_if_needed()
    st.title("Resultados do planejamento")
    st.caption("Explore rotas, mapa e timeline. Os filtros da barra lateral afetam toda a analise atual.")
    message = get_last_message()
    if message:
        st.info(message)
    if snapshot is None:
        st.info("Nenhuma analise carregada. Rode um teste rapido, envie seus arquivos ou abra um JSON salvo.")
        return

    filtered = apply_filters(snapshot, get_filter_criteria())
    render_execution_summary(snapshot.execution_summary, raw_response=get_raw_response())
    render_kpi_cards(snapshot.kpi_cards)
    render_route_charts(filtered.route_rows)
    _render_timeline_workspace(snapshot, filtered)


def _render_timeline_workspace(snapshot, filtered) -> None:
    run_every = None
    if is_timeline_playing():
        frame_interval_ms = max(get_timeline_frame_interval_ms(), 0)
        run_every = None if frame_interval_ms <= 0 else frame_interval_ms / 1000

    @st.fragment(run_every=run_every)
    def _workspace() -> None:
        selected_route_id = render_route_table(filtered.route_rows, current_route_id=get_selected_route_id())
        if selected_route_id is not None:
            set_selected_route_id(selected_route_id)

        timeline = build_timeline_snapshot(
            filtered,
            selected_route_id=get_selected_route_id(),
            include_return_to_base=get_timeline_include_return_to_base(),
        )
        _reconcile_timeline_state(timeline)
        _tick_timeline_autoplay(timeline)
        current_at = get_timeline_current_at()
        _render_timeline_controls(timeline)
        current_at = get_timeline_current_at()

        map_column, detail_column = st.columns([1.4, 1.0])
        with map_column:
            map_selected_route = render_route_map(
                snapshot,
                nodes=filtered.map_nodes,
                segments=filtered.map_segments,
                selected_route_id=get_selected_route_id(),
                timeline=timeline,
                current_at=current_at,
            )
            if map_selected_route:
                set_selected_route_id(map_selected_route)
        with detail_column:
            selected_route_id = get_selected_route_id()
            _render_route_stepper(timeline, selected_route_id)
            current_at = get_timeline_current_at()
            route_row = _find_route_row(filtered.route_rows, selected_route_id)
            stop_rows = () if route_row is None else tuple(
                row for row in filtered.route_stop_rows if row.id_rota == route_row.id_rota
            )
            route_playback = find_timeline_route(timeline.routes, selected_route_id) if timeline.available else None
            route_state = resolve_route_state(route_playback, current_at) if route_playback is not None else None
            stop_statuses = {row.sequencia: derive_stop_temporal_status(row, current_at) for row in stop_rows}
            render_route_detail(
                route_row,
                stop_rows,
                route_state=route_state,
                current_at_label=format_timeline_label(current_at, timeline.timezone_label) if current_at else None,
                stop_statuses=stop_statuses,
            )

    _workspace()


def _render_timeline_controls(timeline) -> None:
    st.markdown("### Timeline aproximada")
    if timeline.warnings:
        with st.expander("Avisos da timeline", expanded=False):
            for warning in timeline.warnings:
                st.write(f"- {warning}")
    if not timeline.available:
        st.info("Timeline indisponivel para os filtros atuais.")
        return

    controls = st.columns([1, 1, 1, 1, 1.2, 1.2])
    if controls[0].button("Evento anterior", width="stretch"):
        set_timeline_current_at(find_neighbor_event_at(timeline, get_timeline_current_at(), direction="previous"))
        set_timeline_playing(False)
    if controls[1].button("Pausar" if is_timeline_playing() else "Play", width="stretch"):
        set_timeline_playing(not is_timeline_playing())
    if controls[2].button("Proximo evento", width="stretch"):
        set_timeline_current_at(find_neighbor_event_at(timeline, get_timeline_current_at(), direction="next"))
        set_timeline_playing(False)
    if controls[3].button("Reset", width="stretch"):
        set_timeline_current_at(timeline.start_at)
        set_timeline_playing(False)

    current_step = get_timeline_step_seconds()
    step_index = AUTOPLAY_STEP_OPTIONS.index(current_step) if current_step in AUTOPLAY_STEP_OPTIONS else 1
    selected_step = controls[4].selectbox(
        "Passo autoplay",
        options=AUTOPLAY_STEP_OPTIONS,
        index=step_index,
        format_func=_step_option_label,
        key=TIMELINE_STEP_SECONDS_KEY,
    )
    if selected_step != current_step:
        set_timeline_playing(False)

    include_return = controls[5].checkbox(
        "Retorno a base",
        value=get_timeline_include_return_to_base(),
        key=TIMELINE_INCLUDE_RETURN_KEY,
    )
    if include_return != get_timeline_include_return_to_base():
        set_timeline_playing(False)

    marks = minute_marks(timeline)
    if not marks:
        st.info("Sem marcas temporais suficientes para exibir o slider.")
        return
    current_at = get_timeline_current_at()
    if current_at not in marks:
        current_at = marks[0]
        set_timeline_current_at(current_at)
    if get_timeline_current_at_widget() != current_at:
        prime_timeline_current_at_widget(current_at)
    selected_at = st.select_slider(
        "Horario planejado",
        options=marks,
        key=TIMELINE_CURRENT_AT_WIDGET_KEY,
        format_func=lambda value: format_timeline_label(value, timeline.timezone_label),
    )
    if selected_at != get_timeline_current_at():
        set_timeline_current_at(selected_at)
    st.caption(
        "Janela temporal: "
        f"{format_timeline_label(timeline.start_at, timeline.timezone_label)} "
        f"ate {format_timeline_label(timeline.end_at, timeline.timezone_label)}"
    )


def _render_route_stepper(timeline, selected_route_id: str | None) -> None:
    st.subheader("Stepper da rota")
    if not timeline.available:
        st.info("Timeline indisponivel para navegar por eventos da rota.")
        return
    route_playback = find_timeline_route(timeline.routes, selected_route_id)
    if route_playback is None or not route_playback.steps:
        st.info("A rota selecionada nao possui passos temporais disponiveis.")
        return
    if selected_route_id != route_playback.id_rota:
        set_selected_route_id(route_playback.id_rota)
    step_labels = [
        f"{step.label} | {format_timeline_label(step.timestamp, timeline.timezone_label)}"
        for step in route_playback.steps
    ]
    current_index = resolve_selected_step_index(route_playback.steps, get_timeline_current_at())
    selected_label = st.radio(
        "Eventos da rota selecionada",
        options=step_labels,
        index=current_index,
        label_visibility="collapsed",
    )
    selected_index = step_labels.index(selected_label)
    selected_step = route_playback.steps[selected_index]
    if selected_step.timestamp != get_timeline_current_at():
        set_timeline_current_at(selected_step.timestamp)
        set_timeline_playing(False)
        st.rerun()


def _reconcile_timeline_state(timeline) -> str | None:
    if not timeline.available:
        set_timeline_current_at(None)
        set_timeline_playing(False)
        return None
    selected_route = find_timeline_route(timeline.routes, get_selected_route_id())
    if selected_route is not None and selected_route.id_rota != get_selected_route_id():
        set_selected_route_id(selected_route.id_rota)
    current_at = clamp_timeline_current_at(timeline, get_timeline_current_at())
    if current_at != get_timeline_current_at():
        set_timeline_current_at(current_at)
    return current_at


def _find_route_row(route_rows, route_id: str | None):
    if not route_rows:
        return None
    if route_id:
        for row in route_rows:
            if row.id_rota == route_id:
                return row
    return route_rows[0]


def _tick_timeline_autoplay(timeline) -> None:
    if not timeline.available or not is_timeline_playing():
        return
    current_at = get_timeline_current_at()
    next_at = advance_timeline_current_at(
        timeline,
        current_at,
        step_seconds=get_timeline_step_seconds(),
    )
    if next_at is None or next_at == current_at:
        set_timeline_playing(False)
        return
    set_timeline_current_at(next_at)
    if next_at == timeline.end_at:
        set_timeline_playing(False)


def _step_option_label(value: int) -> str:
    if value == 60:
        return "1 min"
    if value == 300:
        return "5 min"
    if value == 900:
        return "15 min"
    return f"{value}s"


if __name__ == "__main__":
    main()

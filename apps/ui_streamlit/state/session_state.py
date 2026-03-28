from __future__ import annotations

import streamlit as st

from apps.ui_streamlit.services.alerts import build_alerts
from apps.ui_streamlit.services.export import OfflineLoadResult
from apps.ui_streamlit.services.filters import FilterCriteria
from apps.ui_streamlit.services.ui_settings import load_ui_settings
from apps.ui_streamlit.services.view_models import (
    InspectionSnapshotViewModel,
    build_inspection_snapshot,
    with_alerts,
)


DEFAULT_API_BASE_URL = load_ui_settings().api_base_url
DEFAULT_WAIT_THRESHOLD_SECONDS = 900
DEFAULT_TIMELINE_STEP_SECONDS = 300
DEFAULT_TIMELINE_FRAME_INTERVAL_MS = 250

RAW_RESPONSE_KEY = "ui_raw_response"
INPUT_PAYLOAD_KEY = "ui_input_payload"
SOURCE_KIND_KEY = "ui_source_kind"
SNAPSHOT_KEY = "ui_inspection_snapshot"
SELECTED_ROUTE_KEY = "ui_selected_route_id"
HEALTH_STATUS_KEY = "ui_health_status"
HEALTH_ERROR_KEY = "ui_health_error"
WAIT_THRESHOLD_KEY = "ui_wait_threshold_seconds"
APPLIED_WAIT_THRESHOLD_KEY = "ui_applied_wait_threshold_seconds"
EXECUTION_LOCK_KEY = "ui_execution_locked"
LAST_MESSAGE_KEY = "ui_last_message"
FILTER_VIATURAS_KEY = "ui_filter_viaturas"
FILTER_CLASSES_KEY = "ui_filter_classes"
FILTER_CRITICIDADES_KEY = "ui_filter_criticidades"
FILTER_SEVERIDADES_KEY = "ui_filter_severidades"
FILTER_STATUS_KEY = "ui_filter_status"
FILTER_TIME_START_KEY = "ui_filter_time_start"
FILTER_TIME_END_KEY = "ui_filter_time_end"
OFFLINE_SIGNATURE_KEY = "ui_offline_signature"
TIMELINE_CURRENT_AT_KEY = "ui_timeline_current_at"
TIMELINE_CURRENT_AT_WIDGET_KEY = "ui_timeline_current_at_widget"
TIMELINE_IS_PLAYING_KEY = "ui_timeline_is_playing"
TIMELINE_STEP_SECONDS_KEY = "ui_timeline_step_seconds"
TIMELINE_FRAME_INTERVAL_MS_KEY = "ui_timeline_frame_interval_ms"
TIMELINE_INCLUDE_RETURN_KEY = "ui_timeline_include_return_to_base"


def ensure_session_state() -> None:
    if RAW_RESPONSE_KEY not in st.session_state:
        st.session_state[RAW_RESPONSE_KEY] = None
    if INPUT_PAYLOAD_KEY not in st.session_state:
        st.session_state[INPUT_PAYLOAD_KEY] = None
    if SOURCE_KIND_KEY not in st.session_state:
        st.session_state[SOURCE_KIND_KEY] = "inline"
    if SNAPSHOT_KEY not in st.session_state:
        st.session_state[SNAPSHOT_KEY] = None
    if SELECTED_ROUTE_KEY not in st.session_state:
        st.session_state[SELECTED_ROUTE_KEY] = None
    if HEALTH_STATUS_KEY not in st.session_state:
        st.session_state[HEALTH_STATUS_KEY] = None
    if HEALTH_ERROR_KEY not in st.session_state:
        st.session_state[HEALTH_ERROR_KEY] = None
    if WAIT_THRESHOLD_KEY not in st.session_state:
        st.session_state[WAIT_THRESHOLD_KEY] = DEFAULT_WAIT_THRESHOLD_SECONDS
    if APPLIED_WAIT_THRESHOLD_KEY not in st.session_state:
        st.session_state[APPLIED_WAIT_THRESHOLD_KEY] = DEFAULT_WAIT_THRESHOLD_SECONDS
    if EXECUTION_LOCK_KEY not in st.session_state:
        st.session_state[EXECUTION_LOCK_KEY] = False
    if LAST_MESSAGE_KEY not in st.session_state:
        st.session_state[LAST_MESSAGE_KEY] = None
    if FILTER_VIATURAS_KEY not in st.session_state:
        st.session_state[FILTER_VIATURAS_KEY] = []
    if FILTER_CLASSES_KEY not in st.session_state:
        st.session_state[FILTER_CLASSES_KEY] = []
    if FILTER_CRITICIDADES_KEY not in st.session_state:
        st.session_state[FILTER_CRITICIDADES_KEY] = []
    if FILTER_SEVERIDADES_KEY not in st.session_state:
        st.session_state[FILTER_SEVERIDADES_KEY] = []
    if FILTER_STATUS_KEY not in st.session_state:
        st.session_state[FILTER_STATUS_KEY] = []
    if FILTER_TIME_START_KEY not in st.session_state:
        st.session_state[FILTER_TIME_START_KEY] = ""
    if FILTER_TIME_END_KEY not in st.session_state:
        st.session_state[FILTER_TIME_END_KEY] = ""
    if OFFLINE_SIGNATURE_KEY not in st.session_state:
        st.session_state[OFFLINE_SIGNATURE_KEY] = None
    if TIMELINE_CURRENT_AT_KEY not in st.session_state:
        st.session_state[TIMELINE_CURRENT_AT_KEY] = None
    if TIMELINE_CURRENT_AT_WIDGET_KEY not in st.session_state:
        st.session_state[TIMELINE_CURRENT_AT_WIDGET_KEY] = None
    if TIMELINE_IS_PLAYING_KEY not in st.session_state:
        st.session_state[TIMELINE_IS_PLAYING_KEY] = False
    if TIMELINE_STEP_SECONDS_KEY not in st.session_state:
        st.session_state[TIMELINE_STEP_SECONDS_KEY] = DEFAULT_TIMELINE_STEP_SECONDS
    if TIMELINE_FRAME_INTERVAL_MS_KEY not in st.session_state:
        st.session_state[TIMELINE_FRAME_INTERVAL_MS_KEY] = DEFAULT_TIMELINE_FRAME_INTERVAL_MS
    if TIMELINE_INCLUDE_RETURN_KEY not in st.session_state:
        st.session_state[TIMELINE_INCLUDE_RETURN_KEY] = False


def get_api_base_url() -> str:
    return DEFAULT_API_BASE_URL


def store_execution_result(
    raw_response: dict,
    *,
    input_payload: dict | None,
    source_kind: str,
) -> InspectionSnapshotViewModel:
    ensure_session_state()
    st.session_state[RAW_RESPONSE_KEY] = raw_response
    st.session_state[INPUT_PAYLOAD_KEY] = input_payload
    st.session_state[SOURCE_KIND_KEY] = source_kind
    _reset_timeline_state()
    snapshot = rebuild_snapshot()
    return snapshot


def store_offline_payload(payload: OfflineLoadResult) -> InspectionSnapshotViewModel:
    ensure_session_state()
    st.session_state[RAW_RESPONSE_KEY] = payload.raw_response
    st.session_state[INPUT_PAYLOAD_KEY] = payload.input_payload
    st.session_state[SOURCE_KIND_KEY] = payload.source_kind
    _reset_timeline_state()
    if payload.inspection_snapshot is not None:
        st.session_state[SNAPSHOT_KEY] = payload.inspection_snapshot
        _reconcile_selected_route(payload.inspection_snapshot)
        return payload.inspection_snapshot
    return rebuild_snapshot()


def rebuild_snapshot() -> InspectionSnapshotViewModel:
    ensure_session_state()
    raw_response = st.session_state.get(RAW_RESPONSE_KEY)
    if not isinstance(raw_response, dict):
        raise ValueError("Nao ha resposta bruta da API em sessao para reconstruir a visualizacao.")
    snapshot = build_inspection_snapshot(
        raw_response,
        input_payload=st.session_state.get(INPUT_PAYLOAD_KEY),
    )
    snapshot = with_alerts(
        snapshot,
        build_alerts(
            raw_response,
            snapshot,
            wait_threshold_seconds=int(st.session_state.get(WAIT_THRESHOLD_KEY, DEFAULT_WAIT_THRESHOLD_SECONDS)),
        ),
    )
    st.session_state[SNAPSHOT_KEY] = snapshot
    st.session_state[APPLIED_WAIT_THRESHOLD_KEY] = int(
        st.session_state.get(WAIT_THRESHOLD_KEY, DEFAULT_WAIT_THRESHOLD_SECONDS)
    )
    _reconcile_selected_route(snapshot)
    return snapshot


def refresh_snapshot_if_needed() -> InspectionSnapshotViewModel | None:
    ensure_session_state()
    snapshot = get_snapshot()
    if snapshot is None:
        return None
    applied = int(st.session_state.get(APPLIED_WAIT_THRESHOLD_KEY, DEFAULT_WAIT_THRESHOLD_SECONDS))
    current = int(st.session_state.get(WAIT_THRESHOLD_KEY, DEFAULT_WAIT_THRESHOLD_SECONDS))
    if applied != current:
        return rebuild_snapshot()
    return snapshot


def clear_loaded_result() -> None:
    ensure_session_state()
    st.session_state[RAW_RESPONSE_KEY] = None
    st.session_state[INPUT_PAYLOAD_KEY] = None
    st.session_state[SNAPSHOT_KEY] = None
    st.session_state[SELECTED_ROUTE_KEY] = None
    st.session_state[LAST_MESSAGE_KEY] = None
    st.session_state[OFFLINE_SIGNATURE_KEY] = None
    _reset_timeline_state()


def get_snapshot() -> InspectionSnapshotViewModel | None:
    ensure_session_state()
    snapshot = st.session_state.get(SNAPSHOT_KEY)
    return snapshot if isinstance(snapshot, InspectionSnapshotViewModel) else None


def get_raw_response() -> dict | None:
    ensure_session_state()
    payload = st.session_state.get(RAW_RESPONSE_KEY)
    return payload if isinstance(payload, dict) else None


def get_input_payload() -> dict | None:
    ensure_session_state()
    payload = st.session_state.get(INPUT_PAYLOAD_KEY)
    return payload if isinstance(payload, dict) else None


def get_source_kind() -> str:
    ensure_session_state()
    return str(st.session_state.get(SOURCE_KIND_KEY) or "inline")


def set_selected_route_id(route_id: str | None) -> None:
    ensure_session_state()
    st.session_state[SELECTED_ROUTE_KEY] = route_id


def get_selected_route_id() -> str | None:
    ensure_session_state()
    route_id = st.session_state.get(SELECTED_ROUTE_KEY)
    return str(route_id) if route_id else None


def set_health_status(payload: dict | None, error_message: str | None = None) -> None:
    ensure_session_state()
    st.session_state[HEALTH_STATUS_KEY] = payload
    st.session_state[HEALTH_ERROR_KEY] = error_message


def get_health_status() -> tuple[dict | None, str | None]:
    ensure_session_state()
    payload = st.session_state.get(HEALTH_STATUS_KEY)
    error = st.session_state.get(HEALTH_ERROR_KEY)
    return (payload if isinstance(payload, dict) else None, str(error) if error else None)


def set_execution_lock(value: bool) -> None:
    ensure_session_state()
    st.session_state[EXECUTION_LOCK_KEY] = bool(value)


def is_execution_locked() -> bool:
    ensure_session_state()
    return bool(st.session_state.get(EXECUTION_LOCK_KEY, False))


def set_last_message(message: str | None) -> None:
    ensure_session_state()
    st.session_state[LAST_MESSAGE_KEY] = message


def get_last_message() -> str | None:
    ensure_session_state()
    value = st.session_state.get(LAST_MESSAGE_KEY)
    return str(value) if value else None


def get_filter_criteria() -> FilterCriteria:
    ensure_session_state()
    return FilterCriteria(
        viaturas=tuple(st.session_state.get(FILTER_VIATURAS_KEY, [])),
        classes_operacionais=tuple(st.session_state.get(FILTER_CLASSES_KEY, [])),
        criticidades=tuple(st.session_state.get(FILTER_CRITICIDADES_KEY, [])),
        severidades=tuple(st.session_state.get(FILTER_SEVERIDADES_KEY, [])),
        statuses_atendimento=tuple(st.session_state.get(FILTER_STATUS_KEY, [])),
        faixa_inicio=str(st.session_state.get(FILTER_TIME_START_KEY) or "").strip() or None,
        faixa_fim=str(st.session_state.get(FILTER_TIME_END_KEY) or "").strip() or None,
    )


def get_timeline_current_at() -> str | None:
    ensure_session_state()
    value = st.session_state.get(TIMELINE_CURRENT_AT_KEY)
    return str(value) if value else None


def set_timeline_current_at(value: str | None) -> None:
    ensure_session_state()
    st.session_state[TIMELINE_CURRENT_AT_KEY] = value


def get_timeline_current_at_widget() -> str | None:
    ensure_session_state()
    value = st.session_state.get(TIMELINE_CURRENT_AT_WIDGET_KEY)
    return str(value) if value else None


def prime_timeline_current_at_widget(value: str | None) -> None:
    ensure_session_state()
    st.session_state[TIMELINE_CURRENT_AT_WIDGET_KEY] = value


def is_timeline_playing() -> bool:
    ensure_session_state()
    return bool(st.session_state.get(TIMELINE_IS_PLAYING_KEY, False))


def set_timeline_playing(value: bool) -> None:
    ensure_session_state()
    st.session_state[TIMELINE_IS_PLAYING_KEY] = bool(value)


def get_timeline_step_seconds() -> int:
    ensure_session_state()
    value = st.session_state.get(TIMELINE_STEP_SECONDS_KEY, DEFAULT_TIMELINE_STEP_SECONDS)
    return int(value or DEFAULT_TIMELINE_STEP_SECONDS)


def set_timeline_step_seconds(value: int) -> None:
    ensure_session_state()
    st.session_state[TIMELINE_STEP_SECONDS_KEY] = int(value)


def get_timeline_frame_interval_ms() -> int:
    ensure_session_state()
    value = st.session_state.get(TIMELINE_FRAME_INTERVAL_MS_KEY, DEFAULT_TIMELINE_FRAME_INTERVAL_MS)
    return int(value or DEFAULT_TIMELINE_FRAME_INTERVAL_MS)


def get_timeline_include_return_to_base() -> bool:
    ensure_session_state()
    return bool(st.session_state.get(TIMELINE_INCLUDE_RETURN_KEY, False))


def set_timeline_include_return_to_base(value: bool) -> None:
    ensure_session_state()
    st.session_state[TIMELINE_INCLUDE_RETURN_KEY] = bool(value)


def _reset_timeline_state() -> None:
    st.session_state[TIMELINE_CURRENT_AT_KEY] = None
    st.session_state[TIMELINE_CURRENT_AT_WIDGET_KEY] = None
    st.session_state[TIMELINE_IS_PLAYING_KEY] = False
    st.session_state[TIMELINE_STEP_SECONDS_KEY] = DEFAULT_TIMELINE_STEP_SECONDS
    st.session_state[TIMELINE_FRAME_INTERVAL_MS_KEY] = DEFAULT_TIMELINE_FRAME_INTERVAL_MS
    st.session_state[TIMELINE_INCLUDE_RETURN_KEY] = False


def _reconcile_selected_route(snapshot: InspectionSnapshotViewModel) -> None:
    current = get_selected_route_id()
    route_ids = [row.id_rota for row in snapshot.route_rows]
    if current in route_ids:
        return
    st.session_state[SELECTED_ROUTE_KEY] = route_ids[0] if route_ids else None

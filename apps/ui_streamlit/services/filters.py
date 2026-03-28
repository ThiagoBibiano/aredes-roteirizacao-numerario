from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Any

from apps.ui_streamlit.services.view_models import (
    AlertViewModel,
    InspectionSnapshotViewModel,
    MapNodeViewModel,
    MapSegmentViewModel,
    RouteRowViewModel,
    RouteStopRowViewModel,
    parse_time_value,
)


@dataclass(slots=True, frozen=True)
class FilterCriteria:
    viaturas: tuple[str, ...] = ()
    classes_operacionais: tuple[str, ...] = ()
    criticidades: tuple[str, ...] = ()
    severidades: tuple[str, ...] = ()
    statuses_atendimento: tuple[str, ...] = ()
    faixa_inicio: str | None = None
    faixa_fim: str | None = None


@dataclass(slots=True, frozen=True)
class FilteredInspectionSnapshot:
    route_rows: tuple[RouteRowViewModel, ...]
    route_stop_rows: tuple[RouteStopRowViewModel, ...]
    map_nodes: tuple[MapNodeViewModel, ...]
    map_segments: tuple[MapSegmentViewModel, ...]
    alerts: tuple[AlertViewModel, ...]
    event_rows: tuple[dict[str, Any], ...]
    reason_rows: tuple[dict[str, Any], ...]
    non_served_rows: tuple[dict[str, Any], ...]
    excluded_rows: tuple[dict[str, Any], ...]
    cancelled_rows: tuple[dict[str, Any], ...]
    error_rows: tuple[dict[str, Any], ...]


def apply_filters(
    snapshot: InspectionSnapshotViewModel,
    criteria: FilterCriteria,
) -> FilteredInspectionSnapshot:
    route_rows = tuple(row for row in snapshot.route_rows if _matches_route(row, criteria))
    route_ids = {row.id_rota for row in route_rows}
    base_ids = {row.id_base for row in route_rows}
    route_stop_rows = tuple(
        row for row in snapshot.route_stop_rows if row.id_rota in route_ids and _matches_stop(row, criteria)
    )
    alerts = tuple(alert for alert in snapshot.alerts if _matches_alert(alert, criteria, route_ids))
    event_rows = tuple(row for row in snapshot.event_rows if _matches_mapping(row, criteria))
    reason_rows = tuple(row for row in snapshot.reason_rows if _matches_mapping(row, criteria))
    non_served_rows = tuple(row for row in snapshot.non_served_rows if _matches_mapping(row, criteria))
    excluded_rows = tuple(row for row in snapshot.excluded_rows if _matches_mapping(row, criteria))
    cancelled_rows = tuple(row for row in snapshot.cancelled_rows if _matches_mapping(row, criteria))
    error_rows = tuple(row for row in snapshot.error_rows if _matches_mapping(row, criteria))
    map_nodes = tuple(
        node
        for node in snapshot.map_nodes
        if _matches_node(node, criteria, route_ids, base_ids)
    )
    map_segments = tuple(
        segment
        for segment in snapshot.map_segments
        if segment.id_rota in route_ids and _matches_segment(segment, criteria)
    )
    return FilteredInspectionSnapshot(
        route_rows=route_rows,
        route_stop_rows=route_stop_rows,
        map_nodes=map_nodes,
        map_segments=map_segments,
        alerts=alerts,
        event_rows=event_rows,
        reason_rows=reason_rows,
        non_served_rows=non_served_rows,
        excluded_rows=excluded_rows,
        cancelled_rows=cancelled_rows,
        error_rows=error_rows,
    )


def _matches_route(row: RouteRowViewModel, criteria: FilterCriteria) -> bool:
    if criteria.statuses_atendimento and row.status_atendimento not in criteria.statuses_atendimento:
        return False
    if criteria.viaturas and row.id_viatura not in criteria.viaturas:
        return False
    if criteria.classes_operacionais and row.classe_operacional not in criteria.classes_operacionais:
        return False
    if criteria.criticidades and not set(row.criticidades).intersection(criteria.criticidades):
        return False
    return _matches_time_window(row.inicio_previsto, row.fim_previsto, criteria)


def _matches_stop(row: RouteStopRowViewModel, criteria: FilterCriteria) -> bool:
    if criteria.statuses_atendimento and row.status_atendimento not in criteria.statuses_atendimento:
        return False
    if criteria.viaturas and row.id_viatura not in criteria.viaturas:
        return False
    if criteria.classes_operacionais and row.classe_operacional not in criteria.classes_operacionais:
        return False
    if criteria.criticidades and row.criticidade not in criteria.criticidades:
        return False
    return _matches_time_window(row.inicio_previsto, row.fim_previsto, criteria)


def _matches_alert(alert: AlertViewModel, criteria: FilterCriteria, route_ids: set[str]) -> bool:
    if criteria.severidades and alert.severity not in criteria.severidades:
        return False
    if criteria.statuses_atendimento and alert.status_atendimento and alert.status_atendimento not in criteria.statuses_atendimento:
        return False
    if criteria.viaturas and alert.id_viatura and alert.id_viatura not in criteria.viaturas:
        return False
    if criteria.classes_operacionais and alert.classe_operacional and alert.classe_operacional not in criteria.classes_operacionais:
        return False
    if criteria.criticidades and alert.criticidade and alert.criticidade not in criteria.criticidades:
        return False
    if route_ids and alert.id_rota and alert.id_rota not in route_ids:
        return False
    return True


def _matches_mapping(row: dict[str, Any], criteria: FilterCriteria) -> bool:
    if criteria.severidades and row.get("severidade") and str(row.get("severidade")) not in criteria.severidades:
        return False
    if criteria.statuses_atendimento and row.get("status_atendimento") and str(row.get("status_atendimento")) not in criteria.statuses_atendimento:
        return False
    if criteria.classes_operacionais and row.get("classe_operacional") and str(row.get("classe_operacional")) not in criteria.classes_operacionais:
        return False
    if criteria.criticidades and row.get("criticidade") and str(row.get("criticidade")) not in criteria.criticidades:
        return False
    return True


def _matches_node(
    node: MapNodeViewModel,
    criteria: FilterCriteria,
    route_ids: set[str],
    base_ids: set[str],
) -> bool:
    if node.kind == "base":
        return bool(base_ids) and bool(node.source_id and node.source_id in base_ids)
    if route_ids and node.id_rota and node.id_rota not in route_ids:
        return False
    if criteria.statuses_atendimento and node.status_atendimento and node.status_atendimento not in criteria.statuses_atendimento:
        return False
    if criteria.viaturas and node.id_viatura and node.id_viatura not in criteria.viaturas:
        return False
    if criteria.classes_operacionais and node.classe_operacional and node.classe_operacional not in criteria.classes_operacionais:
        return False
    if criteria.criticidades and node.criticidade and node.criticidade not in criteria.criticidades:
        return False
    return True


def _matches_segment(segment: MapSegmentViewModel, criteria: FilterCriteria) -> bool:
    if criteria.statuses_atendimento and segment.status_atendimento not in criteria.statuses_atendimento:
        return False
    if criteria.viaturas and segment.id_viatura not in criteria.viaturas:
        return False
    if criteria.classes_operacionais and segment.classe_operacional not in criteria.classes_operacionais:
        return False
    return True


def _matches_time_window(inicio: str, fim: str, criteria: FilterCriteria) -> bool:
    if not criteria.faixa_inicio and not criteria.faixa_fim:
        return True
    start = parse_time_value(inicio)
    end = parse_time_value(fim)
    if start is None or end is None:
        return True
    filter_start = parse_time_value(criteria.faixa_inicio)
    filter_end = parse_time_value(criteria.faixa_fim)
    if filter_start and end < filter_start:
        return False
    if filter_end and start > filter_end:
        return False
    return True

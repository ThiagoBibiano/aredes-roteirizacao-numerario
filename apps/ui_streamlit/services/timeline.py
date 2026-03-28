from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, tzinfo
from typing import Iterable

from apps.ui_streamlit.services.filters import FilteredInspectionSnapshot
from apps.ui_streamlit.services.view_models import (
    MapNodeViewModel,
    RouteRowViewModel,
    RouteStopRowViewModel,
    parse_datetime,
)


@dataclass(slots=True, frozen=True)
class TimelineStepViewModel:
    kind: str
    timestamp: str
    sequencia: int
    label: str
    id_rota: str
    id_ordem: str | None = None
    id_ponto: str | None = None


@dataclass(slots=True, frozen=True)
class TimelineStopPlaybackViewModel:
    sequencia: int
    id_ordem: str
    id_ponto: str
    criticidade: str | None
    start_at: str
    end_at: str
    anchor_at: str
    latitude: float | None
    longitude: float | None


@dataclass(slots=True, frozen=True)
class TimelineSegmentPlaybackViewModel:
    kind: str
    ordem_segmento: int
    start_at: str
    end_at: str
    from_latitude: float | None
    from_longitude: float | None
    to_latitude: float | None
    to_longitude: float | None


@dataclass(slots=True, frozen=True)
class TimelineRoutePlaybackViewModel:
    id_rota: str
    id_viatura: str
    classe_operacional: str
    start_at: str
    end_at: str
    base_latitude: float | None
    base_longitude: float | None
    final_latitude: float | None
    final_longitude: float | None
    steps: tuple[TimelineStepViewModel, ...]
    stops: tuple[TimelineStopPlaybackViewModel, ...]
    segments: tuple[TimelineSegmentPlaybackViewModel, ...]


@dataclass(slots=True, frozen=True)
class TimelineVehiclePositionViewModel:
    id_rota: str
    id_viatura: str
    latitude: float | None
    longitude: float | None
    phase: str
    active_segment: int | None = None
    active_stop: int | None = None


@dataclass(slots=True, frozen=True)
class TimelineRouteStateViewModel:
    id_rota: str
    current_at: str
    phase: str
    next_label: str | None
    active_stop_sequence: int | None
    active_segment_sequence: int | None
    completed_stop_sequences: tuple[int, ...]
    future_stop_sequences: tuple[int, ...]
    completed_segment_sequences: tuple[int, ...]
    future_segment_sequences: tuple[int, ...]
    vehicle_position: TimelineVehiclePositionViewModel


@dataclass(slots=True, frozen=True)
class TimelineSnapshotViewModel:
    available: bool
    warnings: tuple[str, ...]
    start_at: str | None
    end_at: str | None
    timezone_label: str
    routes: tuple[TimelineRoutePlaybackViewModel, ...]
    selected_route_steps: tuple[TimelineStepViewModel, ...]


def build_timeline_snapshot(
    snapshot: FilteredInspectionSnapshot,
    *,
    selected_route_id: str | None,
    include_return_to_base: bool = False,
) -> TimelineSnapshotViewModel:
    warnings: list[str] = []
    reference_tz = _resolve_reference_timezone(snapshot.route_rows, snapshot.route_stop_rows)
    routes: list[TimelineRoutePlaybackViewModel] = []
    start_candidates: list[datetime] = []
    end_candidates: list[datetime] = []

    for route_row in snapshot.route_rows:
        playback, route_warnings = _build_route_playback(
            route_row,
            route_stop_rows=tuple(row for row in snapshot.route_stop_rows if row.id_rota == route_row.id_rota),
            map_nodes=snapshot.map_nodes,
            reference_tz=reference_tz,
            include_return_to_base=include_return_to_base,
        )
        warnings.extend(route_warnings)
        if playback is None:
            continue
        routes.append(playback)
        start_dt = parse_datetime(playback.start_at)
        end_dt = parse_datetime(playback.end_at)
        if start_dt is not None:
            start_candidates.append(_normalize_datetime(start_dt, reference_tz))
        if end_dt is not None:
            end_candidates.append(_normalize_datetime(end_dt, reference_tz))

    routes.sort(key=lambda item: (item.classe_operacional, item.id_viatura, item.id_rota))
    if not routes or not start_candidates or not end_candidates:
        return TimelineSnapshotViewModel(
            available=False,
            warnings=tuple(warnings or ["Timeline indisponivel: nao ha rotas com horarios planejados validos."]),
            start_at=None,
            end_at=None,
            timezone_label=_timezone_label(reference_tz),
            routes=tuple(routes),
            selected_route_steps=(),
        )

    selected_route = find_timeline_route(routes, selected_route_id)
    return TimelineSnapshotViewModel(
        available=True,
        warnings=tuple(warnings),
        start_at=_format_datetime(min(start_candidates), reference_tz),
        end_at=_format_datetime(max(end_candidates), reference_tz),
        timezone_label=_timezone_label(reference_tz),
        routes=tuple(routes),
        selected_route_steps=selected_route.steps if selected_route is not None else (),
    )


def find_timeline_route(
    routes: Iterable[TimelineRoutePlaybackViewModel],
    route_id: str | None,
) -> TimelineRoutePlaybackViewModel | None:
    route_list = tuple(routes)
    if not route_list:
        return None
    if route_id:
        for route in route_list:
            if route.id_rota == route_id:
                return route
    return route_list[0]


def clamp_timeline_current_at(
    timeline: TimelineSnapshotViewModel,
    current_at: str | None,
) -> str | None:
    if not timeline.available or not timeline.start_at or not timeline.end_at:
        return None
    reference_tz = _parse_timeline_timezone(timeline.start_at)
    start_dt = _normalize_datetime(parse_datetime(timeline.start_at), reference_tz)
    end_dt = _normalize_datetime(parse_datetime(timeline.end_at), reference_tz)
    current_dt = _normalize_datetime(parse_datetime(current_at), reference_tz) if current_at else start_dt
    if current_dt <= start_dt:
        return timeline.start_at
    if current_dt >= end_dt:
        return timeline.end_at
    return _format_datetime(_floor_to_minute(current_dt), reference_tz)


def advance_timeline_current_at(
    timeline: TimelineSnapshotViewModel,
    current_at: str | None,
    *,
    step_seconds: int,
) -> str | None:
    if not timeline.available or not timeline.start_at or not timeline.end_at:
        return None
    reference_tz = _parse_timeline_timezone(timeline.start_at)
    base_dt = _normalize_datetime(parse_datetime(clamp_timeline_current_at(timeline, current_at)), reference_tz)
    next_dt = base_dt + timedelta(seconds=max(step_seconds, 0))
    return clamp_timeline_current_at(timeline, _format_datetime(next_dt, reference_tz))


def find_neighbor_event_at(
    timeline: TimelineSnapshotViewModel,
    current_at: str | None,
    *,
    direction: str,
) -> str | None:
    if not timeline.available:
        return None
    reference_tz = _parse_timeline_timezone(timeline.start_at)
    current_dt = _normalize_datetime(parse_datetime(clamp_timeline_current_at(timeline, current_at)), reference_tz)
    steps = sorted(
        _normalize_datetime(parsed, reference_tz)
        for route in timeline.routes
        for step in route.steps
        if (parsed := parse_datetime(step.timestamp)) is not None
    )
    if not steps:
        return clamp_timeline_current_at(timeline, current_at)
    if direction == "previous":
        for candidate in reversed(steps):
            if candidate < current_dt:
                return _format_datetime(candidate, reference_tz)
        return _format_datetime(steps[0], reference_tz)
    for candidate in steps:
        if candidate > current_dt:
            return _format_datetime(candidate, reference_tz)
    return _format_datetime(steps[-1], reference_tz)


def resolve_route_state(
    route: TimelineRoutePlaybackViewModel | None,
    current_at: str | None,
) -> TimelineRouteStateViewModel | None:
    if route is None:
        return None
    reference_tz = _parse_timeline_timezone(route.start_at)
    current_dt = _normalize_datetime(parse_datetime(current_at or route.start_at), reference_tz)
    start_dt = _normalize_datetime(parse_datetime(route.start_at), reference_tz)
    end_dt = _normalize_datetime(parse_datetime(route.end_at), reference_tz)

    completed_stop_sequences: list[int] = []
    future_stop_sequences: list[int] = []
    active_stop: TimelineStopPlaybackViewModel | None = None
    for stop in route.stops:
        stop_start = _normalize_datetime(parse_datetime(stop.start_at), reference_tz)
        stop_end = _normalize_datetime(parse_datetime(stop.end_at), reference_tz)
        if current_dt < stop_start:
            future_stop_sequences.append(stop.sequencia)
            continue
        if _is_in_interval(current_dt, stop_start, stop_end):
            active_stop = stop
            continue
        completed_stop_sequences.append(stop.sequencia)

    completed_segment_sequences: list[int] = []
    future_segment_sequences: list[int] = []
    active_segment: TimelineSegmentPlaybackViewModel | None = None
    for segment in route.segments:
        segment_start = _normalize_datetime(parse_datetime(segment.start_at), reference_tz)
        segment_end = _normalize_datetime(parse_datetime(segment.end_at), reference_tz)
        if current_dt < segment_start:
            future_segment_sequences.append(segment.ordem_segmento)
            continue
        if _is_in_interval(current_dt, segment_start, segment_end):
            active_segment = segment
            continue
        completed_segment_sequences.append(segment.ordem_segmento)

    phase = "aguardando"
    next_label = None
    vehicle_position = TimelineVehiclePositionViewModel(
        id_rota=route.id_rota,
        id_viatura=route.id_viatura,
        latitude=route.base_latitude,
        longitude=route.base_longitude,
        phase=phase,
    )

    if current_dt >= end_dt:
        phase = "finalizada"
        vehicle_position = TimelineVehiclePositionViewModel(
            id_rota=route.id_rota,
            id_viatura=route.id_viatura,
            latitude=route.final_latitude,
            longitude=route.final_longitude,
            phase=phase,
        )
    elif active_stop is not None:
        phase = "em_atendimento"
        next_label = _next_stop_label(route, current_dt, reference_tz)
        vehicle_position = TimelineVehiclePositionViewModel(
            id_rota=route.id_rota,
            id_viatura=route.id_viatura,
            latitude=active_stop.latitude,
            longitude=active_stop.longitude,
            phase=phase,
            active_stop=active_stop.sequencia,
        )
    elif active_segment is not None:
        phase = "encerrando" if active_segment.kind == "retorno" else "em_deslocamento"
        next_label = _segment_next_label(active_segment, route)
        vehicle_position = TimelineVehiclePositionViewModel(
            id_rota=route.id_rota,
            id_viatura=route.id_viatura,
            latitude=_interpolate(
                active_segment.from_latitude,
                active_segment.to_latitude,
                active_segment.start_at,
                active_segment.end_at,
                current_dt,
                reference_tz,
            ),
            longitude=_interpolate(
                active_segment.from_longitude,
                active_segment.to_longitude,
                active_segment.start_at,
                active_segment.end_at,
                current_dt,
                reference_tz,
            ),
            phase=phase,
            active_segment=active_segment.ordem_segmento,
        )
    elif current_dt < start_dt:
        phase = "aguardando"
        next_label = route.steps[1].label if len(route.steps) > 1 else route.steps[0].label if route.steps else None
    elif future_stop_sequences:
        phase = "em_deslocamento"
        next_label = _next_stop_label(route, current_dt, reference_tz)
        vehicle_position = TimelineVehiclePositionViewModel(
            id_rota=route.id_rota,
            id_viatura=route.id_viatura,
            latitude=_last_known_latitude(route, completed_stop_sequences),
            longitude=_last_known_longitude(route, completed_stop_sequences),
            phase=phase,
        )
    else:
        phase = "encerrando"
        vehicle_position = TimelineVehiclePositionViewModel(
            id_rota=route.id_rota,
            id_viatura=route.id_viatura,
            latitude=route.final_latitude,
            longitude=route.final_longitude,
            phase=phase,
        )

    return TimelineRouteStateViewModel(
        id_rota=route.id_rota,
        current_at=_format_datetime(current_dt, reference_tz),
        phase=phase,
        next_label=next_label,
        active_stop_sequence=active_stop.sequencia if active_stop else None,
        active_segment_sequence=active_segment.ordem_segmento if active_segment else None,
        completed_stop_sequences=tuple(completed_stop_sequences),
        future_stop_sequences=tuple(future_stop_sequences),
        completed_segment_sequences=tuple(completed_segment_sequences),
        future_segment_sequences=tuple(future_segment_sequences),
        vehicle_position=vehicle_position,
    )


def resolve_vehicle_positions(
    timeline: TimelineSnapshotViewModel,
    current_at: str | None,
) -> tuple[TimelineVehiclePositionViewModel, ...]:
    positions = []
    for route in timeline.routes:
        state = resolve_route_state(route, current_at)
        if state is None:
            continue
        positions.append(state.vehicle_position)
    return tuple(positions)


def derive_stop_temporal_status(
    stop: RouteStopRowViewModel,
    current_at: str | None,
) -> str:
    if not current_at:
        return "futura"
    reference_tz = _parse_timeline_timezone(current_at)
    stop_start = parse_datetime(stop.inicio_previsto)
    stop_end = parse_datetime(stop.fim_previsto) or stop_start
    current_dt = _normalize_datetime(parse_datetime(current_at), reference_tz)
    if stop_start is None or stop_end is None:
        return "futura"
    start_dt = _normalize_datetime(stop_start, reference_tz)
    end_dt = _normalize_datetime(stop_end, reference_tz)
    if current_dt < start_dt:
        return "futura"
    if _is_in_interval(current_dt, start_dt, end_dt):
        return "ativa"
    return "concluida"


def resolve_selected_step_index(
    steps: tuple[TimelineStepViewModel, ...],
    current_at: str | None,
) -> int:
    if not steps:
        return 0
    reference_tz = _parse_timeline_timezone(steps[0].timestamp)
    current_dt = _normalize_datetime(parse_datetime(current_at or steps[0].timestamp), reference_tz)
    index = 0
    for candidate_index, step in enumerate(steps):
        step_dt = _normalize_datetime(parse_datetime(step.timestamp), reference_tz)
        if step_dt <= current_dt:
            index = candidate_index
        else:
            break
    return index


def format_timeline_label(value: str | None, timezone_label: str) -> str:
    if not value:
        return "-"
    parsed = parse_datetime(value)
    if parsed is None:
        return str(value)
    normalized = _normalize_datetime(parsed, parsed.tzinfo)
    return f"{normalized.strftime('%Y-%m-%d %H:%M:%S')} ({timezone_label})"


def minute_marks(timeline: TimelineSnapshotViewModel) -> tuple[str, ...]:
    if not timeline.available or not timeline.start_at or not timeline.end_at:
        return ()
    reference_tz = _parse_timeline_timezone(timeline.start_at)
    start_dt = _normalize_datetime(parse_datetime(timeline.start_at), reference_tz)
    end_dt = _normalize_datetime(parse_datetime(timeline.end_at), reference_tz)
    values = {
        _format_datetime(start_dt, reference_tz),
        _format_datetime(end_dt, reference_tz),
    }
    cursor = _floor_to_minute(start_dt)
    while cursor < end_dt:
        if cursor >= start_dt:
            values.add(_format_datetime(cursor, reference_tz))
        cursor += timedelta(minutes=1)
    for route in timeline.routes:
        for step in route.steps:
            if parse_datetime(step.timestamp) is not None:
                values.add(step.timestamp)
    return tuple(sorted(values))


def _build_route_playback(
    route_row: RouteRowViewModel,
    *,
    route_stop_rows: tuple[RouteStopRowViewModel, ...],
    map_nodes: tuple[MapNodeViewModel, ...],
    reference_tz: tzinfo | None,
    include_return_to_base: bool,
) -> tuple[TimelineRoutePlaybackViewModel | None, tuple[str, ...]]:
    warnings: list[str] = []
    timed_stops: list[TimelineStopPlaybackViewModel] = []
    route_start = parse_datetime(route_row.inicio_previsto)
    route_end = parse_datetime(route_row.fim_previsto)
    base_node = _find_base_node(map_nodes, route_row.id_base)

    for stop_row in sorted(route_stop_rows, key=lambda item: item.sequencia):
        stop_start = parse_datetime(stop_row.inicio_previsto)
        stop_end = parse_datetime(stop_row.fim_previsto) or stop_start
        if stop_start is None and stop_end is None:
            warnings.append(
                f"Parada ignorada na timeline por horario invalido: rota {route_row.id_rota}, ordem {stop_row.id_ordem}."
            )
            continue
        if stop_start is None:
            stop_start = stop_end
        if stop_end is None:
            stop_end = stop_start
        stop_node = _find_stop_node(map_nodes, stop_row)
        anchor_dt = stop_start + ((stop_end - stop_start) / 2 if stop_end >= stop_start else timedelta(0))
        timed_stops.append(
            TimelineStopPlaybackViewModel(
                sequencia=stop_row.sequencia,
                id_ordem=stop_row.id_ordem,
                id_ponto=stop_row.id_ponto,
                criticidade=stop_row.criticidade or None,
                start_at=_format_datetime(_normalize_datetime(stop_start, reference_tz), reference_tz),
                end_at=_format_datetime(_normalize_datetime(stop_end, reference_tz), reference_tz),
                anchor_at=_format_datetime(_normalize_datetime(anchor_dt, reference_tz), reference_tz),
                latitude=stop_node.latitude if stop_node else None,
                longitude=stop_node.longitude if stop_node else None,
            )
        )

    route_start = route_start or (parse_datetime(timed_stops[0].start_at) if timed_stops else None)
    route_end = route_end or (parse_datetime(timed_stops[-1].end_at) if timed_stops else None)
    if route_start is None or route_end is None:
        warnings.append(f"Rota ignorada na timeline por inicio/fim planejado invalido: {route_row.id_rota}.")
        return None, tuple(warnings)

    route_start = _normalize_datetime(route_start, reference_tz)
    route_end = _normalize_datetime(route_end, reference_tz)
    if route_end < route_start:
        warnings.append(f"Rota com fim anterior ao inicio ajustada na timeline: {route_row.id_rota}.")
        route_end = route_start

    steps: list[TimelineStepViewModel] = [
        TimelineStepViewModel(
            kind="inicio_rota",
            timestamp=_format_datetime(route_start, reference_tz),
            sequencia=0,
            label=f"Inicio da rota {route_row.id_rota}",
            id_rota=route_row.id_rota,
        )
    ]
    for stop in timed_stops:
        steps.append(
            TimelineStepViewModel(
                kind="parada",
                timestamp=stop.anchor_at,
                sequencia=stop.sequencia,
                label=f"Parada {stop.sequencia}: {stop.id_ponto} / {stop.id_ordem}",
                id_rota=route_row.id_rota,
                id_ordem=stop.id_ordem,
                id_ponto=stop.id_ponto,
            )
        )
    steps.append(
        TimelineStepViewModel(
            kind="fim_rota",
            timestamp=_format_datetime(route_end, reference_tz),
            sequencia=(timed_stops[-1].sequencia + 1) if timed_stops else 1,
            label=f"Fim da rota {route_row.id_rota}",
            id_rota=route_row.id_rota,
        )
    )

    segments: list[TimelineSegmentPlaybackViewModel] = []
    previous_latitude = base_node.latitude if base_node else None
    previous_longitude = base_node.longitude if base_node else None
    previous_end_at = _format_datetime(route_start, reference_tz)
    for stop in timed_stops:
        if (
            previous_latitude is not None
            and previous_longitude is not None
            and stop.latitude is not None
            and stop.longitude is not None
        ):
            segments.append(
                TimelineSegmentPlaybackViewModel(
                    kind="deslocamento",
                    ordem_segmento=stop.sequencia,
                    start_at=previous_end_at,
                    end_at=stop.start_at,
                    from_latitude=previous_latitude,
                    from_longitude=previous_longitude,
                    to_latitude=stop.latitude,
                    to_longitude=stop.longitude,
                )
            )
        previous_latitude = stop.latitude if stop.latitude is not None else previous_latitude
        previous_longitude = stop.longitude if stop.longitude is not None else previous_longitude
        previous_end_at = stop.end_at

    final_latitude = previous_latitude if previous_latitude is not None else (base_node.latitude if base_node else None)
    final_longitude = previous_longitude if previous_longitude is not None else (base_node.longitude if base_node else None)
    if (
        include_return_to_base
        and timed_stops
        and base_node is not None
        and timed_stops[-1].latitude is not None
        and timed_stops[-1].longitude is not None
    ):
        segments.append(
            TimelineSegmentPlaybackViewModel(
                kind="retorno",
                ordem_segmento=timed_stops[-1].sequencia + 1,
                start_at=timed_stops[-1].end_at,
                end_at=_format_datetime(route_end, reference_tz),
                from_latitude=timed_stops[-1].latitude,
                from_longitude=timed_stops[-1].longitude,
                to_latitude=base_node.latitude,
                to_longitude=base_node.longitude,
            )
        )
        final_latitude = base_node.latitude
        final_longitude = base_node.longitude

    return (
        TimelineRoutePlaybackViewModel(
            id_rota=route_row.id_rota,
            id_viatura=route_row.id_viatura,
            classe_operacional=route_row.classe_operacional,
            start_at=_format_datetime(route_start, reference_tz),
            end_at=_format_datetime(route_end, reference_tz),
            base_latitude=base_node.latitude if base_node else None,
            base_longitude=base_node.longitude if base_node else None,
            final_latitude=final_latitude,
            final_longitude=final_longitude,
            steps=tuple(steps),
            stops=tuple(timed_stops),
            segments=tuple(segments),
        ),
        tuple(warnings),
    )


def _find_base_node(
    map_nodes: tuple[MapNodeViewModel, ...],
    base_id: str,
) -> MapNodeViewModel | None:
    for node in map_nodes:
        if node.kind == "base" and node.source_id == base_id:
            return node
    return None


def _find_stop_node(
    map_nodes: tuple[MapNodeViewModel, ...],
    stop_row: RouteStopRowViewModel,
) -> MapNodeViewModel | None:
    for node in map_nodes:
        if node.id_rota != stop_row.id_rota:
            continue
        if node.source_id != stop_row.id_ponto:
            continue
        if str(node.tooltip_fields.get("id_ordem") or "") == stop_row.id_ordem:
            return node
    for node in map_nodes:
        if node.id_rota == stop_row.id_rota and node.source_id == stop_row.id_ponto:
            return node
    return None


def _next_stop_label(
    route: TimelineRoutePlaybackViewModel,
    current_dt: datetime,
    reference_tz: tzinfo | None,
) -> str | None:
    for stop in route.stops:
        stop_start = _normalize_datetime(parse_datetime(stop.start_at), reference_tz)
        if current_dt <= stop_start:
            return f"{stop.id_ponto} / {stop.id_ordem}"
    for segment in route.segments:
        if segment.kind == "retorno":
            segment_start = _normalize_datetime(parse_datetime(segment.start_at), reference_tz)
            if current_dt <= segment_start:
                return "Retorno a base"
    return None


def _segment_next_label(
    segment: TimelineSegmentPlaybackViewModel,
    route: TimelineRoutePlaybackViewModel,
) -> str | None:
    if segment.kind == "retorno":
        return "Retorno a base"
    for stop in route.stops:
        if stop.sequencia == segment.ordem_segmento:
            return f"{stop.id_ponto} / {stop.id_ordem}"
    return None


def _last_known_latitude(
    route: TimelineRoutePlaybackViewModel,
    completed_stop_sequences: list[int],
) -> float | None:
    for stop in reversed(route.stops):
        if stop.sequencia in completed_stop_sequences and stop.latitude is not None:
            return stop.latitude
    return route.base_latitude


def _last_known_longitude(
    route: TimelineRoutePlaybackViewModel,
    completed_stop_sequences: list[int],
) -> float | None:
    for stop in reversed(route.stops):
        if stop.sequencia in completed_stop_sequences and stop.longitude is not None:
            return stop.longitude
    return route.base_longitude


def _interpolate(
    start_value: float | None,
    end_value: float | None,
    start_at: str,
    end_at: str,
    current_dt: datetime,
    reference_tz: tzinfo | None,
) -> float | None:
    start_dt = _normalize_datetime(parse_datetime(start_at), reference_tz)
    end_dt = _normalize_datetime(parse_datetime(end_at), reference_tz)
    if start_value is None:
        return end_value
    if end_value is None:
        return start_value
    total_seconds = (end_dt - start_dt).total_seconds()
    if total_seconds <= 0:
        return end_value
    elapsed_seconds = max(0.0, min((current_dt - start_dt).total_seconds(), total_seconds))
    progress = elapsed_seconds / total_seconds
    return start_value + ((end_value - start_value) * progress)


def _resolve_reference_timezone(
    route_rows: tuple[RouteRowViewModel, ...],
    route_stop_rows: tuple[RouteStopRowViewModel, ...],
) -> tzinfo | None:
    for value in (
        *(row.inicio_previsto for row in route_rows),
        *(row.fim_previsto for row in route_rows),
        *(row.inicio_previsto for row in route_stop_rows),
        *(row.fim_previsto for row in route_stop_rows),
    ):
        parsed = parse_datetime(value)
        if parsed is not None and parsed.tzinfo is not None:
            return parsed.tzinfo
    return UTC


def _normalize_datetime(
    value: datetime | None,
    reference_tz: tzinfo | None,
) -> datetime:
    if value is None:
        raise ValueError("Horario invalido para operacao temporal.")
    if value.tzinfo is None:
        return value.replace(tzinfo=reference_tz or UTC)
    if reference_tz is None:
        return value
    return value.astimezone(reference_tz)


def _format_datetime(value: datetime, reference_tz: tzinfo | None) -> str:
    normalized = _normalize_datetime(value, reference_tz)
    return normalized.isoformat(timespec="seconds")


def _timezone_label(reference_tz: tzinfo | None) -> str:
    current = datetime.now(reference_tz or UTC).strftime("%z")
    if not current:
        return "UTC"
    return f"UTC{current[:3]}:{current[3:]}"


def _parse_timeline_timezone(value: str | None) -> tzinfo | None:
    parsed = parse_datetime(value)
    if parsed is None or parsed.tzinfo is None:
        return UTC
    return parsed.tzinfo


def _is_in_interval(current_dt: datetime, start_dt: datetime, end_dt: datetime) -> bool:
    if end_dt <= start_dt:
        return current_dt == start_dt
    return start_dt <= current_dt < end_dt


def _floor_to_minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)

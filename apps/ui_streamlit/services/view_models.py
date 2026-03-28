from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable


CRITICITY_ORDER = {
    None: -1,
    "baixa": 0,
    "media": 1,
    "alta": 2,
    "critica": 3,
}


@dataclass(slots=True, frozen=True)
class ExecutionSummaryViewModel:
    id_execucao: str
    hash_cenario: str
    status_final: str
    reused_cached_result: bool
    recovered_previous_context: bool
    attempt_number: int
    snapshot_materialized: bool


@dataclass(slots=True, frozen=True)
class KpiCardsViewModel:
    custo_total_estimado: str
    distancia_total_estimada: int
    duracao_total_estimada_segundos: int
    taxa_atendimento: str
    utilizacao_frota: str
    viaturas_acionadas: int
    total_ordens_atendidas: int
    total_ordens_especiais_atendidas: int
    total_ordens_nao_atendidas: int
    impacto_financeiro_cancelamentos: str
    penalidade_total_nao_atendimento: str


@dataclass(slots=True, frozen=True)
class RouteRowViewModel:
    classe_operacional: str
    id_rota: str
    id_viatura: str
    id_base: str
    inicio_previsto: str
    fim_previsto: str
    distancia_estimada: int
    duracao_estimada_segundos: int
    custo_estimado: str
    quantidade_paradas: int
    atingiu_limite_segurado: bool
    possui_violacao_janela: bool
    possui_excesso_capacidade: bool
    maior_criticidade: str | None
    criticidades: tuple[str, ...]
    status_atendimento: str = "atendida"


@dataclass(slots=True, frozen=True)
class RouteStopRowViewModel:
    id_rota: str
    id_viatura: str
    classe_operacional: str
    sequencia: int
    id_ordem: str
    id_ponto: str
    tipo_servico: str
    criticidade: str
    inicio_previsto: str
    fim_previsto: str
    folga_janela_segundos: int
    espera_segundos: int
    atraso_segundos: int
    demanda: dict[str, Any]
    carga_acumulada: dict[str, Any]
    status_atendimento: str = "atendida"


@dataclass(slots=True, frozen=True)
class MapNodeViewModel:
    node_id: str
    source_id: str | None
    kind: str
    latitude: float
    longitude: float
    label: str
    tooltip_fields: dict[str, Any]
    id_rota: str | None = None
    id_viatura: str | None = None
    classe_operacional: str | None = None
    criticidade: str | None = None
    status_atendimento: str | None = None


@dataclass(slots=True, frozen=True)
class MapSegmentViewModel:
    segment_id: str
    id_rota: str
    id_viatura: str
    from_latitude: float
    from_longitude: float
    to_latitude: float
    to_longitude: float
    ordem_segmento: int
    classe_operacional: str
    destacado: bool = False
    status_atendimento: str = "atendida"


@dataclass(slots=True, frozen=True)
class AlertViewModel:
    severity: str
    category: str
    title: str
    description: str
    related_entity_type: str
    related_entity_id: str | None
    id_rota: str | None = None
    id_viatura: str | None = None
    classe_operacional: str | None = None
    criticidade: str | None = None
    status_atendimento: str | None = None


@dataclass(slots=True, frozen=True)
class InspectionSnapshotViewModel:
    execution_summary: ExecutionSummaryViewModel
    kpi_cards: KpiCardsViewModel
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
    relatorio_destaques: tuple[str, ...]
    available_filters: dict[str, tuple[str, ...]]
    map_available: bool
    map_warnings: tuple[str, ...]
    source_has_inputs: bool


def build_inspection_snapshot(
    raw_response: dict[str, Any],
    *,
    input_payload: dict[str, Any] | None = None,
) -> InspectionSnapshotViewModel:
    result = _resolve_result(raw_response)
    route_rows = build_route_rows(raw_response)
    route_stop_rows = build_route_stop_rows(raw_response)
    map_nodes, map_segments, map_warnings, map_available = build_map_layers(raw_response, input_payload=input_payload)
    snapshot = InspectionSnapshotViewModel(
        execution_summary=build_execution_summary(raw_response),
        kpi_cards=build_kpi_cards(raw_response),
        route_rows=route_rows,
        route_stop_rows=route_stop_rows,
        map_nodes=map_nodes,
        map_segments=map_segments,
        alerts=(),
        event_rows=build_event_rows(raw_response),
        reason_rows=build_reason_rows(raw_response),
        non_served_rows=build_non_served_rows(raw_response),
        excluded_rows=build_excluded_rows(raw_response),
        cancelled_rows=build_cancelled_rows(raw_response),
        error_rows=build_error_rows(raw_response),
        relatorio_destaques=tuple(result.get("relatorio_planejamento", {}).get("destaques", []) or ()),
        available_filters={},
        map_available=map_available,
        map_warnings=tuple(map_warnings),
        source_has_inputs=bool(input_payload and input_payload.get("bases") and input_payload.get("pontos")),
    )
    return replace(snapshot, available_filters=build_available_filters(snapshot))


def with_alerts(
    snapshot: InspectionSnapshotViewModel,
    alerts: Iterable[AlertViewModel],
) -> InspectionSnapshotViewModel:
    resolved = replace(snapshot, alerts=tuple(alerts))
    return replace(resolved, available_filters=build_available_filters(resolved))


def build_execution_summary(raw_response: dict[str, Any]) -> ExecutionSummaryViewModel:
    return ExecutionSummaryViewModel(
        id_execucao=str(raw_response.get("id_execucao") or ""),
        hash_cenario=str(raw_response.get("hash_cenario") or ""),
        status_final=str(raw_response.get("status_final") or ""),
        reused_cached_result=bool(raw_response.get("reused_cached_result", False)),
        recovered_previous_context=bool(raw_response.get("recovered_previous_context", False)),
        attempt_number=int(raw_response.get("attempt_number", 0) or 0),
        snapshot_materialized=raw_response.get("snapshot_materialization") is not None,
    )


def build_kpi_cards(raw_response: dict[str, Any]) -> KpiCardsViewModel:
    result = _resolve_result(raw_response)
    operacional = result.get("kpi_operacional", {})
    gerencial = result.get("kpi_gerencial", {})
    resumo = result.get("resumo_operacional", {})
    return KpiCardsViewModel(
        custo_total_estimado=str(gerencial.get("custo_total_estimado") or "0"),
        distancia_total_estimada=int(operacional.get("distancia_total_estimada", 0) or 0),
        duracao_total_estimada_segundos=int(operacional.get("duracao_total_estimada_segundos", 0) or 0),
        taxa_atendimento=str(operacional.get("taxa_atendimento") or "0"),
        utilizacao_frota=str(operacional.get("utilizacao_frota") or "0"),
        viaturas_acionadas=int(operacional.get("viaturas_acionadas", 0) or 0),
        total_ordens_atendidas=int(operacional.get("total_ordens_atendidas", 0) or 0),
        total_ordens_especiais_atendidas=int(operacional.get("total_ordens_especiais_atendidas", 0) or 0),
        total_ordens_nao_atendidas=int(resumo.get("total_ordens_nao_atendidas", 0) or 0),
        impacto_financeiro_cancelamentos=str(gerencial.get("impacto_financeiro_cancelamentos") or "0"),
        penalidade_total_nao_atendimento=str(gerencial.get("penalidade_total_nao_atendimento") or "0"),
    )


def build_route_rows(raw_response: dict[str, Any]) -> tuple[RouteRowViewModel, ...]:
    result = _resolve_result(raw_response)
    rows: list[RouteRowViewModel] = []
    for collection_name in ("rotas_suprimento", "rotas_recolhimento"):
        for route in result.get(collection_name, []) or []:
            criticidades = tuple(sorted({str(stop.get("criticidade") or "") for stop in route.get("paradas", []) if stop.get("criticidade")}))
            rows.append(
                RouteRowViewModel(
                    classe_operacional=str(route.get("classe_operacional") or collection_name.replace("rotas_", "")),
                    id_rota=str(route.get("id_rota") or ""),
                    id_viatura=str(route.get("id_viatura") or ""),
                    id_base=str(route.get("id_base") or ""),
                    inicio_previsto=str(route.get("inicio_previsto") or ""),
                    fim_previsto=str(route.get("fim_previsto") or ""),
                    distancia_estimada=int(route.get("distancia_estimada", 0) or 0),
                    duracao_estimada_segundos=int(route.get("duracao_estimada_segundos", 0) or 0),
                    custo_estimado=str(route.get("custo_estimado") or "0"),
                    quantidade_paradas=len(route.get("paradas", []) or []),
                    atingiu_limite_segurado=bool(route.get("atingiu_limite_segurado", False)),
                    possui_violacao_janela=bool(route.get("possui_violacao_janela", False)),
                    possui_excesso_capacidade=bool(route.get("possui_excesso_capacidade", False)),
                    maior_criticidade=_highest_criticidade(criticidades),
                    criticidades=criticidades,
                )
            )
    rows.sort(key=lambda item: (item.classe_operacional, item.id_viatura, item.id_rota))
    return tuple(rows)


def build_route_stop_rows(raw_response: dict[str, Any]) -> tuple[RouteStopRowViewModel, ...]:
    result = _resolve_result(raw_response)
    rows: list[RouteStopRowViewModel] = []
    for collection_name in ("rotas_suprimento", "rotas_recolhimento"):
        for route in result.get(collection_name, []) or []:
            for stop in route.get("paradas", []) or []:
                rows.append(
                    RouteStopRowViewModel(
                        id_rota=str(route.get("id_rota") or ""),
                        id_viatura=str(route.get("id_viatura") or ""),
                        classe_operacional=str(route.get("classe_operacional") or collection_name.replace("rotas_", "")),
                        sequencia=int(stop.get("sequencia", 0) or 0),
                        id_ordem=str(stop.get("id_ordem") or ""),
                        id_ponto=str(stop.get("id_ponto") or ""),
                        tipo_servico=str(stop.get("tipo_servico") or ""),
                        criticidade=str(stop.get("criticidade") or ""),
                        inicio_previsto=str(stop.get("inicio_previsto") or ""),
                        fim_previsto=str(stop.get("fim_previsto") or ""),
                        folga_janela_segundos=int(stop.get("folga_janela_segundos", 0) or 0),
                        espera_segundos=int(stop.get("espera_segundos", 0) or 0),
                        atraso_segundos=int(stop.get("atraso_segundos", 0) or 0),
                        demanda=dict(stop.get("demanda") or {}),
                        carga_acumulada=dict(stop.get("carga_acumulada") or {}),
                    )
                )
    rows.sort(key=lambda item: (item.id_rota, item.sequencia))
    return tuple(rows)


def build_map_layers(
    raw_response: dict[str, Any],
    *,
    input_payload: dict[str, Any] | None,
    include_return_to_base: bool = False,
) -> tuple[tuple[MapNodeViewModel, ...], tuple[MapSegmentViewModel, ...], tuple[str, ...], bool]:
    if not input_payload:
        return (), (), (
            "Mapa indisponivel: resultado carregado sem bases e pontos de entrada.",
        ), False

    bases_index = {
        str(base.get("id_base") or ""): base
        for base in input_payload.get("bases", []) or []
        if isinstance(base, dict) and base.get("id_base")
    }
    points_index = {
        str(point.get("id_ponto") or ""): point
        for point in input_payload.get("pontos", []) or []
        if isinstance(point, dict) and point.get("id_ponto")
    }
    if not bases_index or not points_index:
        return (), (), (
            "Mapa indisponivel: a entrada local nao contem bases e pontos suficientes para cruzamento de coordenadas.",
        ), False

    result = _resolve_result(raw_response)
    warnings: set[str] = set()
    nodes: list[MapNodeViewModel] = []
    segments: list[MapSegmentViewModel] = []
    seen_base_ids: set[str] = set()

    for base_id, base in bases_index.items():
        coordinates = _extract_coordinates(base)
        if coordinates is None:
            warnings.add(f"Base sem coordenadas validas ignorada no mapa: {base_id}.")
            continue
        nodes.append(
            MapNodeViewModel(
                node_id=f"base:{base_id}",
                source_id=base_id,
                kind="base",
                latitude=coordinates[0],
                longitude=coordinates[1],
                label=str(base.get("nome") or base_id),
                tooltip_fields={"id_base": base_id, "nome": str(base.get("nome") or base_id)},
            )
        )
        seen_base_ids.add(base_id)

    for route in _iter_routes(result):
        base_id = str(route.get("id_base") or "")
        base_payload = bases_index.get(base_id)
        base_coordinates = None if base_payload is None else _extract_coordinates(base_payload)
        if base_payload is None or base_coordinates is None:
            warnings.add(f"Base referenciada pela rota nao encontrada no input original: {base_id}.")
            continue
        previous_point = base_coordinates
        previous_label = base_id
        for ordinal, stop in enumerate(route.get("paradas", []) or [], start=1):
            point_id = str(stop.get("id_ponto") or "")
            point_payload = points_index.get(point_id)
            coordinates = None if point_payload is None else _extract_coordinates(point_payload)
            if point_payload is None or coordinates is None:
                warnings.add(f"Ponto referenciado pela rota nao encontrado no input original: {point_id}.")
                continue
            nodes.append(
                MapNodeViewModel(
                    node_id=f"ponto_atendido:{route.get('id_rota')}:{stop.get('id_ordem')}:{ordinal}",
                    source_id=point_id,
                    kind="ponto_atendido",
                    latitude=coordinates[0],
                    longitude=coordinates[1],
                    label=f"{point_id} - ordem {stop.get('id_ordem')}",
                    tooltip_fields={
                        "id_rota": route.get("id_rota"),
                        "id_viatura": route.get("id_viatura"),
                        "id_ordem": stop.get("id_ordem"),
                        "id_ponto": point_id,
                        "criticidade": stop.get("criticidade"),
                        "inicio_previsto": stop.get("inicio_previsto"),
                    },
                    id_rota=str(route.get("id_rota") or ""),
                    id_viatura=str(route.get("id_viatura") or ""),
                    classe_operacional=str(route.get("classe_operacional") or ""),
                    criticidade=str(stop.get("criticidade") or "") or None,
                    status_atendimento="atendida",
                )
            )
            segments.append(
                MapSegmentViewModel(
                    segment_id=f"segment:{route.get('id_rota')}:{ordinal}",
                    id_rota=str(route.get("id_rota") or ""),
                    id_viatura=str(route.get("id_viatura") or ""),
                    from_latitude=previous_point[0],
                    from_longitude=previous_point[1],
                    to_latitude=coordinates[0],
                    to_longitude=coordinates[1],
                    ordem_segmento=ordinal,
                    classe_operacional=str(route.get("classe_operacional") or ""),
                )
            )
            previous_point = coordinates
            previous_label = point_id
        if include_return_to_base and route.get("paradas"):
            segments.append(
                MapSegmentViewModel(
                    segment_id=f"segment:{route.get('id_rota')}:retorno",
                    id_rota=str(route.get("id_rota") or ""),
                    id_viatura=str(route.get("id_viatura") or ""),
                    from_latitude=previous_point[0],
                    from_longitude=previous_point[1],
                    to_latitude=base_coordinates[0],
                    to_longitude=base_coordinates[1],
                    ordem_segmento=len(route.get("paradas") or []) + 1,
                    classe_operacional=str(route.get("classe_operacional") or ""),
                )
            )

    for row in build_non_served_rows(raw_response):
        point_id = str(row.get("id_ponto") or "")
        point_payload = points_index.get(point_id)
        coordinates = None if point_payload is None else _extract_coordinates(point_payload)
        if point_payload is None or coordinates is None:
            warnings.add(f"Ponto nao atendido sem coordenada local disponivel: {point_id}.")
            continue
        nodes.append(
            MapNodeViewModel(
                node_id=f"ponto_nao_atendido:{row.get('id_ordem')}",
                source_id=point_id,
                kind="ponto_nao_atendido",
                latitude=coordinates[0],
                longitude=coordinates[1],
                label=f"{point_id} - ordem {row.get('id_ordem')}",
                tooltip_fields=row,
                classe_operacional=str(row.get("classe_operacional") or "") or None,
                criticidade=str(row.get("criticidade") or "") or None,
                status_atendimento="nao_atendida",
            )
        )

    for kind, rows in (("ponto_excluido", build_excluded_rows(raw_response)), ("ponto_cancelado", build_cancelled_rows(raw_response))):
        for row in rows:
            point_id = str(row.get("id_ponto") or "")
            point_payload = points_index.get(point_id)
            coordinates = None if point_payload is None else _extract_coordinates(point_payload)
            if point_payload is None or coordinates is None:
                warnings.add(f"Ponto de excecao sem coordenada local disponivel: {point_id}.")
                continue
            nodes.append(
                MapNodeViewModel(
                    node_id=f"{kind}:{row.get('id_ordem')}",
                    source_id=point_id,
                    kind=kind,
                    latitude=coordinates[0],
                    longitude=coordinates[1],
                    label=f"{point_id} - ordem {row.get('id_ordem')}",
                    tooltip_fields=row,
                    classe_operacional=str(row.get("classe_operacional") or "") or None,
                    criticidade=str(row.get("criticidade") or "") or None,
                    status_atendimento=str(row.get("status_atendimento") or "") or None,
                )
            )

    map_available = bool(nodes or segments)
    return tuple(nodes), tuple(segments), tuple(sorted(warnings)), map_available


def build_event_rows(raw_response: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    result = _resolve_result(raw_response)
    rows = []
    for event in result.get("eventos_auditoria", []) or []:
        rows.append(
            {
                "id_evento": event.get("id_evento"),
                "tipo_evento": event.get("tipo_evento"),
                "severidade": event.get("severidade"),
                "entidade_afetada": event.get("entidade_afetada"),
                "id_entidade": event.get("id_entidade"),
                "regra_relacionada": event.get("regra_relacionada"),
                "motivo": event.get("motivo"),
                "timestamp_evento": event.get("timestamp_evento"),
                "campo_afetado": event.get("campo_afetado"),
                "valor_observado": event.get("valor_observado"),
                "valor_esperado": event.get("valor_esperado"),
            }
        )
    return tuple(rows)


def build_reason_rows(raw_response: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    result = _resolve_result(raw_response)
    rows = []
    for reason in result.get("motivos_inviabilidade", []) or []:
        rows.append(
            {
                "codigo": reason.get("codigo"),
                "descricao": reason.get("descricao"),
                "entidade": reason.get("entidade"),
                "id_entidade": reason.get("id_entidade"),
                "severidade": reason.get("severidade"),
                "origem": reason.get("origem"),
                "regra_relacionada": reason.get("regra_relacionada"),
                "contexto": dict(reason.get("contexto") or {}),
            }
        )
    return tuple(rows)


def build_non_served_rows(raw_response: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    result = _resolve_result(raw_response)
    rows = []
    for order in result.get("ordens_nao_atendidas", []) or []:
        rows.append(
            {
                "id_ordem": order.get("id_ordem"),
                "id_no": order.get("id_no"),
                "id_ponto": order.get("id_ponto"),
                "tipo_servico": order.get("tipo_servico"),
                "classe_operacional": order.get("classe_operacional"),
                "criticidade": order.get("criticidade"),
                "penalidade_aplicada": order.get("penalidade_aplicada"),
                "motivo": order.get("motivo"),
                "status_atendimento": "nao_atendida",
            }
        )
    return tuple(rows)


def build_excluded_rows(raw_response: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    result = _resolve_result(raw_response)
    return tuple(_flatten_order_classified(item, status_atendimento="excluida") for item in result.get("ordens_excluidas", []) or [])


def build_cancelled_rows(raw_response: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    result = _resolve_result(raw_response)
    return tuple(_flatten_order_classified(item, status_atendimento="cancelada") for item in result.get("ordens_canceladas", []) or [])


def build_error_rows(raw_response: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    result = _resolve_result(raw_response)
    rows = []
    for error in result.get("erros", []) or []:
        rows.append(
            {
                "id_erro": error.get("id_erro"),
                "tipo_erro": error.get("tipo_erro"),
                "codigo_erro": error.get("codigo_erro") or error.get("codigo_regra"),
                "mensagem": error.get("mensagem"),
                "entidade": error.get("entidade"),
                "id_entidade": error.get("id_entidade"),
                "campo": error.get("campo"),
                "severidade": error.get("severidade", "erro"),
                "timestamp": error.get("timestamp"),
            }
        )
    return tuple(rows)


def build_available_filters(snapshot: InspectionSnapshotViewModel) -> dict[str, tuple[str, ...]]:
    viaturas = sorted({row.id_viatura for row in snapshot.route_rows if row.id_viatura} | {alert.id_viatura for alert in snapshot.alerts if alert.id_viatura})
    classes = sorted(
        {row.classe_operacional for row in snapshot.route_rows if row.classe_operacional}
        | {row.classe_operacional for row in snapshot.route_stop_rows if row.classe_operacional}
        | {str(row.get("classe_operacional")) for row in snapshot.non_served_rows if row.get("classe_operacional")}
        | {str(row.get("classe_operacional")) for row in snapshot.excluded_rows if row.get("classe_operacional")}
        | {str(row.get("classe_operacional")) for row in snapshot.cancelled_rows if row.get("classe_operacional")}
        | {alert.classe_operacional for alert in snapshot.alerts if alert.classe_operacional}
    )
    criticidades = sorted(
        {row.criticidade for row in snapshot.route_stop_rows if row.criticidade}
        | {str(row.get("criticidade")) for row in snapshot.non_served_rows if row.get("criticidade")}
        | {str(row.get("criticidade")) for row in snapshot.excluded_rows if row.get("criticidade")}
        | {str(row.get("criticidade")) for row in snapshot.cancelled_rows if row.get("criticidade")}
        | {alert.criticidade for alert in snapshot.alerts if alert.criticidade}
    )
    severidades = sorted(
        {str(row.get("severidade")) for row in snapshot.event_rows if row.get("severidade")}
        | {str(row.get("severidade")) for row in snapshot.reason_rows if row.get("severidade")}
        | {str(row.get("severidade")) for row in snapshot.error_rows if row.get("severidade")}
        | {alert.severity for alert in snapshot.alerts if alert.severity}
    )
    statuses = sorted(
        {row.status_atendimento for row in snapshot.route_rows if row.status_atendimento}
        | {row.status_atendimento for row in snapshot.route_stop_rows if row.status_atendimento}
        | {str(row.get("status_atendimento")) for row in snapshot.non_served_rows if row.get("status_atendimento")}
        | {str(row.get("status_atendimento")) for row in snapshot.excluded_rows if row.get("status_atendimento")}
        | {str(row.get("status_atendimento")) for row in snapshot.cancelled_rows if row.get("status_atendimento")}
        | {alert.status_atendimento for alert in snapshot.alerts if alert.status_atendimento}
    )
    return {
        "viaturas": tuple(viaturas),
        "classes_operacionais": tuple(classes),
        "criticidades": tuple(criticidades),
        "severidades": tuple(severidades),
        "statuses_atendimento": tuple(statuses),
    }


def inspection_snapshot_to_dict(snapshot: InspectionSnapshotViewModel) -> dict[str, Any]:
    return _serialize(snapshot)


def inspection_snapshot_from_dict(payload: dict[str, Any]) -> InspectionSnapshotViewModel:
    return InspectionSnapshotViewModel(
        execution_summary=ExecutionSummaryViewModel(**payload["execution_summary"]),
        kpi_cards=KpiCardsViewModel(**payload["kpi_cards"]),
        route_rows=tuple(RouteRowViewModel(**item) for item in payload.get("route_rows", [])),
        route_stop_rows=tuple(RouteStopRowViewModel(**item) for item in payload.get("route_stop_rows", [])),
        map_nodes=tuple(MapNodeViewModel(**item) for item in payload.get("map_nodes", [])),
        map_segments=tuple(MapSegmentViewModel(**item) for item in payload.get("map_segments", [])),
        alerts=tuple(AlertViewModel(**item) for item in payload.get("alerts", [])),
        event_rows=tuple(dict(item) for item in payload.get("event_rows", [])),
        reason_rows=tuple(dict(item) for item in payload.get("reason_rows", [])),
        non_served_rows=tuple(dict(item) for item in payload.get("non_served_rows", [])),
        excluded_rows=tuple(dict(item) for item in payload.get("excluded_rows", [])),
        cancelled_rows=tuple(dict(item) for item in payload.get("cancelled_rows", [])),
        error_rows=tuple(dict(item) for item in payload.get("error_rows", [])),
        relatorio_destaques=tuple(payload.get("relatorio_destaques", [])),
        available_filters={key: tuple(values) for key, values in (payload.get("available_filters") or {}).items()},
        map_available=bool(payload.get("map_available", False)),
        map_warnings=tuple(payload.get("map_warnings", [])),
        source_has_inputs=bool(payload.get("source_has_inputs", False)),
    )


def find_route_row(snapshot: InspectionSnapshotViewModel, route_id: str | None) -> RouteRowViewModel | None:
    if route_id is None:
        return snapshot.route_rows[0] if snapshot.route_rows else None
    for row in snapshot.route_rows:
        if row.id_rota == route_id:
            return row
    return snapshot.route_rows[0] if snapshot.route_rows else None


def route_stop_rows_for_route(
    snapshot: InspectionSnapshotViewModel,
    route_id: str,
) -> tuple[RouteStopRowViewModel, ...]:
    return tuple(row for row in snapshot.route_stop_rows if row.id_rota == route_id)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def parse_time_value(value: str | None) -> time | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if "T" in candidate:
        parsed = parse_datetime(candidate)
        return None if parsed is None else parsed.timetz().replace(tzinfo=None)
    try:
        return time.fromisoformat(candidate)
    except ValueError:
        return None


def decimal_from_any(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _resolve_result(raw_response: dict[str, Any]) -> dict[str, Any]:
    result = raw_response.get("result")
    if isinstance(result, dict):
        return result
    return raw_response


def _iter_routes(result: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for collection_name in ("rotas_suprimento", "rotas_recolhimento"):
        for route in result.get(collection_name, []) or []:
            yield route


def _highest_criticidade(values: Iterable[str]) -> str | None:
    best: str | None = None
    best_rank = -1
    for value in values:
        rank = CRITICITY_ORDER.get(value, -1)
        if rank > best_rank:
            best = value
            best_rank = rank
    return best


def _extract_coordinates(payload: dict[str, Any]) -> tuple[float, float] | None:
    try:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    return latitude, longitude


def _flatten_order_classified(item: dict[str, Any], *, status_atendimento: str) -> dict[str, Any]:
    ordem = dict(item.get("ordem") or {})
    return {
        "id_ordem": ordem.get("id_ordem"),
        "id_ponto": ordem.get("id_ponto"),
        "tipo_servico": ordem.get("tipo_servico"),
        "classe_operacional": ordem.get("classe_operacional"),
        "criticidade": ordem.get("criticidade"),
        "status_cancelamento": ordem.get("status_cancelamento"),
        "motivo_exclusao": item.get("motivo_exclusao") or ordem.get("motivo_exclusao"),
        "impacto_financeiro_previsto": item.get("impacto_financeiro_previsto") or ordem.get("impacto_financeiro_previsto"),
        "impacto_operacional": item.get("impacto_operacional"),
        "elegivel_no_cutoff": item.get("elegivel_no_cutoff"),
        "planeavel": item.get("planeavel"),
        "status_ordem": item.get("status_ordem") or ordem.get("status_ordem"),
        "status_atendimento": status_atendimento,
    }


def _serialize(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {field.name: _serialize(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value

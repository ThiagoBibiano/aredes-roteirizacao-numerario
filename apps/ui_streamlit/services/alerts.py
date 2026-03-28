from __future__ import annotations

from typing import Iterable

from apps.ui_streamlit.services.view_models import (
    AlertViewModel,
    InspectionSnapshotViewModel,
    decimal_from_any,
)


def build_alerts(
    raw_response: dict,
    snapshot: InspectionSnapshotViewModel,
    *,
    wait_threshold_seconds: int = 900,
) -> tuple[AlertViewModel, ...]:
    alerts: list[AlertViewModel] = []
    seen: set[tuple[str, str, str, str | None]] = set()

    def add(alert: AlertViewModel) -> None:
        key = (alert.severity, alert.category, alert.related_entity_type, alert.related_entity_id)
        if key in seen:
            return
        seen.add(key)
        alerts.append(alert)

    status_final = snapshot.execution_summary.status_final
    if status_final in {"inviavel", "falha"}:
        add(
            AlertViewModel(
                severity="critico",
                category="status_execucao",
                title="Execucao com status critico",
                description=f"O backend retornou status_final='{status_final}'.",
                related_entity_type="Execucao",
                related_entity_id=snapshot.execution_summary.id_execucao,
            )
        )

    if snapshot.execution_summary.reused_cached_result:
        add(
            AlertViewModel(
                severity="info",
                category="cache",
                title="Resultado reaproveitado do cache",
                description="O backend reutilizou o resultado do mesmo hash de cenario.",
                related_entity_type="Execucao",
                related_entity_id=snapshot.execution_summary.id_execucao,
            )
        )
    if snapshot.execution_summary.recovered_previous_context:
        add(
            AlertViewModel(
                severity="info",
                category="contexto",
                title="Contexto anterior recuperado",
                description="A execucao reutilizou o contexto persistido do cenario anterior.",
                related_entity_type="Execucao",
                related_entity_id=snapshot.execution_summary.id_execucao,
            )
        )

    if snapshot.non_served_rows:
        add(
            AlertViewModel(
                severity="erro",
                category="ordens_nao_atendidas",
                title="Ha ordens nao atendidas",
                description=f"Total de ordens nao atendidas: {len(snapshot.non_served_rows)}.",
                related_entity_type="Execucao",
                related_entity_id=snapshot.execution_summary.id_execucao,
                status_atendimento="nao_atendida",
            )
        )
    if snapshot.excluded_rows:
        add(
            AlertViewModel(
                severity="aviso",
                category="ordens_excluidas",
                title="Ha ordens excluidas antes do planejamento",
                description=f"Total de ordens excluidas: {len(snapshot.excluded_rows)}.",
                related_entity_type="Execucao",
                related_entity_id=snapshot.execution_summary.id_execucao,
                status_atendimento="excluida",
            )
        )

    for route in snapshot.route_rows:
        if route.atingiu_limite_segurado:
            add(
                AlertViewModel(
                    severity="aviso",
                    category="limite_segurado",
                    title="Rota no limite segurado",
                    description=f"A rota {route.id_rota} atingiu o limite segurado.",
                    related_entity_type="Rota",
                    related_entity_id=route.id_rota,
                    id_rota=route.id_rota,
                    id_viatura=route.id_viatura,
                    classe_operacional=route.classe_operacional,
                    status_atendimento=route.status_atendimento,
                )
            )
        if route.possui_violacao_janela:
            add(
                AlertViewModel(
                    severity="erro",
                    category="violacao_janela",
                    title="Rota com violacao de janela",
                    description=f"A rota {route.id_rota} contem violacao de janela planejada.",
                    related_entity_type="Rota",
                    related_entity_id=route.id_rota,
                    id_rota=route.id_rota,
                    id_viatura=route.id_viatura,
                    classe_operacional=route.classe_operacional,
                    status_atendimento=route.status_atendimento,
                )
            )
        if route.possui_excesso_capacidade:
            add(
                AlertViewModel(
                    severity="critico",
                    category="excesso_capacidade",
                    title="Rota com excesso de capacidade",
                    description=f"A rota {route.id_rota} excedeu a capacidade planejada.",
                    related_entity_type="Rota",
                    related_entity_id=route.id_rota,
                    id_rota=route.id_rota,
                    id_viatura=route.id_viatura,
                    classe_operacional=route.classe_operacional,
                    status_atendimento=route.status_atendimento,
                )
            )

    for stop in snapshot.route_stop_rows:
        if stop.atraso_segundos > 0:
            add(
                AlertViewModel(
                    severity="aviso",
                    category="parada_atrasada",
                    title="Parada com atraso",
                    description=(
                        f"A ordem {stop.id_ordem} na rota {stop.id_rota} possui atraso de {stop.atraso_segundos} segundos."
                    ),
                    related_entity_type="Ordem",
                    related_entity_id=stop.id_ordem,
                    id_rota=stop.id_rota,
                    id_viatura=stop.id_viatura,
                    classe_operacional=stop.classe_operacional,
                    criticidade=stop.criticidade,
                    status_atendimento=stop.status_atendimento,
                )
            )
        if stop.espera_segundos > wait_threshold_seconds:
            add(
                AlertViewModel(
                    severity="aviso",
                    category="espera_elevada",
                    title="Parada com espera elevada",
                    description=(
                        f"A ordem {stop.id_ordem} na rota {stop.id_rota} possui espera de {stop.espera_segundos} segundos."
                    ),
                    related_entity_type="Ordem",
                    related_entity_id=stop.id_ordem,
                    id_rota=stop.id_rota,
                    id_viatura=stop.id_viatura,
                    classe_operacional=stop.classe_operacional,
                    criticidade=stop.criticidade,
                    status_atendimento=stop.status_atendimento,
                )
            )

    for row in snapshot.non_served_rows:
        severity = "erro" if row.get("criticidade") in {"alta", "critica"} else "aviso"
        add(
            AlertViewModel(
                severity=severity,
                category="ordem_nao_atendida",
                title="Ordem nao atendida",
                description=f"A ordem {row.get('id_ordem')} nao foi atendida: {row.get('motivo')}.",
                related_entity_type="Ordem",
                related_entity_id=str(row.get("id_ordem") or ""),
                classe_operacional=str(row.get("classe_operacional") or "") or None,
                criticidade=str(row.get("criticidade") or "") or None,
                status_atendimento="nao_atendida",
            )
        )

    for row in snapshot.cancelled_rows:
        if decimal_from_any(row.get("impacto_financeiro_previsto")) > 0:
            add(
                AlertViewModel(
                    severity="aviso",
                    category="cancelamento_com_impacto",
                    title="Cancelamento com impacto",
                    description=(
                        f"A ordem {row.get('id_ordem')} foi cancelada com impacto financeiro previsto de "
                        f"{row.get('impacto_financeiro_previsto')}."
                    ),
                    related_entity_type="Ordem",
                    related_entity_id=str(row.get("id_ordem") or ""),
                    classe_operacional=str(row.get("classe_operacional") or "") or None,
                    criticidade=str(row.get("criticidade") or "") or None,
                    status_atendimento="cancelada",
                )
            )

    for reason in snapshot.reason_rows:
        severity = str(reason.get("severidade") or "")
        if severity not in {"erro", "critico"}:
            continue
        add(
            AlertViewModel(
                severity=severity,
                category="motivo_inviabilidade",
                title="Motivo de inviabilidade relevante",
                description=str(reason.get("descricao") or reason.get("codigo") or "Motivo de inviabilidade"),
                related_entity_type=str(reason.get("entidade") or "Execucao"),
                related_entity_id=str(reason.get("id_entidade") or snapshot.execution_summary.id_execucao),
            )
        )

    for highlight in snapshot.relatorio_destaques:
        add(
            AlertViewModel(
                severity="info",
                category="destaque_gerencial",
                title="Destaque do relatorio de planejamento",
                description=str(highlight),
                related_entity_type="Execucao",
                related_entity_id=snapshot.execution_summary.id_execucao,
            )
        )

    return tuple(alerts)

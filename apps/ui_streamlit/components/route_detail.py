from __future__ import annotations

import streamlit as st

from apps.ui_streamlit.services.timeline import TimelineRouteStateViewModel
from apps.ui_streamlit.services.view_models import RouteRowViewModel, RouteStopRowViewModel


def render_route_detail(
    route_row: RouteRowViewModel | None,
    stop_rows: tuple[RouteStopRowViewModel, ...],
    *,
    route_state: TimelineRouteStateViewModel | None = None,
    current_at_label: str | None = None,
    stop_statuses: dict[int, str] | None = None,
) -> None:
    st.subheader("Detalhe da rota")
    if route_row is None:
        st.info("Selecione uma rota para ver a sequencia de paradas.")
        return

    columns = st.columns(4)
    columns[0].metric("Rota", route_row.id_rota)
    columns[1].metric("Viatura", route_row.id_viatura)
    columns[2].metric("Classe", route_row.classe_operacional)
    columns[3].metric("Paradas", str(route_row.quantidade_paradas))
    st.caption(
        f"Inicio: {route_row.inicio_previsto} | Fim: {route_row.fim_previsto} | "
        f"Custo: {route_row.custo_estimado} | Distancia: {route_row.distancia_estimada}"
    )

    if route_state is not None:
        summary_columns = st.columns(3)
        summary_columns[0].metric("Fase atual", route_state.phase.replace("_", " ").title())
        summary_columns[1].metric("Proximo ponto", route_state.next_label or "-")
        summary_columns[2].metric("Horario atual", current_at_label or route_state.current_at)

    if not stop_rows:
        st.info("Nao ha paradas disponiveis para a rota selecionada nos filtros atuais.")
        return

    temporal_statuses = stop_statuses or {}
    st.dataframe(
        [
            {
                "sequencia": row.sequencia,
                "status_temporal": temporal_statuses.get(row.sequencia, "futura"),
                "id_ordem": row.id_ordem,
                "id_ponto": row.id_ponto,
                "tipo_servico": row.tipo_servico,
                "criticidade": row.criticidade,
                "inicio_previsto": row.inicio_previsto,
                "fim_previsto": row.fim_previsto,
                "folga_janela_segundos": row.folga_janela_segundos,
                "espera_segundos": row.espera_segundos,
                "atraso_segundos": row.atraso_segundos,
                "demanda": row.demanda,
                "carga_acumulada": row.carga_acumulada,
            }
            for row in stop_rows
        ],
        width="stretch",
        hide_index=True,
    )

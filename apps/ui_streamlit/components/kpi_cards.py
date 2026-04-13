from __future__ import annotations

from decimal import Decimal, InvalidOperation

import plotly.graph_objects as go
import streamlit as st

from apps.ui_streamlit.services.view_models import KpiCardsViewModel, RouteRowViewModel


def render_kpi_cards(kpi: KpiCardsViewModel) -> None:
    first_row = st.columns(5)
    first_row[0].metric("Custo total", kpi.custo_total_estimado)
    first_row[1].metric("Distancia estimada", str(kpi.distancia_total_estimada))
    first_row[2].metric("Duracao estimada (s)", str(kpi.duracao_total_estimada_segundos))
    first_row[3].metric("Taxa atendimento", _format_ratio(kpi.taxa_atendimento))
    first_row[4].metric("Utilizacao frota", _format_ratio(kpi.utilizacao_frota))

    second_row = st.columns(5)
    second_row[0].metric("Viaturas acionadas", str(kpi.viaturas_acionadas))
    second_row[1].metric("Ordens atendidas", str(kpi.total_ordens_atendidas))
    second_row[2].metric("Ordens especiais", str(kpi.total_ordens_especiais_atendidas))
    second_row[3].metric("Ordens nao atendidas", str(kpi.total_ordens_nao_atendidas))
    second_row[4].metric("Impacto cancelamentos", kpi.impacto_financeiro_cancelamentos)

def render_route_charts(route_rows: tuple[RouteRowViewModel, ...]) -> None:
    if not route_rows:
        st.info("Nenhuma rota disponivel para os graficos atuais.")
        return

    route_labels = [row.id_rota for row in route_rows]
    costs = [_to_float(row.custo_estimado) for row in route_rows]
    distances = [row.distancia_estimada for row in route_rows]
    chart_columns = st.columns(2)

    with chart_columns[0]:
        cost_chart = go.Figure(
            data=[
                go.Bar(
                    x=route_labels,
                    y=costs,
                    marker_color=[_class_color(row.classe_operacional) for row in route_rows],
                    name="Custo",
                )
            ]
        )
        cost_chart.update_layout(
            title="Custo estimado por rota",
            xaxis_title="Rota",
            yaxis_title="Custo estimado",
            margin=dict(l=20, r=20, t=50, b=20),
            height=320,
        )
        st.plotly_chart(cost_chart, width="stretch")

    with chart_columns[1]:
        distance_chart = go.Figure(
            data=[
                go.Bar(
                    x=route_labels,
                    y=distances,
                    marker_color=[_class_color(row.classe_operacional) for row in route_rows],
                    name="Distancia",
                )
            ]
        )
        distance_chart.update_layout(
            title="Distancia estimada por rota",
            xaxis_title="Rota",
            yaxis_title="Metros",
            margin=dict(l=20, r=20, t=50, b=20),
            height=320,
        )
        st.plotly_chart(distance_chart, width="stretch")

def _format_ratio(value: str) -> str:
    try:
        decimal_value = Decimal(str(value)) * Decimal("100")
        return f"{decimal_value.quantize(Decimal('0.01'))}%"
    except (InvalidOperation, ValueError):
        return str(value)

def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def _class_color(value: str) -> str:
    if value == "recolhimento":
        return "#e76f51"
    return "#1d3557"

from __future__ import annotations

from collections import Counter

import plotly.graph_objects as go
import streamlit as st

from apps.ui_streamlit.services.filters import FilteredInspectionSnapshot
from apps.ui_streamlit.services.view_models import AlertViewModel


def render_alert_panel(alerts: tuple[AlertViewModel, ...]) -> None:
    st.subheader("Alertas derivados")
    if not alerts:
        st.success("Nenhum alerta derivado para os filtros atuais.")
        return
    counts = Counter(alert.severity for alert in alerts)
    chart = go.Figure(
        data=[go.Bar(x=list(counts.keys()), y=list(counts.values()), marker_color=[_severity_color(key) for key in counts])]
    )
    chart.update_layout(
        title="Alertas por severidade",
        xaxis_title="Severidade",
        yaxis_title="Quantidade",
        height=280,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(chart, width="stretch")
    st.dataframe(
        [
            {
                "severity": alert.severity,
                "category": alert.category,
                "title": alert.title,
                "description": alert.description,
                "related_entity_type": alert.related_entity_type,
                "related_entity_id": alert.related_entity_id,
            }
            for alert in alerts
        ],
        width="stretch",
        hide_index=True,
    )


def render_audit_panel(filtered_snapshot: FilteredInspectionSnapshot) -> None:
    st.subheader("Auditoria e inviabilidades")
    tabs = st.tabs(["Eventos de auditoria", "Motivos de inviabilidade"])
    with tabs[0]:
        if filtered_snapshot.event_rows:
            st.dataframe(filtered_snapshot.event_rows, width="stretch", hide_index=True)
        else:
            st.info("Nao ha eventos de auditoria para os filtros atuais.")
    with tabs[1]:
        if filtered_snapshot.reason_rows:
            st.dataframe(filtered_snapshot.reason_rows, width="stretch", hide_index=True)
        else:
            st.info("Nao ha motivos de inviabilidade para os filtros atuais.")

def _severity_color(severity: str) -> str:
    palette = {
        "info": "#457b9d",
        "aviso": "#e9c46a",
        "erro": "#e76f51",
        "critico": "#d62828",
    }
    return palette.get(severity, "#457b9d")

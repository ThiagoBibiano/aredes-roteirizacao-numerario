from __future__ import annotations

import streamlit as st

from apps.ui_streamlit.services.filters import FilteredInspectionSnapshot


def render_exception_panel(filtered_snapshot: FilteredInspectionSnapshot) -> None:
    st.subheader("Excecoes operacionais")
    tabs = st.tabs([
        "Ordens nao atendidas",
        "Ordens excluidas",
        "Ordens canceladas",
        "Erros",
    ])
    datasets = (
        filtered_snapshot.non_served_rows,
        filtered_snapshot.excluded_rows,
        filtered_snapshot.cancelled_rows,
        filtered_snapshot.error_rows,
    )
    empty_messages = (
        "Nao ha ordens nao atendidas para os filtros atuais.",
        "Nao ha ordens excluidas para os filtros atuais.",
        "Nao ha ordens canceladas para os filtros atuais.",
        "Nao ha erros para os filtros atuais.",
    )
    for index, tab in enumerate(tabs):
        with tab:
            if datasets[index]:
                st.dataframe(datasets[index], width="stretch", hide_index=True)
            else:
                st.info(empty_messages[index])

from __future__ import annotations

import streamlit as st

from apps.ui_streamlit.services.view_models import ExecutionSummaryViewModel


def render_execution_summary(
    summary: ExecutionSummaryViewModel,
    *,
    raw_response: dict | None = None,
) -> None:
    st.subheader("Resumo da execucao")
    columns = st.columns(4)
    columns[0].metric("id_execucao", summary.id_execucao or "-")
    columns[1].metric("status_final", summary.status_final or "-")
    columns[2].metric("attempt_number", str(summary.attempt_number))
    columns[3].metric("snapshot", "sim" if summary.snapshot_materialized else "nao")
    st.code(f"hash_cenario: {summary.hash_cenario or '-'}")

    badges: list[str] = []
    if summary.reused_cached_result:
        badges.append("cache reutilizado")
    if summary.recovered_previous_context:
        badges.append("contexto recuperado")
    if summary.snapshot_materialized:
        badges.append("snapshot materializado")
    st.caption(" | ".join(badges) if badges else "Sem indicadores adicionais nesta execucao.")

    if not raw_response:
        return
    with st.expander("Metadados tecnicos da resposta", expanded=False):
        st.write(
            {
                "output_path": raw_response.get("output_path"),
                "result_path": raw_response.get("result_path"),
                "state_path": raw_response.get("state_path"),
                "scenario_path": raw_response.get("scenario_path"),
                "manifest_path": raw_response.get("manifest_path"),
                "snapshot_materialization": raw_response.get("snapshot_materialization"),
            }
        )

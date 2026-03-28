from __future__ import annotations

import sys
from pathlib import Path

_CURRENT_PATH = Path(__file__).resolve()
_REPO_ROOT = next(parent for parent in _CURRENT_PATH.parents if (parent / "pyproject.toml").exists())
for _candidate in (_REPO_ROOT, _REPO_ROOT / "src"):
    _candidate_str = str(_candidate)
    if _candidate_str not in sys.path:
        sys.path.insert(0, _candidate_str)

import streamlit as st

from apps.ui_streamlit.components.audit_panel import render_alert_panel, render_audit_panel
from apps.ui_streamlit.components.exception_panel import render_exception_panel
from apps.ui_streamlit.components.execution_summary import render_execution_summary
from apps.ui_streamlit.components.sidebar import render_global_sidebar
from apps.ui_streamlit.services.filters import apply_filters
from apps.ui_streamlit.state.session_state import ensure_session_state, get_filter_criteria, get_last_message, get_raw_response, refresh_snapshot_if_needed


def main() -> None:
    st.set_page_config(page_title="Auditoria", layout="wide")
    ensure_session_state()
    render_global_sidebar()
    snapshot = refresh_snapshot_if_needed()
    st.title("Auditoria e excecoes")
    st.caption("Entenda o que ficou de fora do planejamento, onde houve gargalo e quais alertas merecem revisao.")
    message = get_last_message()
    if message:
        st.info(message)
    if snapshot is None:
        st.info("Nenhuma analise carregada. Rode um teste rapido, envie seus arquivos ou abra um JSON salvo.")
        return
    filtered = apply_filters(snapshot, get_filter_criteria())
    render_execution_summary(snapshot.execution_summary, raw_response=get_raw_response())
    summary = st.columns(4)
    summary[0].metric("Eventos", str(len(filtered.event_rows)))
    summary[1].metric("Motivos inviabilidade", str(len(filtered.reason_rows)))
    summary[2].metric("Ordens nao atendidas", str(len(filtered.non_served_rows)))
    summary[3].metric("Alertas", str(len(filtered.alerts)))
    render_alert_panel(filtered.alerts)
    render_audit_panel(filtered)
    render_exception_panel(filtered)


if __name__ == "__main__":
    main()

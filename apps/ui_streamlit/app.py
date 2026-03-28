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

from apps.ui_streamlit.components.execution_summary import render_execution_summary
from apps.ui_streamlit.components.kpi_cards import render_kpi_cards
from apps.ui_streamlit.components.sidebar import render_global_sidebar
from apps.ui_streamlit.state.session_state import ensure_session_state, get_last_message, refresh_snapshot_if_needed


def main() -> None:
    st.set_page_config(page_title="UI Planejamento", layout="wide")
    ensure_session_state()
    render_global_sidebar()
    snapshot = refresh_snapshot_if_needed()

    st.title("Central de planejamento")
    st.write(
        "A interface foi organizada para tres caminhos simples: testar rapidamente, rodar com seus arquivos ou continuar uma analise que ja esta aberta nesta sessao."
    )
    message = get_last_message()
    if message:
        st.info(message)

    actions = st.columns(3)
    with actions[0]:
        with st.container(border=True):
            st.markdown("### Teste rapido")
            st.write("Use o cenario fake configurado na aplicacao para validar backend, mapa e filtros sem preparar nada.")
            _nav_button("Abrir execucao", "pages/01_execucao.py", key="home_open_execution")
    with actions[1]:
        with st.container(border=True):
            st.markdown("### Dados reais")
            st.write("Envie os JSONs operacionais do dia. Esse e o fluxo pensado para os arquivos reais.")
            _nav_button("Enviar arquivos", "pages/01_execucao.py", key="home_send_files")
    with actions[2]:
        with st.container(border=True):
            st.markdown("### Analise salva")
            st.write("Se voce ja exportou um JSON, pode reabrir a analise pela barra lateral e seguir de onde parou.")
            if snapshot is not None:
                _nav_button("Continuar resultados", "pages/02_resultado.py", key="home_continue_results")
            else:
                st.caption("Abra um JSON salvo pela barra lateral para habilitar este atalho.")

    if snapshot is None:
        st.info("Nenhuma analise carregada nesta sessao. Comece pela pagina de execucao.")
        return

    st.markdown("### Resumo da analise atual")
    render_execution_summary(snapshot.execution_summary)
    render_kpi_cards(snapshot.kpi_cards)
    shortcuts = st.columns(2)
    with shortcuts[0]:
        _nav_button("Abrir resultados", "pages/02_resultado.py", key="home_shortcut_results")
    with shortcuts[1]:
        _nav_button("Abrir auditoria", "pages/03_auditoria.py", key="home_shortcut_audit")


def _nav_button(label: str, page: str, *, key: str) -> None:
    if st.button(label, key=key, width="stretch"):
        st.switch_page(page)


if __name__ == "__main__":
    main()

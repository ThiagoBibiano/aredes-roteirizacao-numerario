from __future__ import annotations

import hashlib

import streamlit as st

from apps.ui_streamlit import UI_VERSION
from apps.ui_streamlit.services.export import build_enriched_export, build_raw_export, load_exported_payload
from apps.ui_streamlit.state.session_state import (
    FILTER_CLASSES_KEY,
    FILTER_CRITICIDADES_KEY,
    FILTER_SEVERIDADES_KEY,
    FILTER_STATUS_KEY,
    FILTER_TIME_END_KEY,
    FILTER_TIME_START_KEY,
    FILTER_VIATURAS_KEY,
    OFFLINE_SIGNATURE_KEY,
    WAIT_THRESHOLD_KEY,
    clear_loaded_result,
    ensure_session_state,
    get_api_base_url,
    get_input_payload,
    get_raw_response,
    get_snapshot,
    get_source_kind,
    refresh_snapshot_if_needed,
    set_last_message,
    store_offline_payload,
)


def render_global_sidebar() -> None:
    ensure_session_state()
    st.sidebar.title("Planejamento")
    st.sidebar.caption(f"UI Streamlit {UI_VERSION}")
    _render_nav_button(st.sidebar, "Inicio", "app.py", key="sidebar_nav_home")
    _render_nav_button(st.sidebar, "Executar planejamento", "pages/01_execucao.py", key="sidebar_nav_execucao")

    snapshot = refresh_snapshot_if_needed() or get_snapshot()
    if snapshot is not None:
        _render_nav_button(st.sidebar, "Resultados", "pages/02_resultado.py", key="sidebar_nav_resultados")
        _render_nav_button(st.sidebar, "Auditoria", "pages/03_auditoria.py", key="sidebar_nav_auditoria")
    else:
        st.sidebar.caption("Resultados e auditoria aparecem aqui depois da primeira execucao ou importacao.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Abrir analise salva")
    st.sidebar.caption("Use um JSON exportado anteriormente para continuar a inspecao sem rodar o modelo novamente.")
    uploaded = st.sidebar.file_uploader(
        "Selecionar JSON",
        type=["json"],
        accept_multiple_files=False,
        key="sidebar_offline_upload",
    )
    if uploaded is not None:
        signature = hashlib.sha1(uploaded.getvalue()).hexdigest()
        if signature != st.session_state.get(OFFLINE_SIGNATURE_KEY):
            try:
                loaded = load_exported_payload(uploaded.getvalue())
                store_offline_payload(loaded)
                st.session_state[OFFLINE_SIGNATURE_KEY] = signature
                if loaded.warnings:
                    st.sidebar.warning(" ".join(loaded.warnings))
                set_last_message("Analise salva carregada com sucesso.")
            except ValueError as exc:
                st.sidebar.error(str(exc))

    with st.sidebar.expander("Como usar esta sessao", expanded=snapshot is None):
        st.write("1. Abra a pagina de execucao.")
        st.write("2. Rode o teste rapido ou envie seus arquivos JSON.")
        st.write("3. Continue a analise em Resultados e Auditoria.")

    with st.sidebar.expander("Regra de alerta para espera", expanded=False):
        st.number_input(
            "Considerar espera longa acima de (segundos)",
            min_value=0,
            step=60,
            key=WAIT_THRESHOLD_KEY,
            help=(
                "Quando uma parada ultrapassa este tempo de espera, a UI passa a destacar a situacao nos alertas e na auditoria."
            ),
        )

    if snapshot is None:
        st.sidebar.info("Nenhuma analise carregada nesta sessao.")
        return

    st.sidebar.markdown("---")
    st.sidebar.subheader("Analise atual")
    st.sidebar.caption(f"Origem: {_source_kind_label(get_source_kind())}")

    with st.sidebar.expander("Filtros desta analise", expanded=True):
        _render_filters(st, snapshot.available_filters)

    raw_response = get_raw_response()
    if raw_response is None:
        return

    st.sidebar.markdown("---")
    st.sidebar.subheader("Salvar ou reiniciar")
    input_payload = get_input_payload()
    file_stem = snapshot.execution_summary.id_execucao or "planejamento"
    st.sidebar.download_button(
        "Baixar resposta bruta",
        data=build_raw_export(raw_response),
        file_name=f"{file_stem}-raw.json",
        mime="application/json",
        width="stretch",
    )
    st.sidebar.download_button(
        "Baixar analise enriquecida",
        data=build_enriched_export(
            raw_response,
            input_payload=input_payload,
            inspection_snapshot=snapshot,
            source_kind=get_source_kind(),
            api_base_url=get_api_base_url(),
        ),
        file_name=f"{file_stem}-enriched.json",
        mime="application/json",
        width="stretch",
    )
    if st.sidebar.button("Limpar analise atual", width="stretch"):
        clear_loaded_result()
        st.rerun()


def _render_nav_button(container, label: str, page: str, *, key: str) -> None:
    if container.button(label, key=key, width="stretch"):
        st.switch_page(page)


def _render_filters(container, available_filters: dict[str, tuple[str, ...]]) -> None:
    _sanitize_state_values(FILTER_VIATURAS_KEY, available_filters.get("viaturas", ()))
    _sanitize_state_values(FILTER_CLASSES_KEY, available_filters.get("classes_operacionais", ()))
    _sanitize_state_values(FILTER_CRITICIDADES_KEY, available_filters.get("criticidades", ()))
    _sanitize_state_values(FILTER_SEVERIDADES_KEY, available_filters.get("severidades", ()))
    _sanitize_state_values(FILTER_STATUS_KEY, available_filters.get("statuses_atendimento", ()))
    container.multiselect("Viaturas", available_filters.get("viaturas", ()), key=FILTER_VIATURAS_KEY)
    container.multiselect(
        "Classe operacional",
        available_filters.get("classes_operacionais", ()),
        key=FILTER_CLASSES_KEY,
    )
    container.multiselect("Criticidade", available_filters.get("criticidades", ()), key=FILTER_CRITICIDADES_KEY)
    container.multiselect("Severidade", available_filters.get("severidades", ()), key=FILTER_SEVERIDADES_KEY)
    container.multiselect("Status de atendimento", available_filters.get("statuses_atendimento", ()), key=FILTER_STATUS_KEY)
    container.text_input(
        "Mostrar somente a partir de",
        key=FILTER_TIME_START_KEY,
        help="Aceita HH:MM ou timestamp ISO. Deixe em branco para nao limitar o inicio.",
    )
    container.text_input(
        "Mostrar somente ate",
        key=FILTER_TIME_END_KEY,
        help="Aceita HH:MM ou timestamp ISO. Deixe em branco para nao limitar o fim.",
    )


def _sanitize_state_values(key: str, allowed_values: tuple[str, ...]) -> None:
    current_values = st.session_state.get(key, []) or []
    st.session_state[key] = [value for value in current_values if value in allowed_values]


def _source_kind_label(source_kind: str) -> str:
    labels = {
        "dataset": "cenario de teste",
        "inline": "dados enviados pela interface",
        "offline_raw": "resposta bruta importada",
        "offline_enriched": "analise enriquecida importada",
    }
    return labels.get(source_kind, source_kind)

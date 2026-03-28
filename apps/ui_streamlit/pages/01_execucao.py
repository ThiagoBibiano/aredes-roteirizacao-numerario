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

from apps.ui_streamlit.client.api_client import PlanningApiClient, UiApiError
from apps.ui_streamlit.components.execution_summary import render_execution_summary
from apps.ui_streamlit.components.sidebar import render_global_sidebar
from apps.ui_streamlit.components.upload_panel import render_inline_upload_panel
from apps.ui_streamlit.services.ui_settings import load_inline_documents_from_settings, load_ui_settings
from apps.ui_streamlit.services.validation import (
    build_dataset_payload,
    build_inline_payload_from_documents,
    load_dataset_payload_from_directory,
)
from apps.ui_streamlit.state.session_state import (
    ensure_session_state,
    get_api_base_url,
    get_health_status,
    get_last_message,
    get_raw_response,
    get_snapshot,
    is_execution_locked,
    set_execution_lock,
    set_health_status,
    set_last_message,
    store_execution_result,
)


PARAM_MATERIALIZE_KEY = "ui_execution_materialize_snapshot"
PARAM_MAX_ITERATIONS_KEY = "ui_execution_max_iterations"
PARAM_SEED_KEY = "ui_execution_seed"
PARAM_COLLECT_STATS_KEY = "ui_execution_collect_stats"
PARAM_DISPLAY_KEY = "ui_execution_display"
HEALTH_AUTO_CHECKED_KEY = "ui_health_auto_checked"


def main() -> None:
    st.set_page_config(page_title="Execucao", layout="wide")
    ensure_session_state()
    ui_settings = load_ui_settings()
    inline_defaults = load_inline_documents_from_settings(ui_settings)
    _ensure_execution_defaults(ui_settings)
    render_global_sidebar()

    st.title("Rodar planejamento")
    st.write(
        "Escolha uma forma de comecar. O resultado permanece nesta sessao e voce pode seguir direto para Resultados e Auditoria."
    )
    message = get_last_message()
    if message:
        st.info(message)

    _maybe_auto_check_health(ui_settings)
    _render_connection_panel(ui_settings)
    _render_next_steps(get_snapshot())

    with st.expander("Ajustes avancados desta execucao", expanded=False):
        st.caption(
            "Use estes parametros quando precisar controlar o comportamento da execucao. Se nao tiver certeza, pode deixar como esta."
        )
        _render_execution_parameters()

    test_tab, real_tab = st.tabs(["Teste rapido", "Dados reais"])
    with test_tab:
        _render_fake_experience(ui_settings)
    with real_tab:
        _render_real_data_experience(inline_defaults)

    snapshot = get_snapshot()
    raw_response = get_raw_response()
    if snapshot is not None:
        st.markdown("### Ultima analise desta sessao")
        render_execution_summary(snapshot.execution_summary, raw_response=raw_response)
        _render_result_shortcuts()
    if raw_response is not None:
        with st.expander("Resposta tecnica da API", expanded=False):
            st.json(raw_response)

    _render_technical_details(ui_settings, inline_defaults)


def _ensure_execution_defaults(ui_settings) -> None:
    defaults = {
        PARAM_MATERIALIZE_KEY: ui_settings.parameters.materialize_snapshot,
        PARAM_MAX_ITERATIONS_KEY: ui_settings.parameters.max_iterations,
        PARAM_SEED_KEY: ui_settings.parameters.seed,
        PARAM_COLLECT_STATS_KEY: ui_settings.parameters.collect_stats,
        PARAM_DISPLAY_KEY: ui_settings.parameters.display,
        HEALTH_AUTO_CHECKED_KEY: False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _maybe_auto_check_health(ui_settings) -> None:
    if not ui_settings.auto_check_health:
        return
    if st.session_state.get(HEALTH_AUTO_CHECKED_KEY):
        return
    _refresh_health_check()
    st.session_state[HEALTH_AUTO_CHECKED_KEY] = True


def _render_connection_panel(ui_settings) -> None:
    health_payload, health_error = get_health_status()
    container = st.container(border=True)
    container.subheader("Conexao com o backend")
    container.caption(
        "A conexao da API ja vem do settings da aplicacao. Voce nao precisa preencher endpoint nesta tela."
    )
    info_column, action_column = container.columns([3, 1])
    with info_column:
        if health_payload is not None:
            application = health_payload.get("application") or "API"
            status = health_payload.get("status") or "ok"
            st.success(f"Backend pronto: {application} ({status}).")
        elif health_error:
            st.error("Nao foi possivel falar com o backend. Suba a API antes de executar o planejamento.")
            st.caption(health_error)
        else:
            st.info("Use o botao ao lado para validar a conexao antes de rodar ou, se preferir, execute um teste rapido e a interface mostrara qualquer falha.")
    with action_column:
        if st.button("Testar conexao", width="stretch"):
            _refresh_health_check()
            st.rerun()


def _render_next_steps(snapshot) -> None:
    st.markdown("### Como deseja comecar?")
    columns = st.columns(3)
    with columns[0]:
        with st.container(border=True):
            st.markdown("#### 1. Teste rapido")
            st.write("Roda um cenario de exemplo ja preparado, sem precisar subir arquivos nem mexer em diretorios.")
    with columns[1]:
        with st.container(border=True):
            st.markdown("#### 2. Dados reais")
            st.write("Envie os JSONs operacionais do dia. Esse e o fluxo pensado para os arquivos reais.")
    with columns[2]:
        with st.container(border=True):
            st.markdown("#### 3. Continuar a analise")
            if snapshot is None:
                st.write("Depois da primeira execucao, a analise atual fica disponivel em Resultados e Auditoria.")
            else:
                st.write("Ja existe uma analise carregada nesta sessao. Voce pode abrir resultados ou auditoria a qualquer momento.")
                _render_result_shortcuts()


def _render_fake_experience(ui_settings) -> None:
    st.subheader("Teste rapido com cenario de exemplo")
    st.write(
        "Use esta opcao para validar instalacao, conhecer a interface ou demonstrar a ferramenta. A aplicacao usa o cenario fake configurado internamente."
    )
    highlights = st.columns(3)
    highlights[0].metric("Preparacao", "1 clique")
    highlights[1].metric("Arquivos manuais", "Nao precisa")
    highlights[2].metric("Ideal para", "Demonstracao")
    if st.button("Rodar teste rapido", type="primary", width="stretch", disabled=is_execution_locked(), key="run_fake_test"):
        parameters = _get_execution_parameters()
        _handle_fake_submission(ui_settings, parameters)


def _render_real_data_experience(inline_defaults) -> None:
    st.subheader("Planejar com seus arquivos")
    st.write(
        "Envie os arquivos JSON do dia operacional. Se este ambiente ja tiver arquivos configurados no settings, eles entram automaticamente como preenchimento inicial."
    )
    with st.expander("Quais arquivos preciso enviar?", expanded=True):
        st.write("contexto.json: identifica a execucao e a data de operacao.")
        st.write("bases.json: bases operacionais com localizacao e disponibilidade.")
        st.write("pontos.json: pontos de atendimento com localizacao e janelas.")
        st.write("viaturas.json: frota disponivel, capacidades e base de origem.")
        st.write("ordens.json: ordens do dia, criticidades, volumes e janelas.")
        st.write("snapshot_source.json: opcional. Quando enviado, a UI ativa materialize_snapshot automaticamente.")

    _render_inline_defaults_panel(inline_defaults)
    uploads = render_inline_upload_panel()
    actions = st.columns(2)
    validate_clicked = actions[0].button("Verificar arquivos", width="stretch", key="validate_real_files")
    execute_clicked = actions[1].button(
        "Planejar com estes arquivos",
        type="primary",
        width="stretch",
        disabled=is_execution_locked(),
        key="execute_real_files",
    )
    if validate_clicked or execute_clicked:
        documents = dict(inline_defaults.documents)
        documents.update(uploads)
        parameters = _get_execution_parameters()
        _handle_inline_submission(documents, parameters, execute_clicked, settings_warnings=inline_defaults.warnings)


def _render_inline_defaults_panel(inline_defaults) -> None:
    configured_count = len(inline_defaults.configured_paths)
    loaded_count = len(inline_defaults.documents)
    if configured_count:
        st.info(
            f"Este ambiente ja possui {loaded_count} arquivo(s) pronto(s) para uso automatico. Qualquer upload manual substitui apenas o arquivo correspondente."
        )
    else:
        st.caption("Nenhum arquivo foi preconfigurado neste ambiente. Nesse caso, envie todos os JSONs obrigatorios.")

    for warning in inline_defaults.warnings:
        st.warning(warning)


def _render_execution_parameters() -> None:
    st.checkbox(
        "Gerar materializacao do snapshot logistico",
        key=PARAM_MATERIALIZE_KEY,
        help="Ative apenas quando precisar que o backend materialize o snapshot durante a execucao.",
    )
    st.number_input(
        "Numero maximo de iteracoes",
        min_value=1,
        step=1,
        key=PARAM_MAX_ITERATIONS_KEY,
        help="Quanto maior este valor, mais tempo o solver pode gastar tentando melhorar a solucao.",
    )
    st.number_input(
        "Seed aleatoria",
        min_value=1,
        step=1,
        key=PARAM_SEED_KEY,
        help="Permite repetir a execucao com a mesma semente quando quiser comparar resultados.",
    )
    st.checkbox(
        "Coletar estatisticas detalhadas",
        key=PARAM_COLLECT_STATS_KEY,
        help="Ative quando quiser mais detalhes tecnicos sobre a execucao do solver.",
    )
    st.checkbox(
        "Habilitar exibicao detalhada do backend",
        key=PARAM_DISPLAY_KEY,
        help="Mantido para compatibilidade com a API. Em geral nao e necessario alterar.",
    )


def _get_execution_parameters() -> dict[str, object]:
    return {
        "materialize_snapshot": bool(st.session_state.get(PARAM_MATERIALIZE_KEY, False)),
        "max_iterations": int(st.session_state.get(PARAM_MAX_ITERATIONS_KEY, 100) or 100),
        "seed": int(st.session_state.get(PARAM_SEED_KEY, 1) or 1),
        "collect_stats": bool(st.session_state.get(PARAM_COLLECT_STATS_KEY, False)),
        "display": bool(st.session_state.get(PARAM_DISPLAY_KEY, False)),
    }


def _handle_fake_submission(ui_settings, parameters: dict[str, object]) -> None:
    dataset = ui_settings.dataset
    path_parameters = {
        "output_path": dataset.output_path,
        "snapshot_dir": dataset.snapshot_dir,
        "source_dir": dataset.source_dir,
        "state_dir": dataset.state_dir,
    }
    try:
        payload = build_dataset_payload(dataset.dataset_dir, parameters, path_parameters)
    except ValueError as exc:
        st.error(str(exc))
        return
    local_payload = load_dataset_payload_from_directory(dataset.dataset_dir)
    for warning in local_payload.warnings:
        st.warning(warning)
    _execute_request(
        request_kind="dataset",
        payload=payload,
        input_payload=local_payload.input_payload,
        success_message="Teste rapido executado com sucesso.",
    )


def _handle_inline_submission(
    documents: dict[str, bytes],
    parameters: dict[str, object],
    should_execute: bool,
    *,
    settings_warnings: tuple[str, ...] = (),
) -> None:
    for warning in settings_warnings:
        st.warning(warning)
    build_result = build_inline_payload_from_documents(documents, parameters)
    if build_result.errors:
        for error in build_result.errors:
            st.error(error)
        return
    for warning in build_result.warnings:
        st.warning(warning)
    st.success("Arquivos validados com sucesso.")
    if not should_execute or build_result.payload is None:
        return
    _execute_request(
        request_kind="inline",
        payload=build_result.payload,
        input_payload={
            "contexto": build_result.payload["contexto"],
            "bases": build_result.payload["bases"],
            "pontos": build_result.payload["pontos"],
            "viaturas": build_result.payload["viaturas"],
            "ordens": build_result.payload["ordens"],
            **({"snapshot_source": build_result.payload["snapshot_source"]} if build_result.payload.get("snapshot_source") is not None else {}),
        },
        success_message="Planejamento executado com sucesso.",
    )


def _execute_request(
    *,
    request_kind: str,
    payload: dict,
    input_payload: dict | None,
    success_message: str,
) -> None:
    api_base_url = get_api_base_url()
    set_execution_lock(True)
    try:
        with PlanningApiClient(api_base_url) as client:
            with st.spinner("Executando planejamento no backend..."):
                if request_kind == "inline":
                    raw_response = client.run_inline(payload)
                else:
                    raw_response = client.run_dataset(payload)
        store_execution_result(
            raw_response,
            input_payload=input_payload,
            source_kind=request_kind,
        )
        set_last_message(success_message)
        st.switch_page("pages/02_resultado.py")
    except UiApiError as exc:
        set_last_message(exc.detail or str(exc))
        st.error(exc.detail or str(exc))
    finally:
        set_execution_lock(False)


def _refresh_health_check() -> None:
    api_base_url = get_api_base_url()
    try:
        with PlanningApiClient(api_base_url) as client:
            payload = client.health()
        set_health_status(payload, None)
        set_last_message("Conectividade com o backend validada com sucesso.")
    except UiApiError as exc:
        set_health_status(None, exc.detail or str(exc))
        set_last_message(exc.detail or str(exc))


def _render_result_shortcuts() -> None:
    shortcuts = st.columns(2)
    with shortcuts[0]:
        if st.button("Abrir resultados", key="execution_open_results", width="stretch"):
            st.switch_page("pages/02_resultado.py")
    with shortcuts[1]:
        if st.button("Abrir auditoria", key="execution_open_audit", width="stretch"):
            st.switch_page("pages/03_auditoria.py")


def _render_technical_details(ui_settings, inline_defaults) -> None:
    with st.expander("Detalhes tecnicos", expanded=False):
        st.write("Conexao configurada via settings da aplicacao.")
        st.write(f"API base URL: {ui_settings.api_base_url}")
        st.write(f"Cenario de teste configurado: {ui_settings.dataset.dataset_dir}")
        if ui_settings.sources:
            st.write("Arquivos de settings lidos:")
            for source in ui_settings.sources:
                st.write(f"- {source}")
        if inline_defaults.configured_paths:
            st.write("Arquivos preconfigurados no ambiente:")
            for filename, path in inline_defaults.configured_paths.items():
                st.write(f"- {filename}: {path}")


if __name__ == "__main__":
    main()

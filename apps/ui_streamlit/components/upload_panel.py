from __future__ import annotations

import streamlit as st


UPLOAD_SPECS = (
    ("contexto.json", "contexto.json", "Identifica a execucao e a data de operacao."),
    ("bases.json", "bases.json", "Lista as bases operacionais com localizacao e disponibilidade."),
    ("pontos.json", "pontos.json", "Lista os pontos de atendimento com localizacao e janela."),
    ("viaturas.json", "viaturas.json", "Descreve a frota disponivel, capacidades e base de origem."),
    ("ordens.json", "ordens.json", "Lista as ordens do dia, criticidades, janelas e demanda."),
    (
        "snapshot_source.json",
        "snapshot_source.json (opcional)",
        "Use apenas quando precisar enviar o snapshot de origem junto com a execucao.",
    ),
)


def render_inline_upload_panel() -> dict[str, bytes]:
    uploads: dict[str, bytes] = {}
    for filename, label, help_text in UPLOAD_SPECS:
        uploaded = st.file_uploader(
            label,
            type=["json"],
            key=f"upload::{filename}",
            accept_multiple_files=False,
            help=help_text,
        )
        if uploaded is not None:
            uploads[filename] = uploaded.getvalue()
    return uploads

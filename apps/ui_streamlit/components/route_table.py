from __future__ import annotations

from typing import Any

import streamlit as st

try:
    import pandas as pd
except Exception:  # pragma: no cover - fallback when pandas is absent
    pd = None

from apps.ui_streamlit.services.view_models import RouteRowViewModel


def render_route_table(
    route_rows: tuple[RouteRowViewModel, ...],
    *,
    current_route_id: str | None,
) -> str | None:
    st.subheader("Rotas planejadas")
    if not route_rows:
        st.info("Nenhuma rota corresponde aos filtros atuais.")
        return None

    records = [
        {
            "classe_operacional": row.classe_operacional,
            "id_rota": row.id_rota,
            "id_viatura": row.id_viatura,
            "id_base": row.id_base,
            "inicio_previsto": row.inicio_previsto,
            "fim_previsto": row.fim_previsto,
            "quantidade_paradas": row.quantidade_paradas,
            "custo_estimado": row.custo_estimado,
            "distancia_estimada": row.distancia_estimada,
            "violacao_janela": row.possui_violacao_janela,
            "excesso_capacidade": row.possui_excesso_capacidade,
            "limite_segurado": row.atingiu_limite_segurado,
        }
        for row in route_rows
    ]
    data = pd.DataFrame(records) if pd is not None else records
    selection = st.dataframe(
        data,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="route_table_selection",
    )
    selected_row_index = _extract_selected_row_index(selection)
    if selected_row_index is not None and 0 <= selected_row_index < len(route_rows):
        return route_rows[selected_row_index].id_rota
    if current_route_id and any(row.id_rota == current_route_id for row in route_rows):
        return current_route_id
    return route_rows[0].id_rota

def _extract_selected_row_index(selection: Any) -> int | None:
    if selection is None:
        return None
    if isinstance(selection, dict):
        rows = selection.get("rows")
        if isinstance(rows, list) and rows:
            try:
                return int(rows[0])
            except (TypeError, ValueError):
                return None
        for value in selection.values():
            resolved = _extract_selected_row_index(value)
            if resolved is not None:
                return resolved
    return None

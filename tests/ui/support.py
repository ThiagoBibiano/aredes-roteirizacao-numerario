from __future__ import annotations

import copy
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "src"):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from apps.ui_streamlit.services.alerts import build_alerts
from apps.ui_streamlit.services.view_models import (
    AlertViewModel,
    ExecutionSummaryViewModel,
    InspectionSnapshotViewModel,
    KpiCardsViewModel,
    MapNodeViewModel,
    MapSegmentViewModel,
    RouteRowViewModel,
    RouteStopRowViewModel,
    build_available_filters,
    build_inspection_snapshot,
    with_alerts,
)
from roteirizacao.api import ApiSettings, create_app
from tests.contract.test_api import ApiContractTest


def inline_payload() -> dict[str, object]:
    return copy.deepcopy(ApiContractTest().inline_payload())


def dual_class_payload() -> dict[str, object]:
    payload = inline_payload()
    payload["ordens"] = [
        payload["ordens"][0],
        {
            **payload["ordens"][0],
            "id_ordem": "ORD-REC",
            "tipo_servico": "recolhimento",
            "valor_estimado": "80000.00",
            "volume_estimado": "4",
            "penalidade_nao_atendimento": "12000.00",
        },
    ]
    return payload


def non_served_payload() -> dict[str, object]:
    payload = inline_payload()
    payload["pontos"] = [
        {
            **payload["pontos"][0],
            "id_ponto": "PONTO-LONGE",
            "latitude": -23.0,
            "longitude": -45.0,
        }
    ]
    payload["ordens"] = [
        {
            **payload["ordens"][0],
            "id_ordem": "ORD-LOW",
            "id_ponto": "PONTO-LONGE",
            "penalidade_nao_atendimento": "50000.00",
            "inicio_janela": "2026-03-21T06:00:00+00:00",
            "fim_janela": "2026-03-21T06:05:00+00:00",
        }
    ]
    return payload


def exception_payload() -> dict[str, object]:
    payload = inline_payload()
    payload["ordens"] = [
        {
            **payload["ordens"][0],
            "id_ordem": "ORD-EXC",
            "status_cancelamento": "cancelada_antes_cutoff",
            "instante_cancelamento": "2026-03-21T17:00:00+00:00",
        },
        {
            **payload["ordens"][0],
            "id_ordem": "ORD-CANC",
            "status_cancelamento": "cancelada_apos_cutoff",
            "instante_cancelamento": "2026-03-21T19:00:00+00:00",
            "taxa_improdutiva": "250.00",
        },
    ]
    return payload


def invalid_payload() -> dict[str, object]:
    payload = inline_payload()
    payload["ordens"] = [{**payload["ordens"][0], "id_ponto": ""}]
    return payload


def run_api_response(payload: dict[str, object] | None = None) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        client = TestClient(
            create_app(ApiSettings(api_runs_dir=Path(tmp_dir) / "api_runs", host="127.0.0.1", port=8000))
        )
        response = client.post("/api/v1/planning/run", json=payload or inline_payload())
        if response.status_code != 200:
            raise AssertionError(f"Resposta inesperada da API de teste: {response.status_code} - {response.text}")
        return response.json()


def build_snapshot(
    raw_response: dict[str, object],
    *,
    input_payload: dict[str, object] | None,
    wait_threshold_seconds: int = 900,
) -> InspectionSnapshotViewModel:
    snapshot = build_inspection_snapshot(raw_response, input_payload=input_payload)
    return with_alerts(
        snapshot,
        build_alerts(raw_response, snapshot, wait_threshold_seconds=wait_threshold_seconds),
    )


def synthetic_snapshot() -> InspectionSnapshotViewModel:
    snapshot = InspectionSnapshotViewModel(
        execution_summary=ExecutionSummaryViewModel(
            id_execucao="exec-ui-01",
            hash_cenario="hash-ui-01",
            status_final="concluida_com_ressalvas",
            reused_cached_result=False,
            recovered_previous_context=False,
            attempt_number=1,
            snapshot_materialized=False,
        ),
        kpi_cards=KpiCardsViewModel(
            custo_total_estimado="1500.00",
            distancia_total_estimada=1000,
            duracao_total_estimada_segundos=3600,
            taxa_atendimento="0.5000",
            utilizacao_frota="1.0000",
            viaturas_acionadas=2,
            total_ordens_atendidas=2,
            total_ordens_especiais_atendidas=1,
            total_ordens_nao_atendidas=1,
            impacto_financeiro_cancelamentos="250.00",
            penalidade_total_nao_atendimento="1.00",
        ),
        route_rows=(
            RouteRowViewModel(
                classe_operacional="suprimento",
                id_rota="R1",
                id_viatura="VTR-01",
                id_base="BASE-01",
                inicio_previsto="2026-03-22T09:00:00+00:00",
                fim_previsto="2026-03-22T10:00:00+00:00",
                distancia_estimada=400,
                duracao_estimada_segundos=1800,
                custo_estimado="500.00",
                quantidade_paradas=1,
                atingiu_limite_segurado=False,
                possui_violacao_janela=False,
                possui_excesso_capacidade=False,
                maior_criticidade="alta",
                criticidades=("alta",),
            ),
            RouteRowViewModel(
                classe_operacional="recolhimento",
                id_rota="R2",
                id_viatura="VTR-02",
                id_base="BASE-01",
                inicio_previsto="2026-03-22T10:00:00+00:00",
                fim_previsto="2026-03-22T11:00:00+00:00",
                distancia_estimada=600,
                duracao_estimada_segundos=1800,
                custo_estimado="1000.00",
                quantidade_paradas=1,
                atingiu_limite_segurado=True,
                possui_violacao_janela=True,
                possui_excesso_capacidade=False,
                maior_criticidade="critica",
                criticidades=("critica",),
            ),
        ),
        route_stop_rows=(
            RouteStopRowViewModel(
                id_rota="R1",
                id_viatura="VTR-01",
                classe_operacional="suprimento",
                sequencia=1,
                id_ordem="ORD-01",
                id_ponto="PONTO-01",
                tipo_servico="suprimento",
                criticidade="alta",
                inicio_previsto="2026-03-22T09:10:00+00:00",
                fim_previsto="2026-03-22T09:20:00+00:00",
                folga_janela_segundos=120,
                espera_segundos=0,
                atraso_segundos=0,
                demanda={"volume": "5"},
                carga_acumulada={"volume": "5"},
            ),
            RouteStopRowViewModel(
                id_rota="R2",
                id_viatura="VTR-02",
                classe_operacional="recolhimento",
                sequencia=1,
                id_ordem="ORD-02",
                id_ponto="PONTO-02",
                tipo_servico="recolhimento",
                criticidade="critica",
                inicio_previsto="2026-03-22T10:10:00+00:00",
                fim_previsto="2026-03-22T10:20:00+00:00",
                folga_janela_segundos=60,
                espera_segundos=950,
                atraso_segundos=20,
                demanda={"financeiro": "80000.00"},
                carga_acumulada={"financeiro": "80000.00"},
            ),
        ),
        map_nodes=(
            MapNodeViewModel("base:BASE-01", "BASE-01", "base", -23.55, -46.63, "Base 01", {"id_base": "BASE-01"}),
            MapNodeViewModel("n1", "PONTO-01", "ponto_atendido", -23.54, -46.64, "PONTO-01", {"id_ordem": "ORD-01"}, id_rota="R1", id_viatura="VTR-01", classe_operacional="suprimento", criticidade="alta", status_atendimento="atendida"),
            MapNodeViewModel("n2", "PONTO-02", "ponto_atendido", -23.53, -46.62, "PONTO-02", {"id_ordem": "ORD-02"}, id_rota="R2", id_viatura="VTR-02", classe_operacional="recolhimento", criticidade="critica", status_atendimento="atendida"),
            MapNodeViewModel("n3", "PONTO-03", "ponto_nao_atendido", -23.52, -46.61, "PONTO-03", {"id_ordem": "ORD-03"}, classe_operacional="suprimento", criticidade="media", status_atendimento="nao_atendida"),
            MapNodeViewModel("n4", "PONTO-04", "ponto_excluido", -23.51, -46.60, "PONTO-04", {"id_ordem": "ORD-04"}, classe_operacional="suprimento", criticidade="baixa", status_atendimento="excluida"),
            MapNodeViewModel("n5", "PONTO-05", "ponto_cancelado", -23.50, -46.59, "PONTO-05", {"id_ordem": "ORD-05"}, classe_operacional="recolhimento", criticidade="alta", status_atendimento="cancelada"),
        ),
        map_segments=(
            MapSegmentViewModel("s1", "R1", "VTR-01", -23.55, -46.63, -23.54, -46.64, 1, "suprimento"),
            MapSegmentViewModel("s2", "R2", "VTR-02", -23.55, -46.63, -23.53, -46.62, 1, "recolhimento"),
        ),
        alerts=(
            AlertViewModel("aviso", "limite_segurado", "Rota no limite segurado", "Rota R2", "Rota", "R2", id_rota="R2", id_viatura="VTR-02", classe_operacional="recolhimento", status_atendimento="atendida"),
            AlertViewModel("erro", "ordem_nao_atendida", "Ordem nao atendida", "ORD-03", "Ordem", "ORD-03", classe_operacional="suprimento", criticidade="media", status_atendimento="nao_atendida"),
        ),
        event_rows=(
            {"id_evento": "EVT-1", "severidade": "info", "tipo_evento": "saida"},
            {"id_evento": "EVT-2", "severidade": "erro", "tipo_evento": "erro"},
        ),
        reason_rows=(
            {"codigo": "R-1", "descricao": "Motivo critico", "severidade": "critico"},
        ),
        non_served_rows=(
            {"id_ordem": "ORD-03", "criticidade": "media", "classe_operacional": "suprimento", "status_atendimento": "nao_atendida"},
        ),
        excluded_rows=(
            {"id_ordem": "ORD-04", "criticidade": "baixa", "classe_operacional": "suprimento", "status_atendimento": "excluida"},
        ),
        cancelled_rows=(
            {"id_ordem": "ORD-05", "criticidade": "alta", "classe_operacional": "recolhimento", "status_atendimento": "cancelada"},
        ),
        error_rows=(
            {"id_erro": "ERR-1", "severidade": "erro"},
        ),
        relatorio_destaques=("ha_rotas_no_limite_segurado",),
        available_filters={},
        map_available=True,
        map_warnings=(),
        source_has_inputs=True,
    )
    return replace(snapshot, available_filters=build_available_filters(snapshot))

from __future__ import annotations

import copy
import unittest

from apps.ui_streamlit.services.alerts import build_alerts
from apps.ui_streamlit.services.view_models import build_inspection_snapshot
from tests.ui.support import build_snapshot, dual_class_payload, exception_payload, inline_payload, non_served_payload, run_api_response


class AlertsTest(unittest.TestCase):
    def test_alerta_para_ordens_nao_atendidas(self) -> None:
        payload = non_served_payload()
        raw_response = run_api_response(payload)
        snapshot = build_snapshot(raw_response, input_payload=payload)

        self.assertTrue(any(alert.category == "ordem_nao_atendida" for alert in snapshot.alerts))

    def test_alerta_para_limite_segurado(self) -> None:
        payload = dual_class_payload()
        raw_response = run_api_response(payload)
        snapshot = build_snapshot(raw_response, input_payload=payload)

        self.assertTrue(any(alert.category == "limite_segurado" for alert in snapshot.alerts))

    def test_alerta_para_violacao_de_janela(self) -> None:
        payload = inline_payload()
        raw_response = run_api_response(payload)
        modified = copy.deepcopy(raw_response)
        modified["result"]["rotas_suprimento"][0]["possui_violacao_janela"] = True
        snapshot = build_snapshot(modified, input_payload=payload)

        self.assertTrue(any(alert.category == "violacao_janela" for alert in snapshot.alerts))

    def test_alerta_para_excesso_de_capacidade(self) -> None:
        payload = inline_payload()
        raw_response = run_api_response(payload)
        modified = copy.deepcopy(raw_response)
        modified["result"]["rotas_suprimento"][0]["possui_excesso_capacidade"] = True
        snapshot = build_snapshot(modified, input_payload=payload)

        self.assertTrue(any(alert.category == "excesso_capacidade" for alert in snapshot.alerts))

    def test_alerta_para_cancelamento_com_impacto(self) -> None:
        payload = exception_payload()
        raw_response = run_api_response(payload)
        snapshot = build_snapshot(raw_response, input_payload=payload)

        self.assertTrue(any(alert.category == "cancelamento_com_impacto" for alert in snapshot.alerts))

    def test_alerta_para_espera_elevada(self) -> None:
        payload = inline_payload()
        raw_response = run_api_response(payload)
        modified = copy.deepcopy(raw_response)
        modified["result"]["rotas_suprimento"][0]["paradas"][0]["espera_segundos"] = 901
        snapshot = build_snapshot(modified, input_payload=payload, wait_threshold_seconds=900)

        self.assertTrue(any(alert.category == "espera_elevada" for alert in snapshot.alerts))

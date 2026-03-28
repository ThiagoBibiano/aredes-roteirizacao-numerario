from __future__ import annotations

import copy
import unittest

from apps.ui_streamlit.services.view_models import (
    build_execution_summary,
    build_inspection_snapshot,
    build_kpi_cards,
    build_route_rows,
    build_route_stop_rows,
)
from tests.ui.support import (
    dual_class_payload,
    inline_payload,
    invalid_payload,
    non_served_payload,
    run_api_response,
)


class ViewModelsTest(unittest.TestCase):
    def test_build_execution_summary_from_success_response(self) -> None:
        raw_response = run_api_response()
        summary = build_execution_summary(raw_response)

        self.assertEqual(summary.id_execucao, raw_response["id_execucao"])
        self.assertEqual(summary.hash_cenario, raw_response["hash_cenario"])
        self.assertEqual(summary.status_final, raw_response["status_final"])

    def test_build_kpi_cards_from_result(self) -> None:
        raw_response = run_api_response()
        cards = build_kpi_cards(raw_response)

        self.assertGreater(cards.distancia_total_estimada, 0)
        self.assertEqual(cards.total_ordens_atendidas, 1)
        self.assertEqual(cards.total_ordens_nao_atendidas, 0)

    def test_build_route_rows_from_supply_and_collection_routes(self) -> None:
        raw_response = run_api_response(dual_class_payload())
        rows = build_route_rows(raw_response)

        self.assertEqual(len(rows), 2)
        self.assertEqual({row.classe_operacional for row in rows}, {"suprimento", "recolhimento"})

    def test_build_route_stop_rows_preserves_sequence_order(self) -> None:
        raw_response = run_api_response()
        modified = copy.deepcopy(raw_response)
        route = modified["result"]["rotas_suprimento"][0]
        original_stop = route["paradas"][0]
        route["paradas"] = [
            {**original_stop, "sequencia": 2, "id_ordem": "ORD-02"},
            {**original_stop, "sequencia": 1, "id_ordem": "ORD-01"},
        ]

        rows = build_route_stop_rows(modified)

        self.assertEqual([row.sequencia for row in rows], [1, 2])
        self.assertEqual([row.id_ordem for row in rows], ["ORD-01", "ORD-02"])

    def test_build_map_nodes_marks_non_served_orders(self) -> None:
        payload = non_served_payload()
        raw_response = run_api_response(payload)
        snapshot = build_inspection_snapshot(raw_response, input_payload=payload)

        self.assertTrue(any(node.kind == "ponto_nao_atendido" for node in snapshot.map_nodes))

    def test_build_map_segments_from_route_sequence(self) -> None:
        payload = inline_payload()
        raw_response = run_api_response(payload)
        snapshot = build_inspection_snapshot(raw_response, input_payload=payload)

        self.assertTrue(snapshot.map_available)
        self.assertGreaterEqual(len(snapshot.map_segments), 1)
        self.assertEqual(snapshot.map_segments[0].ordem_segmento, 1)

    def test_missing_point_reference_is_handled_without_crash(self) -> None:
        payload = inline_payload()
        payload["pontos"] = [
            {**payload["pontos"][0], "id_ponto": "PONTO-OUTRO"},
        ]
        raw_response = run_api_response()
        snapshot = build_inspection_snapshot(raw_response, input_payload=payload)

        self.assertTrue(snapshot.map_available)
        self.assertTrue(any("PONTO-01" in warning for warning in snapshot.map_warnings))

    def test_inviable_result_generates_empty_route_views(self) -> None:
        payload = invalid_payload()
        raw_response = run_api_response(payload)
        snapshot = build_inspection_snapshot(raw_response, input_payload=payload)

        self.assertEqual(snapshot.execution_summary.status_final, "inviavel")
        self.assertEqual(snapshot.route_rows, ())
        self.assertEqual(snapshot.map_segments, ())

    def test_offline_raw_without_input_payload_disables_map(self) -> None:
        raw_response = run_api_response()
        snapshot = build_inspection_snapshot(raw_response, input_payload=None)

        self.assertFalse(snapshot.map_available)
        self.assertTrue(snapshot.map_warnings)

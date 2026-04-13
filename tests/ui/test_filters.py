from __future__ import annotations

import unittest

from apps.ui_streamlit.services.filters import FilterCriteria, apply_filters
from tests.ui.support import synthetic_snapshot


class FiltersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = synthetic_snapshot()

    def test_filter_by_viatura(self) -> None:
        filtered = apply_filters(self.snapshot, FilterCriteria(viaturas=("VTR-02",)))

        self.assertEqual(len(filtered.route_rows), 1)
        self.assertEqual(filtered.route_rows[0].id_viatura, "VTR-02")
        self.assertEqual(len(filtered.map_segments), 1)

    def test_filter_by_classe_operacional(self) -> None:
        filtered = apply_filters(self.snapshot, FilterCriteria(classes_operacionais=("suprimento",)))

        self.assertEqual(len(filtered.route_rows), 1)
        self.assertEqual(filtered.route_rows[0].classe_operacional, "suprimento")

    def test_filter_by_criticidade(self) -> None:
        filtered = apply_filters(self.snapshot, FilterCriteria(criticidades=("critica",)))

        self.assertEqual(len(filtered.route_stop_rows), 1)
        self.assertEqual(filtered.route_stop_rows[0].criticidade, "critica")

    def test_filter_by_severidade(self) -> None:
        filtered = apply_filters(self.snapshot, FilterCriteria(severidades=("erro",)))

        self.assertEqual(len(filtered.alerts), 1)
        self.assertEqual(filtered.alerts[0].severity, "erro")
        self.assertEqual(len(filtered.event_rows), 1)

    def test_filter_by_status_atendimento(self) -> None:
        filtered = apply_filters(self.snapshot, FilterCriteria(statuses_atendimento=("cancelada",)))

        self.assertEqual(filtered.route_rows, ())
        self.assertEqual(len(filtered.cancelled_rows), 1)
        self.assertEqual(filtered.cancelled_rows[0]["status_atendimento"], "cancelada")

    def test_filter_by_faixa_horario(self) -> None:
        filtered = apply_filters(self.snapshot, FilterCriteria(faixa_inicio="10:01", faixa_fim="10:30"))

        self.assertEqual(len(filtered.route_rows), 1)
        self.assertEqual(filtered.route_rows[0].id_rota, "R2")

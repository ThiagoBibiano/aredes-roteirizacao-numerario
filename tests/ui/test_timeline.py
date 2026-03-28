from __future__ import annotations

import unittest
from dataclasses import replace

from apps.ui_streamlit.services.filters import FilterCriteria, apply_filters
from apps.ui_streamlit.services.timeline import (
    build_timeline_snapshot,
    clamp_timeline_current_at,
    find_timeline_route,
    resolve_route_state,
)
from apps.ui_streamlit.services.view_models import InspectionSnapshotViewModel, RouteStopRowViewModel
from tests.ui.support import build_snapshot, run_api_response, synthetic_snapshot


class TimelineTest(unittest.TestCase):
    def test_builds_global_timeline_bounds(self) -> None:
        timeline = self._build_timeline(synthetic_snapshot(), selected_route_id="R1")

        self.assertTrue(timeline.available)
        self.assertEqual(timeline.start_at, "2026-03-22T09:00:00+00:00")
        self.assertEqual(timeline.end_at, "2026-03-22T11:00:00+00:00")

    def test_generates_ordered_discrete_steps_for_route(self) -> None:
        timeline = self._build_timeline(synthetic_snapshot(), selected_route_id="R1")
        route = find_timeline_route(timeline.routes, "R1")

        self.assertIsNotNone(route)
        self.assertEqual([step.kind for step in route.steps], ["inicio_rota", "parada", "fim_rota"])
        self.assertEqual([step.sequencia for step in route.steps], [0, 1, 2])

    def test_interpolates_vehicle_position_on_active_segment(self) -> None:
        timeline = self._build_timeline(synthetic_snapshot(), selected_route_id="R1")
        route = find_timeline_route(timeline.routes, "R1")
        state = resolve_route_state(route, "2026-03-22T09:05:00+00:00")

        self.assertEqual(state.phase, "em_deslocamento")
        self.assertEqual(state.active_segment_sequence, 1)
        self.assertAlmostEqual(state.vehicle_position.latitude, -23.545, places=3)
        self.assertAlmostEqual(state.vehicle_position.longitude, -46.635, places=3)

    def test_keeps_vehicle_fixed_during_service_window(self) -> None:
        timeline = self._build_timeline(synthetic_snapshot(), selected_route_id="R1")
        route = find_timeline_route(timeline.routes, "R1")
        state = resolve_route_state(route, "2026-03-22T09:15:00+00:00")

        self.assertEqual(state.phase, "em_atendimento")
        self.assertEqual(state.active_stop_sequence, 1)
        self.assertAlmostEqual(state.vehicle_position.latitude, -23.54, places=3)
        self.assertAlmostEqual(state.vehicle_position.longitude, -46.64, places=3)

    def test_return_to_base_toggle_changes_end_of_route_motion(self) -> None:
        base_snapshot = synthetic_snapshot()
        without_return = self._build_timeline(base_snapshot, selected_route_id="R1", include_return_to_base=False)
        with_return = self._build_timeline(base_snapshot, selected_route_id="R1", include_return_to_base=True)

        route_without_return = find_timeline_route(without_return.routes, "R1")
        route_with_return = find_timeline_route(with_return.routes, "R1")
        state_without_return = resolve_route_state(route_without_return, "2026-03-22T09:40:00+00:00")
        state_with_return = resolve_route_state(route_with_return, "2026-03-22T09:40:00+00:00")

        self.assertEqual(state_without_return.phase, "encerrando")
        self.assertAlmostEqual(state_without_return.vehicle_position.latitude, -23.54, places=3)
        self.assertEqual(state_with_return.phase, "encerrando")
        self.assertEqual(state_with_return.active_segment_sequence, 2)
        self.assertAlmostEqual(state_with_return.vehicle_position.latitude, -23.545, places=3)

    def test_clamps_current_time_when_filters_reduce_window(self) -> None:
        snapshot = synthetic_snapshot()
        full_timeline = self._build_timeline(snapshot, selected_route_id="R2")
        filtered_snapshot = apply_filters(snapshot, FilterCriteria(viaturas=("VTR-01",)))
        filtered_timeline = build_timeline_snapshot(filtered_snapshot, selected_route_id="R2")

        clamped = clamp_timeline_current_at(filtered_timeline, full_timeline.end_at)

        self.assertEqual(filtered_timeline.start_at, "2026-03-22T09:00:00+00:00")
        self.assertEqual(filtered_timeline.end_at, "2026-03-22T10:00:00+00:00")
        self.assertEqual(clamped, "2026-03-22T10:00:00+00:00")

    def test_invalid_stop_timestamp_is_ignored_without_crash(self) -> None:
        snapshot = synthetic_snapshot()
        invalid_stop = replace(
            snapshot.route_stop_rows[0],
            inicio_previsto="invalido",
            fim_previsto="",
        )
        invalid_snapshot = replace(
            snapshot,
            route_stop_rows=(invalid_stop, *snapshot.route_stop_rows[1:]),
        )

        timeline = self._build_timeline(invalid_snapshot, selected_route_id="R1")
        route = find_timeline_route(timeline.routes, "R1")

        self.assertTrue(timeline.available)
        self.assertTrue(any("Parada ignorada" in warning for warning in timeline.warnings))
        self.assertEqual([step.kind for step in route.steps], ["inicio_rota", "fim_rota"])

    def test_offline_raw_keeps_timeline_available_without_map(self) -> None:
        raw_response = run_api_response()
        snapshot = build_snapshot(raw_response, input_payload=None)

        timeline = self._build_timeline(snapshot, selected_route_id=None)

        self.assertFalse(snapshot.map_available)
        self.assertTrue(timeline.available)
        self.assertGreaterEqual(len(timeline.routes), 1)

    def _build_timeline(
        self,
        snapshot: InspectionSnapshotViewModel,
        *,
        selected_route_id: str | None,
        include_return_to_base: bool = False,
    ):
        filtered = apply_filters(snapshot, FilterCriteria())
        return build_timeline_snapshot(
            filtered,
            selected_route_id=selected_route_id,
            include_return_to_base=include_return_to_base,
        )

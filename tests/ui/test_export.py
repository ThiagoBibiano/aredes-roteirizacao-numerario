from __future__ import annotations

import json
import unittest

from apps.ui_streamlit.services.export import build_enriched_export, build_raw_export, load_exported_payload
from tests.ui.support import build_snapshot, inline_payload, run_api_response


class ExportTest(unittest.TestCase):
    def test_raw_export_round_trip(self) -> None:
        raw_response = run_api_response()
        exported = build_raw_export(raw_response)
        loaded = load_exported_payload(exported)

        self.assertEqual(loaded.raw_response["id_execucao"], raw_response["id_execucao"])
        self.assertIsNone(loaded.inspection_snapshot)
        self.assertEqual(loaded.source_kind, "offline_raw")

    def test_enriched_export_round_trip(self) -> None:
        payload = inline_payload()
        raw_response = run_api_response(payload)
        snapshot = build_snapshot(raw_response, input_payload=payload)
        exported = build_enriched_export(
            raw_response,
            input_payload=payload,
            inspection_snapshot=snapshot,
            source_kind="inline",
            api_base_url="http://127.0.0.1:8000",
        )
        loaded = load_exported_payload(exported)

        self.assertEqual(loaded.raw_response["id_execucao"], raw_response["id_execucao"])
        self.assertIsNotNone(loaded.inspection_snapshot)
        self.assertEqual(loaded.source_kind, "inline")
        self.assertTrue(loaded.inspection_snapshot.map_available)

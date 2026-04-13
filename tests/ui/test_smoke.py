from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "src"):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

try:
    from streamlit.testing.v1 import AppTest
except Exception:  # pragma: no cover - dependency optional during static analysis
    AppTest = None

from apps.ui_streamlit.state.session_state import (
    APPLIED_WAIT_THRESHOLD_KEY,
    INPUT_PAYLOAD_KEY,
    RAW_RESPONSE_KEY,
    SNAPSHOT_KEY,
    SOURCE_KIND_KEY,
    WAIT_THRESHOLD_KEY,
)
from tests.ui.support import build_snapshot, inline_payload, run_api_response


@unittest.skipIf(AppTest is None, "streamlit nao instalado no ambiente")
class StreamlitSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = inline_payload()
        self.raw_response = run_api_response(self.payload)
        self.snapshot = build_snapshot(self.raw_response, input_payload=self.payload)

    def test_execution_page_renders(self) -> None:
        app = AppTest.from_file(str(ROOT / "apps/ui_streamlit/pages/01_execucao.py"))
        app.run()

        self.assertFalse(app.exception)
        self.assertIn("Rodar planejamento", app.title[0].value)
        self.assertEqual(len(app.text_input), 0)

    def test_results_page_renders(self) -> None:
        app = AppTest.from_file(str(ROOT / "apps/ui_streamlit/pages/02_resultado.py"))
        self._seed_session_state(app)
        app.run()

        self.assertFalse(app.exception)
        self.assertIn("Resultados do planejamento", app.title[0].value)
        self.assertEqual(len(app.select_slider), 1)
        self.assertGreaterEqual(len(app.radio), 1)

    def test_audit_page_renders(self) -> None:
        app = AppTest.from_file(str(ROOT / "apps/ui_streamlit/pages/03_auditoria.py"))
        self._seed_session_state(app)
        app.run()

        self.assertFalse(app.exception)
        self.assertIn("Auditoria e excecoes", app.title[0].value)

    def _seed_session_state(self, app: AppTest) -> None:
        app.session_state[RAW_RESPONSE_KEY] = self.raw_response
        app.session_state[INPUT_PAYLOAD_KEY] = self.payload
        app.session_state[SNAPSHOT_KEY] = self.snapshot
        app.session_state[SOURCE_KIND_KEY] = "inline"
        app.session_state[WAIT_THRESHOLD_KEY] = 900
        app.session_state[APPLIED_WAIT_THRESHOLD_KEY] = 900

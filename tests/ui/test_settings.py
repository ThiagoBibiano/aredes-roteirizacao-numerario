from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from apps.ui_streamlit.services.ui_settings import (
    build_ui_settings,
    load_inline_documents_from_settings,
    load_ui_settings,
)


class UiSettingsTest(unittest.TestCase):
    def test_build_ui_settings_applies_defaults_and_normalizes_mode(self) -> None:
        settings = build_ui_settings({"execution": {"default_mode": "desconhecido"}})

        self.assertEqual(settings.api_base_url, "http://127.0.0.1:8000")
        self.assertEqual(settings.default_mode, "dataset")
        self.assertEqual(settings.dataset.dataset_dir, "data/fake_solution")
        self.assertEqual(settings.parameters.max_iterations, 100)

    def test_load_ui_settings_merges_base_and_local_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir) / "settings.toml"
            local = Path(tmp_dir) / "settings.local.toml"
            base.write_text(
                'api_base_url = "http://base"\n[execution]\ndefault_mode = "dataset"\n[execution.dataset]\ndataset_dir = "data/base"\n',
                encoding="utf-8",
            )
            local.write_text(
                '[execution]\ndefault_mode = "inline"\n[execution.parameters]\nseed = 7\n',
                encoding="utf-8",
            )

            settings = load_ui_settings((base, local))

        self.assertEqual(settings.api_base_url, "http://base")
        self.assertEqual(settings.default_mode, "inline")
        self.assertEqual(settings.dataset.dataset_dir, "data/base")
        self.assertEqual(settings.parameters.seed, 7)
        self.assertEqual(settings.sources, (str(base), str(local)))

    def test_load_inline_documents_from_settings_reads_files_and_warns_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            contexto = Path(tmp_dir) / "contexto.json"
            contexto.write_text('{"id_execucao": "exec-1", "data_operacao": "2026-03-22"}', encoding="utf-8")
            settings = build_ui_settings(
                {
                    "execution": {
                        "inline": {
                            "files": {
                                "contexto": str(contexto),
                                "bases": str(Path(tmp_dir) / "bases.json"),
                            }
                        }
                    }
                }
            )

            loaded = load_inline_documents_from_settings(settings)

        self.assertIn("contexto.json", loaded.documents)
        self.assertEqual(loaded.configured_paths["contexto.json"], str(contexto))
        self.assertTrue(any("bases.json" in warning for warning in loaded.warnings))

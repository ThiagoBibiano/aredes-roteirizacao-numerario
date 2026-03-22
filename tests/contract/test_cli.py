from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from roteirizacao.cli import main

try:
    import pyvrp  # noqa: F401
except Exception:  # pragma: no cover - environment-dependent branch
    PYVRP_AVAILABLE = False
else:
    PYVRP_AVAILABLE = True


class CliContractTest(unittest.TestCase):
    def write_dataset(self, dataset_dir: Path) -> None:
        (dataset_dir / "logistics_sources").mkdir(parents=True, exist_ok=True)
        (dataset_dir / "outputs").mkdir(parents=True, exist_ok=True)
        (dataset_dir / "contexto.json").write_text(
            json.dumps(
                {
                    "id_execucao": "exec-smoke-2026-03-21",
                    "data_operacao": "2026-03-21",
                    "cutoff": "2026-03-20T18:00:00+00:00",
                    "timestamp_referencia": "2026-03-20T18:30:00+00:00",
                    "versao_schema": "1.0",
                },
                indent=2,
                ensure_ascii=True,
            )
            + "\n"
        )
        (dataset_dir / "bases.json").write_text(
            json.dumps(
                [
                    {
                        "id_base": "BASE-01",
                        "nome": "Base Central Fake",
                        "latitude": -23.5505,
                        "longitude": -46.6333,
                        "inicio_operacao": "2026-03-21T06:00:00+00:00",
                        "fim_operacao": "2026-03-21T22:00:00+00:00",
                        "status_ativo": True,
                    }
                ],
                indent=2,
                ensure_ascii=True,
            )
            + "\n"
        )
        (dataset_dir / "pontos.json").write_text(
            json.dumps(
                [
                    {
                        "id_ponto": "PONTO-01",
                        "tipo_ponto": "agencia",
                        "latitude": -23.5489,
                        "longitude": -46.6388,
                        "setor_geografico": "centro",
                        "inicio_janela": "2026-03-21T08:00:00+00:00",
                        "fim_janela": "2026-03-21T17:00:00+00:00",
                        "tempo_servico": 20,
                        "status_ativo": True,
                    }
                ],
                indent=2,
                ensure_ascii=True,
            )
            + "\n"
        )
        (dataset_dir / "viaturas.json").write_text(
            json.dumps(
                [
                    {
                        "id_viatura": "VTR-01",
                        "tipo_viatura": "media",
                        "id_base_origem": "BASE-01",
                        "inicio_turno": "2026-03-21T06:00:00+00:00",
                        "fim_turno": "2026-03-21T18:00:00+00:00",
                        "custo_fixo": "500.00",
                        "custo_variavel": "2.50",
                        "capacidade_financeira": "100000.00",
                        "capacidade_volumetrica": "20",
                        "teto_segurado": "80000.00",
                        "compatibilidade_servico": ["suprimento", "recolhimento", "extraordinario"],
                        "status_ativo": True,
                    }
                ],
                indent=2,
                ensure_ascii=True,
            )
            + "\n"
        )
        (dataset_dir / "ordens.json").write_text(
            json.dumps(
                [
                    {
                        "id_ordem": "ORD-SMOKE-01",
                        "origem_ordem": "erp_fake",
                        "data_operacao": "2026-03-21",
                        "timestamp_criacao": "2026-03-20T15:00:00+00:00",
                        "tipo_servico": "suprimento",
                        "classe_planejamento": "padrao",
                        "id_ponto": "PONTO-01",
                        "valor_estimado": "15000.00",
                        "volume_estimado": "5",
                        "inicio_janela": "2026-03-21T09:00:00+00:00",
                        "fim_janela": "2026-03-21T11:00:00+00:00",
                        "tempo_servico": 20,
                        "criticidade": "alta",
                        "penalidade_nao_atendimento": "20000.00",
                        "penalidade_atraso": "500.00",
                        "status_cancelamento": "nao_cancelada",
                        "taxa_improdutiva": "0",
                    }
                ],
                indent=2,
                ensure_ascii=True,
            )
            + "\n"
        )
        (dataset_dir / "logistics_sources" / "2026-03-21.json").write_text(
            json.dumps(
                {
                    "snapshot_id": "snap-fake-2026-03-21",
                    "generated_at": "2026-03-20T17:00:00+00:00",
                    "strategy_name": "real_snapshot_v1",
                    "source_name": "fake_smoke_source",
                    "arcs": [
                        {
                            "id_origem": "dep-BASE-01",
                            "id_destino": "dep-BASE-01",
                            "distancia_metros": 0,
                            "tempo_segundos": 0,
                            "custo": "0.00",
                        },
                        {
                            "id_origem": "dep-BASE-01",
                            "id_destino": "no-ORD-SMOKE-01",
                            "distancia_metros": 2400,
                            "tempo_segundos": 420,
                            "custo": "8.40",
                        },
                        {
                            "id_origem": "no-ORD-SMOKE-01",
                            "id_destino": "dep-BASE-01",
                            "distancia_metros": 2400,
                            "tempo_segundos": 420,
                            "custo": "8.40",
                        },
                        {
                            "id_origem": "no-ORD-SMOKE-01",
                            "id_destino": "no-ORD-SMOKE-01",
                            "distancia_metros": 0,
                            "tempo_segundos": 0,
                            "custo": "0.00",
                        },
                    ],
                },
                indent=2,
                ensure_ascii=True,
            )
            + "\n"
        )

    def test_materialize_snapshot_command_writes_versioned_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_dir = Path(tmp_dir)
            self.write_dataset(dataset_dir)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "materialize-snapshot",
                        "--date",
                        "2026-03-21",
                        "--source-dir",
                        str(dataset_dir / "logistics_sources"),
                        "--snapshot-dir",
                        str(dataset_dir / "logistics_snapshots"),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue((dataset_dir / "logistics_snapshots" / "2026-03-21.json").exists())
            self.assertTrue(
                (dataset_dir / "logistics_snapshots" / "versions" / "2026-03-21" / "manifest.json").exists()
            )
            self.assertIn("snap-fake-2026-03-21", stdout.getvalue())

    @unittest.skipUnless(PYVRP_AVAILABLE, "pyvrp nao instalado no ambiente")
    def test_run_planning_command_writes_smoke_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_dir = Path(tmp_dir)
            self.write_dataset(dataset_dir)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "run-planning",
                        "--dataset-dir",
                        str(dataset_dir),
                        "--materialize-snapshot",
                        "--max-iterations",
                        "50",
                        "--seed",
                        "1",
                    ]
                )

            self.assertEqual(exit_code, 0)
            output_path = dataset_dir / "outputs" / "resultado-planejamento.json"
            self.assertTrue(output_path.exists())

            payload = json.loads(output_path.read_text())
            self.assertEqual(payload["status_final"], "concluida")
            self.assertEqual(payload["resumo_operacional"]["total_rotas"], 1)
            self.assertEqual(payload["resumo_operacional"]["total_ordens_planejadas"], 1)
            self.assertEqual(payload["rotas_suprimento"][0]["paradas"][0]["id_ordem"], "ORD-SMOKE-01")
            self.assertIn("resultado-planejamento.json", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

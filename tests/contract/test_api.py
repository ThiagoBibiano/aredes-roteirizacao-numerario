from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from roteirizacao.api import ApiSettings, create_app


class ApiContractTest(unittest.TestCase):
    def create_client(self, api_runs_dir: Path) -> TestClient:
        return TestClient(create_app(ApiSettings(api_runs_dir=api_runs_dir, host="127.0.0.1", port=8000)))

    def inline_payload(self) -> dict[str, object]:
        return {
            "contexto": {
                "id_execucao": "exec-api-2026-03-22",
                "data_operacao": "2026-03-22",
                "cutoff": "2026-03-21T18:00:00+00:00",
                "timestamp_referencia": "2026-03-21T18:30:00+00:00",
                "versao_schema": "1.0",
            },
            "bases": [
                {
                    "id_base": "BASE-01",
                    "nome": "Base Central API",
                    "latitude": -23.5505,
                    "longitude": -46.6333,
                    "inicio_operacao": "2026-03-22T06:00:00+00:00",
                    "fim_operacao": "2026-03-22T22:00:00+00:00",
                    "status_ativo": True,
                }
            ],
            "pontos": [
                {
                    "id_ponto": "PONTO-01",
                    "tipo_ponto": "agencia",
                    "latitude": -23.5489,
                    "longitude": -46.6388,
                    "setor_geografico": "centro",
                    "inicio_janela": "2026-03-22T08:00:00+00:00",
                    "fim_janela": "2026-03-22T17:00:00+00:00",
                    "tempo_servico": 20,
                    "status_ativo": True,
                }
            ],
            "viaturas": [
                {
                    "id_viatura": "VTR-01",
                    "tipo_viatura": "media",
                    "id_base_origem": "BASE-01",
                    "inicio_turno": "2026-03-22T06:00:00+00:00",
                    "fim_turno": "2026-03-22T18:00:00+00:00",
                    "custo_fixo": "500.00",
                    "custo_variavel": "2.50",
                    "capacidade_financeira": "100000.00",
                    "capacidade_volumetrica": "20",
                    "teto_segurado": "80000.00",
                    "compatibilidade_servico": ["suprimento", "recolhimento", "extraordinario"],
                    "status_ativo": True,
                }
            ],
            "ordens": [
                {
                    "id_ordem": "ORD-API-01",
                    "origem_ordem": "erp_api",
                    "data_operacao": "2026-03-22",
                    "timestamp_criacao": "2026-03-21T15:00:00+00:00",
                    "tipo_servico": "suprimento",
                    "classe_planejamento": "padrao",
                    "id_ponto": "PONTO-01",
                    "valor_estimado": "15000.00",
                    "volume_estimado": "5",
                    "inicio_janela": "2026-03-22T09:00:00+00:00",
                    "fim_janela": "2026-03-22T11:00:00+00:00",
                    "tempo_servico": 20,
                    "criticidade": "alta",
                    "penalidade_nao_atendimento": "20000.00",
                    "penalidade_atraso": "500.00",
                    "status_cancelamento": "nao_cancelada",
                    "taxa_improdutiva": "0",
                }
            ],
            "max_iterations": 25,
            "seed": 1,
        }

    def write_dataset(self, dataset_dir: Path) -> None:
        payload = self.inline_payload()
        (dataset_dir / "logistics_sources").mkdir(parents=True, exist_ok=True)
        (dataset_dir / "contexto.json").write_text(json.dumps(payload["contexto"], indent=2, ensure_ascii=True) + "\n")
        (dataset_dir / "bases.json").write_text(json.dumps(payload["bases"], indent=2, ensure_ascii=True) + "\n")
        (dataset_dir / "pontos.json").write_text(json.dumps(payload["pontos"], indent=2, ensure_ascii=True) + "\n")
        (dataset_dir / "viaturas.json").write_text(json.dumps(payload["viaturas"], indent=2, ensure_ascii=True) + "\n")
        (dataset_dir / "ordens.json").write_text(json.dumps(payload["ordens"], indent=2, ensure_ascii=True) + "\n")

    def test_health_endpoint_returns_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self.create_client(Path(tmp_dir) / "api_runs")
            response = client.get("/health")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "ok")

    def test_materialize_snapshot_endpoint_persists_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source_dir = tmp_path / "sources"
            snapshot_dir = tmp_path / "snapshots"
            source_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / "2026-03-22.json").write_text(
                json.dumps(
                    {
                        "snapshot_id": "snap-api-2026-03-22",
                        "generated_at": "2026-03-21T17:00:00+00:00",
                        "strategy_name": "api_snapshot_v1",
                        "source_name": "api_test_source",
                        "arcs": [
                            {
                                "id_origem": "dep-BASE-01",
                                "id_destino": "dep-BASE-01",
                                "distancia_metros": 0,
                                "tempo_segundos": 0,
                                "custo": "0.00",
                            }
                        ],
                    },
                    indent=2,
                    ensure_ascii=True,
                )
                + "\n"
            )
            client = self.create_client(tmp_path / "api_runs")

            response = client.post(
                "/api/v1/snapshots/materialize",
                json={
                    "data_operacao": "2026-03-22",
                    "source_dir": str(source_dir),
                    "snapshot_dir": str(snapshot_dir),
                },
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue((snapshot_dir / "2026-03-22.json").exists())
            self.assertTrue((snapshot_dir / "versions" / "2026-03-22" / "manifest.json").exists())
            self.assertEqual(response.json()["snapshot_id"], "snap-api-2026-03-22")

    def test_inline_planning_endpoint_runs_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self.create_client(Path(tmp_dir) / "api_runs")
            payload = self.inline_payload()

            first = client.post("/api/v1/planning/run", json=payload)
            second = client.post("/api/v1/planning/run", json=payload)

            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)
            first_payload = first.json()
            second_payload = second.json()
            self.assertEqual(first_payload["status_final"], "concluida")
            self.assertEqual(first_payload["hash_cenario"], second_payload["hash_cenario"])
            self.assertFalse(first_payload["reused_cached_result"])
            self.assertTrue(second_payload["reused_cached_result"])
            self.assertTrue(second_payload["recovered_previous_context"])
            self.assertEqual(first_payload["result"]["resumo_operacional"]["total_rotas"], 1)

    def test_dataset_planning_endpoint_runs_existing_dataset_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            dataset_dir = tmp_path / "dataset"
            dataset_dir.mkdir(parents=True, exist_ok=True)
            self.write_dataset(dataset_dir)
            client = self.create_client(tmp_path / "api_runs")

            response = client.post(
                "/api/v1/planning/run-dataset",
                json={
                    "dataset_dir": str(dataset_dir),
                    "max_iterations": 25,
                    "seed": 1,
                },
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["status_final"], "concluida")
            self.assertEqual(payload["result"]["resumo_operacional"]["total_ordens_planejadas"], 1)
            self.assertTrue(Path(payload["result_path"]).exists())


if __name__ == "__main__":
    unittest.main()

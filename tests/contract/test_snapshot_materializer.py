from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from roteirizacao.application import (
    FileSystemSnapshotRepository,
    JsonFileLogisticsSnapshotSource,
    LogisticsSnapshotMaterializer,
    PersistedSnapshotLogisticsMatrixProvider,
)
from roteirizacao.domain import (
    ClasseOperacional,
    ContextoExecucao,
    Coordenada,
    Criticidade,
    JanelaTempo,
    MetadadoRastreabilidade,
    NoRoteirizacao,
    TipoServico,
    DepositoRoteirizacao,
)


class SnapshotMaterializerContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.context = ContextoExecucao(
            id_execucao="exec-2026-03-21",
            data_operacao=date(2026, 3, 21),
            cutoff=datetime(2026, 3, 20, 18, 0, tzinfo=timezone.utc),
            timestamp_referencia=datetime(2026, 3, 20, 18, 30, tzinfo=timezone.utc),
        )
        self.domain_metadata = MetadadoRastreabilidade(
            id_execucao=self.context.id_execucao,
            origem="snapshot-materializer-test",
            timestamp_referencia=self.context.timestamp_referencia,
            versao_schema="1.0",
            hash_conteudo="test",
        )

    def deposito(self) -> DepositoRoteirizacao:
        return DepositoRoteirizacao(
            id_deposito="dep-BASE-01",
            id_base="BASE-01",
            localizacao=Coordenada(latitude=-23.5505, longitude=-46.6333),
        )

    def no(self) -> NoRoteirizacao:
        return NoRoteirizacao(
            id_no="no-ORD-01",
            id_ordem="ORD-01",
            id_ponto="PONTO-01",
            localizacao=Coordenada(latitude=-23.5489, longitude=-46.6388),
            tipo_servico=TipoServico.SUPRIMENTO,
            classe_operacional=ClasseOperacional.SUPRIMENTO,
            criticidade=Criticidade.ALTA,
            janela_tempo=JanelaTempo(
                inicio=datetime(2026, 3, 21, 9, 0, tzinfo=timezone.utc),
                fim=datetime(2026, 3, 21, 11, 0, tzinfo=timezone.utc),
            ),
            tempo_servico=20,
            demandas={"volume": Decimal("5"), "financeiro": Decimal("15000.00")},
            penalidade_nao_atendimento=Decimal("8000.00"),
            penalidade_atraso=Decimal("500.00"),
            metadados=self.domain_metadata,
        )

    def write_source_snapshot(self, source_dir: Path) -> None:
        payload = {
            "snapshot_id": "snap-source-2026-03-21",
            "generated_at": "2026-03-20T17:00:00+00:00",
            "strategy_name": "real_snapshot_v1",
            "source_name": "arquivo_operacional",
            "arcs": [
                {
                    "id_origem": "no-ORD-01",
                    "id_destino": "dep-BASE-01",
                    "distancia_metros": 2400,
                    "tempo_segundos": 420,
                    "custo": "8.40",
                },
                {
                    "id_origem": "dep-BASE-01",
                    "id_destino": "dep-BASE-01",
                    "distancia_metros": 0,
                    "tempo_segundos": 0,
                    "custo": "0.00",
                },
                {
                    "id_origem": "no-ORD-01",
                    "id_destino": "no-ORD-01",
                    "distancia_metros": 0,
                    "tempo_segundos": 0,
                    "custo": "0.00",
                },
                {
                    "id_origem": "dep-BASE-01",
                    "id_destino": "no-ORD-01",
                    "distancia_metros": 2400,
                    "tempo_segundos": 420,
                    "custo": "8.40",
                },
            ],
        }
        (source_dir / f"{self.context.data_operacao.isoformat()}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
        )

    def test_materializes_current_and_versioned_snapshot_files(self) -> None:
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as snapshot_tmp:
            source_dir = Path(source_tmp)
            snapshot_dir = Path(snapshot_tmp)
            self.write_source_snapshot(source_dir)

            materializer = LogisticsSnapshotMaterializer(
                JsonFileLogisticsSnapshotSource(source_dir),
                FileSystemSnapshotRepository(snapshot_dir),
            )
            result = materializer.materialize(self.context.data_operacao)

            self.assertEqual(result.snapshot_id, "snap-source-2026-03-21")
            self.assertTrue(result.snapshot_path.exists())
            self.assertTrue(result.version_path.exists())
            self.assertTrue(result.manifest_path.exists())

            current_payload = json.loads(result.snapshot_path.read_text())
            manifest_payload = json.loads(result.manifest_path.read_text())

            self.assertEqual(current_payload["schema_version"], "1.0")
            self.assertEqual(current_payload["source_name"], "arquivo_operacional")
            self.assertIn("materialized_at", current_payload)
            self.assertEqual(current_payload["arcs"][0]["id_origem"], "dep-BASE-01")
            self.assertEqual(current_payload["arcs"][-1]["id_origem"], "no-ORD-01")
            self.assertEqual(manifest_payload["latest_snapshot_id"], "snap-source-2026-03-21")
            self.assertEqual(len(manifest_payload["versions"]), 1)
            self.assertEqual(manifest_payload["versions"][0]["content_hash"], result.content_hash)

    def test_persisted_provider_reads_materialized_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as snapshot_tmp:
            source_dir = Path(source_tmp)
            snapshot_dir = Path(snapshot_tmp)
            self.write_source_snapshot(source_dir)

            materializer = LogisticsSnapshotMaterializer(
                JsonFileLogisticsSnapshotSource(source_dir),
                FileSystemSnapshotRepository(snapshot_dir),
            )
            materializer.materialize(self.context.data_operacao)

            provider = PersistedSnapshotLogisticsMatrixProvider(self.context, snapshot_dir=snapshot_dir)
            matriz, eventos = provider.build(
                id_matriz="matrix-materialized-test",
                depositos=[self.deposito()],
                nos=[self.no()],
                metadados=self.domain_metadata,
            )

            trecho = matriz.trecho("dep-BASE-01", "no-ORD-01")
            self.assertEqual(matriz.estrategia_geracao, "real_snapshot_v1")
            self.assertEqual(trecho.distancia_metros, 2400)
            self.assertEqual(trecho.tempo_segundos, 420)
            self.assertEqual(str(trecho.custo), "8.40")
            self.assertEqual(eventos[0].contexto_adicional["snapshot_id"], "snap-source-2026-03-21")


if __name__ == "__main__":
    unittest.main()

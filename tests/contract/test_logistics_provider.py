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
    FallbackLogisticsMatrixProvider,
    LogisticsMatrixBuilder,
    OptimizationInstanceBuilder,
    PersistedSnapshotLogisticsMatrixProvider,
    PreparationPipeline,
)
from roteirizacao.domain import (
    BaseBruta,
    ClasseOperacional,
    ContextoExecucao,
    Coordenada,
    Criticidade,
    JanelaTempo,
    MetadadoIngestao,
    MetadadoRastreabilidade,
    NoRoteirizacao,
    OrdemBruta,
    PontoBruto,
    SeveridadeEvento,
    TipoServico,
    ViaturaBruta,
    DepositoRoteirizacao,
)


def metadata(origin: str, external_id: str) -> MetadadoIngestao:
    return MetadadoIngestao(
        origem=origin,
        timestamp_ingestao=datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc),
        identificador_externo=external_id,
    )


class LogisticsProviderContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.context = ContextoExecucao(
            id_execucao="exec-2026-03-21",
            data_operacao=date(2026, 3, 21),
            cutoff=datetime(2026, 3, 20, 18, 0, tzinfo=timezone.utc),
            timestamp_referencia=datetime(2026, 3, 20, 18, 30, tzinfo=timezone.utc),
        )
        self.domain_metadata = MetadadoRastreabilidade(
            id_execucao=self.context.id_execucao,
            origem="snapshot-test",
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

    def no(self, node_id: str = "no-ORD-01") -> NoRoteirizacao:
        return NoRoteirizacao(
            id_no=node_id,
            id_ordem=node_id.removeprefix("no-"),
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

    def write_snapshot(self, directory: Path, *, node_id: str, distance: int, duration: int, cost: str) -> None:
        payload = {
            "snapshot_id": "snap-2026-03-21",
            "generated_at": "2026-03-20T17:00:00+00:00",
            "strategy_name": "snapshot_json_v1",
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
                    "id_destino": node_id,
                    "distancia_metros": distance,
                    "tempo_segundos": duration,
                    "custo": cost,
                },
                {
                    "id_origem": node_id,
                    "id_destino": "dep-BASE-01",
                    "distancia_metros": distance,
                    "tempo_segundos": duration,
                    "custo": cost,
                },
                {
                    "id_origem": node_id,
                    "id_destino": node_id,
                    "distancia_metros": 0,
                    "tempo_segundos": 0,
                    "custo": "0.00",
                },
            ],
        }
        (directory / f"{self.context.data_operacao.isoformat()}.json").write_text(json.dumps(payload))

    def base_bruta(self) -> BaseBruta:
        return BaseBruta(
            payload={
                "id_base": "BASE-01",
                "nome": "Base Central",
                "latitude": -23.5505,
                "longitude": -46.6333,
                "inicio_operacao": "2026-03-21T06:00:00+00:00",
                "fim_operacao": "2026-03-21T22:00:00+00:00",
                "status_ativo": True,
            },
            metadado_ingestao=metadata("cadastro_bases", "base-01"),
        )

    def ponto_bruto(self) -> PontoBruto:
        return PontoBruto(
            payload={
                "id_ponto": "PONTO-01",
                "tipo_ponto": "agencia",
                "latitude": -23.5489,
                "longitude": -46.6388,
                "setor_geografico": "centro",
                "inicio_janela": "2026-03-21T08:00:00+00:00",
                "fim_janela": "2026-03-21T17:00:00+00:00",
                "tempo_servico": 20,
            },
            metadado_ingestao=metadata("cadastro_pontos", "ponto-01"),
        )

    def viatura_bruta(self) -> ViaturaBruta:
        return ViaturaBruta(
            payload={
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
            },
            metadado_ingestao=metadata("cadastro_frota", "viatura-01"),
        )

    def ordem_bruta(self, **overrides: object) -> OrdemBruta:
        payload = {
            "id_ordem": "ORD-SNAP",
            "origem_ordem": "erp",
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
            "penalidade_nao_atendimento": "8000.00",
            "penalidade_atraso": "500.00",
            "status_cancelamento": "nao_cancelada",
            "taxa_improdutiva": "0",
        }
        payload.update(overrides)
        return OrdemBruta(payload=payload, metadado_ingestao=metadata("ordens_dia", str(payload["id_ordem"])))

    def test_loads_persisted_snapshot_for_requested_locations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            self.write_snapshot(tmp_path, node_id="no-ORD-01", distance=4321, duration=777, cost="12.34")
            provider = PersistedSnapshotLogisticsMatrixProvider(self.context, snapshot_dir=tmp_path)

            matriz, eventos = provider.build(
                id_matriz="matrix-provider-test",
                depositos=[self.deposito()],
                nos=[self.no()],
                metadados=self.domain_metadata,
            )

            self.assertEqual(matriz.estrategia_geracao, "snapshot_json_v1")
            self.assertEqual(matriz.trecho("dep-BASE-01", "no-ORD-01").distancia_metros, 4321)
            self.assertEqual(matriz.trecho("dep-BASE-01", "no-ORD-01").tempo_segundos, 777)
            self.assertEqual(str(matriz.trecho("dep-BASE-01", "no-ORD-01").custo), "12.34")
            self.assertEqual(eventos[0].contexto_adicional["fonte"], "snapshot_persistido")
            self.assertTrue(matriz.hash_matriz)

    def test_falls_back_to_geometric_builder_when_snapshot_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            provider = FallbackLogisticsMatrixProvider(
                self.context,
                primary=PersistedSnapshotLogisticsMatrixProvider(self.context, snapshot_dir=Path(tmp_dir)),
                fallback=LogisticsMatrixBuilder(self.context),
            )

            matriz, eventos = provider.build(
                id_matriz="matrix-provider-fallback",
                depositos=[self.deposito()],
                nos=[self.no()],
                metadados=self.domain_metadata,
            )

            self.assertEqual(matriz.estrategia_geracao, "haversine_v1")
            self.assertEqual(eventos[0].severidade, SeveridadeEvento.AVISO)
            self.assertEqual(eventos[0].contexto_adicional["fonte"], "fallback_builder_local")
            self.assertTrue(any(event.contexto_adicional and event.contexto_adicional.get("fonte") == "builder_local" for event in eventos[1:]))

    def test_instance_builder_uses_snapshot_provider_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            self.write_snapshot(tmp_path, node_id="no-ORD-SNAP", distance=2500, duration=480, cost="9.99")
            provider = FallbackLogisticsMatrixProvider(
                self.context,
                primary=PersistedSnapshotLogisticsMatrixProvider(self.context, snapshot_dir=tmp_path),
                fallback=LogisticsMatrixBuilder(self.context),
            )
            pipeline = PreparationPipeline(self.context)
            builder = OptimizationInstanceBuilder(self.context, matrix_provider=provider)
            preparation = pipeline.run(
                bases_brutas=[self.base_bruta()],
                pontos_brutos=[self.ponto_bruto()],
                viaturas_brutas=[self.viatura_bruta()],
                ordens_brutas=[self.ordem_bruta()],
            )

            result = builder.build(preparation)
            instancia = result.instancias[ClasseOperacional.SUPRIMENTO]

            self.assertEqual(instancia.matriz_logistica.estrategia_geracao, "snapshot_json_v1")
            self.assertEqual(instancia.matriz_logistica.trecho("dep-BASE-01", "no-ORD-SNAP").distancia_metros, 2500)
            self.assertEqual(instancia.parametros_construcao["estrategia_matriz"], "snapshot_json_v1")
            self.assertTrue(any(event.contexto_adicional and event.contexto_adicional.get("fonte") == "snapshot_persistido" for event in result.eventos_auditoria))


if __name__ == "__main__":
    unittest.main()

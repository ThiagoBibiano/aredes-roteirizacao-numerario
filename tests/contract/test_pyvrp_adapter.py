from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from roteirizacao.application import OptimizationInstanceBuilder, PreparationPipeline
from roteirizacao.domain import (
    BaseBruta,
    ClasseOperacional,
    ContextoExecucao,
    MetadadoIngestao,
    OrdemBruta,
    PontoBruto,
    ViaturaBruta,
)
from roteirizacao.optimization import PyVRPAdapter


def metadata(origin: str, external_id: str) -> MetadadoIngestao:
    return MetadadoIngestao(
        origem=origin,
        timestamp_ingestao=datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc),
        identificador_externo=external_id,
    )


class PyVRPAdapterContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.context = ContextoExecucao(
            id_execucao="exec-2026-03-21",
            data_operacao=date(2026, 3, 21),
            cutoff=datetime(2026, 3, 20, 18, 0, tzinfo=timezone.utc),
            timestamp_referencia=datetime(2026, 3, 20, 18, 30, tzinfo=timezone.utc),
        )
        self.pipeline = PreparationPipeline(self.context)
        self.builder = OptimizationInstanceBuilder(self.context)
        self.adapter = PyVRPAdapter()

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
            "id_ordem": "ORD-01",
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

    def build_instance(self, order: OrdemBruta, *, tipo: ClasseOperacional) -> object:
        preparation = self.pipeline.run(
            bases_brutas=[self.base_bruta()],
            pontos_brutos=[self.ponto_bruto()],
            viaturas_brutas=[self.viatura_bruta()],
            ordens_brutas=[order],
        )
        result = self.builder.build(preparation)
        return result.instancias[tipo]

    def test_maps_supply_instance_to_delivery_payload(self) -> None:
        instancia = self.build_instance(self.ordem_bruta(tipo_servico="suprimento"), tipo=ClasseOperacional.SUPRIMENTO)
        payload = self.adapter.build_payload(instancia)

        self.assertEqual(payload.profile_name, "suprimento")
        self.assertEqual(len(payload.depots), 1)
        self.assertEqual(len(payload.clients), 1)
        self.assertEqual(payload.clients[0].delivery, (500, 1500000))
        self.assertEqual(payload.clients[0].pickup, (0, 0))
        self.assertEqual(payload.clients[0].prize, 800000)
        self.assertFalse(payload.clients[0].required)

    def test_maps_recolhimento_instance_to_pickup_payload(self) -> None:
        instancia = self.build_instance(self.ordem_bruta(id_ordem="ORD-REC", tipo_servico="recolhimento"), tipo=ClasseOperacional.RECOLHIMENTO)
        payload = self.adapter.build_payload(instancia)

        self.assertEqual(payload.profile_name, "recolhimento")
        self.assertEqual(payload.clients[0].delivery, (0, 0))
        self.assertEqual(payload.clients[0].pickup, (500, 1500000))
        self.assertEqual(payload.vehicle_types[0].capacity, (2000, 8000000))

    def test_uses_logistics_matrix_edges_and_metadata(self) -> None:
        instancia = self.build_instance(self.ordem_bruta(tipo_servico="suprimento"), tipo=ClasseOperacional.SUPRIMENTO)
        payload = self.adapter.build_payload(instancia)
        trecho = instancia.matriz_logistica.trecho("dep-BASE-01", "no-ORD-01")
        edge_map = {(edge.frm, edge.to): edge for edge in payload.edges}

        self.assertEqual(payload.metadata["hash_matriz"], instancia.matriz_logistica.hash_matriz)
        self.assertEqual(payload.metadata["estrategia_matriz"], "haversine_v1")
        self.assertEqual(len(payload.edges), len(instancia.matriz_logistica.trechos))
        self.assertIn((0, 1), edge_map)
        self.assertEqual(edge_map[(0, 1)].distance, trecho.distancia_metros)
        self.assertEqual(edge_map[(0, 1)].duration, trecho.tempo_segundos)

    def test_time_windows_are_relative_to_common_origin(self) -> None:
        instancia = self.build_instance(self.ordem_bruta(tipo_servico="suprimento"), tipo=ClasseOperacional.SUPRIMENTO)
        payload = self.adapter.build_payload(instancia)

        self.assertEqual(payload.vehicle_types[0].tw_early, 0)
        self.assertGreater(payload.vehicle_types[0].tw_late, payload.vehicle_types[0].tw_early)
        self.assertGreaterEqual(payload.clients[0].tw_early, 0)
        self.assertGreater(payload.clients[0].tw_late, payload.clients[0].tw_early)

    def test_build_model_requires_pyvrp_when_library_is_missing(self) -> None:
        instancia = self.build_instance(self.ordem_bruta(tipo_servico="suprimento"), tipo=ClasseOperacional.SUPRIMENTO)
        has_pyvrp = importlib.util.find_spec("pyvrp") is not None

        if has_pyvrp:
            model = self.adapter.build_model(instancia)
            self.assertIsNotNone(model)
        else:
            with self.assertRaises(ModuleNotFoundError):
                self.adapter.build_model(instancia)


if __name__ == "__main__":
    unittest.main()

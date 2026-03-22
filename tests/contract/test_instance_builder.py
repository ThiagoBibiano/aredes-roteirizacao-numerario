from __future__ import annotations

import sys
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
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
    TipoEventoAuditoria,
    ViaturaBruta,
)


def metadata(origin: str, external_id: str) -> MetadadoIngestao:
    return MetadadoIngestao(
        origem=origin,
        timestamp_ingestao=datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc),
        identificador_externo=external_id,
    )


class InstanceBuilderContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.context = ContextoExecucao(
            id_execucao="exec-2026-03-21",
            data_operacao=date(2026, 3, 21),
            cutoff=datetime(2026, 3, 20, 18, 0, tzinfo=timezone.utc),
            timestamp_referencia=datetime(2026, 3, 20, 18, 30, tzinfo=timezone.utc),
        )
        self.pipeline = PreparationPipeline(self.context)
        self.builder = OptimizationInstanceBuilder(self.context)

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

    def viatura_bruta(self, **overrides: object) -> ViaturaBruta:
        payload = {
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
        }
        payload.update(overrides)
        return ViaturaBruta(payload=payload, metadado_ingestao=metadata("cadastro_frota", str(payload["id_viatura"])))

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

    def prepare(self, orders: list[OrdemBruta], vehicles: list[ViaturaBruta] | None = None):
        return self.pipeline.run(
            bases_brutas=[self.base_bruta()],
            pontos_brutos=[self.ponto_bruto()],
            viaturas_brutas=vehicles or [self.viatura_bruta()],
            ordens_brutas=orders,
        )

    def test_builds_separate_instances_per_operational_class(self) -> None:
        preparation = self.prepare(
            [
                self.ordem_bruta(id_ordem="ORD-SUP", tipo_servico="suprimento"),
                self.ordem_bruta(id_ordem="ORD-REC", tipo_servico="recolhimento"),
            ]
        )

        result = self.builder.build(preparation)

        self.assertFalse(result.possui_erros)
        self.assertEqual(set(result.instancias), {ClasseOperacional.SUPRIMENTO, ClasseOperacional.RECOLHIMENTO})
        self.assertEqual(len(result.instancias[ClasseOperacional.SUPRIMENTO].nos_atendimento), 1)
        self.assertEqual(len(result.instancias[ClasseOperacional.RECOLHIMENTO].nos_atendimento), 1)

    def test_recolhimento_instance_uses_financial_dimension_limited_by_insurance(self) -> None:
        preparation = self.prepare([
            self.ordem_bruta(id_ordem="ORD-REC", tipo_servico="recolhimento", valor_estimado="20000.00")
        ])

        result = self.builder.build(preparation)
        instancia = result.instancias[ClasseOperacional.RECOLHIMENTO]
        veiculo = instancia.veiculos[0]

        self.assertEqual(instancia.dimensoes_capacidade, ("volume", "financeiro"))
        self.assertEqual(str(veiculo.capacidades["financeiro"]), "80000.00")
        self.assertIn("teto_segurado_aplicado", instancia.restricoes_extras)
        self.assertTrue(instancia.parametros_construcao["requires_financial_accretion"])

    def test_cancelled_or_excluded_orders_do_not_enter_instance(self) -> None:
        preparation = self.prepare(
            [
                self.ordem_bruta(id_ordem="ORD-OK", tipo_servico="suprimento"),
                self.ordem_bruta(
                    id_ordem="ORD-CANCEL",
                    tipo_servico="suprimento",
                    status_cancelamento="cancelada_antes_cutoff",
                    instante_cancelamento="2026-03-20T10:00:00+00:00",
                ),
            ]
        )

        result = self.builder.build(preparation)
        instancia = result.instancias[ClasseOperacional.SUPRIMENTO]

        self.assertEqual(len(instancia.nos_atendimento), 1)
        self.assertEqual(instancia.nos_atendimento[0].id_ordem, "ORD-OK")

    def test_marks_vehicle_node_ineligibility_explicitly(self) -> None:
        preparation = self.prepare(
            [self.ordem_bruta(id_ordem="ORD-SETOR", tipo_servico="suprimento")],
            vehicles=[
                self.viatura_bruta(id_viatura="VTR-OK", compatibilidade_setor=["centro"]),
                self.viatura_bruta(id_viatura="VTR-NOK", compatibilidade_setor=["zona_sul"]),
            ],
        )

        result = self.builder.build(preparation)
        instancia = result.instancias[ClasseOperacional.SUPRIMENTO]
        eligibilidade = {item.id_veiculo: item for item in instancia.elegibilidade_veiculo_no}

        self.assertTrue(eligibilidade["veh-VTR-OK-suprimento"].elegivel)
        self.assertFalse(eligibilidade["veh-VTR-NOK-suprimento"].elegivel)
        self.assertIn("setor_incompativel", eligibilidade["veh-VTR-NOK-suprimento"].motivo)

    def test_returns_error_when_no_vehicle_is_eligible(self) -> None:
        preparation = self.prepare(
            [self.ordem_bruta(id_ordem="ORD-REC", tipo_servico="recolhimento")],
            vehicles=[self.viatura_bruta(id_viatura="VTR-SUP", compatibilidade_servico=["suprimento"])],
        )

        result = self.builder.build(preparation)

        self.assertTrue(result.possui_erros)
        self.assertNotIn(ClasseOperacional.RECOLHIMENTO, result.instancias)
        self.assertTrue(any(error.codigo_regra == "negocio.inviabilidade_operacional" for error in result.erros))

    def test_instance_has_hash_penalties_matrix_and_build_audit_events(self) -> None:
        preparation = self.prepare([
            self.ordem_bruta(id_ordem="ORD-HASH", tipo_servico="suprimento")
        ])

        result = self.builder.build(preparation)
        instancia = result.instancias[ClasseOperacional.SUPRIMENTO]
        matriz = instancia.matriz_logistica
        trecho_saida = matriz.trecho("dep-BASE-01", "no-ORD-HASH")
        trecho_retorno = matriz.trecho("no-ORD-HASH", "dep-BASE-01")

        self.assertIsNotNone(instancia.hash_cenario)
        self.assertIsNotNone(matriz.hash_matriz)
        self.assertEqual(len(instancia.penalidades), 2)
        self.assertEqual(matriz.ids_localizacao, ("dep-BASE-01", "no-ORD-HASH"))
        self.assertEqual(matriz.trecho("dep-BASE-01", "dep-BASE-01").distancia_metros, 0)
        self.assertGreater(trecho_saida.distancia_metros or 0, 0)
        self.assertGreater(trecho_saida.tempo_segundos or 0, 0)
        self.assertEqual(trecho_saida.distancia_metros, trecho_retorno.distancia_metros)
        self.assertEqual(instancia.custos_por_arco["dep-BASE-01->no-ORD-HASH"], trecho_saida.custo)
        self.assertTrue(any(event.tipo_evento == TipoEventoAuditoria.CONSTRUCAO_INSTANCIA for event in result.eventos_auditoria))
        self.assertTrue(any(event.entidade_afetada == "MatrizLogistica" for event in result.eventos_auditoria))
        self.assertEqual(instancia.parametros_construcao["estrategia_matriz"], "haversine_v1")
        self.assertEqual(instancia.parametros_construcao["hash_matriz"], matriz.hash_matriz)
        self.assertIsInstance(instancia.custos_por_arco["dep-BASE-01->no-ORD-HASH"], Decimal)


if __name__ == "__main__":
    unittest.main()

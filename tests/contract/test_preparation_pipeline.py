from __future__ import annotations

import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from roteirizacao.application import PreparationPipeline
from roteirizacao.domain import (
    BaseBruta,
    ClasseOperacional,
    ContextoExecucao,
    MetadadoIngestao,
    OrdemBruta,
    PontoBruto,
    StatusOrdem,
    TipoEventoAuditoria,
    TipoServico,
    ViaturaBruta,
)


def metadata(origin: str, external_id: str) -> MetadadoIngestao:
    return MetadadoIngestao(
        origem=origin,
        timestamp_ingestao=datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc),
        identificador_externo=external_id,
    )


class PreparationPipelineContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.context = ContextoExecucao(
            id_execucao="exec-2026-03-21",
            data_operacao=date(2026, 3, 21),
            cutoff=datetime(2026, 3, 20, 18, 0, tzinfo=timezone.utc),
            timestamp_referencia=datetime(2026, 3, 20, 18, 30, tzinfo=timezone.utc),
        )
        self.pipeline = PreparationPipeline(self.context)

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
                "teto_segurado": "120000.00",
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

    def run_pipeline(self, *orders: OrdemBruta):
        return self.pipeline.run(
            bases_brutas=[self.base_bruta()],
            pontos_brutos=[self.ponto_bruto()],
            viaturas_brutas=[self.viatura_bruta()],
            ordens_brutas=list(orders),
        )

    def test_happy_path_generates_plannable_order(self) -> None:
        result = self.run_pipeline(self.ordem_bruta())

        self.assertFalse(result.possui_erros)
        self.assertEqual(len(result.bases), 1)
        self.assertEqual(len(result.pontos), 1)
        self.assertEqual(len(result.viaturas), 1)
        self.assertEqual(len(result.ordens_validadas), 1)
        self.assertEqual(len(result.ordens_planejaveis), 1)
        self.assertEqual(result.ordens_planejaveis[0].status_ordem, StatusOrdem.PLANEJAVEL)
        self.assertEqual(result.ordens_planejaveis[0].ordem.classe_operacional, ClasseOperacional.SUPRIMENTO)

    def test_missing_required_field_creates_schema_error(self) -> None:
        result = self.run_pipeline(self.ordem_bruta(id_ordem="", id_ponto=""))

        self.assertTrue(result.possui_erros)
        self.assertEqual(len(result.ordens_validadas), 0)
        self.assertTrue(any(error.codigo_erro == "schema.obrigatorio_ausente" for error in result.erros if hasattr(error, "codigo_erro")))

    def test_negative_penalty_creates_domain_validation_error(self) -> None:
        result = self.run_pipeline(self.ordem_bruta(penalidade_nao_atendimento="-1"))

        self.assertTrue(result.possui_erros)
        self.assertEqual(len(result.ordens_validadas), 0)
        self.assertTrue(any(getattr(error, "codigo_regra", "") == "dominio.invariante_violada" for error in result.erros))

    def test_cancelled_before_cutoff_becomes_excluded(self) -> None:
        result = self.run_pipeline(
            self.ordem_bruta(
                id_ordem="ORD-02",
                status_cancelamento="cancelada_antes_cutoff",
                instante_cancelamento="2026-03-20T10:00:00+00:00",
            )
        )

        self.assertFalse(result.possui_erros)
        self.assertEqual(len(result.ordens_excluidas), 1)
        self.assertEqual(result.ordens_excluidas[0].status_ordem, StatusOrdem.EXCLUIDA)
        self.assertTrue(any(event.tipo_evento == TipoEventoAuditoria.EXCLUSAO for event in result.eventos_auditoria))

    def test_cancelled_after_cutoff_generates_impact_and_audit(self) -> None:
        result = self.run_pipeline(
            self.ordem_bruta(
                id_ordem="ORD-03",
                tipo_servico="recolhimento",
                status_cancelamento="cancelada_com_parada_improdutiva",
                instante_cancelamento="2026-03-20T19:30:00+00:00",
                taxa_improdutiva="350.00",
            )
        )

        self.assertFalse(result.possui_erros)
        self.assertEqual(len(result.ordens_canceladas), 1)
        ordem = result.ordens_canceladas[0]
        self.assertEqual(ordem.status_ordem, StatusOrdem.CANCELADA)
        self.assertEqual(str(ordem.impacto_financeiro_previsto), "350.00")
        self.assertEqual(ordem.impacto_operacional, "parada_improdutiva")
        self.assertTrue(any(event.tipo_evento == TipoEventoAuditoria.CANCELAMENTO for event in result.eventos_auditoria))

    def test_special_service_alias_is_normalized_to_extraordinary(self) -> None:
        result = self.run_pipeline(
            self.ordem_bruta(
                id_ordem="ORD-04",
                tipo_servico="especial",
                classe_planejamento="especial",
                classe_operacional="recolhimento",
            )
        )

        self.assertFalse(result.possui_erros)
        self.assertEqual(result.ordens_planejaveis[0].ordem.tipo_servico, TipoServico.EXTRAORDINARIO)
        self.assertEqual(result.ordens_planejaveis[0].ordem.classe_operacional, ClasseOperacional.RECOLHIMENTO)
        self.assertTrue(
            any(
                event.regra_relacionada == "alias.tipo_servico"
                for event in result.eventos_auditoria
            )
        )

    def test_orders_are_grouped_by_operational_class(self) -> None:
        result = self.run_pipeline(
            self.ordem_bruta(id_ordem="ORD-05", tipo_servico="suprimento"),
            self.ordem_bruta(id_ordem="ORD-06", tipo_servico="recolhimento"),
        )

        grouped = result.ordens_por_classe_operacional()

        self.assertIn("suprimento", grouped)
        self.assertIn("recolhimento", grouped)
        self.assertEqual(len(grouped["suprimento"]), 1)
        self.assertEqual(len(grouped["recolhimento"]), 1)

    def test_serialization_of_validated_entities_is_stable(self) -> None:
        result = self.run_pipeline(self.ordem_bruta())

        base_dict = result.bases[0].to_dict()
        ordem_dict = result.ordens_planejaveis[0].to_dict()

        self.assertEqual(base_dict["id_base"], "BASE-01")
        self.assertEqual(ordem_dict["ordem"]["id_ordem"], "ORD-01")
        self.assertEqual(ordem_dict["ordem"]["tipo_servico"], "suprimento")
        self.assertEqual(ordem_dict["status_ordem"], "planejavel")


if __name__ == "__main__":
    unittest.main()

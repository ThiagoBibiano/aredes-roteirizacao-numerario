from __future__ import annotations

import sys
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from roteirizacao.application import OptimizationInstanceBuilder, PlanningExecutor, PreparationPipeline
from roteirizacao.domain import (
    BaseBruta,
    ClasseOperacional,
    ContextoExecucao,
    MetadadoIngestao,
    OrdemBruta,
    PontoBruto,
    StatusExecucaoPlanejamento,
    TipoEventoAuditoria,
    ViaturaBruta,
)


def metadata(origin: str, external_id: str) -> MetadadoIngestao:
    return MetadadoIngestao(
        origem=origin,
        timestamp_ingestao=datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc),
        identificador_externo=external_id,
    )


class PlanningExecutorContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.context = ContextoExecucao(
            id_execucao="exec-2026-03-21",
            data_operacao=date(2026, 3, 21),
            cutoff=datetime(2026, 3, 20, 18, 0, tzinfo=timezone.utc),
            timestamp_referencia=datetime(2026, 3, 20, 18, 30, tzinfo=timezone.utc),
        )
        self.pipeline = PreparationPipeline(self.context)
        self.builder = OptimizationInstanceBuilder(self.context)
        self.executor = PlanningExecutor(self.context, max_iterations=25, seed=1)

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

    def ponto_bruto(self, point_id: str = "PONTO-01", *, latitude: float = -23.5489, longitude: float = -46.6388) -> PontoBruto:
        return PontoBruto(
            payload={
                "id_ponto": point_id,
                "tipo_ponto": "agencia",
                "latitude": latitude,
                "longitude": longitude,
                "setor_geografico": "centro",
                "inicio_janela": "2026-03-21T08:00:00+00:00",
                "fim_janela": "2026-03-21T17:00:00+00:00",
                "tempo_servico": 20,
            },
            metadado_ingestao=metadata("cadastro_pontos", point_id.lower()),
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

    def execute(self, *, pontos: list[PontoBruto], ordens: list[OrdemBruta]):
        preparation = self.pipeline.run(
            bases_brutas=[self.base_bruta()],
            pontos_brutos=pontos,
            viaturas_brutas=[self.viatura_bruta()],
            ordens_brutas=ordens,
        )
        instance_result = self.builder.build(preparation)
        return self.executor.run(preparation, instance_result)

    def test_builds_planned_routes_for_each_operational_class(self) -> None:
        resultado = self.execute(
            pontos=[self.ponto_bruto()],
            ordens=[
                self.ordem_bruta(id_ordem="ORD-SUP", tipo_servico="suprimento"),
                self.ordem_bruta(
                    id_ordem="ORD-REC",
                    tipo_servico="recolhimento",
                    valor_estimado="80000.00",
                    volume_estimado="4",
                    penalidade_nao_atendimento="12000.00",
                ),
            ],
        )

        self.assertEqual(resultado.status_final, StatusExecucaoPlanejamento.CONCLUIDA)
        self.assertEqual(len(resultado.rotas_suprimento), 1)
        self.assertEqual(len(resultado.rotas_recolhimento), 1)
        self.assertEqual(resultado.rotas_suprimento[0].paradas[0].id_ordem, "ORD-SUP")
        self.assertEqual(resultado.rotas_recolhimento[0].paradas[0].id_ordem, "ORD-REC")
        self.assertTrue(resultado.rotas_recolhimento[0].atingiu_limite_segurado)
        self.assertEqual(resultado.resumo_operacional.total_rotas, 2)
        self.assertEqual(resultado.resumo_operacional.total_ordens_planejadas, 2)
        self.assertEqual(resultado.kpi_operacional.taxa_atendimento, Decimal("1.0000"))
        self.assertEqual(resultado.kpi_operacional.utilizacao_frota, Decimal("1.0000"))
        self.assertFalse(resultado.ordens_nao_atendidas)

    def test_marks_low_penalty_order_as_not_attended(self) -> None:
        resultado = self.execute(
            pontos=[self.ponto_bruto(point_id="PONTO-LONGE", latitude=-23.0000, longitude=-45.0000)],
            ordens=[
                self.ordem_bruta(
                    id_ordem="ORD-LOW",
                    id_ponto="PONTO-LONGE",
                    penalidade_nao_atendimento="1.00",
                )
            ],
        )

        self.assertEqual(resultado.status_final, StatusExecucaoPlanejamento.CONCLUIDA_COM_RESSALVAS)
        self.assertEqual(len(resultado.rotas_suprimento), 0)
        self.assertEqual(len(resultado.ordens_nao_atendidas), 1)
        self.assertEqual(resultado.ordens_nao_atendidas[0].id_ordem, "ORD-LOW")
        self.assertEqual(resultado.kpi_gerencial.penalidade_total_nao_atendimento, Decimal("1.00"))
        self.assertEqual(resultado.kpi_operacional.taxa_atendimento, Decimal("0.0000"))

    def test_consolidates_audit_events_and_hashes(self) -> None:
        resultado = self.execute(
            pontos=[self.ponto_bruto()],
            ordens=[self.ordem_bruta(id_ordem="ORD-AUD")],
        )

        tipos_evento = {evento.tipo_evento for evento in resultado.eventos_auditoria}
        self.assertIn(TipoEventoAuditoria.ROTEIRIZACAO, tipos_evento)
        self.assertIn(TipoEventoAuditoria.SAIDA, tipos_evento)
        self.assertIn(ClasseOperacional.SUPRIMENTO.value, resultado.hashes_cenario)
        self.assertTrue(resultado.hashes_cenario[ClasseOperacional.SUPRIMENTO.value])
        self.assertEqual(resultado.rotas_suprimento[0].paradas[0].carga_acumulada["volume"], Decimal("5"))
        self.assertEqual(resultado.rotas_suprimento[0].paradas[0].carga_acumulada["financeiro"], Decimal("15000.00"))
        self.assertIsNotNone(resultado.rotas_suprimento[0].paradas[0].inicio_previsto.tzinfo)


if __name__ == "__main__":
    unittest.main()

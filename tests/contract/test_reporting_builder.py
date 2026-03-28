from __future__ import annotations

import sys
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from roteirizacao.application import (
    OptimizationInstanceBuilder,
    PlanningAuditTrailBuilder,
    PlanningReportingBuilder,
    PreparationPipeline,
    RoutePostProcessor,
    SolverExecutionArtifact,
)
from roteirizacao.domain import BaseBruta, ClasseOperacional, ContextoExecucao, MetadadoIngestao, OrdemBruta, PontoBruto, StatusExecucaoPlanejamento, ViaturaBruta
from roteirizacao.optimization import PyVRPAdapter

try:
    import pyvrp  # noqa: F401
except Exception:  # pragma: no cover - environment-dependent branch
    PYVRP_AVAILABLE = False
else:
    PYVRP_AVAILABLE = True


def metadata(origin: str, external_id: str) -> MetadadoIngestao:
    return MetadadoIngestao(
        origem=origin,
        timestamp_ingestao=datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc),
        identificador_externo=external_id,
    )


class ReportingBuilderContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.context = ContextoExecucao(
            id_execucao="exec-2026-03-21",
            data_operacao=date(2026, 3, 21),
            cutoff=datetime(2026, 3, 20, 18, 0, tzinfo=timezone.utc),
            timestamp_referencia=datetime(2026, 3, 20, 18, 30, tzinfo=timezone.utc),
        )
        self.pipeline = PreparationPipeline(self.context)
        self.instance_builder = OptimizationInstanceBuilder(self.context)
        self.post_processor = RoutePostProcessor(self.context)
        self.audit_builder = PlanningAuditTrailBuilder(self.context)
        self.reporting_builder = PlanningReportingBuilder(self.context)
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
            "penalidade_nao_atendimento": "20000.00",
            "penalidade_atraso": "500.00",
            "status_cancelamento": "nao_cancelada",
            "taxa_improdutiva": "0",
        }
        payload.update(overrides)
        return OrdemBruta(payload=payload, metadado_ingestao=metadata("ordens_dia", str(payload["id_ordem"])))

    @unittest.skipUnless(PYVRP_AVAILABLE, "pyvrp nao instalado no ambiente")
    def test_consolidates_kpis_and_business_report(self) -> None:
        preparation = self.pipeline.run(
            bases_brutas=[self.base_bruta()],
            pontos_brutos=[self.ponto_bruto()],
            viaturas_brutas=[self.viatura_bruta()],
            ordens_brutas=[
                self.ordem_bruta(id_ordem="ORD-SUP", tipo_servico="suprimento", classe_planejamento="padrao"),
                self.ordem_bruta(
                    id_ordem="ORD-REC-ESP",
                    tipo_servico="recolhimento",
                    classe_planejamento="especial",
                    timestamp_criacao="2026-03-21T07:30:00+00:00",
                    valor_estimado="80000.00",
                    volume_estimado="4",
                ),
            ],
        )
        instance_result = self.instance_builder.build(preparation)
        eventos = list(preparation.eventos_auditoria)
        eventos.extend(instance_result.eventos_auditoria)
        artifacts: list[SolverExecutionArtifact] = []
        hashes_cenario = {classe.value: instancia.hash_cenario or "" for classe, instancia in instance_result.instancias.items()}

        for instancia in instance_result.instancias.values():
            payload = self.adapter.build_payload(instancia)
            model = self.adapter.build_model(instancia)
            solver_result = model.solve(pyvrp.stop.MaxIterations(25), seed=1, collect_stats=False, display=False)
            artifacts.append(SolverExecutionArtifact(instancia=instancia, payload=payload, solver_result=solver_result))

        post_processing = self.post_processor.consolidate(
            preparation,
            [self.post_processor.process_execution(artifact) for artifact in artifacts],
        )
        eventos.extend(post_processing.eventos)
        status_final = StatusExecucaoPlanejamento.CONCLUIDA
        audit = self.audit_builder.build(
            status_final=status_final,
            eventos_existentes=eventos,
            erros=[],
            preparation_result=preparation,
            ordens_nao_atendidas=post_processing.ordens_nao_atendidas,
            hashes_cenario=hashes_cenario,
            parametros_planejamento={"seed": 1, "max_iterations": 25},
        )
        reporting = self.reporting_builder.build(
            status_final=status_final,
            preparation_result=preparation,
            rotas_por_classe=post_processing.rotas_por_classe,
            ordens_nao_atendidas=post_processing.ordens_nao_atendidas,
            eventos_auditoria=audit.eventos_auditoria,
            motivos_inviabilidade=audit.motivos_inviabilidade,
        )

        self.assertEqual(reporting.kpi_operacional.total_ordens_atendidas, 2)
        self.assertEqual(reporting.kpi_operacional.total_ordens_especiais_atendidas, 1)
        self.assertEqual(reporting.kpi_operacional.viaturas_acionadas, 1)
        self.assertEqual(reporting.kpi_operacional.rotas_com_limite_segurado, 1)
        self.assertGreater(reporting.kpi_operacional.tempo_total_servico_segundos, 0)
        self.assertGreater(reporting.kpi_gerencial.custo_total_estimado, Decimal("0"))
        self.assertEqual(reporting.relatorio_planejamento.total_eventos_auditoria, len(audit.eventos_auditoria))
        self.assertIn("suprimento", reporting.relatorio_planejamento.classes_processadas)
        self.assertIn("recolhimento", reporting.relatorio_planejamento.classes_processadas)
        self.assertIn("ha_rotas_no_limite_segurado", reporting.relatorio_planejamento.destaques)

    def test_counts_cancellations_and_exclusions_in_indicators(self) -> None:
        preparation = self.pipeline.run(
            bases_brutas=[self.base_bruta()],
            pontos_brutos=[self.ponto_bruto()],
            viaturas_brutas=[self.viatura_bruta()],
            ordens_brutas=[
                self.ordem_bruta(
                    id_ordem="ORD-EXC",
                    status_cancelamento="cancelada_antes_cutoff",
                    instante_cancelamento="2026-03-20T17:00:00+00:00",
                ),
                self.ordem_bruta(
                    id_ordem="ORD-CANC",
                    status_cancelamento="cancelada_apos_cutoff",
                    instante_cancelamento="2026-03-20T19:00:00+00:00",
                    taxa_improdutiva="250.00",
                ),
            ],
        )
        audit = self.audit_builder.build(
            status_final=StatusExecucaoPlanejamento.CONCLUIDA,
            eventos_existentes=preparation.eventos_auditoria,
            erros=preparation.erros,
            preparation_result=preparation,
            ordens_nao_atendidas=[],
            hashes_cenario={},
            parametros_planejamento={"seed": 1, "max_iterations": 25},
        )
        reporting = self.reporting_builder.build(
            status_final=StatusExecucaoPlanejamento.CONCLUIDA,
            preparation_result=preparation,
            rotas_por_classe={ClasseOperacional.SUPRIMENTO: [], ClasseOperacional.RECOLHIMENTO: []},
            ordens_nao_atendidas=[],
            eventos_auditoria=audit.eventos_auditoria,
            motivos_inviabilidade=audit.motivos_inviabilidade,
        )

        self.assertEqual(reporting.kpi_operacional.total_paradas_improdutivas, 1)
        self.assertEqual(reporting.kpi_operacional.total_ordens_excluidas_por_restricao, 1)
        self.assertEqual(reporting.kpi_gerencial.impacto_financeiro_cancelamentos, Decimal("250.00"))
        self.assertEqual(reporting.kpi_gerencial.valor_total_taxas_improdutivas, Decimal("250.00"))
        self.assertIn("ha_cancelamentos_com_impacto", reporting.relatorio_planejamento.destaques)
        self.assertIn("ha_ordens_excluidas_antes_do_planejamento", reporting.relatorio_planejamento.destaques)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from roteirizacao.application import OptimizationInstanceBuilder, PlanningExecutor, PreparationPipeline
from roteirizacao.domain import (
    BaseBruta,
    ContextoExecucao,
    MetadadoIngestao,
    OrdemBruta,
    PontoBruto,
    StatusExecucaoPlanejamento,
    TipoEventoAuditoria,
    ViaturaBruta,
)
from roteirizacao.optimization import PyVRPAdapter

try:
    import pyvrp  # noqa: F401
except Exception:  # pragma: no cover - environment-dependent branch
    PYVRP_AVAILABLE = False
else:
    PYVRP_AVAILABLE = True


class FailingAdapter(PyVRPAdapter):
    def build_model(self, instancia):  # type: ignore[override]
        raise RuntimeError("solver boom")


def metadata(origin: str, external_id: str) -> MetadadoIngestao:
    return MetadadoIngestao(
        origem=origin,
        timestamp_ingestao=datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc),
        identificador_externo=external_id,
    )


class AuditTrailContractTest(unittest.TestCase):
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
        return OrdemBruta(payload=payload, metadado_ingestao=metadata("ordens_dia", str(payload.get("id_ordem", "ordem"))))

    def execute(self, *, ordens: list[OrdemBruta], adapter=None, seed: int = 1, max_iterations: int = 25):
        preparation = self.pipeline.run(
            bases_brutas=[self.base_bruta()],
            pontos_brutos=[self.ponto_bruto()],
            viaturas_brutas=[self.viatura_bruta()],
            ordens_brutas=ordens,
        )
        instance_result = self.builder.build(preparation)
        executor = PlanningExecutor(
            self.context,
            adapter=adapter,
            seed=seed,
            max_iterations=max_iterations,
        )
        return executor.run(preparation, instance_result)

    def test_invalid_order_generates_audit_event(self) -> None:
        resultado = self.execute(
            ordens=[self.ordem_bruta(id_ponto="")],
        )

        self.assertEqual(resultado.status_final, StatusExecucaoPlanejamento.INVIAVEL)
        self.assertIsNotNone(resultado.log_planejamento)
        self.assertTrue(
            any(
                evento.tipo_evento == TipoEventoAuditoria.ERRO and evento.entidade_afetada == "Ordem"
                for evento in resultado.eventos_auditoria
            )
        )
        self.assertTrue(any(motivo.codigo == "schema.obrigatorio_ausente" for motivo in resultado.motivos_inviabilidade))

    def test_cutoff_exclusion_keeps_specific_event_and_reason(self) -> None:
        resultado = self.execute(
            ordens=[
                self.ordem_bruta(
                    id_ordem="ORD-CUT",
                    status_cancelamento="cancelada_antes_cutoff",
                    instante_cancelamento="2026-03-20T17:00:00+00:00",
                )
            ],
        )

        self.assertTrue(
            any(
                evento.tipo_evento == TipoEventoAuditoria.EXCLUSAO
                and evento.id_entidade == "ORD-CUT"
                and evento.regra_relacionada == "negocio.cutoff_exclusao"
                for evento in resultado.eventos_auditoria
            )
        )
        self.assertTrue(
            any(
                motivo.codigo == "cancelada_antes_cutoff" and motivo.origem == "cutoff"
                for motivo in resultado.motivos_inviabilidade
            )
        )

    def test_solver_failure_is_registered_in_audit(self) -> None:
        resultado = self.execute(
            ordens=[self.ordem_bruta(id_ordem="ORD-FAIL")],
            adapter=FailingAdapter(),
        )

        self.assertEqual(resultado.status_final, StatusExecucaoPlanejamento.INVIAVEL)
        self.assertTrue(
            any(
                evento.tipo_evento == TipoEventoAuditoria.ERRO
                and evento.entidade_afetada == "PyVRP"
                and evento.id_entidade is not None
                for evento in resultado.eventos_auditoria
            )
        )
        self.assertTrue(any(motivo.codigo == "roteirizacao.falha_solver" for motivo in resultado.motivos_inviabilidade))
        self.assertGreaterEqual(resultado.log_planejamento.total_motivos_inviabilidade, 1)

    @unittest.skipUnless(PYVRP_AVAILABLE, "pyvrp nao instalado no ambiente")
    def test_persists_planning_parameters_and_timestamps(self) -> None:
        resultado = self.execute(
            ordens=[self.ordem_bruta(id_ordem="ORD-AUD")],
            seed=7,
            max_iterations=33,
        )

        self.assertEqual(resultado.status_final, StatusExecucaoPlanejamento.CONCLUIDA)
        self.assertEqual(resultado.log_planejamento.cutoff, self.context.cutoff)
        self.assertEqual(resultado.log_planejamento.timestamp_referencia, self.context.timestamp_referencia)
        self.assertEqual(resultado.log_planejamento.parametros_planejamento["seed"], 7)
        self.assertEqual(resultado.log_planejamento.parametros_planejamento["max_iterations"], 33)
        self.assertIn("suprimento", resultado.log_planejamento.parametros_planejamento["hashes_cenario"])
        self.assertTrue(
            any(
                evento.regra_relacionada == "auditoria.parametros_planejamento"
                for evento in resultado.eventos_auditoria
            )
        )


if __name__ == "__main__":
    unittest.main()

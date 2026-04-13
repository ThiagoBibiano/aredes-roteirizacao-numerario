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
    PreparationPipeline,
    RoutePostProcessor,
    SolverExecutionArtifact,
)
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
from roteirizacao.optimization import PyVRPAdapter

try:
    import pyvrp  # noqa: F401
except Exception:  # pragma: no cover - environment dependent
    PYVRP_AVAILABLE = False
else:
    PYVRP_AVAILABLE = True


def metadata(origin: str, external_id: str) -> MetadadoIngestao:
    return MetadadoIngestao(
        origem=origin,
        timestamp_ingestao=datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc),
        identificador_externo=external_id,
    )


@unittest.skipUnless(PYVRP_AVAILABLE, "pyvrp nao instalado no ambiente")
class RoutePostProcessorContractTest(unittest.TestCase):
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
        self.post_processor = RoutePostProcessor(self.context)

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

    def post_process(self, *, pontos: list[PontoBruto], ordens: list[OrdemBruta]):
        preparation = self.pipeline.run(
            bases_brutas=[self.base_bruta()],
            pontos_brutos=pontos,
            viaturas_brutas=[self.viatura_bruta()],
            ordens_brutas=ordens,
        )
        instance_result = self.builder.build(preparation)
        artifacts: list[SolverExecutionArtifact] = []

        for instancia in instance_result.instancias.values():
            payload = self.adapter.build_payload(instancia)
            model = self.adapter.build_model(instancia)
            solver_result = model.solve(
                pyvrp.stop.MaxIterations(25),
                seed=1,
                collect_stats=False,
                display=False,
            )
            artifacts.append(
                SolverExecutionArtifact(
                    instancia=instancia,
                    payload=payload,
                    solver_result=solver_result,
                )
            )

        processed = [self.post_processor.process_execution(artifact) for artifact in artifacts]
        return self.post_processor.consolidate(preparation, processed)

    def test_reconstructs_routes_loads_costs_and_summary(self) -> None:
        result = self.post_process(
            pontos=[self.ponto_bruto()],
            ordens=[
                self.ordem_bruta(id_ordem="ORD-SUP", tipo_servico="suprimento"),
                self.ordem_bruta(
                    id_ordem="ORD-REC",
                    tipo_servico="recolhimento",
                    valor_estimado="80000.00",
                    volume_estimado="4",
                ),
            ],
        )

        rota_suprimento = result.rotas_por_classe[ClasseOperacional.SUPRIMENTO][0]
        rota_recolhimento = result.rotas_por_classe[ClasseOperacional.RECOLHIMENTO][0]
        custo_esperado = (
            Decimal("500.00") + (Decimal(rota_suprimento.distancia_estimada) / Decimal("1000")) * Decimal("2.50")
        ).quantize(Decimal("0.01"))

        self.assertEqual(result.resumo_operacional.total_rotas, 2)
        self.assertEqual(result.resumo_operacional.total_ordens_planejadas, 2)
        self.assertEqual(rota_suprimento.paradas[0].id_ordem, "ORD-SUP")
        self.assertEqual(rota_suprimento.paradas[0].carga_acumulada["volume"], Decimal("5"))
        self.assertEqual(rota_suprimento.paradas[0].carga_acumulada["financeiro"], Decimal("15000.00"))
        self.assertEqual(rota_suprimento.custo_estimado, custo_esperado)
        self.assertTrue(rota_recolhimento.atingiu_limite_segurado)
        self.assertFalse(result.ordens_nao_atendidas)
        self.assertTrue(any(evento.tipo_evento == TipoEventoAuditoria.ROTEIRIZACAO for evento in result.eventos))

    def test_keeps_non_attended_orders_outside_routes(self) -> None:
        result = self.post_process(
            pontos=[self.ponto_bruto(point_id="PONTO-LONGE", latitude=-23.0000, longitude=-45.0000)],
            ordens=[
                self.ordem_bruta(
                    id_ordem="ORD-LOW",
                    id_ponto="PONTO-LONGE",
                    penalidade_nao_atendimento="50000.00",
                    valor_estimado="999999999.00",
                )
            ],
        )

        self.assertEqual(len(result.rotas_por_classe[ClasseOperacional.SUPRIMENTO]), 0)
        self.assertEqual(len(result.ordens_nao_atendidas), 1)
        self.assertEqual(result.ordens_nao_atendidas[0].id_ordem, "ORD-LOW")
        self.assertEqual(result.resumo_operacional.total_ordens_nao_atendidas, 1)
        self.assertEqual(result.resumo_operacional.total_ordens_planejadas, 0)


if __name__ == "__main__":
    unittest.main()

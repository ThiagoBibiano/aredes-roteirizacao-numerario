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

from roteirizacao.application import DailyPlanningOrchestrator, DatasetPlanningRequest
from roteirizacao.domain import (
    KpiGerencial,
    KpiOperacional,
    LogPlanejamento,
    RelatorioPlanejamento,
    ResumoOperacional,
    ResultadoPlanejamento,
    StatusExecucaoPlanejamento,
)


class SuccessfulExecutorFactory:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, contexto, request):
        return _SuccessfulExecutor(self, contexto, request)


class FailOnceExecutorFactory:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, contexto, request):
        return _FailOnceExecutor(self, contexto, request)


class _SuccessfulExecutor:
    def __init__(self, factory: SuccessfulExecutorFactory, contexto, request) -> None:
        self.factory = factory
        self.contexto = contexto
        self.request = request

    def run(self, preparation_result, instance_result) -> ResultadoPlanejamento:
        self.factory.calls += 1
        hashes = {classe.value: instancia.hash_cenario or "" for classe, instancia in instance_result.instancias.items()}
        resumo = ResumoOperacional(
            total_rotas=0,
            total_rotas_suprimento=0,
            total_rotas_recolhimento=0,
            total_ordens_planejadas=len(preparation_result.ordens_planejaveis),
            total_ordens_nao_atendidas=0,
            total_ordens_excluidas=len(preparation_result.ordens_excluidas),
            total_ordens_canceladas=len(preparation_result.ordens_canceladas),
        )
        return ResultadoPlanejamento(
            id_execucao=self.contexto.id_execucao,
            data_operacao=self.contexto.data_operacao,
            status_final=StatusExecucaoPlanejamento.CONCLUIDA,
            resumo_operacional=resumo,
            kpi_operacional=KpiOperacional(
                distancia_total_estimada=0,
                duracao_total_estimada_segundos=0,
                tempo_total_servico_segundos=0,
                taxa_atendimento=Decimal("1.0000"),
                utilizacao_frota=Decimal("0.0000"),
                rotas_com_limite_segurado=0,
                total_ordens_atendidas=len(preparation_result.ordens_planejaveis),
                total_ordens_especiais_atendidas=0,
                viaturas_acionadas=0,
                total_paradas_improdutivas=0,
                total_ordens_excluidas_por_restricao=len(preparation_result.ordens_excluidas),
            ),
            kpi_gerencial=KpiGerencial(
                custo_total_estimado=Decimal("0"),
                penalidade_total_nao_atendimento=Decimal("0"),
                impacto_financeiro_cancelamentos=Decimal("0"),
                valor_total_taxas_improdutivas=Decimal("0"),
                custo_medio_por_rota=Decimal("0"),
                custo_medio_por_ordem_planejada=Decimal("0"),
            ),
            ordens_excluidas=tuple(preparation_result.ordens_excluidas),
            ordens_canceladas=tuple(preparation_result.ordens_canceladas),
            hashes_cenario=hashes,
            log_planejamento=LogPlanejamento(
                id_execucao=self.contexto.id_execucao,
                data_operacao=self.contexto.data_operacao,
                status_final=StatusExecucaoPlanejamento.CONCLUIDA,
                cutoff=self.contexto.cutoff,
                timestamp_referencia=self.contexto.timestamp_referencia,
                total_eventos=0,
                total_erros=0,
                total_motivos_inviabilidade=0,
                parametros_planejamento={
                    "seed": self.request.seed,
                    "max_iterations": self.request.max_iterations,
                },
            ),
            relatorio_planejamento=RelatorioPlanejamento(
                id_execucao=self.contexto.id_execucao,
                data_operacao=self.contexto.data_operacao,
                status_final=StatusExecucaoPlanejamento.CONCLUIDA,
                total_ordens_atendidas=len(preparation_result.ordens_planejaveis),
                total_ordens_especiais_atendidas=0,
                total_ordens_nao_atendidas=0,
                total_ordens_excluidas=len(preparation_result.ordens_excluidas),
                total_ordens_canceladas=len(preparation_result.ordens_canceladas),
                total_viaturas_acionadas=0,
                total_eventos_auditoria=0,
                total_motivos_inviabilidade=0,
                classes_processadas=tuple(sorted(hashes)),
                custo_total_estimado=Decimal("0"),
                impacto_financeiro_cancelamentos=Decimal("0"),
                destaques=(),
            ),
        )


class _FailOnceExecutor(_SuccessfulExecutor):
    def __init__(self, factory: FailOnceExecutorFactory, contexto, request) -> None:
        super().__init__(factory, contexto, request)

    def run(self, preparation_result, instance_result) -> ResultadoPlanejamento:
        self.factory.calls += 1
        if self.factory.calls == 1:
            raise RuntimeError("falha tecnica do solver")
        hashes = {classe.value: instancia.hash_cenario or "" for classe, instancia in instance_result.instancias.items()}
        resumo = ResumoOperacional(
            total_rotas=0,
            total_rotas_suprimento=0,
            total_rotas_recolhimento=0,
            total_ordens_planejadas=len(preparation_result.ordens_planejaveis),
            total_ordens_nao_atendidas=0,
            total_ordens_excluidas=len(preparation_result.ordens_excluidas),
            total_ordens_canceladas=len(preparation_result.ordens_canceladas),
        )
        return ResultadoPlanejamento(
            id_execucao=self.contexto.id_execucao,
            data_operacao=self.contexto.data_operacao,
            status_final=StatusExecucaoPlanejamento.CONCLUIDA,
            resumo_operacional=resumo,
            kpi_operacional=KpiOperacional(
                distancia_total_estimada=0,
                duracao_total_estimada_segundos=0,
                tempo_total_servico_segundos=0,
                taxa_atendimento=Decimal("1.0000"),
                utilizacao_frota=Decimal("0.0000"),
                rotas_com_limite_segurado=0,
                total_ordens_atendidas=len(preparation_result.ordens_planejaveis),
                total_ordens_especiais_atendidas=0,
                viaturas_acionadas=0,
                total_paradas_improdutivas=0,
                total_ordens_excluidas_por_restricao=len(preparation_result.ordens_excluidas),
            ),
            kpi_gerencial=KpiGerencial(
                custo_total_estimado=Decimal("0"),
                penalidade_total_nao_atendimento=Decimal("0"),
                impacto_financeiro_cancelamentos=Decimal("0"),
                valor_total_taxas_improdutivas=Decimal("0"),
                custo_medio_por_rota=Decimal("0"),
                custo_medio_por_ordem_planejada=Decimal("0"),
            ),
            ordens_excluidas=tuple(preparation_result.ordens_excluidas),
            ordens_canceladas=tuple(preparation_result.ordens_canceladas),
            hashes_cenario=hashes,
            log_planejamento=LogPlanejamento(
                id_execucao=self.contexto.id_execucao,
                data_operacao=self.contexto.data_operacao,
                status_final=StatusExecucaoPlanejamento.CONCLUIDA,
                cutoff=self.contexto.cutoff,
                timestamp_referencia=self.contexto.timestamp_referencia,
                total_eventos=0,
                total_erros=0,
                total_motivos_inviabilidade=0,
                parametros_planejamento={
                    "seed": self.request.seed,
                    "max_iterations": self.request.max_iterations,
                },
            ),
            relatorio_planejamento=RelatorioPlanejamento(
                id_execucao=self.contexto.id_execucao,
                data_operacao=self.contexto.data_operacao,
                status_final=StatusExecucaoPlanejamento.CONCLUIDA,
                total_ordens_atendidas=len(preparation_result.ordens_planejaveis),
                total_ordens_especiais_atendidas=0,
                total_ordens_nao_atendidas=0,
                total_ordens_excluidas=len(preparation_result.ordens_excluidas),
                total_ordens_canceladas=len(preparation_result.ordens_canceladas),
                total_viaturas_acionadas=0,
                total_eventos_auditoria=0,
                total_motivos_inviabilidade=0,
                classes_processadas=tuple(sorted(hashes)),
                custo_total_estimado=Decimal("0"),
                impacto_financeiro_cancelamentos=Decimal("0"),
                destaques=(),
            ),
        )


class OrchestrationContractTest(unittest.TestCase):
    def write_dataset(self, dataset_dir: Path, *, timestamp_referencia: str = "2026-03-20T18:30:00+00:00") -> None:
        (dataset_dir / "outputs").mkdir(parents=True, exist_ok=True)
        (dataset_dir / "contexto.json").write_text(
            json.dumps(
                {
                    "id_execucao": "exec-smoke-2026-03-21",
                    "data_operacao": "2026-03-21",
                    "cutoff": "2026-03-20T18:00:00+00:00",
                    "timestamp_referencia": timestamp_referencia,
                    "versao_schema": "1.0",
                },
                indent=2,
                ensure_ascii=True,
            )
            + "\n"
        )
        (dataset_dir / "bases.json").write_text(
            json.dumps(
                [
                    {
                        "id_base": "BASE-01",
                        "nome": "Base Central Fake",
                        "latitude": -23.5505,
                        "longitude": -46.6333,
                        "inicio_operacao": "2026-03-21T06:00:00+00:00",
                        "fim_operacao": "2026-03-21T22:00:00+00:00",
                        "status_ativo": True,
                    }
                ],
                indent=2,
                ensure_ascii=True,
            )
            + "\n"
        )
        (dataset_dir / "pontos.json").write_text(
            json.dumps(
                [
                    {
                        "id_ponto": "PONTO-01",
                        "tipo_ponto": "agencia",
                        "latitude": -23.5489,
                        "longitude": -46.6388,
                        "setor_geografico": "centro",
                        "inicio_janela": "2026-03-21T08:00:00+00:00",
                        "fim_janela": "2026-03-21T17:00:00+00:00",
                        "tempo_servico": 20,
                        "status_ativo": True,
                    }
                ],
                indent=2,
                ensure_ascii=True,
            )
            + "\n"
        )
        (dataset_dir / "viaturas.json").write_text(
            json.dumps(
                [
                    {
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
                        "status_ativo": True,
                    }
                ],
                indent=2,
                ensure_ascii=True,
            )
            + "\n"
        )
        (dataset_dir / "ordens.json").write_text(
            json.dumps(
                [
                    {
                        "id_ordem": "ORD-SMOKE-01",
                        "origem_ordem": "erp_fake",
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
                ],
                indent=2,
                ensure_ascii=True,
            )
            + "\n"
        )

    def read_manifest(self, state_dir: Path) -> dict[str, object]:
        return json.loads((state_dir / "manifest.json").read_text())

    def test_same_execution_repeated_does_not_duplicate_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_dir = Path(tmp_dir)
            self.write_dataset(dataset_dir)
            factory = SuccessfulExecutorFactory()
            orchestrator = DailyPlanningOrchestrator(executor_factory=factory)
            request = DatasetPlanningRequest(dataset_dir=dataset_dir)

            first = orchestrator.run(request)
            second = orchestrator.run(request)

            state_dir = dataset_dir / "outputs" / "executions"
            manifest = self.read_manifest(state_dir)

            self.assertEqual(first.hash_cenario, second.hash_cenario)
            self.assertFalse(first.reused_cached_result)
            self.assertTrue(second.reused_cached_result)
            self.assertEqual(factory.calls, 1)
            self.assertEqual(len(manifest["scenarios"]), 1)
            self.assertEqual(manifest["scenarios"][0]["cache_hits"], 1)
            self.assertTrue((state_dir / first.hash_cenario / "resultado-planejamento.json").exists())

    def test_solver_failure_allows_safe_retry_without_duplicate_effects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_dir = Path(tmp_dir)
            self.write_dataset(dataset_dir)
            factory = FailOnceExecutorFactory()
            orchestrator = DailyPlanningOrchestrator(executor_factory=factory)
            request = DatasetPlanningRequest(dataset_dir=dataset_dir)

            with self.assertRaisesRegex(RuntimeError, "falha tecnica do solver"):
                orchestrator.run(request)

            state_dir = dataset_dir / "outputs" / "executions"
            manifest_after_failure = self.read_manifest(state_dir)
            hash_cenario = manifest_after_failure["latest_hash_cenario"]
            failed_state = json.loads((state_dir / hash_cenario / "estado.json").read_text())
            self.assertEqual(failed_state["status"], "failed")
            self.assertFalse((state_dir / hash_cenario / "resultado-planejamento.pkl").exists())

            recovered = orchestrator.run(request)
            manifest_after_retry = self.read_manifest(state_dir)
            completed_state = json.loads((state_dir / hash_cenario / "estado.json").read_text())

            self.assertEqual(recovered.hash_cenario, hash_cenario)
            self.assertFalse(recovered.reused_cached_result)
            self.assertTrue(recovered.recovered_previous_context)
            self.assertEqual(recovered.attempt_number, 2)
            self.assertEqual(factory.calls, 2)
            self.assertEqual(completed_state["status"], "completed")
            self.assertEqual(completed_state["attempts"], 2)
            self.assertEqual(len(manifest_after_retry["scenarios"]), 1)

    def test_scenario_change_alters_hash_cenario(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_dir = Path(tmp_dir)
            self.write_dataset(dataset_dir)
            factory = SuccessfulExecutorFactory()
            orchestrator = DailyPlanningOrchestrator(executor_factory=factory)
            request = DatasetPlanningRequest(dataset_dir=dataset_dir)

            first = orchestrator.run(request)

            altered_orders = json.loads((dataset_dir / "ordens.json").read_text())
            altered_orders[0]["valor_estimado"] = "17500.00"
            (dataset_dir / "ordens.json").write_text(json.dumps(altered_orders, indent=2, ensure_ascii=True) + "\n")

            second = orchestrator.run(request)
            manifest = self.read_manifest(dataset_dir / "outputs" / "executions")

            self.assertNotEqual(first.hash_cenario, second.hash_cenario)
            self.assertEqual(factory.calls, 2)
            self.assertEqual(len(manifest["scenarios"]), 2)

    def test_same_scenario_recovers_previous_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_dir = Path(tmp_dir)
            initial_timestamp = "2026-03-20T18:30:00+00:00"
            self.write_dataset(dataset_dir, timestamp_referencia=initial_timestamp)
            factory = SuccessfulExecutorFactory()
            orchestrator = DailyPlanningOrchestrator(executor_factory=factory)
            request = DatasetPlanningRequest(dataset_dir=dataset_dir)

            first = orchestrator.run(request)

            self.write_dataset(dataset_dir, timestamp_referencia="2026-03-20T19:45:00+00:00")
            recovered = orchestrator.run(request)

            self.assertEqual(first.hash_cenario, recovered.hash_cenario)
            self.assertTrue(recovered.recovered_previous_context)
            self.assertTrue(recovered.reused_cached_result)
            self.assertEqual(factory.calls, 1)
            self.assertEqual(
                recovered.resultado_planejamento.log_planejamento.timestamp_referencia,
                datetime.fromisoformat(initial_timestamp),
            )
            self.assertEqual(
                recovered.resultado_planejamento.hashes_cenario["orquestracao"],
                first.hash_cenario,
            )


if __name__ == "__main__":
    unittest.main()

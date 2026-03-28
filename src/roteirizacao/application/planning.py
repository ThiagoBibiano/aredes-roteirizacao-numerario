from __future__ import annotations

from itertools import count
from typing import Any

from roteirizacao.application.audit import PlanningAuditTrailBuilder
from roteirizacao.application.instance_builder import InstanceBuildResult
from roteirizacao.application.post_processing import RoutePostProcessor, SolverExecutionArtifact
from roteirizacao.application.preparation import PreparationResult
from roteirizacao.application.reporting import PlanningReportingBuilder
from roteirizacao.domain.enums import ClasseOperacional, SeveridadeEvento, StatusExecucaoPlanejamento, TipoEventoAuditoria
from roteirizacao.domain.events import ErroValidacao, EventoAuditoria
from roteirizacao.domain.results import ResultadoPlanejamento
from roteirizacao.domain.services import ContextoExecucao
from roteirizacao.optimization import PyVRPAdapter


class PlanningExecutor:
    SERVICE_POLICY_NAME = "maximize_attendance_v1"

    def __init__(
        self,
        contexto: ContextoExecucao,
        *,
        adapter: PyVRPAdapter | None = None,
        post_processor: RoutePostProcessor | None = None,
        audit_builder: PlanningAuditTrailBuilder | None = None,
        reporting_builder: PlanningReportingBuilder | None = None,
        max_iterations: int = 100,
        seed: int = 1,
        collect_stats: bool = False,
        display: bool = False,
    ) -> None:
        self.contexto = contexto
        self.adapter = adapter or PyVRPAdapter()
        self.post_processor = post_processor or RoutePostProcessor(contexto)
        self.audit_builder = audit_builder or PlanningAuditTrailBuilder(contexto)
        self.reporting_builder = reporting_builder or PlanningReportingBuilder(contexto)
        self.max_iterations = max_iterations
        self.seed = seed
        self.collect_stats = collect_stats
        self.display = display
        self._counter = count(1)

    def run(
        self,
        preparation_result: PreparationResult,
        instance_result: InstanceBuildResult,
    ) -> ResultadoPlanejamento:
        eventos = list(preparation_result.eventos_auditoria)
        eventos.extend(instance_result.eventos_auditoria)
        erros = list(preparation_result.erros)
        erros.extend(instance_result.erros)

        hashes_cenario: dict[str, str] = {}
        solver_artifacts: list[SolverExecutionArtifact] = []

        for classe_operacional, instancia in instance_result.instancias.items():
            hashes_cenario[classe_operacional.value] = instancia.hash_cenario or ""
            try:
                payload = self.adapter.build_payload(instancia)
                model = self.adapter.build_model(instancia)
                stop = self._stop_criterion()
                solver_result = model.solve(
                    stop,
                    seed=self.seed,
                    collect_stats=self.collect_stats,
                    display=self.display,
                )
            except ModuleNotFoundError as exc:
                erros.append(
                    self._error(
                        entidade="PyVRP",
                        id_entidade=instancia.id_cenario,
                        mensagem=str(exc),
                        valor_observado="pyvrp_ausente",
                        valor_esperado="biblioteca pyvrp instalada",
                        codigo_regra="roteirizacao.dependencia_ausente",
                    )
                )
                eventos.append(
                    self._event(
                        tipo_evento=TipoEventoAuditoria.ERRO,
                        entidade_afetada="PyVRP",
                        id_entidade=instancia.id_cenario,
                        regra_relacionada="roteirizacao.pyvrp",
                        motivo="solver indisponivel no ambiente",
                        severidade=SeveridadeEvento.ERRO,
                    )
                )
                continue
            except Exception as exc:  # pragma: no cover - defensive branch
                erros.append(
                    self._error(
                        entidade="PyVRP",
                        id_entidade=instancia.id_cenario,
                        mensagem=f"falha ao resolver instancia: {exc}",
                        valor_observado=str(exc),
                        valor_esperado="resultado do solver",
                        codigo_regra="roteirizacao.falha_solver",
                    )
                )
                eventos.append(
                    self._event(
                        tipo_evento=TipoEventoAuditoria.ERRO,
                        entidade_afetada="PyVRP",
                        id_entidade=instancia.id_cenario,
                        regra_relacionada="roteirizacao.pyvrp.solve",
                        motivo="solver retornou falha nao tratada",
                        severidade=SeveridadeEvento.ERRO,
                        contexto_adicional={"erro": str(exc)},
                    )
                )
                continue

            solver_artifacts.append(
                SolverExecutionArtifact(
                    instancia=instancia,
                    payload=payload,
                    solver_result=solver_result,
                )
            )

        processed_classes = [self.post_processor.process_execution(artifact) for artifact in solver_artifacts]
        post_processing = self.post_processor.consolidate(preparation_result, processed_classes)
        eventos.extend(post_processing.eventos)

        rotas_por_classe = post_processing.rotas_por_classe
        ordens_nao_atendidas = post_processing.ordens_nao_atendidas
        resumo = post_processing.resumo_operacional
        status_final = self._final_status(erros, rotas_por_classe, ordens_nao_atendidas)

        eventos.append(
            self._event(
                tipo_evento=TipoEventoAuditoria.SAIDA,
                entidade_afetada="ResultadoPlanejamento",
                id_entidade=self.contexto.id_execucao,
                regra_relacionada="saida.resultado_planejamento",
                motivo="resultado consolidado do planejamento diario",
                contexto_adicional={
                    "status_final": status_final.value,
                    "total_rotas": resumo.total_rotas,
                    "total_ordens_nao_atendidas": resumo.total_ordens_nao_atendidas,
                },
            )
        )

        audit_result = self.audit_builder.build(
            status_final=status_final,
            eventos_existentes=eventos,
            erros=erros,
            preparation_result=preparation_result,
            ordens_nao_atendidas=ordens_nao_atendidas,
            hashes_cenario=hashes_cenario,
            parametros_planejamento={
                "max_iterations": self.max_iterations,
                "seed": self.seed,
                "collect_stats": self.collect_stats,
                "display": self.display,
                "service_policy": self.SERVICE_POLICY_NAME,
                "classes_processadas": sorted(hashes_cenario),
            },
        )
        reporting_result = self.reporting_builder.build(
            status_final=status_final,
            preparation_result=preparation_result,
            rotas_por_classe=rotas_por_classe,
            ordens_nao_atendidas=ordens_nao_atendidas,
            eventos_auditoria=audit_result.eventos_auditoria,
            motivos_inviabilidade=audit_result.motivos_inviabilidade,
        )

        return ResultadoPlanejamento(
            id_execucao=self.contexto.id_execucao,
            data_operacao=self.contexto.data_operacao,
            status_final=status_final,
            resumo_operacional=resumo,
            kpi_operacional=reporting_result.kpi_operacional,
            kpi_gerencial=reporting_result.kpi_gerencial,
            rotas_suprimento=tuple(rotas_por_classe[ClasseOperacional.SUPRIMENTO]),
            rotas_recolhimento=tuple(rotas_por_classe[ClasseOperacional.RECOLHIMENTO]),
            ordens_nao_atendidas=tuple(ordens_nao_atendidas),
            ordens_excluidas=tuple(preparation_result.ordens_excluidas),
            ordens_canceladas=tuple(preparation_result.ordens_canceladas),
            eventos_auditoria=tuple(audit_result.eventos_auditoria),
            erros=tuple(erros),
            hashes_cenario=hashes_cenario,
            log_planejamento=audit_result.log_planejamento,
            motivos_inviabilidade=tuple(audit_result.motivos_inviabilidade),
            relatorio_planejamento=reporting_result.relatorio_planejamento,
        )

    def _final_status(
        self,
        erros: list[Any],
        rotas_por_classe: dict[ClasseOperacional, list],
        ordens_nao_atendidas: list,
    ) -> StatusExecucaoPlanejamento:
        total_rotas = sum(len(rotas) for rotas in rotas_por_classe.values())
        if erros and total_rotas == 0:
            return StatusExecucaoPlanejamento.INVIAVEL
        if erros:
            return StatusExecucaoPlanejamento.CONCLUIDA_COM_RESSALVAS
        if ordens_nao_atendidas:
            return StatusExecucaoPlanejamento.CONCLUIDA_COM_RESSALVAS
        return StatusExecucaoPlanejamento.CONCLUIDA

    def _stop_criterion(self) -> Any:
        import pyvrp

        return pyvrp.stop.MaxIterations(self.max_iterations)

    def _event(
        self,
        *,
        tipo_evento: TipoEventoAuditoria,
        entidade_afetada: str,
        id_entidade: str | None,
        regra_relacionada: str,
        motivo: str,
        severidade: SeveridadeEvento = SeveridadeEvento.INFO,
        contexto_adicional: dict[str, Any] | None = None,
    ) -> EventoAuditoria:
        return EventoAuditoria(
            id_evento=f"evt-plan-{next(self._counter):06d}",
            tipo_evento=tipo_evento,
            severidade=severidade,
            entidade_afetada=entidade_afetada,
            id_entidade=id_entidade,
            regra_relacionada=regra_relacionada,
            motivo=motivo,
            timestamp_evento=self.contexto.timestamp_referencia,
            id_execucao=self.contexto.id_execucao,
            contexto_adicional=contexto_adicional,
        )

    def _error(
        self,
        *,
        entidade: str,
        id_entidade: str | None,
        mensagem: str,
        valor_observado: Any,
        valor_esperado: Any,
        codigo_regra: str,
    ) -> ErroValidacao:
        return ErroValidacao(
            id_erro=f"err-plan-{next(self._counter):06d}",
            codigo_regra=codigo_regra,
            mensagem=mensagem,
            entidade=entidade,
            id_entidade=id_entidade,
            campo=None,
            valor_observado=valor_observado,
            valor_esperado=valor_esperado,
            severidade=SeveridadeEvento.ERRO,
            timestamp=self.contexto.timestamp_referencia,
            id_execucao=self.contexto.id_execucao,
        )

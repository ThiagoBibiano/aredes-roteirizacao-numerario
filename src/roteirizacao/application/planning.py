from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from itertools import count
from typing import Any

from roteirizacao.application.instance_builder import InstanceBuildResult
from roteirizacao.application.post_processing import RoutePostProcessor, SolverExecutionArtifact
from roteirizacao.application.preparation import PreparationResult
from roteirizacao.domain.enums import ClasseOperacional, SeveridadeEvento, StatusExecucaoPlanejamento, TipoEventoAuditoria
from roteirizacao.domain.events import ErroValidacao, EventoAuditoria
from roteirizacao.domain.results import KpiGerencial, KpiOperacional, OrdemNaoAtendida, ResultadoPlanejamento, RotaPlanejada
from roteirizacao.domain.services import ContextoExecucao
from roteirizacao.optimization import PyVRPAdapter


class PlanningExecutor:
    def __init__(
        self,
        contexto: ContextoExecucao,
        *,
        adapter: PyVRPAdapter | None = None,
        post_processor: RoutePostProcessor | None = None,
        max_iterations: int = 100,
        seed: int = 1,
        collect_stats: bool = False,
        display: bool = False,
    ) -> None:
        self.contexto = contexto
        self.adapter = adapter or PyVRPAdapter()
        self.post_processor = post_processor or RoutePostProcessor(contexto)
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
        kpi_operacional = self._build_operational_kpi(rotas_por_classe, ordens_nao_atendidas, instance_result)
        kpi_gerencial = self._build_managerial_kpi(rotas_por_classe, ordens_nao_atendidas)
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

        return ResultadoPlanejamento(
            id_execucao=self.contexto.id_execucao,
            data_operacao=self.contexto.data_operacao,
            status_final=status_final,
            resumo_operacional=resumo,
            kpi_operacional=kpi_operacional,
            kpi_gerencial=kpi_gerencial,
            rotas_suprimento=tuple(rotas_por_classe[ClasseOperacional.SUPRIMENTO]),
            rotas_recolhimento=tuple(rotas_por_classe[ClasseOperacional.RECOLHIMENTO]),
            ordens_nao_atendidas=tuple(ordens_nao_atendidas),
            ordens_excluidas=tuple(preparation_result.ordens_excluidas),
            ordens_canceladas=tuple(preparation_result.ordens_canceladas),
            eventos_auditoria=tuple(eventos),
            erros=tuple(erros),
            hashes_cenario=hashes_cenario,
        )

    def _build_operational_kpi(
        self,
        rotas_por_classe: dict[ClasseOperacional, list[RotaPlanejada]],
        ordens_nao_atendidas: list[OrdemNaoAtendida],
        instance_result: InstanceBuildResult,
    ) -> KpiOperacional:
        todas_rotas = [rota for rotas in rotas_por_classe.values() for rota in rotas]
        distancia_total = sum(rota.distancia_estimada for rota in todas_rotas)
        duracao_total = sum(rota.duracao_estimada_segundos for rota in todas_rotas)
        total_planejadas = sum(len(rota.paradas) for rota in todas_rotas)
        denominador_atendimento = total_planejadas + len(ordens_nao_atendidas)
        taxa_atendimento = Decimal("1") if denominador_atendimento == 0 else (
            Decimal(total_planejadas) / Decimal(denominador_atendimento)
        )

        viaturas_disponiveis = {
            veiculo.id_viatura
            for instancia in instance_result.instancias.values()
            for veiculo in instancia.veiculos
        }
        viaturas_utilizadas = {rota.id_viatura for rota in todas_rotas}
        utilizacao_frota = Decimal("0") if not viaturas_disponiveis else (
            Decimal(len(viaturas_utilizadas)) / Decimal(len(viaturas_disponiveis))
        )

        return KpiOperacional(
            distancia_total_estimada=distancia_total,
            duracao_total_estimada_segundos=duracao_total,
            taxa_atendimento=self._quantize_ratio(taxa_atendimento),
            utilizacao_frota=self._quantize_ratio(utilizacao_frota),
            rotas_com_limite_segurado=sum(1 for rota in todas_rotas if rota.atingiu_limite_segurado),
        )

    def _build_managerial_kpi(
        self,
        rotas_por_classe: dict[ClasseOperacional, list[RotaPlanejada]],
        ordens_nao_atendidas: list[OrdemNaoAtendida],
    ) -> KpiGerencial:
        todas_rotas = [rota for rotas in rotas_por_classe.values() for rota in rotas]
        custo_total = sum((rota.custo_estimado for rota in todas_rotas), start=Decimal("0"))
        penalidade_total = sum((ordem.penalidade_aplicada for ordem in ordens_nao_atendidas), start=Decimal("0"))
        total_ordens_planejadas = sum(len(rota.paradas) for rota in todas_rotas)
        custo_medio_por_rota = Decimal("0") if not todas_rotas else custo_total / Decimal(len(todas_rotas))
        custo_medio_por_ordem = Decimal("0") if total_ordens_planejadas == 0 else custo_total / Decimal(total_ordens_planejadas)
        return KpiGerencial(
            custo_total_estimado=custo_total.quantize(Decimal("0.01")),
            penalidade_total_nao_atendimento=penalidade_total.quantize(Decimal("0.01")),
            custo_medio_por_rota=custo_medio_por_rota.quantize(Decimal("0.01")),
            custo_medio_por_ordem_planejada=custo_medio_por_ordem.quantize(Decimal("0.01")),
        )

    def _final_status(
        self,
        erros: list[Any],
        rotas_por_classe: dict[ClasseOperacional, list[RotaPlanejada]],
        ordens_nao_atendidas: list[OrdemNaoAtendida],
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

    def _quantize_ratio(self, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

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

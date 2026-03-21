from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from itertools import count
from typing import Any

from roteirizacao.application.instance_builder import InstanceBuildResult
from roteirizacao.application.preparation import PreparationResult
from roteirizacao.domain.enums import ClasseOperacional, SeveridadeEvento, StatusExecucaoPlanejamento, TipoEventoAuditoria
from roteirizacao.domain.events import ErroValidacao, EventoAuditoria
from roteirizacao.domain.optimization import InstanciaRoteirizacaoBase, NoRoteirizacao, VeiculoRoteirizacao
from roteirizacao.domain.results import (
    KpiGerencial,
    KpiOperacional,
    OrdemNaoAtendida,
    ParadaPlanejada,
    ResumoOperacional,
    ResultadoPlanejamento,
    RotaPlanejada,
)
from roteirizacao.domain.services import ContextoExecucao
from roteirizacao.optimization import PyVRPAdapter, PyVRPModelPayload

DIMENSAO_FINANCEIRA = "financeiro"


@dataclass(slots=True)
class _ClasseTraduzida:
    rotas: list[RotaPlanejada]
    ordens_nao_atendidas: list[OrdemNaoAtendida]
    eventos: list[EventoAuditoria]


class PlanningExecutor:
    def __init__(
        self,
        contexto: ContextoExecucao,
        *,
        adapter: PyVRPAdapter | None = None,
        max_iterations: int = 100,
        seed: int = 1,
        collect_stats: bool = False,
        display: bool = False,
    ) -> None:
        self.contexto = contexto
        self.adapter = adapter or PyVRPAdapter()
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

        rotas_por_classe: dict[ClasseOperacional, list[RotaPlanejada]] = {
            ClasseOperacional.SUPRIMENTO: [],
            ClasseOperacional.RECOLHIMENTO: [],
        }
        ordens_nao_atendidas: list[OrdemNaoAtendida] = []
        hashes_cenario: dict[str, str] = {}

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

            traduzida = self._translate_solver_result(instancia, payload, solver_result)
            rotas_por_classe[classe_operacional].extend(traduzida.rotas)
            ordens_nao_atendidas.extend(traduzida.ordens_nao_atendidas)
            eventos.extend(traduzida.eventos)

        resumo = self._build_summary(preparation_result, rotas_por_classe, ordens_nao_atendidas)
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

    def _translate_solver_result(
        self,
        instancia: InstanciaRoteirizacaoBase,
        payload: PyVRPModelPayload,
        solver_result: Any,
    ) -> _ClasseTraduzida:
        solution = solver_result.best
        eventos = [
            self._event(
                tipo_evento=TipoEventoAuditoria.ROTEIRIZACAO,
                entidade_afetada="InstanciaRoteirizacaoBase",
                id_entidade=instancia.id_cenario,
                regra_relacionada="roteirizacao.pyvrp.solve",
                motivo="solver executado com sucesso",
                contexto_adicional={
                    "classe_operacional": instancia.classe_operacional.value,
                    "cost": solver_result.cost(),
                    "feasible": solver_result.is_feasible(),
                    "num_routes": solution.num_routes(),
                    "num_missing_clients": solution.num_missing_clients(),
                    "summary": solver_result.summary(),
                },
            )
        ]

        rotas: list[RotaPlanejada] = []
        visited_locations: set[int] = set()
        depot_count = len(payload.depots)

        for route_index, route in enumerate(solution.routes(), start=1):
            veiculo = instancia.veiculos[route.vehicle_type()]
            paradas: list[ParadaPlanejada] = []
            carga_acumulada = {dimension: Decimal("0") for dimension in instancia.dimensoes_capacidade}

            for parada_index, visit in enumerate(route.schedule()[1:-1], start=1):
                location_index = int(visit.location)
                visited_locations.add(location_index)
                no = instancia.nos_atendimento[location_index - depot_count]

                for dimension, valor in no.demandas.items():
                    carga_acumulada[dimension] += valor

                inicio_previsto = payload.time_origin + timedelta(seconds=int(visit.start_service))
                fim_previsto = payload.time_origin + timedelta(seconds=int(visit.end_service))
                folga = int((no.janela_tempo.fim - fim_previsto).total_seconds())

                paradas.append(
                    ParadaPlanejada(
                        sequencia=parada_index,
                        id_ordem=no.id_ordem,
                        id_no=no.id_no,
                        id_ponto=no.id_ponto,
                        tipo_servico=no.tipo_servico,
                        criticidade=no.criticidade,
                        inicio_previsto=inicio_previsto,
                        fim_previsto=fim_previsto,
                        demanda=dict(no.demandas),
                        carga_acumulada=dict(carga_acumulada),
                        folga_janela_segundos=max(folga, 0),
                        espera_segundos=int(visit.wait_duration),
                        atraso_segundos=int(visit.time_warp),
                    )
                )

            if not paradas:
                continue

            inicio_rota = payload.time_origin + timedelta(seconds=int(route.start_time()))
            fim_rota = payload.time_origin + timedelta(seconds=int(route.end_time()))
            carga_total = dict(paradas[-1].carga_acumulada)
            limite_financeiro = veiculo.capacidades.get(DIMENSAO_FINANCEIRA, Decimal("0"))
            rotas.append(
                RotaPlanejada(
                    id_rota=f"rota-{self.contexto.id_execucao}-{instancia.classe_operacional.value}-{route_index:03d}",
                    id_viatura=veiculo.id_viatura,
                    id_base=veiculo.id_base_origem,
                    classe_operacional=instancia.classe_operacional,
                    paradas=tuple(paradas),
                    inicio_previsto=inicio_rota,
                    fim_previsto=fim_rota,
                    distancia_estimada=int(route.distance()),
                    duracao_estimada_segundos=int(route.duration()),
                    custo_estimado=self._estimate_route_cost(route, veiculo),
                    carga_total=carga_total,
                    atingiu_limite_segurado=(
                        instancia.classe_operacional == ClasseOperacional.RECOLHIMENTO
                        and carga_total.get(DIMENSAO_FINANCEIRA, Decimal("0")) >= limite_financeiro
                    ),
                    possui_violacao_janela=bool(route.has_time_warp()),
                    possui_excesso_capacidade=bool(route.has_excess_load()),
                )
            )

        ordens_nao_atendidas: list[OrdemNaoAtendida] = []
        for client_index, no in enumerate(instancia.nos_atendimento, start=depot_count):
            if client_index in visited_locations:
                continue
            ordens_nao_atendidas.append(
                OrdemNaoAtendida(
                    id_ordem=no.id_ordem,
                    id_no=no.id_no,
                    id_ponto=no.id_ponto,
                    tipo_servico=no.tipo_servico,
                    classe_operacional=no.classe_operacional,
                    criticidade=no.criticidade,
                    penalidade_aplicada=no.penalidade_nao_atendimento,
                    motivo="solver_cliente_opcional_nao_selecionado",
                )
            )
            eventos.append(
                self._event(
                    tipo_evento=TipoEventoAuditoria.ROTEIRIZACAO,
                    entidade_afetada="Ordem",
                    id_entidade=no.id_ordem,
                    regra_relacionada="roteirizacao.nao_atendimento",
                    motivo="ordem nao selecionada pelo solver",
                    severidade=SeveridadeEvento.AVISO,
                    contexto_adicional={
                        "classe_operacional": no.classe_operacional.value,
                        "penalidade_nao_atendimento": str(no.penalidade_nao_atendimento),
                    },
                )
            )

        return _ClasseTraduzida(rotas=rotas, ordens_nao_atendidas=ordens_nao_atendidas, eventos=eventos)

    def _build_summary(
        self,
        preparation_result: PreparationResult,
        rotas_por_classe: dict[ClasseOperacional, list[RotaPlanejada]],
        ordens_nao_atendidas: list[OrdemNaoAtendida],
    ) -> ResumoOperacional:
        total_rotas_suprimento = len(rotas_por_classe[ClasseOperacional.SUPRIMENTO])
        total_rotas_recolhimento = len(rotas_por_classe[ClasseOperacional.RECOLHIMENTO])
        total_ordens_planejadas = sum(len(rota.paradas) for rotas in rotas_por_classe.values() for rota in rotas)
        return ResumoOperacional(
            total_rotas=total_rotas_suprimento + total_rotas_recolhimento,
            total_rotas_suprimento=total_rotas_suprimento,
            total_rotas_recolhimento=total_rotas_recolhimento,
            total_ordens_planejadas=total_ordens_planejadas,
            total_ordens_nao_atendidas=len(ordens_nao_atendidas),
            total_ordens_excluidas=len(preparation_result.ordens_excluidas),
            total_ordens_canceladas=len(preparation_result.ordens_canceladas),
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

    def _estimate_route_cost(self, route: Any, veiculo: VeiculoRoteirizacao) -> Decimal:
        distance_km = Decimal(route.distance()) / Decimal("1000")
        distance_cost = distance_km * veiculo.custo_variavel
        return (veiculo.custo_fixo + distance_cost).quantize(Decimal("0.01"))

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

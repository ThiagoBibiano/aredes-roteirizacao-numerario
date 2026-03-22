from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from itertools import count
from typing import Any, Iterable

from roteirizacao.application.preparation import PreparationResult
from roteirizacao.domain.enums import ClasseOperacional, SeveridadeEvento, TipoEventoAuditoria
from roteirizacao.domain.events import EventoAuditoria
from roteirizacao.domain.optimization import InstanciaRoteirizacaoBase, VeiculoRoteirizacao
from roteirizacao.domain.results import OrdemNaoAtendida, ParadaPlanejada, ResumoOperacional, RotaPlanejada
from roteirizacao.domain.services import ContextoExecucao
from roteirizacao.optimization import PyVRPModelPayload

DIMENSAO_FINANCEIRA = "financeiro"


@dataclass(slots=True, frozen=True)
class SolverExecutionArtifact:
    instancia: InstanciaRoteirizacaoBase
    payload: PyVRPModelPayload
    solver_result: Any


@dataclass(slots=True)
class ClassPostProcessingResult:
    classe_operacional: ClasseOperacional
    rotas: list[RotaPlanejada] = field(default_factory=list)
    ordens_nao_atendidas: list[OrdemNaoAtendida] = field(default_factory=list)
    eventos: list[EventoAuditoria] = field(default_factory=list)


@dataclass(slots=True)
class PostProcessingResult:
    rotas_por_classe: dict[ClasseOperacional, list[RotaPlanejada]]
    ordens_nao_atendidas: list[OrdemNaoAtendida]
    resumo_operacional: ResumoOperacional
    eventos: list[EventoAuditoria]


class RoutePostProcessor:
    def __init__(self, contexto: ContextoExecucao) -> None:
        self.contexto = contexto
        self._counter = count(1)

    def process_execution(self, artifact: SolverExecutionArtifact) -> ClassPostProcessingResult:
        instancia = artifact.instancia
        payload = artifact.payload
        solver_result = artifact.solver_result
        solution = solver_result.best

        eventos = [
            self._event(
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

        return ClassPostProcessingResult(
            classe_operacional=instancia.classe_operacional,
            rotas=rotas,
            ordens_nao_atendidas=ordens_nao_atendidas,
            eventos=eventos,
        )

    def consolidate(
        self,
        preparation_result: PreparationResult,
        processed_classes: Iterable[ClassPostProcessingResult],
    ) -> PostProcessingResult:
        rotas_por_classe: dict[ClasseOperacional, list[RotaPlanejada]] = {
            ClasseOperacional.SUPRIMENTO: [],
            ClasseOperacional.RECOLHIMENTO: [],
        }
        ordens_nao_atendidas: list[OrdemNaoAtendida] = []
        eventos: list[EventoAuditoria] = []

        for processed in processed_classes:
            rotas_por_classe[processed.classe_operacional].extend(processed.rotas)
            ordens_nao_atendidas.extend(processed.ordens_nao_atendidas)
            eventos.extend(processed.eventos)

        resumo = self._build_summary(preparation_result, rotas_por_classe, ordens_nao_atendidas)
        return PostProcessingResult(
            rotas_por_classe=rotas_por_classe,
            ordens_nao_atendidas=ordens_nao_atendidas,
            resumo_operacional=resumo,
            eventos=eventos,
        )

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

    def _estimate_route_cost(self, route: Any, veiculo: VeiculoRoteirizacao) -> Decimal:
        distance_km = Decimal(route.distance()) / Decimal("1000")
        distance_cost = distance_km * veiculo.custo_variavel
        return (veiculo.custo_fixo + distance_cost).quantize(Decimal("0.01"))

    def _event(
        self,
        *,
        entidade_afetada: str,
        id_entidade: str | None,
        regra_relacionada: str,
        motivo: str,
        severidade: SeveridadeEvento = SeveridadeEvento.INFO,
        contexto_adicional: dict[str, Any] | None = None,
    ) -> EventoAuditoria:
        return EventoAuditoria(
            id_evento=f"evt-post-{next(self._counter):06d}",
            tipo_evento=TipoEventoAuditoria.ROTEIRIZACAO,
            severidade=severidade,
            entidade_afetada=entidade_afetada,
            id_entidade=id_entidade,
            regra_relacionada=regra_relacionada,
            motivo=motivo,
            timestamp_evento=self.contexto.timestamp_referencia,
            id_execucao=self.contexto.id_execucao,
            contexto_adicional=contexto_adicional,
        )

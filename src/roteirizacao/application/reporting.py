from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from itertools import count
from typing import Iterable

from roteirizacao.application.preparation import PreparationResult
from roteirizacao.domain.enums import ClasseOperacional, ClassePlanejamento, TipoEventoAuditoria
from roteirizacao.domain.events import EventoAuditoria
from roteirizacao.domain.results import (
    KpiGerencial,
    KpiOperacional,
    MotivoInviabilidade,
    OrdemNaoAtendida,
    RelatorioPlanejamento,
    RotaPlanejada,
)
from roteirizacao.domain.services import ContextoExecucao


@dataclass(slots=True)
class ReportingResult:
    kpi_operacional: KpiOperacional
    kpi_gerencial: KpiGerencial
    relatorio_planejamento: RelatorioPlanejamento


class PlanningReportingBuilder:
    def __init__(self, contexto: ContextoExecucao) -> None:
        self.contexto = contexto
        self._counter = count(1)

    def build(
        self,
        *,
        status_final,
        preparation_result: PreparationResult,
        rotas_por_classe: dict[ClasseOperacional, list[RotaPlanejada]],
        ordens_nao_atendidas: Iterable[OrdemNaoAtendida],
        eventos_auditoria: Iterable[EventoAuditoria],
        motivos_inviabilidade: Iterable[MotivoInviabilidade],
    ) -> ReportingResult:
        todas_rotas = [rota for rotas in rotas_por_classe.values() for rota in rotas]
        ordens_nao_atendidas = list(ordens_nao_atendidas)
        eventos_auditoria = list(eventos_auditoria)
        motivos_inviabilidade = list(motivos_inviabilidade)
        ordens_atendidas_ids = [parada.id_ordem for rota in todas_rotas for parada in rota.paradas]
        ordens_classificadas = {ordem.ordem.id_ordem: ordem for ordem in preparation_result.ordens_classificadas}

        total_ordens_atendidas = len(ordens_atendidas_ids)
        total_ordens_especiais_atendidas = sum(
            1
            for id_ordem in ordens_atendidas_ids
            if id_ordem in ordens_classificadas
            and ordens_classificadas[id_ordem].ordem.classe_planejamento == ClassePlanejamento.ESPECIAL
        )
        tempo_total_servico = sum(
            int((parada.fim_previsto - parada.inicio_previsto).total_seconds())
            for rota in todas_rotas
            for parada in rota.paradas
        )
        distancia_total = sum(rota.distancia_estimada for rota in todas_rotas)
        duracao_total = sum(rota.duracao_estimada_segundos for rota in todas_rotas)
        denominador_atendimento = total_ordens_atendidas + len(ordens_nao_atendidas)
        taxa_atendimento = Decimal("1") if denominador_atendimento == 0 else (
            Decimal(total_ordens_atendidas) / Decimal(denominador_atendimento)
        )

        viaturas_disponiveis = {viatura.id_viatura for viatura in preparation_result.viaturas}
        viaturas_acionadas = {rota.id_viatura for rota in todas_rotas}
        utilizacao_frota = Decimal("0") if not viaturas_disponiveis else (
            Decimal(len(viaturas_acionadas)) / Decimal(len(viaturas_disponiveis))
        )

        impacto_cancelamentos = sum(
            (ordem.impacto_financeiro_previsto for ordem in preparation_result.ordens_canceladas),
            start=Decimal("0"),
        )
        valor_total_taxas_improdutivas = sum(
            (
                ordem.impacto_financeiro_previsto
                for ordem in preparation_result.ordens_canceladas
                if ordem.impacto_operacional == "parada_improdutiva"
            ),
            start=Decimal("0"),
        )
        custo_total = sum((rota.custo_estimado for rota in todas_rotas), start=Decimal("0"))
        penalidade_total = sum((ordem.penalidade_aplicada for ordem in ordens_nao_atendidas), start=Decimal("0"))
        custo_medio_por_rota = Decimal("0") if not todas_rotas else custo_total / Decimal(len(todas_rotas))
        custo_medio_por_ordem = Decimal("0") if total_ordens_atendidas == 0 else custo_total / Decimal(total_ordens_atendidas)

        kpi_operacional = KpiOperacional(
            distancia_total_estimada=distancia_total,
            duracao_total_estimada_segundos=duracao_total,
            tempo_total_servico_segundos=tempo_total_servico,
            taxa_atendimento=self._quantize_ratio(taxa_atendimento),
            utilizacao_frota=self._quantize_ratio(utilizacao_frota),
            rotas_com_limite_segurado=sum(1 for rota in todas_rotas if rota.atingiu_limite_segurado),
            total_ordens_atendidas=total_ordens_atendidas,
            total_ordens_especiais_atendidas=total_ordens_especiais_atendidas,
            viaturas_acionadas=len(viaturas_acionadas),
            total_paradas_improdutivas=sum(
                1 for ordem in preparation_result.ordens_canceladas if ordem.impacto_operacional == "parada_improdutiva"
            ),
            total_ordens_excluidas_por_restricao=len(preparation_result.ordens_excluidas),
        )
        kpi_gerencial = KpiGerencial(
            custo_total_estimado=custo_total.quantize(Decimal("0.01")),
            penalidade_total_nao_atendimento=penalidade_total.quantize(Decimal("0.01")),
            impacto_financeiro_cancelamentos=impacto_cancelamentos.quantize(Decimal("0.01")),
            valor_total_taxas_improdutivas=valor_total_taxas_improdutivas.quantize(Decimal("0.01")),
            custo_medio_por_rota=custo_medio_por_rota.quantize(Decimal("0.01")),
            custo_medio_por_ordem_planejada=custo_medio_por_ordem.quantize(Decimal("0.01")),
        )
        relatorio = RelatorioPlanejamento(
            id_execucao=self.contexto.id_execucao,
            data_operacao=self.contexto.data_operacao,
            status_final=status_final,
            total_ordens_atendidas=total_ordens_atendidas,
            total_ordens_especiais_atendidas=total_ordens_especiais_atendidas,
            total_ordens_nao_atendidas=len(ordens_nao_atendidas),
            total_ordens_excluidas=len(preparation_result.ordens_excluidas),
            total_ordens_canceladas=len(preparation_result.ordens_canceladas),
            total_viaturas_acionadas=len(viaturas_acionadas),
            total_eventos_auditoria=len(eventos_auditoria),
            total_motivos_inviabilidade=len(motivos_inviabilidade),
            classes_processadas=tuple(sorted(classe.value for classe, rotas in rotas_por_classe.items() if rotas)),
            custo_total_estimado=kpi_gerencial.custo_total_estimado,
            impacto_financeiro_cancelamentos=kpi_gerencial.impacto_financeiro_cancelamentos,
            destaques=self._build_highlights(
                kpi_operacional=kpi_operacional,
                ordens_nao_atendidas=ordens_nao_atendidas,
                ordens_excluidas=preparation_result.ordens_excluidas,
                ordens_canceladas=preparation_result.ordens_canceladas,
            ),
        )
        return ReportingResult(
            kpi_operacional=kpi_operacional,
            kpi_gerencial=kpi_gerencial,
            relatorio_planejamento=relatorio,
        )

    def _build_highlights(
        self,
        *,
        kpi_operacional: KpiOperacional,
        ordens_nao_atendidas: list[OrdemNaoAtendida],
        ordens_excluidas,
        ordens_canceladas,
    ) -> tuple[str, ...]:
        highlights: list[str] = []
        if ordens_nao_atendidas:
            highlights.append("ha_ordens_nao_atendidas")
        if ordens_excluidas:
            highlights.append("ha_ordens_excluidas_antes_do_planejamento")
        if ordens_canceladas:
            highlights.append("ha_cancelamentos_com_impacto")
        if kpi_operacional.rotas_com_limite_segurado:
            highlights.append("ha_rotas_no_limite_segurado")
        if kpi_operacional.total_paradas_improdutivas:
            highlights.append("ha_paradas_improdutivas")
        return tuple(highlights)

    def _quantize_ratio(self, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

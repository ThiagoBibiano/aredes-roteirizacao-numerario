from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from decimal import Decimal
from hashlib import sha256
from itertools import count
from typing import Any

from roteirizacao.application.preparation import PreparationResult
from roteirizacao.domain.enums import ClasseOperacional, SeveridadeEvento, TipoEventoAuditoria
from roteirizacao.domain.events import ErroValidacao, EventoAuditoria
from roteirizacao.domain.models import Base, OrdemClassificada, Ponto, Viatura
from roteirizacao.domain.optimization import (
    DepositoRoteirizacao,
    InstanciaRoteirizacaoBase,
    NoRoteirizacao,
    PenalidadeRoteirizacao,
    RestricaoElegibilidade,
    VeiculoRoteirizacao,
)
from roteirizacao.domain.serialization import serialize_value
from roteirizacao.domain.services import ContextoExecucao

DIMENSAO_FINANCEIRA = "financeiro"
DIMENSAO_VOLUMETRICA = "volume"


@dataclass(slots=True)
class InstanceBuildResult:
    instancias: dict[ClasseOperacional, InstanciaRoteirizacaoBase] = field(default_factory=dict)
    erros: list[ErroValidacao] = field(default_factory=list)
    eventos_auditoria: list[EventoAuditoria] = field(default_factory=list)

    @property
    def possui_erros(self) -> bool:
        return bool(self.erros)


class OptimizationInstanceBuilder:
    def __init__(self, contexto: ContextoExecucao) -> None:
        self.contexto = contexto
        self._counter = count(1)

    def build(self, preparation_result: PreparationResult) -> InstanceBuildResult:
        result = InstanceBuildResult()
        pontos_by_id = {ponto.id_ponto: ponto for ponto in preparation_result.pontos}
        bases_by_id = {base.id_base: base for base in preparation_result.bases}

        for classe_token, ordens in preparation_result.ordens_planejaveis_por_classe_operacional().items():
            classe_operacional = ClasseOperacional(classe_token)
            instancia, erros, eventos = self._build_instance(
                classe_operacional=classe_operacional,
                ordens=ordens,
                pontos_by_id=pontos_by_id,
                bases_by_id=bases_by_id,
                viaturas=preparation_result.viaturas,
            )
            result.erros.extend(erros)
            result.eventos_auditoria.extend(eventos)
            if instancia is not None:
                result.instancias[classe_operacional] = instancia

        return result

    def _build_instance(
        self,
        *,
        classe_operacional: ClasseOperacional,
        ordens: list[OrdemClassificada],
        pontos_by_id: dict[str, Ponto],
        bases_by_id: dict[str, Base],
        viaturas: list[Viatura],
    ) -> tuple[InstanciaRoteirizacaoBase | None, list[ErroValidacao], list[EventoAuditoria]]:
        erros: list[ErroValidacao] = []
        eventos: list[EventoAuditoria] = []

        nos = tuple(self._to_node(ordem, pontos_by_id[ordem.ordem.id_ponto]) for ordem in ordens)
        elegibilidades, viaturas_consideradas, ha_veiculo_elegivel = self._build_eligibility(
            classe_operacional=classe_operacional,
            nos=nos,
            ordens=ordens,
            pontos_by_id=pontos_by_id,
            viaturas=viaturas,
        )

        if not ha_veiculo_elegivel:
            erros.append(
                self._error(
                    entidade="InstanciaRoteirizacaoBase",
                    id_entidade=classe_operacional.value,
                    mensagem="classe operacional sem veiculos elegiveis",
                    valor_observado=classe_operacional.value,
                    valor_esperado="ao menos um veiculo elegivel",
                    codigo_regra="negocio.inviabilidade_operacional",
                )
            )
            eventos.append(
                self._event(
                    tipo_evento=TipoEventoAuditoria.CONSTRUCAO_INSTANCIA,
                    entidade_afetada="InstanciaRoteirizacaoBase",
                    id_entidade=classe_operacional.value,
                    regra_relacionada="construcao.instancia.inviavel",
                    motivo="classe operacional sem veiculos elegiveis",
                    severidade=SeveridadeEvento.ERRO,
                )
            )
            return None, erros, eventos

        veiculos = tuple(self._to_vehicle(viatura, classe_operacional) for viatura in viaturas_consideradas)
        depositos = tuple(
            DepositoRoteirizacao(
                id_deposito=f"dep-{base.id_base}",
                id_base=base.id_base,
                localizacao=base.localizacao,
            )
            for base in self._bases_da_instancia(viaturas_consideradas, bases_by_id)
        )

        penalidades = tuple(self._build_penalties(nos))
        janelas_tempo = {no.id_no: no.janela_tempo for no in nos}
        tempos_servico = {no.id_no: no.tempo_servico for no in nos}
        custos = {
            "fixo_por_veiculo": {veiculo.id_veiculo: veiculo.custo_fixo for veiculo in veiculos},
            "variavel_por_veiculo": {veiculo.id_veiculo: veiculo.custo_variavel for veiculo in veiculos},
        }
        parametros_construcao = {
            "total_nos": len(nos),
            "total_veiculos": len(veiculos),
            "dimensoes_capacidade": [DIMENSAO_VOLUMETRICA, DIMENSAO_FINANCEIRA],
            "classe_operacional": classe_operacional.value,
            "requires_financial_accretion": classe_operacional == ClasseOperacional.RECOLHIMENTO,
        }
        restricoes_extras = (
            "circuito_fechado",
            "isolamento_estado_fisico",
            "teto_segurado_aplicado" if classe_operacional == ClasseOperacional.RECOLHIMENTO else "capacidade_dupla",
        )
        metadados = ordens[0].ordem.metadados

        instancia = InstanciaRoteirizacaoBase(
            id_cenario=f"cenario-{self.contexto.id_execucao}-{classe_operacional.value}",
            classe_operacional=classe_operacional,
            depositos=depositos,
            nos_atendimento=nos,
            veiculos=veiculos,
            dimensoes_capacidade=(DIMENSAO_VOLUMETRICA, DIMENSAO_FINANCEIRA),
            janelas_tempo=janelas_tempo,
            tempos_servico=tempos_servico,
            custos=custos,
            penalidades=penalidades,
            elegibilidade_veiculo_no=elegibilidades,
            parametros_construcao=parametros_construcao,
            metadados=metadados,
            restricoes_extras=restricoes_extras,
        )
        hash_cenario = self._hash_instance(instancia)
        instancia = replace(instancia, hash_cenario=hash_cenario)

        eventos.append(
            self._event(
                tipo_evento=TipoEventoAuditoria.CONSTRUCAO_INSTANCIA,
                entidade_afetada="InstanciaRoteirizacaoBase",
                id_entidade=instancia.id_cenario,
                regra_relacionada="construcao.instancia",
                motivo="instancia solver-agnostic construida",
                contexto_adicional={
                    "classe_operacional": classe_operacional.value,
                    "hash_cenario": hash_cenario,
                    "total_nos": len(nos),
                    "total_veiculos": len(veiculos),
                },
            )
        )
        return instancia, erros, eventos

    def _to_node(self, ordem: OrdemClassificada, ponto: Ponto) -> NoRoteirizacao:
        return NoRoteirizacao(
            id_no=f"no-{ordem.ordem.id_ordem}",
            id_ordem=ordem.ordem.id_ordem,
            id_ponto=ordem.ordem.id_ponto,
            localizacao=ponto.localizacao,
            tipo_servico=ordem.ordem.tipo_servico,
            classe_operacional=ordem.ordem.classe_operacional,
            criticidade=ordem.ordem.criticidade,
            janela_tempo=ordem.ordem.janela_efetiva,
            tempo_servico=ordem.ordem.tempo_servico,
            demandas={
                DIMENSAO_VOLUMETRICA: ordem.ordem.volume_estimado,
                DIMENSAO_FINANCEIRA: ordem.ordem.valor_estimado,
            },
            penalidade_nao_atendimento=ordem.ordem.penalidade_nao_atendimento,
            penalidade_atraso=ordem.ordem.penalidade_atraso,
            metadados=ordem.ordem.metadados,
        )

    def _to_vehicle(self, viatura: Viatura, classe_operacional: ClasseOperacional) -> VeiculoRoteirizacao:
        capacidade_financeira = viatura.capacidade_financeira
        if classe_operacional == ClasseOperacional.RECOLHIMENTO:
            capacidade_financeira = min(viatura.capacidade_financeira, viatura.teto_segurado)

        return VeiculoRoteirizacao(
            id_veiculo=f"veh-{viatura.id_viatura}-{classe_operacional.value}",
            id_viatura=viatura.id_viatura,
            id_base_origem=viatura.id_base_origem,
            classe_operacional=classe_operacional,
            janela_operacao=viatura.turno,
            capacidades={
                DIMENSAO_VOLUMETRICA: viatura.capacidade_volumetrica,
                DIMENSAO_FINANCEIRA: capacidade_financeira,
            },
            custo_fixo=viatura.custo_fixo,
            custo_variavel=viatura.custo_variavel,
            teto_segurado=viatura.teto_segurado,
            compatibilidade_servico=tuple(sorted(viatura.compatibilidade_servico, key=lambda item: item.value)),
            compatibilidade_ponto=tuple(sorted(viatura.compatibilidade_ponto)),
            compatibilidade_setor=tuple(sorted(viatura.compatibilidade_setor)),
        )

    def _build_penalties(self, nos: tuple[NoRoteirizacao, ...]) -> list[PenalidadeRoteirizacao]:
        penalties: list[PenalidadeRoteirizacao] = []
        for no in nos:
            penalties.append(
                PenalidadeRoteirizacao(
                    id_penalidade=f"pen-{no.id_no}-nao_atendimento",
                    id_alvo=no.id_no,
                    tipo_penalidade="nao_atendimento",
                    valor=no.penalidade_nao_atendimento,
                )
            )
            penalties.append(
                PenalidadeRoteirizacao(
                    id_penalidade=f"pen-{no.id_no}-atraso",
                    id_alvo=no.id_no,
                    tipo_penalidade="atraso",
                    valor=no.penalidade_atraso,
                )
            )
        return penalties

    def _build_eligibility(
        self,
        *,
        classe_operacional: ClasseOperacional,
        nos: tuple[NoRoteirizacao, ...],
        ordens: list[OrdemClassificada],
        pontos_by_id: dict[str, Ponto],
        viaturas: list[Viatura],
    ) -> tuple[tuple[RestricaoElegibilidade, ...], list[Viatura], bool]:
        restricoes: list[RestricaoElegibilidade] = []
        viaturas_consideradas = [viatura for viatura in viaturas if viatura.status_ativo]
        ordem_by_id = {ordem.ordem.id_ordem: ordem for ordem in ordens}
        ha_veiculo_elegivel = False

        for viatura in viaturas_consideradas:
            for no in nos:
                ordem = ordem_by_id[no.id_ordem]
                ponto = pontos_by_id[no.id_ponto]
                reasons: list[str] = []
                if ordem.ordem.tipo_servico not in viatura.compatibilidade_servico:
                    reasons.append("servico_incompativel")
                if viatura.compatibilidade_setor and ponto.setor_geografico not in viatura.compatibilidade_setor:
                    reasons.append("setor_incompativel")
                if viatura.compatibilidade_ponto and ponto.id_ponto not in viatura.compatibilidade_ponto:
                    reasons.append("ponto_incompativel")
                if ponto.compatibilidades_minimas.servicos and ordem.ordem.tipo_servico not in ponto.compatibilidades_minimas.servicos:
                    reasons.append("restricao_servico_do_ponto")

                elegivel = not reasons
                ha_veiculo_elegivel = ha_veiculo_elegivel or elegivel
                restricoes.append(
                    RestricaoElegibilidade(
                        id_veiculo=f"veh-{viatura.id_viatura}-{classe_operacional.value}",
                        id_no=no.id_no,
                        elegivel=elegivel,
                        motivo=None if elegivel else ",".join(reasons),
                    )
                )

        return tuple(restricoes), viaturas_consideradas, ha_veiculo_elegivel

    def _bases_da_instancia(self, viaturas: list[Viatura], bases_by_id: dict[str, Base]) -> list[Base]:
        seen: set[str] = set()
        bases: list[Base] = []
        for viatura in viaturas:
            if viatura.id_base_origem not in seen:
                seen.add(viatura.id_base_origem)
                bases.append(bases_by_id[viatura.id_base_origem])
        return bases

    def _hash_instance(self, instancia: InstanciaRoteirizacaoBase) -> str:
        payload = serialize_value(instancia)
        payload["hash_cenario"] = None
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return sha256(canonical.encode("utf-8")).hexdigest()

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
            id_evento=f"evt-inst-{next(self._counter):06d}",
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
            id_erro=f"err-inst-{next(self._counter):06d}",
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

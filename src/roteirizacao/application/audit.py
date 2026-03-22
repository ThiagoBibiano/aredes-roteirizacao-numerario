from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import Any, Iterable

from roteirizacao.application.preparation import PreparationResult
from roteirizacao.domain.enums import SeveridadeEvento, StatusExecucaoPlanejamento, TipoEventoAuditoria
from roteirizacao.domain.events import ErroContrato, ErroValidacao, EventoAuditoria
from roteirizacao.domain.results import LogPlanejamento, MotivoInviabilidade, OrdemNaoAtendida
from roteirizacao.domain.services import ContextoExecucao


@dataclass(slots=True)
class AuditTrailResult:
    eventos_auditoria: list[EventoAuditoria] = field(default_factory=list)
    motivos_inviabilidade: list[MotivoInviabilidade] = field(default_factory=list)
    log_planejamento: LogPlanejamento | None = None


class PlanningAuditTrailBuilder:
    def __init__(self, contexto: ContextoExecucao) -> None:
        self.contexto = contexto
        self._counter = count(1)

    def build(
        self,
        *,
        status_final: StatusExecucaoPlanejamento,
        eventos_existentes: Iterable[EventoAuditoria],
        erros: Iterable[ErroContrato | ErroValidacao],
        preparation_result: PreparationResult,
        ordens_nao_atendidas: Iterable[OrdemNaoAtendida],
        hashes_cenario: dict[str, str],
        parametros_planejamento: dict[str, Any],
    ) -> AuditTrailResult:
        eventos = list(eventos_existentes)
        motivos: dict[tuple[str, str, str | None, str], MotivoInviabilidade] = {}

        for erro in erros:
            if not self._has_event(
                eventos,
                tipo_evento=TipoEventoAuditoria.ERRO,
                entidade_afetada=erro.entidade,
                id_entidade=getattr(erro, "id_entidade", None),
            ):
                eventos.append(
                    self._event(
                        tipo_evento=TipoEventoAuditoria.ERRO,
                        entidade_afetada=erro.entidade,
                        id_entidade=getattr(erro, "id_entidade", None),
                        regra_relacionada=getattr(erro, "codigo_regra", getattr(erro, "codigo_erro", "auditoria.erro")),
                        motivo="erro consolidado pela auditoria",
                        severidade=getattr(erro, "severidade", SeveridadeEvento.ERRO),
                        campo_afetado=getattr(erro, "campo", None),
                        valor_observado=getattr(erro, "valor_observado", None),
                        valor_esperado=getattr(erro, "valor_esperado", None),
                    )
                )
            self._register_reason(
                motivos,
                codigo=getattr(erro, "codigo_regra", getattr(erro, "codigo_erro", "erro_auditoria")),
                descricao=erro.mensagem,
                entidade=erro.entidade,
                id_entidade=getattr(erro, "id_entidade", None),
                severidade=getattr(erro, "severidade", SeveridadeEvento.ERRO),
                origem="erro",
                regra_relacionada=getattr(erro, "codigo_regra", getattr(erro, "codigo_erro", None)),
                contexto={
                    "campo": getattr(erro, "campo", None),
                    "valor_observado": getattr(erro, "valor_observado", None),
                    "valor_esperado": getattr(erro, "valor_esperado", None),
                },
            )

        for ordem in preparation_result.ordens_excluidas:
            codigo = ordem.motivo_exclusao or "exclusao_sem_motivo"
            if ordem.motivo_exclusao is None:
                eventos.append(
                    self._event(
                        tipo_evento=TipoEventoAuditoria.ERRO,
                        entidade_afetada="Ordem",
                        id_entidade=ordem.ordem.id_ordem,
                        regra_relacionada="auditoria.motivo_exclusao_ausente",
                        motivo="ordem excluida sem motivo explicito",
                        severidade=SeveridadeEvento.ERRO,
                    )
                )
            if not self._has_event(
                eventos,
                tipo_evento=TipoEventoAuditoria.EXCLUSAO,
                entidade_afetada="Ordem",
                id_entidade=ordem.ordem.id_ordem,
            ):
                eventos.append(
                    self._event(
                        tipo_evento=TipoEventoAuditoria.EXCLUSAO,
                        entidade_afetada="Ordem",
                        id_entidade=ordem.ordem.id_ordem,
                        regra_relacionada="auditoria.cutoff_exclusao",
                        motivo="evento de exclusao consolidado pela auditoria",
                        severidade=SeveridadeEvento.AVISO,
                        campo_afetado="motivo_exclusao",
                        valor_observado=codigo,
                    )
                )
            self._register_reason(
                motivos,
                codigo=codigo,
                descricao="ordem excluida antes do planejamento",
                entidade="Ordem",
                id_entidade=ordem.ordem.id_ordem,
                severidade=SeveridadeEvento.AVISO,
                origem="cutoff",
                regra_relacionada="negocio.cutoff_exclusao",
                contexto={
                    "status_ordem": ordem.status_ordem.value,
                    "elegivel_no_cutoff": ordem.elegivel_no_cutoff,
                },
            )

        for ordem in preparation_result.ordens_canceladas:
            codigo = ordem.motivo_exclusao or "cancelamento_sem_motivo"
            if not self._has_event(
                eventos,
                tipo_evento=TipoEventoAuditoria.CANCELAMENTO,
                entidade_afetada="Ordem",
                id_entidade=ordem.ordem.id_ordem,
            ):
                eventos.append(
                    self._event(
                        tipo_evento=TipoEventoAuditoria.CANCELAMENTO,
                        entidade_afetada="Ordem",
                        id_entidade=ordem.ordem.id_ordem,
                        regra_relacionada="auditoria.cancelamento",
                        motivo="evento de cancelamento consolidado pela auditoria",
                        severidade=SeveridadeEvento.AVISO,
                        campo_afetado="status_cancelamento",
                        valor_observado=ordem.ordem.status_cancelamento.value,
                    )
                )
            self._register_reason(
                motivos,
                codigo=codigo,
                descricao="ordem cancelada apos o cut-off",
                entidade="Ordem",
                id_entidade=ordem.ordem.id_ordem,
                severidade=SeveridadeEvento.AVISO,
                origem="cancelamento",
                regra_relacionada="negocio.cancelamento_tardio",
                contexto={
                    "impacto_financeiro_previsto": str(ordem.impacto_financeiro_previsto),
                    "impacto_operacional": ordem.impacto_operacional,
                },
            )

        for ordem in ordens_nao_atendidas:
            self._register_reason(
                motivos,
                codigo=ordem.motivo,
                descricao="ordem nao atendida pelo solver",
                entidade="Ordem",
                id_entidade=ordem.id_ordem,
                severidade=SeveridadeEvento.AVISO,
                origem="roteirizacao",
                regra_relacionada="roteirizacao.nao_atendimento",
                contexto={"penalidade_aplicada": str(ordem.penalidade_aplicada)},
            )

        eventos.append(
            self._event(
                tipo_evento=TipoEventoAuditoria.SAIDA,
                entidade_afetada="ResultadoPlanejamento",
                id_entidade=self.contexto.id_execucao,
                regra_relacionada="auditoria.parametros_planejamento",
                motivo="parametros e hashes da execucao consolidados para auditoria",
                contexto_adicional={
                    **parametros_planejamento,
                    "hashes_cenario": hashes_cenario,
                    "status_final": status_final.value,
                },
            )
        )
        eventos.sort(key=lambda item: (item.timestamp_evento, item.id_evento))

        log_planejamento = LogPlanejamento(
            id_execucao=self.contexto.id_execucao,
            data_operacao=self.contexto.data_operacao,
            status_final=status_final,
            cutoff=self.contexto.cutoff,
            timestamp_referencia=self.contexto.timestamp_referencia,
            total_eventos=len(eventos),
            total_erros=len(list(erros)),
            total_motivos_inviabilidade=len(motivos),
            parametros_planejamento={
                **parametros_planejamento,
                "hashes_cenario": hashes_cenario,
            },
        )
        return AuditTrailResult(
            eventos_auditoria=eventos,
            motivos_inviabilidade=list(motivos.values()),
            log_planejamento=log_planejamento,
        )

    def _register_reason(
        self,
        motivos: dict[tuple[str, str, str | None, str], MotivoInviabilidade],
        *,
        codigo: str,
        descricao: str,
        entidade: str,
        id_entidade: str | None,
        severidade: SeveridadeEvento,
        origem: str,
        regra_relacionada: str | None,
        contexto: dict[str, Any] | None = None,
    ) -> None:
        key = (codigo, entidade, id_entidade, origem)
        motivos[key] = MotivoInviabilidade(
            codigo=codigo,
            descricao=descricao,
            entidade=entidade,
            id_entidade=id_entidade,
            severidade=severidade,
            origem=origem,
            regra_relacionada=regra_relacionada,
            contexto=contexto or {},
        )

    def _has_event(
        self,
        eventos: Iterable[EventoAuditoria],
        *,
        tipo_evento: TipoEventoAuditoria,
        entidade_afetada: str,
        id_entidade: str | None,
    ) -> bool:
        for evento in eventos:
            if (
                evento.tipo_evento == tipo_evento
                and evento.entidade_afetada == entidade_afetada
                and evento.id_entidade == id_entidade
            ):
                return True
        return False

    def _event(
        self,
        *,
        tipo_evento: TipoEventoAuditoria,
        entidade_afetada: str,
        id_entidade: str | None,
        regra_relacionada: str,
        motivo: str,
        severidade: SeveridadeEvento = SeveridadeEvento.INFO,
        campo_afetado: str | None = None,
        valor_observado: Any = None,
        valor_esperado: Any = None,
        contexto_adicional: dict[str, Any] | None = None,
    ) -> EventoAuditoria:
        return EventoAuditoria(
            id_evento=f"evt-audit-{next(self._counter):06d}",
            tipo_evento=tipo_evento,
            severidade=severidade,
            entidade_afetada=entidade_afetada,
            id_entidade=id_entidade,
            regra_relacionada=regra_relacionada,
            motivo=motivo,
            timestamp_evento=self.contexto.timestamp_referencia,
            id_execucao=self.contexto.id_execucao,
            campo_afetado=campo_afetado,
            valor_observado=valor_observado,
            valor_esperado=valor_esperado,
            contexto_adicional=contexto_adicional,
        )

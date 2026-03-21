from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from roteirizacao.domain.events import ErroContrato, ErroValidacao, EventoAuditoria
from roteirizacao.domain.models import Base, BaseBruta, Ordem, OrdemBruta, OrdemClassificada, Ponto, PontoBruto, Viatura, ViaturaBruta
from roteirizacao.domain.services import ContextoExecucao, classify_ordem, validate_base, validate_ordem, validate_ponto, validate_viatura


@dataclass(slots=True)
class PreparationResult:
    bases: list[Base] = field(default_factory=list)
    pontos: list[Ponto] = field(default_factory=list)
    viaturas: list[Viatura] = field(default_factory=list)
    ordens_validadas: list[Ordem] = field(default_factory=list)
    ordens_classificadas: list[OrdemClassificada] = field(default_factory=list)
    ordens_planejaveis: list[OrdemClassificada] = field(default_factory=list)
    ordens_excluidas: list[OrdemClassificada] = field(default_factory=list)
    ordens_canceladas: list[OrdemClassificada] = field(default_factory=list)
    erros: list[ErroContrato | ErroValidacao] = field(default_factory=list)
    eventos_auditoria: list[EventoAuditoria] = field(default_factory=list)

    @property
    def possui_erros(self) -> bool:
        return bool(self.erros)

    def ordens_por_classe_operacional(self) -> dict[str, list[OrdemClassificada]]:
        agrupado: dict[str, list[OrdemClassificada]] = {}
        for ordem in self.ordens_classificadas:
            agrupado.setdefault(ordem.ordem.classe_operacional.value, []).append(ordem)
        return agrupado

    def ordens_planejaveis_por_classe_operacional(self) -> dict[str, list[OrdemClassificada]]:
        agrupado: dict[str, list[OrdemClassificada]] = {}
        for ordem in self.ordens_planejaveis:
            agrupado.setdefault(ordem.ordem.classe_operacional.value, []).append(ordem)
        return agrupado


class PreparationPipeline:
    def __init__(self, contexto: ContextoExecucao) -> None:
        self.contexto = contexto

    def run(
        self,
        *,
        bases_brutas: Iterable[BaseBruta],
        pontos_brutos: Iterable[PontoBruto],
        viaturas_brutas: Iterable[ViaturaBruta],
        ordens_brutas: Iterable[OrdemBruta],
    ) -> PreparationResult:
        result = PreparationResult()

        base_ids: set[str] = set()
        for raw in bases_brutas:
            item, errors, events = validate_base(raw, self.contexto)
            result.erros.extend(errors)
            result.eventos_auditoria.extend(events)
            if item is not None:
                result.bases.append(item)
                base_ids.add(item.id_base)

        ponto_ids: set[str] = set()
        for raw in pontos_brutos:
            item, errors, events = validate_ponto(raw, self.contexto)
            result.erros.extend(errors)
            result.eventos_auditoria.extend(events)
            if item is not None:
                result.pontos.append(item)
                ponto_ids.add(item.id_ponto)

        for raw in viaturas_brutas:
            item, errors, events = validate_viatura(raw, self.contexto, bases_existentes=base_ids)
            result.erros.extend(errors)
            result.eventos_auditoria.extend(events)
            if item is not None:
                result.viaturas.append(item)

        for raw in ordens_brutas:
            item, errors, events = validate_ordem(raw, self.contexto, pontos_existentes=ponto_ids)
            result.erros.extend(errors)
            result.eventos_auditoria.extend(events)
            if item is not None:
                result.ordens_validadas.append(item)

        for ordem in result.ordens_validadas:
            classified, events = classify_ordem(ordem, self.contexto)
            result.ordens_classificadas.append(classified)
            result.eventos_auditoria.extend(events)
            if classified.planeavel:
                result.ordens_planejaveis.append(classified)
            elif classified.status_ordem.value == "excluida":
                result.ordens_excluidas.append(classified)
            else:
                result.ordens_canceladas.append(classified)

        return result

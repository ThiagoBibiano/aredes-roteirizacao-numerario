from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from roteirizacao.domain.enums import SeveridadeEvento, TipoEventoAuditoria
from roteirizacao.domain.serialization import SerializableMixin


@dataclass(slots=True, frozen=True)
class ErroContrato(SerializableMixin):
    id_erro: str
    tipo_erro: str
    codigo_erro: str
    mensagem: str
    entidade: str
    campo: str | None
    valor_observado: Any
    origem: str
    timestamp: datetime
    id_execucao: str


@dataclass(slots=True, frozen=True)
class ErroValidacao(SerializableMixin):
    id_erro: str
    codigo_regra: str
    mensagem: str
    entidade: str
    id_entidade: str | None
    campo: str | None
    valor_observado: Any
    valor_esperado: Any
    severidade: SeveridadeEvento
    timestamp: datetime
    id_execucao: str


@dataclass(slots=True, frozen=True)
class EventoAuditoria(SerializableMixin):
    id_evento: str
    tipo_evento: TipoEventoAuditoria
    severidade: SeveridadeEvento
    entidade_afetada: str
    id_entidade: str | None
    regra_relacionada: str
    motivo: str
    timestamp_evento: datetime
    id_execucao: str
    campo_afetado: str | None = None
    valor_observado: Any = None
    valor_esperado: Any = None
    contexto_adicional: dict[str, Any] | None = None

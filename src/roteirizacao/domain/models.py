from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping

from roteirizacao.domain.enums import (
    ClasseOperacional,
    ClassePlanejamento,
    Criticidade,
    SeveridadeContratual,
    StatusCancelamento,
    StatusOrdem,
    TipoPonto,
    TipoServico,
    TipoViatura,
)
from roteirizacao.domain.serialization import SerializableMixin


@dataclass(slots=True, frozen=True)
class MetadadoIngestao(SerializableMixin):
    origem: str
    timestamp_ingestao: datetime
    versao_schema: str = "1.0"
    identificador_externo: str | None = None


@dataclass(slots=True, frozen=True)
class MetadadoRastreabilidade(SerializableMixin):
    id_execucao: str
    origem: str
    timestamp_referencia: datetime
    versao_schema: str = "1.0"
    hash_conteudo: str | None = None


@dataclass(slots=True, frozen=True)
class Coordenada(SerializableMixin):
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90 <= self.latitude <= 90:
            raise ValueError("latitude invalida")
        if not -180 <= self.longitude <= 180:
            raise ValueError("longitude invalida")


@dataclass(slots=True, frozen=True)
class JanelaTempo(SerializableMixin):
    inicio: datetime
    fim: datetime

    def __post_init__(self) -> None:
        if self.inicio.tzinfo is None or self.fim.tzinfo is None:
            raise ValueError("janela deve conter timezone")
        if self.fim < self.inicio:
            raise ValueError("fim da janela nao pode ser anterior ao inicio")


@dataclass(slots=True, frozen=True)
class CompatibilidadeOperacional(SerializableMixin):
    servicos: frozenset[TipoServico] = field(default_factory=frozenset)
    setores: frozenset[str] = field(default_factory=frozenset)
    tipos_ponto: frozenset[TipoPonto] = field(default_factory=frozenset)
    restricoes_acesso: frozenset[str] = field(default_factory=frozenset)


@dataclass(slots=True, frozen=True)
class BaseBruta(SerializableMixin):
    payload: Mapping[str, Any]
    metadado_ingestao: MetadadoIngestao


@dataclass(slots=True, frozen=True)
class PontoBruto(SerializableMixin):
    payload: Mapping[str, Any]
    metadado_ingestao: MetadadoIngestao


@dataclass(slots=True, frozen=True)
class ViaturaBruta(SerializableMixin):
    payload: Mapping[str, Any]
    metadado_ingestao: MetadadoIngestao


@dataclass(slots=True, frozen=True)
class OrdemBruta(SerializableMixin):
    payload: Mapping[str, Any]
    metadado_ingestao: MetadadoIngestao


@dataclass(slots=True, frozen=True)
class Base(SerializableMixin):
    id_base: str
    nome: str
    localizacao: Coordenada
    janela_operacao: JanelaTempo
    status_ativo: bool
    metadados: MetadadoRastreabilidade
    capacidade_expedicao: int | None = None
    codigo_externo: str | None = None
    atributos_operacionais: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class Ponto(SerializableMixin):
    id_ponto: str
    tipo_ponto: TipoPonto
    localizacao: Coordenada
    status_ativo: bool
    setor_geografico: str
    metadados: MetadadoRastreabilidade
    janelas_padrao: tuple[JanelaTempo, ...] = ()
    tempo_padrao_servico: int | None = None
    restricoes_acesso: tuple[str, ...] = ()
    compatibilidades_minimas: CompatibilidadeOperacional = field(default_factory=CompatibilidadeOperacional)
    endereco_textual: str | None = None


@dataclass(slots=True, frozen=True)
class Viatura(SerializableMixin):
    id_viatura: str
    tipo_viatura: TipoViatura
    id_base_origem: str
    turno: JanelaTempo
    custo_fixo: Decimal
    custo_variavel: Decimal
    capacidade_financeira: Decimal
    capacidade_volumetrica: Decimal
    teto_segurado: Decimal
    compatibilidade_servico: frozenset[TipoServico]
    status_ativo: bool
    metadados: MetadadoRastreabilidade
    compatibilidade_ponto: frozenset[str] = field(default_factory=frozenset)
    compatibilidade_setor: frozenset[str] = field(default_factory=frozenset)
    restricoes_jornada: tuple[str, ...] = ()
    atributos_operacionais: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class Ordem(SerializableMixin):
    id_ordem: str
    origem_ordem: str
    data_operacao: date
    versao_ordem: str
    timestamp_criacao: datetime
    id_ponto: str
    tipo_servico: TipoServico
    classe_planejamento: ClassePlanejamento
    classe_operacional: ClasseOperacional
    criticidade: Criticidade
    valor_estimado: Decimal
    volume_estimado: Decimal
    tempo_servico: int
    janela_efetiva: JanelaTempo
    penalidade_nao_atendimento: Decimal
    penalidade_atraso: Decimal
    status_ordem: StatusOrdem
    status_cancelamento: StatusCancelamento
    taxa_improdutiva: Decimal
    metadados: MetadadoRastreabilidade
    sla: str | None = None
    compatibilidade_requerida: tuple[str, ...] = ()
    instante_cancelamento: datetime | None = None
    elegivel_no_cutoff: bool | None = None
    motivo_exclusao: str | None = None
    impacto_financeiro_previsto: Decimal | None = None
    severidade_contratual: SeveridadeContratual | None = None
    janela_cancelamento: JanelaTempo | None = None


@dataclass(slots=True, frozen=True)
class OrdemClassificada(SerializableMixin):
    ordem: Ordem
    status_ordem: StatusOrdem
    elegivel_no_cutoff: bool
    planeavel: bool
    motivo_exclusao: str | None
    impacto_financeiro_previsto: Decimal
    impacto_operacional: str | None

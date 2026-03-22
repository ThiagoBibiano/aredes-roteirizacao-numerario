from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from roteirizacao.domain.enums import ClasseOperacional, Criticidade, SeveridadeEvento, StatusExecucaoPlanejamento, TipoServico
from roteirizacao.domain.events import ErroContrato, ErroValidacao, EventoAuditoria
from roteirizacao.domain.models import OrdemClassificada
from roteirizacao.domain.serialization import SerializableMixin


@dataclass(slots=True, frozen=True)
class ParadaPlanejada(SerializableMixin):
    sequencia: int
    id_ordem: str
    id_no: str
    id_ponto: str
    tipo_servico: TipoServico
    criticidade: Criticidade
    inicio_previsto: datetime
    fim_previsto: datetime
    demanda: dict[str, Decimal]
    carga_acumulada: dict[str, Decimal]
    folga_janela_segundos: int
    espera_segundos: int = 0
    atraso_segundos: int = 0

    def __post_init__(self) -> None:
        if self.sequencia < 1:
            raise ValueError("sequencia da parada deve ser positiva")
        if self.inicio_previsto.tzinfo is None or self.fim_previsto.tzinfo is None:
            raise ValueError("parada deve conter timezone")
        if self.fim_previsto < self.inicio_previsto:
            raise ValueError("fim previsto nao pode ser anterior ao inicio previsto")


@dataclass(slots=True, frozen=True)
class RotaPlanejada(SerializableMixin):
    id_rota: str
    id_viatura: str
    id_base: str
    classe_operacional: ClasseOperacional
    paradas: tuple[ParadaPlanejada, ...]
    inicio_previsto: datetime
    fim_previsto: datetime
    distancia_estimada: int
    duracao_estimada_segundos: int
    custo_estimado: Decimal
    carga_total: dict[str, Decimal]
    atingiu_limite_segurado: bool
    possui_violacao_janela: bool
    possui_excesso_capacidade: bool

    def __post_init__(self) -> None:
        if self.inicio_previsto.tzinfo is None or self.fim_previsto.tzinfo is None:
            raise ValueError("rota deve conter timezone")
        if self.fim_previsto < self.inicio_previsto:
            raise ValueError("fim previsto da rota nao pode ser anterior ao inicio")


@dataclass(slots=True, frozen=True)
class OrdemNaoAtendida(SerializableMixin):
    id_ordem: str
    id_no: str
    id_ponto: str
    tipo_servico: TipoServico
    classe_operacional: ClasseOperacional
    criticidade: Criticidade
    penalidade_aplicada: Decimal
    motivo: str


@dataclass(slots=True, frozen=True)
class ResumoOperacional(SerializableMixin):
    total_rotas: int
    total_rotas_suprimento: int
    total_rotas_recolhimento: int
    total_ordens_planejadas: int
    total_ordens_nao_atendidas: int
    total_ordens_excluidas: int
    total_ordens_canceladas: int


@dataclass(slots=True, frozen=True)
class KpiOperacional(SerializableMixin):
    distancia_total_estimada: int
    duracao_total_estimada_segundos: int
    taxa_atendimento: Decimal
    utilizacao_frota: Decimal
    rotas_com_limite_segurado: int


@dataclass(slots=True, frozen=True)
class KpiGerencial(SerializableMixin):
    custo_total_estimado: Decimal
    penalidade_total_nao_atendimento: Decimal
    custo_medio_por_rota: Decimal
    custo_medio_por_ordem_planejada: Decimal


@dataclass(slots=True, frozen=True)
class MotivoInviabilidade(SerializableMixin):
    codigo: str
    descricao: str
    entidade: str
    id_entidade: str | None
    severidade: SeveridadeEvento
    origem: str
    regra_relacionada: str | None = None
    contexto: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class LogPlanejamento(SerializableMixin):
    id_execucao: str
    data_operacao: date
    status_final: StatusExecucaoPlanejamento
    cutoff: datetime
    timestamp_referencia: datetime
    total_eventos: int
    total_erros: int
    total_motivos_inviabilidade: int
    parametros_planejamento: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ResultadoPlanejamento(SerializableMixin):
    id_execucao: str
    data_operacao: date
    status_final: StatusExecucaoPlanejamento
    resumo_operacional: ResumoOperacional
    kpi_operacional: KpiOperacional
    kpi_gerencial: KpiGerencial
    rotas_suprimento: tuple[RotaPlanejada, ...] = ()
    rotas_recolhimento: tuple[RotaPlanejada, ...] = ()
    ordens_nao_atendidas: tuple[OrdemNaoAtendida, ...] = ()
    ordens_excluidas: tuple[OrdemClassificada, ...] = ()
    ordens_canceladas: tuple[OrdemClassificada, ...] = ()
    eventos_auditoria: tuple[EventoAuditoria, ...] = ()
    erros: tuple[ErroContrato | ErroValidacao, ...] = ()
    hashes_cenario: dict[str, str] = field(default_factory=dict)
    log_planejamento: LogPlanejamento | None = None
    motivos_inviabilidade: tuple[MotivoInviabilidade, ...] = ()

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from roteirizacao.domain.enums import ClasseOperacional, Criticidade, TipoServico
from roteirizacao.domain.models import Coordenada, JanelaTempo, MetadadoRastreabilidade
from roteirizacao.domain.serialization import SerializableMixin


@dataclass(slots=True, frozen=True)
class DepositoRoteirizacao(SerializableMixin):
    id_deposito: str
    id_base: str
    localizacao: Coordenada


@dataclass(slots=True, frozen=True)
class NoRoteirizacao(SerializableMixin):
    id_no: str
    id_ordem: str
    id_ponto: str
    tipo_servico: TipoServico
    classe_operacional: ClasseOperacional
    criticidade: Criticidade
    janela_tempo: JanelaTempo
    tempo_servico: int
    demandas: dict[str, Decimal]
    penalidade_nao_atendimento: Decimal
    penalidade_atraso: Decimal
    metadados: MetadadoRastreabilidade


@dataclass(slots=True, frozen=True)
class VeiculoRoteirizacao(SerializableMixin):
    id_veiculo: str
    id_viatura: str
    id_base_origem: str
    classe_operacional: ClasseOperacional
    janela_operacao: JanelaTempo
    capacidades: dict[str, Decimal]
    custo_fixo: Decimal
    custo_variavel: Decimal
    teto_segurado: Decimal
    compatibilidade_servico: tuple[TipoServico, ...]
    compatibilidade_ponto: tuple[str, ...] = ()
    compatibilidade_setor: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class PenalidadeRoteirizacao(SerializableMixin):
    id_penalidade: str
    id_alvo: str
    tipo_penalidade: str
    valor: Decimal


@dataclass(slots=True, frozen=True)
class RestricaoElegibilidade(SerializableMixin):
    id_veiculo: str
    id_no: str
    elegivel: bool
    motivo: str | None = None


@dataclass(slots=True, frozen=True)
class InstanciaRoteirizacaoBase(SerializableMixin):
    id_cenario: str
    classe_operacional: ClasseOperacional
    depositos: tuple[DepositoRoteirizacao, ...]
    nos_atendimento: tuple[NoRoteirizacao, ...]
    veiculos: tuple[VeiculoRoteirizacao, ...]
    dimensoes_capacidade: tuple[str, ...]
    janelas_tempo: dict[str, JanelaTempo]
    tempos_servico: dict[str, int]
    custos: dict[str, dict[str, Decimal]]
    penalidades: tuple[PenalidadeRoteirizacao, ...]
    elegibilidade_veiculo_no: tuple[RestricaoElegibilidade, ...]
    parametros_construcao: dict[str, Any]
    metadados: MetadadoRastreabilidade
    custos_por_arco: dict[str, Decimal] = field(default_factory=dict)
    restricoes_extras: tuple[str, ...] = ()
    hash_cenario: str | None = None

    def __post_init__(self) -> None:
        if not self.depositos:
            raise ValueError("instancia deve conter ao menos um deposito")
        if not self.veiculos:
            raise ValueError("instancia deve conter ao menos um veiculo")
        if not self.nos_atendimento:
            raise ValueError("instancia deve conter ao menos um no de atendimento")

        no_ids = {no.id_no for no in self.nos_atendimento}
        veiculo_ids = {veiculo.id_veiculo for veiculo in self.veiculos}

        if set(self.janelas_tempo) != no_ids:
            raise ValueError("janelas_tempo deve cobrir todos os nos da instancia")
        if set(self.tempos_servico) != no_ids:
            raise ValueError("tempos_servico deve cobrir todos os nos da instancia")

        for veiculo in self.veiculos:
            if set(veiculo.capacidades) != set(self.dimensoes_capacidade):
                raise ValueError("veiculo deve declarar todas as dimensoes de capacidade")

        if len(self.penalidades) < len(self.nos_atendimento):
            raise ValueError("toda demanda deve possuir penalidade associada")

        for restricao in self.elegibilidade_veiculo_no:
            if restricao.id_no not in no_ids:
                raise ValueError("restricao de elegibilidade referencia no inexistente")
            if restricao.id_veiculo not in veiculo_ids:
                raise ValueError("restricao de elegibilidade referencia veiculo inexistente")

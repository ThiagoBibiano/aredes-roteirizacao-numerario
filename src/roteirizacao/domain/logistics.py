from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from roteirizacao.domain.models import MetadadoRastreabilidade
from roteirizacao.domain.serialization import SerializableMixin


@dataclass(slots=True, frozen=True)
class TrechoLogistico(SerializableMixin):
    id_origem: str
    id_destino: str
    distancia_metros: int | None
    tempo_segundos: int | None
    custo: Decimal | None
    disponivel: bool = True
    restricao: str | None = None

    def __post_init__(self) -> None:
        if self.disponivel:
            if self.distancia_metros is None or self.tempo_segundos is None or self.custo is None:
                raise ValueError("trecho disponivel deve possuir distancia, tempo e custo")
            if self.distancia_metros < 0 or self.tempo_segundos < 0 or self.custo < 0:
                raise ValueError("trecho disponivel nao pode possuir valores negativos")
        else:
            if self.distancia_metros is not None and self.distancia_metros < 0:
                raise ValueError("distancia de trecho indisponivel nao pode ser negativa")
            if self.tempo_segundos is not None and self.tempo_segundos < 0:
                raise ValueError("tempo de trecho indisponivel nao pode ser negativo")
            if self.custo is not None and self.custo < 0:
                raise ValueError("custo de trecho indisponivel nao pode ser negativo")

    @property
    def chave(self) -> str:
        return f"{self.id_origem}->{self.id_destino}"


@dataclass(slots=True, frozen=True)
class MatrizLogistica(SerializableMixin):
    id_matriz: str
    ids_localizacao: tuple[str, ...]
    trechos: tuple[TrechoLogistico, ...]
    estrategia_geracao: str
    timestamp_geracao: datetime
    metadados: MetadadoRastreabilidade
    unidade_distancia: str = "metros"
    unidade_tempo: str = "segundos"
    hash_matriz: str | None = None

    def __post_init__(self) -> None:
        if self.timestamp_geracao.tzinfo is None:
            raise ValueError("matriz logistica deve conter timezone")
        if len(set(self.ids_localizacao)) != len(self.ids_localizacao):
            raise ValueError("ids_localizacao da matriz devem ser unicos")

        localizacoes = set(self.ids_localizacao)
        expected_pairs = {
            (origem, destino)
            for origem in self.ids_localizacao
            for destino in self.ids_localizacao
        }
        observed_pairs: set[tuple[str, str]] = set()
        for trecho in self.trechos:
            pair = (trecho.id_origem, trecho.id_destino)
            if trecho.id_origem not in localizacoes or trecho.id_destino not in localizacoes:
                raise ValueError("trecho da matriz referencia localizacao inexistente")
            if pair in observed_pairs:
                raise ValueError("matriz logistica nao pode possuir trechos duplicados")
            observed_pairs.add(pair)

        if observed_pairs != expected_pairs:
            raise ValueError("matriz logistica deve cobrir todos os pares ordenados de localizacao")

    def trecho(self, id_origem: str, id_destino: str) -> TrechoLogistico:
        for trecho in self.trechos:
            if trecho.id_origem == id_origem and trecho.id_destino == id_destino:
                return trecho
        raise KeyError(f"trecho inexistente: {id_origem}->{id_destino}")

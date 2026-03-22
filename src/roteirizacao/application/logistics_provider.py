from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from itertools import count
from pathlib import Path
from typing import Iterable

from roteirizacao.application.logistics_matrix import LogisticsMatrixBuilder, hash_matrix_payload
from roteirizacao.domain.enums import SeveridadeEvento, TipoEventoAuditoria
from roteirizacao.domain.events import EventoAuditoria
from roteirizacao.domain.logistics import MatrizLogistica, TrechoLogistico
from roteirizacao.domain.optimization import DepositoRoteirizacao, NoRoteirizacao
from roteirizacao.domain.serialization import ensure_datetime
from roteirizacao.domain.services import ContextoExecucao


class SnapshotUnavailableError(FileNotFoundError):
    pass


class SnapshotCoverageError(ValueError):
    pass


class LogisticsMatrixProvider(ABC):
    @abstractmethod
    def build(
        self,
        *,
        id_matriz: str,
        depositos: Iterable[DepositoRoteirizacao],
        nos: Iterable[NoRoteirizacao],
        metadados,
    ) -> tuple[MatrizLogistica, list[EventoAuditoria]]:
        """Resolve a matriz logistica para a instancia solicitada."""


class PersistedSnapshotLogisticsMatrixProvider(LogisticsMatrixProvider):
    def __init__(self, contexto: ContextoExecucao, *, snapshot_dir: Path) -> None:
        self.contexto = contexto
        self.snapshot_dir = Path(snapshot_dir)
        self._counter = count(1)

    def build(
        self,
        *,
        id_matriz: str,
        depositos: Iterable[DepositoRoteirizacao],
        nos: Iterable[NoRoteirizacao],
        metadados,
    ) -> tuple[MatrizLogistica, list[EventoAuditoria]]:
        snapshot_path = self.snapshot_dir / f"{self.contexto.data_operacao.isoformat()}.json"
        if not snapshot_path.exists():
            raise SnapshotUnavailableError(f"snapshot nao encontrado: {snapshot_path}")

        payload = json.loads(snapshot_path.read_text())
        strategy_name = str(payload.get("strategy_name", "snapshot_persistido_v1"))
        generated_at = ensure_datetime(payload.get("generated_at"), "generated_at")
        arcs = payload.get("arcs")
        if not isinstance(arcs, list):
            raise SnapshotCoverageError("snapshot deve conter uma lista de arcos")

        localizacoes = list(depositos) + list(nos)
        ids_localizacao = tuple(self._location_id(item) for item in localizacoes)
        requested_pairs = [
            (origem, destino)
            for origem in ids_localizacao
            for destino in ids_localizacao
        ]

        arc_map: dict[tuple[str, str], dict] = {}
        for arc in arcs:
            if not isinstance(arc, dict):
                continue
            id_origem = str(arc.get("id_origem"))
            id_destino = str(arc.get("id_destino"))
            if id_origem in ids_localizacao and id_destino in ids_localizacao:
                arc_map[(id_origem, id_destino)] = arc

        missing_pairs = [pair for pair in requested_pairs if pair not in arc_map]
        if missing_pairs:
            raise SnapshotCoverageError(
                f"snapshot nao cobre todos os pares solicitados: {missing_pairs[0][0]}->{missing_pairs[0][1]}"
            )

        trechos: list[TrechoLogistico] = []
        for id_origem, id_destino in requested_pairs:
            raw_arc = arc_map[(id_origem, id_destino)]
            disponivel = bool(raw_arc.get("disponivel", True))
            custo_raw = raw_arc.get("custo")
            custo = None if custo_raw is None else Decimal(str(custo_raw))
            trechos.append(
                TrechoLogistico(
                    id_origem=id_origem,
                    id_destino=id_destino,
                    distancia_metros=raw_arc.get("distancia_metros"),
                    tempo_segundos=raw_arc.get("tempo_segundos"),
                    custo=custo,
                    disponivel=disponivel,
                    restricao=raw_arc.get("restricao"),
                )
            )

        matriz = MatrizLogistica(
            id_matriz=id_matriz,
            ids_localizacao=ids_localizacao,
            trechos=tuple(trechos),
            estrategia_geracao=strategy_name,
            timestamp_geracao=generated_at,
            metadados=metadados,
            hash_matriz=hash_matrix_payload(
                id_matriz=id_matriz,
                ids_localizacao=ids_localizacao,
                trechos=tuple(trechos),
                estrategia_geracao=strategy_name,
                timestamp_geracao=generated_at,
                metadados=metadados,
            ),
        )
        evento = self._event(
            id_entidade=id_matriz,
            regra_relacionada="carregamento.snapshot_logistico",
            motivo="snapshot logistico persistido carregado para a instancia",
            contexto_adicional={
                "fonte": "snapshot_persistido",
                "snapshot_path": str(snapshot_path),
                "snapshot_id": payload.get("snapshot_id"),
                "hash_matriz": matriz.hash_matriz,
                "estrategia_geracao": strategy_name,
            },
        )
        return matriz, [evento]

    def _location_id(self, item: DepositoRoteirizacao | NoRoteirizacao) -> str:
        if isinstance(item, DepositoRoteirizacao):
            return item.id_deposito
        return item.id_no

    def _event(
        self,
        *,
        id_entidade: str | None,
        regra_relacionada: str,
        motivo: str,
        severidade: SeveridadeEvento = SeveridadeEvento.INFO,
        contexto_adicional: dict | None = None,
    ) -> EventoAuditoria:
        return EventoAuditoria(
            id_evento=f"evt-provider-{next(self._counter):06d}",
            tipo_evento=TipoEventoAuditoria.CONSTRUCAO_INSTANCIA,
            severidade=severidade,
            entidade_afetada="MatrizLogistica",
            id_entidade=id_entidade,
            regra_relacionada=regra_relacionada,
            motivo=motivo,
            timestamp_evento=self.contexto.timestamp_referencia,
            id_execucao=self.contexto.id_execucao,
            contexto_adicional=contexto_adicional,
        )


class FallbackLogisticsMatrixProvider(LogisticsMatrixProvider):
    def __init__(
        self,
        contexto: ContextoExecucao,
        *,
        primary: LogisticsMatrixProvider,
        fallback: LogisticsMatrixBuilder,
    ) -> None:
        self.contexto = contexto
        self.primary = primary
        self.fallback = fallback
        self._counter = count(1)

    def build(
        self,
        *,
        id_matriz: str,
        depositos: Iterable[DepositoRoteirizacao],
        nos: Iterable[NoRoteirizacao],
        metadados,
    ) -> tuple[MatrizLogistica, list[EventoAuditoria]]:
        try:
            return self.primary.build(
                id_matriz=id_matriz,
                depositos=depositos,
                nos=nos,
                metadados=metadados,
            )
        except (SnapshotUnavailableError, SnapshotCoverageError, KeyError, ValueError, json.JSONDecodeError) as exc:
            matriz, eventos = self.fallback.build(
                id_matriz=id_matriz,
                depositos=depositos,
                nos=nos,
                metadados=metadados,
            )
            warning = self._event(
                id_entidade=id_matriz,
                regra_relacionada="carregamento.snapshot_logistico.fallback",
                motivo="snapshot persistido indisponivel ou invalido; fallback geometrico aplicado",
                severidade=SeveridadeEvento.AVISO,
                contexto_adicional={
                    "erro": str(exc),
                    "fonte": "fallback_builder_local",
                    "estrategia_geracao": matriz.estrategia_geracao,
                    "hash_matriz": matriz.hash_matriz,
                },
            )
            return matriz, [warning, *eventos]

    def _event(
        self,
        *,
        id_entidade: str | None,
        regra_relacionada: str,
        motivo: str,
        severidade: SeveridadeEvento,
        contexto_adicional: dict | None = None,
    ) -> EventoAuditoria:
        return EventoAuditoria(
            id_evento=f"evt-provider-{next(self._counter):06d}",
            tipo_evento=TipoEventoAuditoria.CONSTRUCAO_INSTANCIA,
            severidade=severidade,
            entidade_afetada="MatrizLogistica",
            id_entidade=id_entidade,
            regra_relacionada=regra_relacionada,
            motivo=motivo,
            timestamp_evento=self.contexto.timestamp_referencia,
            id_execucao=self.contexto.id_execucao,
            contexto_adicional=contexto_adicional,
        )

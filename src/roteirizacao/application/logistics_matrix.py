from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from math import asin, ceil, cos, radians, sin, sqrt
from typing import Iterable

from roteirizacao.domain.enums import SeveridadeEvento, TipoEventoAuditoria
from roteirizacao.domain.events import EventoAuditoria
from roteirizacao.domain.logistics import MatrizLogistica, TrechoLogistico
from roteirizacao.domain.optimization import DepositoRoteirizacao, NoRoteirizacao
from roteirizacao.domain.serialization import serialize_value
from roteirizacao.domain.services import ContextoExecucao


class LogisticsMatrixBuilder:
    def __init__(
        self,
        contexto: ContextoExecucao,
        *,
        strategy_name: str = "haversine_v1",
        average_speed_kmh: Decimal = Decimal("35"),
        base_cost_per_km: Decimal = Decimal("1.00"),
    ) -> None:
        self.contexto = contexto
        self.strategy_name = strategy_name
        self.average_speed_kmh = average_speed_kmh
        self.base_cost_per_km = base_cost_per_km

    def build(
        self,
        *,
        id_matriz: str,
        depositos: Iterable[DepositoRoteirizacao],
        nos: Iterable[NoRoteirizacao],
        metadados,
        arcos_indisponiveis: set[tuple[str, str]] | None = None,
    ) -> tuple[MatrizLogistica, EventoAuditoria]:
        localizacoes = list(depositos) + list(nos)
        ids_localizacao = tuple(self._location_id(item) for item in localizacoes)
        arcos_bloqueados = arcos_indisponiveis or set()

        trechos: list[TrechoLogistico] = []
        for origem in localizacoes:
            for destino in localizacoes:
                id_origem = self._location_id(origem)
                id_destino = self._location_id(destino)
                if (id_origem, id_destino) in arcos_bloqueados:
                    trechos.append(
                        TrechoLogistico(
                            id_origem=id_origem,
                            id_destino=id_destino,
                            distancia_metros=None,
                            tempo_segundos=None,
                            custo=None,
                            disponivel=False,
                            restricao="arco_indisponivel",
                        )
                    )
                    continue

                distancia_metros = self._distance_meters(origem.localizacao.latitude, origem.localizacao.longitude, destino.localizacao.latitude, destino.localizacao.longitude)
                tempo_segundos = self._travel_seconds(distancia_metros)
                custo = self._cost_for_distance(distancia_metros)
                trechos.append(
                    TrechoLogistico(
                        id_origem=id_origem,
                        id_destino=id_destino,
                        distancia_metros=distancia_metros,
                        tempo_segundos=tempo_segundos,
                        custo=custo,
                    )
                )

        matriz = MatrizLogistica(
            id_matriz=id_matriz,
            ids_localizacao=ids_localizacao,
            trechos=tuple(trechos),
            estrategia_geracao=self.strategy_name,
            timestamp_geracao=self.contexto.timestamp_referencia,
            metadados=metadados,
        )
        hash_matriz = self._hash_matrix(matriz)
        matriz = replace(matriz, hash_matriz=hash_matriz)
        evento = EventoAuditoria(
            id_evento=f"evt-matrix-{self.contexto.id_execucao}-{id_matriz}",
            tipo_evento=TipoEventoAuditoria.CONSTRUCAO_INSTANCIA,
            severidade=SeveridadeEvento.INFO,
            entidade_afetada="MatrizLogistica",
            id_entidade=id_matriz,
            regra_relacionada="construcao.matriz_logistica",
            motivo="malha logistica versionada e auditavel gerada para a instancia",
            timestamp_evento=self.contexto.timestamp_referencia,
            id_execucao=self.contexto.id_execucao,
            contexto_adicional={
                "estrategia_geracao": self.strategy_name,
                "hash_matriz": hash_matriz,
                "total_localizacoes": len(ids_localizacao),
                "total_trechos": len(trechos),
                "arcos_indisponiveis": len(arcos_bloqueados),
            },
        )
        return matriz, evento

    def _location_id(self, item: DepositoRoteirizacao | NoRoteirizacao) -> str:
        if isinstance(item, DepositoRoteirizacao):
            return item.id_deposito
        return item.id_no

    def _distance_meters(self, lat1: float, lon1: float, lat2: float, lon2: float) -> int:
        if lat1 == lat2 and lon1 == lon2:
            return 0
        raio_terra_m = 6_371_000
        d_lat = radians(lat2 - lat1)
        d_lon = radians(lon2 - lon1)
        a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
        c = 2 * asin(sqrt(a))
        return int(round(raio_terra_m * c))

    def _travel_seconds(self, distancia_metros: int) -> int:
        if distancia_metros == 0:
            return 0
        metros_por_segundo = float(self.average_speed_kmh) * 1000 / 3600
        return max(1, int(ceil(distancia_metros / metros_por_segundo)))

    def _cost_for_distance(self, distancia_metros: int) -> Decimal:
        distancia_km = Decimal(distancia_metros) / Decimal("1000")
        return (distancia_km * self.base_cost_per_km).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _hash_matrix(self, matriz: MatrizLogistica) -> str:
        payload = serialize_value(matriz)
        payload["hash_matriz"] = None
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return sha256(canonical.encode("utf-8")).hexdigest()

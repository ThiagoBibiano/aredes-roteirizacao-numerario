from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from roteirizacao.domain.enums import ClasseOperacional
from roteirizacao.domain.optimization import InstanciaRoteirizacaoBase, NoRoteirizacao, VeiculoRoteirizacao
from roteirizacao.optimization.solver_adapter import SolverAdapter


@dataclass(slots=True, frozen=True)
class PyVRPDepotData:
    name: str
    x: int
    y: int
    tw_early: int
    tw_late: int


@dataclass(slots=True, frozen=True)
class PyVRPClientData:
    name: str
    x: int
    y: int
    delivery: tuple[int, ...]
    pickup: tuple[int, ...]
    service_duration: int
    tw_early: int
    tw_late: int
    prize: int
    required: bool


@dataclass(slots=True, frozen=True)
class PyVRPVehicleTypeData:
    name: str
    start_depot: int
    end_depot: int
    capacity: tuple[int, ...]
    num_available: int
    fixed_cost: int
    unit_distance_cost: int
    unit_duration_cost: int
    tw_early: int
    tw_late: int
    profile: int = 0


@dataclass(slots=True, frozen=True)
class PyVRPEdgeData:
    frm: int
    to: int
    distance: int
    duration: int
    profile: int = 0


@dataclass(slots=True, frozen=True)
class PyVRPModelPayload:
    instance_id: str
    profile_name: str
    time_origin: datetime
    depots: tuple[PyVRPDepotData, ...]
    clients: tuple[PyVRPClientData, ...]
    vehicle_types: tuple[PyVRPVehicleTypeData, ...]
    edges: tuple[PyVRPEdgeData, ...]
    dimensions: tuple[str, ...]
    penalties: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class PyVRPAdapter(SolverAdapter):
    SERVICE_PRIORITY_BONUS = Decimal("100000000.00")

    def __init__(
        self,
        *,
        coordinate_scale: int = 1000,
        amount_scale: int = 100,
        duration_unit_seconds: int = 60,
    ) -> None:
        self.coordinate_scale = coordinate_scale
        self.amount_scale = amount_scale
        self.duration_unit_seconds = duration_unit_seconds

    def build_payload(self, instancia: InstanciaRoteirizacaoBase) -> PyVRPModelPayload:
        time_origin = self._time_origin(instancia)
        service_priority_bonus = self._service_priority_bonus(instancia)
        depots = tuple(
            PyVRPDepotData(
                name=deposito.id_deposito,
                x=self._scale_coordinate(deposito.localizacao.latitude),
                y=self._scale_coordinate(deposito.localizacao.longitude),
                tw_early=0,
                tw_late=self._offset_seconds(time_origin, self._max_vehicle_time(instancia)),
            )
            for deposito in instancia.depositos
        )
        depot_index = {deposito.id_deposito: idx for idx, deposito in enumerate(instancia.depositos)}

        clients = tuple(
            self._build_client(
                instancia,
                time_origin,
                no,
                service_priority_bonus=service_priority_bonus,
            )
            for no in instancia.nos_atendimento
        )
        vehicle_types = tuple(
            self._build_vehicle_type(instancia, time_origin, depot_index, veiculo)
            for veiculo in instancia.veiculos
        )
        edges = self._build_edges(instancia)
        penalties = {
            penalidade.id_alvo: self._scale_amount(penalidade.valor)
            for penalidade in instancia.penalidades
            if penalidade.tipo_penalidade == "nao_atendimento"
        }

        return PyVRPModelPayload(
            instance_id=instancia.id_cenario,
            profile_name=instancia.classe_operacional.value,
            time_origin=time_origin,
            depots=depots,
            clients=clients,
            vehicle_types=vehicle_types,
            edges=edges,
            dimensions=instancia.dimensoes_capacidade,
            penalties=penalties,
            metadata={
                "hash_cenario": instancia.hash_cenario,
                "classe_operacional": instancia.classe_operacional.value,
                "restricoes_extras": list(instancia.restricoes_extras),
                "hash_matriz": instancia.matriz_logistica.hash_matriz,
                "estrategia_matriz": instancia.matriz_logistica.estrategia_geracao,
            },
        )

    def build_model(self, instancia: InstanciaRoteirizacaoBase) -> Any:
        try:
            import pyvrp
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "pyvrp nao esta instalado no ambiente. Instale a biblioteca para construir o modelo nativo."
            ) from exc

        payload = self.build_payload(instancia)
        model = pyvrp.Model()
        native_profile = model.add_profile(name=payload.profile_name)

        locations: list[Any] = []
        for depot in payload.depots:
            locations.append(
                model.add_depot(
                    x=depot.x,
                    y=depot.y,
                    tw_early=depot.tw_early,
                    tw_late=depot.tw_late,
                    name=depot.name,
                )
            )

        for client in payload.clients:
            locations.append(
                model.add_client(
                    x=client.x,
                    y=client.y,
                    delivery=list(client.delivery),
                    pickup=list(client.pickup),
                    service_duration=client.service_duration,
                    tw_early=client.tw_early,
                    tw_late=client.tw_late,
                    prize=client.prize,
                    required=client.required,
                    name=client.name,
                )
            )

        for vehicle in payload.vehicle_types:
            model.add_vehicle_type(
                num_available=vehicle.num_available,
                capacity=list(vehicle.capacity),
                start_depot=locations[vehicle.start_depot],
                end_depot=locations[vehicle.end_depot],
                fixed_cost=vehicle.fixed_cost,
                tw_early=vehicle.tw_early,
                tw_late=vehicle.tw_late,
                unit_distance_cost=vehicle.unit_distance_cost,
                unit_duration_cost=vehicle.unit_duration_cost,
                profile=native_profile,
                name=vehicle.name,
            )

        for edge in payload.edges:
            model.add_edge(
                locations[edge.frm],
                locations[edge.to],
                distance=edge.distance,
                duration=edge.duration,
                profile=native_profile,
            )

        return model

    def _build_client(
        self,
        instancia: InstanciaRoteirizacaoBase,
        time_origin: datetime,
        no: NoRoteirizacao,
        *,
        service_priority_bonus: Decimal,
    ) -> PyVRPClientData:
        ordered_demands = [self._scale_amount(no.demandas[dimension]) for dimension in instancia.dimensoes_capacidade]

        if instancia.classe_operacional == ClasseOperacional.RECOLHIMENTO:
            pickup = tuple(ordered_demands)
            delivery = tuple(0 for _ in ordered_demands)
        else:
            delivery = tuple(ordered_demands)
            pickup = tuple(0 for _ in ordered_demands)

        return PyVRPClientData(
            name=no.id_no,
            x=self._scale_coordinate(no.localizacao.latitude),
            y=self._scale_coordinate(no.localizacao.longitude),
            delivery=delivery,
            pickup=pickup,
            service_duration=self._scale_duration_seconds(no.tempo_servico),
            tw_early=self._offset_seconds(time_origin, no.janela_tempo.inicio),
            tw_late=self._offset_seconds(time_origin, no.janela_tempo.fim),
            prize=self._scale_amount(no.penalidade_nao_atendimento + service_priority_bonus),
            required=False,
        )

    def _build_vehicle_type(
        self,
        instancia: InstanciaRoteirizacaoBase,
        time_origin: datetime,
        depot_index: dict[str, int],
        veiculo: VeiculoRoteirizacao,
    ) -> PyVRPVehicleTypeData:
        start_end = depot_index[f"dep-{veiculo.id_base_origem}"]
        capacity = tuple(self._scale_amount(veiculo.capacidades[dimension]) for dimension in instancia.dimensoes_capacidade)
        variable_cost = max(self._scale_amount(veiculo.custo_variavel), 1)
        return PyVRPVehicleTypeData(
            name=veiculo.id_veiculo,
            start_depot=start_end,
            end_depot=start_end,
            capacity=capacity,
            num_available=1,
            fixed_cost=self._scale_amount(veiculo.custo_fixo),
            unit_distance_cost=variable_cost,
            unit_duration_cost=1,
            tw_early=self._offset_seconds(time_origin, veiculo.janela_operacao.inicio),
            tw_late=self._offset_seconds(time_origin, veiculo.janela_operacao.fim),
        )

    def _build_edges(self, instancia: InstanciaRoteirizacaoBase) -> tuple[PyVRPEdgeData, ...]:
        index_by_location = {
            location_id: idx
            for idx, location_id in enumerate(instancia.matriz_logistica.ids_localizacao)
        }
        edges = []
        for trecho in instancia.matriz_logistica.trechos:
            if not trecho.disponivel:
                continue
            edges.append(
                PyVRPEdgeData(
                    frm=index_by_location[trecho.id_origem],
                    to=index_by_location[trecho.id_destino],
                    distance=trecho.distancia_metros or 0,
                    duration=trecho.tempo_segundos or 0,
                )
            )
        return tuple(edges)

    def _time_origin(self, instancia: InstanciaRoteirizacaoBase) -> datetime:
        candidates = [veiculo.janela_operacao.inicio for veiculo in instancia.veiculos]
        candidates.extend(no.janela_tempo.inicio for no in instancia.nos_atendimento)
        return min(candidates)

    def _max_vehicle_time(self, instancia: InstanciaRoteirizacaoBase) -> datetime:
        return max(veiculo.janela_operacao.fim for veiculo in instancia.veiculos)

    def _service_priority_bonus(self, instancia: InstanciaRoteirizacaoBase) -> Decimal:
        return self.SERVICE_PRIORITY_BONUS

    def _offset_seconds(self, origin: datetime, value: datetime) -> int:
        return int((value - origin).total_seconds())

    def _scale_coordinate(self, value: float) -> int:
        return int(round(value * self.coordinate_scale))

    def _scale_amount(self, value: Decimal) -> int:
        return int(round(float(value) * self.amount_scale))

    def _scale_duration_seconds(self, minutes: int) -> int:
        return minutes * self.duration_unit_seconds

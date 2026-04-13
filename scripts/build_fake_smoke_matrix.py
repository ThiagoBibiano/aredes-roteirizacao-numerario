#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class MatrixBuildConfig:
    dataset_dir: Path
    date: str
    detour_factor: float
    average_speed_mps: float
    cost_per_km: Decimal


def parse_args() -> MatrixBuildConfig:
    parser = argparse.ArgumentParser(
        description=(
            "Regenera a matriz logistica sintetica do dataset fake com base "
            "nas bases cadastradas e nas ordens de servico atuais."
        )
    )
    parser.add_argument(
        "--dataset-dir",
        default="data/fake_smoke",
        help="Diretorio do dataset fake.",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Data operacional no formato YYYY-MM-DD. Se omitida, usa contexto.json.",
    )
    parser.add_argument(
        "--detour-factor",
        type=float,
        default=1.25,
        help="Fator multiplicativo sobre a distancia geodesica para aproximar malha viaria.",
    )
    parser.add_argument(
        "--average-speed-mps",
        type=float,
        default=8.5,
        help="Velocidade media sintetica em metros por segundo.",
    )
    parser.add_argument(
        "--cost-per-km",
        type=Decimal,
        default=Decimal("3.00"),
        help="Custo sintetico por km usado para preencher os arcos.",
    )
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    context_payload = json.loads((dataset_dir / "contexto.json").read_text())
    date = args.date or context_payload["data_operacao"]
    return MatrixBuildConfig(
        dataset_dir=dataset_dir,
        date=date,
        detour_factor=args.detour_factor,
        average_speed_mps=args.average_speed_mps,
        cost_per_km=args.cost_per_km,
    )


def load_json(path: Path) -> object:
    return json.loads(path.read_text())


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def build_locations(dataset_dir: Path) -> dict[str, tuple[float, float]]:
    bases = load_json(dataset_dir / "bases.json")
    points_by_id = {item["id_ponto"]: item for item in load_json(dataset_dir / "pontos.json")}
    orders = load_json(dataset_dir / "ordens.json")

    locations: dict[str, tuple[float, float]] = {}

    for base in bases:
        locations[f"dep-{base['id_base']}"] = (float(base["latitude"]), float(base["longitude"]))

    for order in orders:
        point = points_by_id[order["id_ponto"]]
        locations[f"no-{order['id_ordem']}"] = (float(point["latitude"]), float(point["longitude"]))

    return locations


def build_arcs(locations: dict[str, tuple[float, float]], config: MatrixBuildConfig) -> list[dict[str, object]]:
    arcs: list[dict[str, object]] = []
    location_items = list(locations.items())

    for origin_id, (origin_lat, origin_lon) in location_items:
        for destination_id, (destination_lat, destination_lon) in location_items:
            if origin_id == destination_id:
                distance_m = 0
                duration_s = 0
            else:
                straight_distance = haversine_meters(origin_lat, origin_lon, destination_lat, destination_lon)
                distance_m = int(round(straight_distance * config.detour_factor))
                duration_s = max(180, int(round(distance_m / config.average_speed_mps)))

            cost = (
                Decimal(distance_m) / Decimal("1000") * config.cost_per_km
            ).quantize(Decimal("0.01"))

            arcs.append(
                {
                    "id_origem": origin_id,
                    "id_destino": destination_id,
                    "distancia_metros": distance_m,
                    "tempo_segundos": duration_s,
                    "custo": str(cost),
                }
            )

    return arcs


def main() -> int:
    config = parse_args()
    locations = build_locations(config.dataset_dir)
    arcs = build_arcs(locations, config)
    generated_at = datetime.now(timezone.utc).isoformat()
    dataset_token = config.dataset_dir.name.strip() or "fake"
    payload = {
        "snapshot_id": f"snap-{dataset_token}-{config.date}",
        "generated_at": generated_at,
        "strategy_name": "synthetic_geodesic_v1",
        "source_name": f"{dataset_token}_source",
        "arcs": arcs,
    }

    output_path = config.dataset_dir / "logistics_sources" / f"{config.date}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "dataset_dir": str(config.dataset_dir),
                "date": config.date,
                "locations": len(locations),
                "arcs": len(arcs),
                "output": str(output_path),
                "strategy_name": payload["strategy_name"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

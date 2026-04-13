from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCENARIO_CATALOG_PATH = PROJECT_ROOT / "data" / "scenarios" / "catalog_v1.json"


@dataclass(slots=True, frozen=True)
class BenchmarkScenarioSpec:
    scenario_id: str
    family: str
    layer: str
    seed: int
    classe_operacional: str
    n_orders: int
    n_vehicles: int
    window_profile: str
    volume_pressure: str
    cash_pressure: str
    priority_ratio: float
    geo_density: str
    pedagogical_hypothesis: str
    dataset_dir: Path

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "BenchmarkScenarioSpec":
        required_fields = (
            "scenario_id",
            "family",
            "layer",
            "seed",
            "classe_operacional",
            "n_orders",
            "n_vehicles",
            "window_profile",
            "volume_pressure",
            "cash_pressure",
            "priority_ratio",
            "geo_density",
            "pedagogical_hypothesis",
            "dataset_dir",
        )
        missing = [field for field in required_fields if field not in payload]
        if missing:
            raise ValueError(f"cenario sem campos obrigatorios: {', '.join(missing)}")

        return cls(
            scenario_id=str(payload["scenario_id"]),
            family=str(payload["family"]),
            layer=str(payload["layer"]),
            seed=int(payload["seed"]),
            classe_operacional=str(payload["classe_operacional"]),
            n_orders=int(payload["n_orders"]),
            n_vehicles=int(payload["n_vehicles"]),
            window_profile=str(payload["window_profile"]),
            volume_pressure=str(payload["volume_pressure"]),
            cash_pressure=str(payload["cash_pressure"]),
            priority_ratio=float(payload["priority_ratio"]),
            geo_density=str(payload["geo_density"]),
            pedagogical_hypothesis=str(payload["pedagogical_hypothesis"]),
            dataset_dir=Path(str(payload["dataset_dir"])),
        )


def load_scenario_catalog(path: Path | str = DEFAULT_SCENARIO_CATALOG_PATH) -> tuple[BenchmarkScenarioSpec, ...]:
    catalog_path = Path(path)
    if not catalog_path.is_absolute():
        repo_relative = PROJECT_ROOT / catalog_path
        if repo_relative.exists():
            catalog_path = repo_relative
    payload = json.loads(catalog_path.read_text())
    scenarios = payload.get("scenarios", [])
    if not isinstance(scenarios, list):
        raise ValueError("catalogo de cenarios invalido: campo 'scenarios' deve ser lista")
    return tuple(BenchmarkScenarioSpec.from_payload(item) for item in scenarios)


def group_specs_by_dataset_dir(specs: tuple[BenchmarkScenarioSpec, ...] | list[BenchmarkScenarioSpec]) -> dict[Path, list[BenchmarkScenarioSpec]]:
    grouped: dict[Path, list[BenchmarkScenarioSpec]] = defaultdict(list)
    for spec in specs:
        grouped[spec.dataset_dir].append(spec)
    return dict(grouped)

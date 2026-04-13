#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = PROJECT_ROOT / "data" / "scenarios" / "catalog_v1.json"
CLASSES = ("suprimento", "recolhimento")
FAMILY_CONFIG = {
    "balanced_control": {
        "window_profile": "balanced",
        "volume_pressure": "balanced",
        "cash_pressure": "balanced",
        "priority_ratio": {"didatica": 0.34, "benchmark": 0.30, "estresse": 0.25},
        "geo_density": {"didatica": "clustered", "benchmark": "balanced", "estresse": "dispersed"},
        "hypothesis": {
            "didatica": "cenario de controle para explicar o protocolo e validar o baseline em pequena escala",
            "benchmark": "cenario de referencia para comparar custo e cobertura em escala intermediaria",
            "estresse": "cenario de escala alta para mostrar a virada de custo computacional do baseline exato",
        },
    },
    "tight_windows": {
        "window_profile": "tight",
        "volume_pressure": "balanced",
        "cash_pressure": "balanced",
        "priority_ratio": {"didatica": 0.34, "benchmark": 0.30, "estresse": 0.30},
        "geo_density": {"didatica": "clustered", "benchmark": "balanced", "estresse": "dispersed"},
        "hypothesis": {
            "didatica": "o gargalo dominante e temporal e aparece de forma legivel em sala",
            "benchmark": "o baseline exato ainda ajuda a validar cobertura, mas o tempo cresce quando as janelas apertam",
            "estresse": "a combinacao de janelas apertadas e escala maior amplia a vantagem operacional do heuristico",
        },
    },
    "volume_pressure": {
        "window_profile": "balanced",
        "volume_pressure": "high",
        "cash_pressure": "balanced",
        "priority_ratio": {"didatica": 0.25, "benchmark": 0.25, "estresse": 0.25},
        "geo_density": {"didatica": "clustered", "benchmark": "dispersed", "estresse": "dispersed"},
        "hypothesis": {
            "didatica": "o gargalo dominante e a capacidade volumetrica das viaturas",
            "benchmark": "o uso de frota sobe mesmo com custo controlado quando o volume passa a restringir combinacoes",
            "estresse": "a escalabilidade piora quando capacidade fisica passa a dominar a decomposicao das rotas",
        },
    },
    "cash_pressure": {
        "window_profile": "balanced",
        "volume_pressure": "balanced",
        "cash_pressure": "high",
        "priority_ratio": {"didatica": 0.34, "benchmark": 0.34, "estresse": 0.30},
        "geo_density": {"didatica": "balanced", "benchmark": "dispersed", "estresse": "dispersed"},
        "hypothesis": {
            "didatica": "o limite financeiro e o teto segurado ficam evidentes sem excesso de ruido visual",
            "benchmark": "o baseline ajuda a medir o impacto da restricao financeira sobre cobertura e uso de viaturas",
            "estresse": "a pressao financeira em escala alta evidencia a diferenca entre controle de otimalidade e viabilidade operacional",
        },
    },
}
LAYER_CONFIG = {
    "didatica": {"n_orders": 6, "n_vehicles": 3, "seeds": (1,)},
    "benchmark": {"n_orders": 10, "n_vehicles": 5, "seeds": (1, 2, 3)},
    "estresse": {"n_orders": 20, "n_vehicles": 8, "seeds": (1, 2, 3)},
}


def build_catalog() -> dict[str, object]:
    scenarios: list[dict[str, object]] = []
    for family, family_config in FAMILY_CONFIG.items():
        for layer, layer_config in LAYER_CONFIG.items():
            for seed in layer_config["seeds"]:
                dataset_dir = f"data/scenarios/generated/{family}_{layer}_seed{seed:02d}"
                for classe_operacional in CLASSES:
                    scenarios.append(
                        {
                            "scenario_id": f"{family}_{layer}_seed{seed:02d}_{classe_operacional}",
                            "family": family,
                            "layer": layer,
                            "seed": seed,
                            "classe_operacional": classe_operacional,
                            "n_orders": layer_config["n_orders"],
                            "n_vehicles": layer_config["n_vehicles"],
                            "window_profile": family_config["window_profile"],
                            "volume_pressure": family_config["volume_pressure"],
                            "cash_pressure": family_config["cash_pressure"],
                            "priority_ratio": family_config["priority_ratio"][layer],
                            "geo_density": family_config["geo_density"][layer],
                            "pedagogical_hypothesis": family_config["hypothesis"][layer],
                            "dataset_dir": dataset_dir,
                        }
                    )
    return {"version": "1.0", "scenarios": scenarios}


def main() -> int:
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(json.dumps(build_catalog(), indent=2, ensure_ascii=False) + "\n")
    print(str(CATALOG_PATH.relative_to(PROJECT_ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

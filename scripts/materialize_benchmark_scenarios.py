#!/usr/bin/env python3
from __future__ import annotations

import argparse

from roteirizacao.benchmark.scenario_generator import materialize_scenarios_from_catalog


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materializa os datasets declarativos do catalogo de benchmark.")
    parser.add_argument("--catalog", default="data/scenarios/catalog_v1.json", help="Caminho do catalogo JSON.")
    parser.add_argument("--scenario-id", action="append", default=None, help="Scenario id especifico. Pode repetir.")
    parser.add_argument("--overwrite", action="store_true", help="Regenera datasets ja materializados.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    materialized = materialize_scenarios_from_catalog(
        catalog_path=args.catalog,
        scenario_ids=None if not args.scenario_id else set(args.scenario_id),
        overwrite=args.overwrite,
    )
    for path in materialized:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

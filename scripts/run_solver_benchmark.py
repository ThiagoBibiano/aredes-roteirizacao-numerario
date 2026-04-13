#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")

from roteirizacao.benchmark.runner import BenchmarkRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa o benchmark PyVRP x PuLP a partir do catalogo declarativo.")
    parser.add_argument("--catalog", default="data/scenarios/catalog_v1.json", help="Caminho do catalogo JSON.")
    parser.add_argument("--output-dir", default="data/benchmarks", help="Diretorio para results.csv, summary.json e plots.")
    parser.add_argument("--scenario-id", action="append", default=None, help="Scenario id especifico. Pode repetir.")
    parser.add_argument("--overwrite-scenarios", action="store_true", help="Regenera os datasets declarativos antes de executar.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runner = BenchmarkRunner(catalog_path=args.catalog, output_dir=args.output_dir)
    artifacts = runner.run(
        scenario_ids=None if not args.scenario_id else set(args.scenario_id),
        overwrite_scenarios=args.overwrite_scenarios,
    )
    print(artifacts.results_path)
    print(artifacts.summary_path)
    print(artifacts.plots_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Ferramentas de benchmark para comparacao PyVRP x PuLP."""

from roteirizacao.benchmark.common import BenchmarkResultRecord, BenchmarkRoute, BenchmarkSolution, build_result_record
from roteirizacao.benchmark.scenario_catalog import (
    DEFAULT_SCENARIO_CATALOG_PATH,
    BenchmarkScenarioSpec,
    group_specs_by_dataset_dir,
    load_scenario_catalog,
)

__all__ = [
    "BenchmarkResultRecord",
    "BenchmarkRoute",
    "BenchmarkScenarioSpec",
    "BenchmarkSolution",
    "DEFAULT_SCENARIO_CATALOG_PATH",
    "build_result_record",
    "group_specs_by_dataset_dir",
    "load_scenario_catalog",
]

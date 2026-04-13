from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from roteirizacao.benchmark.runner import BenchmarkRunner, load_instances_from_dataset
from roteirizacao.domain.enums import ClasseOperacional


class BenchmarkRunnerContractTest(unittest.TestCase):
    def test_load_instances_from_dataset_prefers_dataset_snapshot_when_available(self) -> None:
        instances = load_instances_from_dataset(ROOT / "data" / "fake_smoke")

        self.assertEqual(
            instances[ClasseOperacional.RECOLHIMENTO].matriz_logistica.estrategia_geracao,
            "synthetic_geodesic_v1",
        )
        self.assertEqual(
            instances[ClasseOperacional.SUPRIMENTO].matriz_logistica.estrategia_geracao,
            "synthetic_geodesic_v1",
        )

    def test_smoke_runner_produces_results_summary_and_plots_for_didatic_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "benchmark"
            runner = BenchmarkRunner(
                catalog_path=ROOT / "data" / "scenarios" / "catalog_v1.json",
                output_dir=output_dir,
            )

            artifacts = runner.run(scenario_ids={"balanced_control_didatica_seed01_suprimento"})

            self.assertTrue(artifacts.results_path.exists())
            self.assertTrue(artifacts.summary_path.exists())
            self.assertTrue((artifacts.plots_dir / "runtime_s_x_orders.png").exists())

            with artifacts.results_path.open() as stream:
                rows = list(csv.DictReader(stream))

            self.assertEqual(len(rows), 2)
            self.assertEqual({row["solver"] for row in rows}, {"pyvrp", "pulp"})
            self.assertTrue(all(row["feasible"] == "True" for row in rows))
            self.assertEqual({row["service_rate"] for row in rows}, {"1.0000"})


if __name__ == "__main__":
    unittest.main()

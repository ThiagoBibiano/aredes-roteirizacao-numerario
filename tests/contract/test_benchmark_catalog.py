from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from roteirizacao.benchmark.scenario_catalog import group_specs_by_dataset_dir, load_scenario_catalog


class BenchmarkCatalogContractTest(unittest.TestCase):
    def test_catalog_v1_has_expected_shape_and_pairing(self) -> None:
        specs = load_scenario_catalog(ROOT / "data" / "scenarios" / "catalog_v1.json")
        grouped = group_specs_by_dataset_dir(specs)

        self.assertEqual(len(specs), 56)
        self.assertEqual(len(grouped), 28)
        self.assertEqual({spec.family for spec in specs}, {"balanced_control", "tight_windows", "volume_pressure", "cash_pressure"})
        self.assertEqual({spec.layer for spec in specs}, {"didatica", "benchmark", "estresse"})
        self.assertTrue(all(spec.n_orders in {6, 10, 20} for spec in specs))
        self.assertTrue(all(spec.n_vehicles in {3, 5, 8} for spec in specs))

        for dataset_dir, dataset_specs in grouped.items():
            self.assertEqual({spec.classe_operacional for spec in dataset_specs}, {"suprimento", "recolhimento"})
            self.assertEqual(len(dataset_specs), 2)
            self.assertTrue(str(dataset_dir).startswith("data/scenarios/generated/"))


if __name__ == "__main__":
    unittest.main()

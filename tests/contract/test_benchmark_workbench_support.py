from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "notebook"))

from benchmark_workbench_support import full_run_route_sequences, load_benchmark_summary, run_randomized_pressure_benchmark


class BenchmarkWorkbenchSupportContractTest(unittest.TestCase):
    def test_smoke_benchmark_generates_sample_and_full_run_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "benchmark_workbench"

            artifacts = run_randomized_pressure_benchmark(
                base_scenario="operacao_controlada",
                order_shares=(0.20,),
                repetitions=1,
                pyvrp_max_iterations=10,
                pulp_time_limit_seconds=5,
                full_run_pulp_time_limit_seconds=20,
                output_dir=output_dir,
                with_basemap=False,
            )

            self.assertTrue(artifacts.results_path.exists())
            self.assertTrue(artifacts.summary_path.exists())
            self.assertTrue((artifacts.plots_dir / "painel_tendencias.png").exists())
            self.assertTrue((artifacts.plots_dir / "painel_dispersao.png").exists())
            self.assertTrue((artifacts.plots_dir / "erro_relativo_fo_pct.png").exists())
            self.assertTrue((artifacts.plots_dir / "taxa_viabilidade_pulp.png").exists())
            self.assertTrue((artifacts.plots_dir / "rodada_exaustiva_100_rotas.png").exists())

            summary = load_benchmark_summary(artifacts.summary_path)
            self.assertIn("records", summary)
            self.assertIn("aggregates", summary)
            self.assertIn("relative_objective_error_records", summary)
            self.assertIn("full_run", summary)

            self.assertEqual(len(summary["records"]), 2)
            self.assertEqual({row["solver"] for row in summary["records"]}, {"pyvrp", "pulp"})
            self.assertEqual(summary["dataset_manifests"][0]["order_share_pct"], 20)
            self.assertEqual(set(summary["dataset_manifests"][0]["per_class_counts"]), {"suprimento", "recolhimento"})

            full_run = summary["full_run"]
            self.assertEqual(full_run["manifest"]["order_share_pct"], 100)
            self.assertEqual(full_run["manifest"]["repetition"], 1)
            self.assertEqual(set(full_run["solvers"]), {"pyvrp", "pulp"})
            self.assertEqual(set(full_run["solvers"]["pyvrp"]["solutions_by_class"]), {"suprimento", "recolhimento"})

            pyvrp_sup_rows = full_run_route_sequences(artifacts.full_run, solver="pyvrp", classe_operacional="suprimento")
            pyvrp_rec_rows = full_run_route_sequences(artifacts.full_run, solver="pyvrp", classe_operacional="recolhimento")
            self.assertTrue(pyvrp_sup_rows)
            self.assertTrue(pyvrp_rec_rows)
            self.assertTrue(all(row["Classe operacional"] == "suprimento" for row in pyvrp_sup_rows))
            self.assertTrue(all(row["Classe operacional"] == "recolhimento" for row in pyvrp_rec_rows))
            self.assertTrue(any(" - " in row["Sequencia"] for row in pyvrp_sup_rows + pyvrp_rec_rows))
            self.assertTrue(all("Leitura correta" in row for row in pyvrp_sup_rows))


if __name__ == "__main__":
    unittest.main()

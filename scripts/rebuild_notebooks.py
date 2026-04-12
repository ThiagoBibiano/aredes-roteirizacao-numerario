#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import nbformat as nbf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = PROJECT_ROOT / "notebook"


def build_solver_workbench() -> nbf.NotebookNode:
    cells = [
        nbf.v4.new_markdown_cell(
            "# Workbench do Solver\n\n"
            "Notebook de demonstracao orientado por narrativa. O objetivo aqui e responder, em ordem, "
            "qual problema esta sendo resolvido, o que torna o cenario dificil, como a rede deve ser lida, "
            "qual foi a solucao produzida e qual takeaway deve entrar na apresentacao."
        ),
        nbf.v4.new_code_cell(
            "from pathlib import Path\n"
            "from IPython.display import Markdown, display\n"
            "\n"
            "PROJECT_ROOT = next(parent for parent in [Path.cwd(), *Path.cwd().parents] if (parent / 'pyproject.toml').exists())\n"
            "NOTEBOOK_DIR = PROJECT_ROOT / 'notebook'\n"
            "import sys\n"
            "if str(PROJECT_ROOT / 'src') not in sys.path:\n"
            "    sys.path.insert(0, str(PROJECT_ROOT / 'src'))\n"
            "if str(NOTEBOOK_DIR) not in sys.path:\n"
            "    sys.path.insert(0, str(NOTEBOOK_DIR))\n"
            "\n"
            "from solver_workbench_support import (\n"
            "    analyze_scenario,\n"
            "    build_takeaway,\n"
            "    compile_scenario,\n"
            "    export_presentation_bundle,\n"
            "    load_scenario_artifacts,\n"
            "    plot_base_graph,\n"
            "    plot_kpi_dashboard,\n"
            "    plot_solution_graph,\n"
            "    route_sequences,\n"
            "    run_scenario,\n"
            "    summarize_dataset,\n"
            "    summarize_orchestration,\n"
            ")\n"
            "\n"
            "SCENARIO = 'operacao_controlada'\n"
            "MAX_ITERATIONS = 50\n"
            "SEED = 1\n"
            "WITH_BASEMAP = False\n"
            "EXPORT_DIR = PROJECT_ROOT / 'docs' / 'apresentacao' / 'assets' / 'generated' / 'notebook'\n"
            "display(Markdown(f'**Configuracao ativa**: cenario=`{SCENARIO}`, max_iterations=`{MAX_ITERATIONS}`, seed=`{SEED}`'))"
        ),
        nbf.v4.new_markdown_cell("## 1. Qual problema estou resolvendo?"),
        nbf.v4.new_code_cell(
            "compile_scenario(SCENARIO)\n"
            "ARTIFACTS = load_scenario_artifacts(SCENARIO)\n"
            "DATASET_SUMMARY = summarize_dataset(ARTIFACTS)\n"
            "SCENARIO_ANALYSIS = analyze_scenario(ARTIFACTS)\n"
            "DATASET_SUMMARY | {'dominant_bottleneck': SCENARIO_ANALYSIS['dominant_bottleneck'], 'priority_ratio': SCENARIO_ANALYSIS['priority_ratio']}"
        ),
        nbf.v4.new_markdown_cell("## 2. O que torna esse cenario dificil?"),
        nbf.v4.new_code_cell(
            "display(Markdown(\n"
            "    f\"**Leitura do gargalo**: `{SCENARIO_ANALYSIS['dominant_bottleneck']}`. \"\n"
            "    f\"Janela media: `{SCENARIO_ANALYSIS['avg_window_hours']}` h, \"\n"
            "    f\"pressao financeira: `{SCENARIO_ANALYSIS['cash_pressure_ratio']}`, \"\n"
            "    f\"pressao volumetrica: `{SCENARIO_ANALYSIS['volume_pressure_ratio']}`.\"\n"
            "))\n"
            "SCENARIO_ANALYSIS"
        ),
        nbf.v4.new_markdown_cell("## 3. Como a rede-base deve ser lida?"),
        nbf.v4.new_code_cell("plot_base_graph(ARTIFACTS, with_basemap=WITH_BASEMAP)"),
        nbf.v4.new_markdown_cell("## 4. Quais parametros de execucao governam a leitura da solucao?"),
        nbf.v4.new_code_cell(
            "{\n"
            "    'scenario': SCENARIO,\n"
            "    'max_iterations': MAX_ITERATIONS,\n"
            "    'seed': SEED,\n"
            "    'materialize_snapshot': True,\n"
            "    'service_policy': 'maximize_attendance_v1',\n"
            "}"
        ),
        nbf.v4.new_markdown_cell("## 5. O que o solver construiu?"),
        nbf.v4.new_code_cell(
            "ORCHESTRATION = run_scenario(\n"
            "    SCENARIO,\n"
            "    max_iterations=MAX_ITERATIONS,\n"
            "    seed=SEED,\n"
            "    materialize_snapshot=True,\n"
            ")\n"
            "SUMMARY = summarize_orchestration(ORCHESTRATION)\n"
            "SUMMARY"
        ),
        nbf.v4.new_code_cell("plot_solution_graph(ORCHESTRATION, ARTIFACTS, with_basemap=WITH_BASEMAP)"),
        nbf.v4.new_markdown_cell("## 6. Qual foi o saldo operacional em KPI e sequencia?"),
        nbf.v4.new_code_cell("plot_kpi_dashboard(ORCHESTRATION)"),
        nbf.v4.new_code_cell("route_sequences(ORCHESTRATION)"),
        nbf.v4.new_markdown_cell("## 7. Qual takeaway entra na apresentacao?"),
        nbf.v4.new_code_cell(
            "display(Markdown(build_takeaway(ORCHESTRATION, ARTIFACTS)))\n"
            "export_presentation_bundle(ORCHESTRATION, ARTIFACTS, output_dir=EXPORT_DIR, with_basemap=WITH_BASEMAP)"
        ),
    ]
    notebook = nbf.v4.new_notebook(cells=cells)
    notebook.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    notebook.metadata["language_info"] = {"name": "python", "version": "3.13"}
    return notebook


def build_benchmark_workbench() -> nbf.NotebookNode:
    cells = [
        nbf.v4.new_markdown_cell(
            "# Benchmark PyVRP x PuLP\n\n"
            "Notebook separado do PoC de apresentacao. Aqui o foco e um experimento analitico por amostragem aleatoria "
            "a partir de `operacao_sob_pressao`, com leitura de medias, dispersao, erro relativo da funcao objetivo e "
            "uma rodada exaustiva final com 100% das ordens."
        ),
        nbf.v4.new_code_cell(
            "from pathlib import Path\n"
            "from IPython.display import Image, Markdown, display\n"
            "\n"
            "PROJECT_ROOT = next(parent for parent in [Path.cwd(), *Path.cwd().parents] if (parent / 'pyproject.toml').exists())\n"
            "NOTEBOOK_DIR = PROJECT_ROOT / 'notebook'\n"
            "import sys\n"
            "if str(PROJECT_ROOT / 'src') not in sys.path:\n"
            "    sys.path.insert(0, str(PROJECT_ROOT / 'src'))\n"
            "if str(NOTEBOOK_DIR) not in sys.path:\n"
            "    sys.path.insert(0, str(NOTEBOOK_DIR))\n"
            "\n"
            "from benchmark_workbench_support import (\n"
            "    build_benchmark_takeaway,\n"
            "    full_run_route_sequences,\n"
            "    load_benchmark_summary,\n"
            "    rows_to_markdown_table,\n"
            "    run_randomized_pressure_benchmark,\n"
            "    summarize_full_run,\n"
            "    summarize_full_run_by_class,\n"
            "    summarize_pulp_viability,\n"
            "    summarize_relative_objective_errors,\n"
            "    summarize_records,\n"
            ")\n"
            "\n"
            "BASE_SCENARIO = 'operacao_sob_pressao'\n"
            "ORDER_SHARES = (0.20, 0.40, 0.60, 0.80)\n"
            "REPETITIONS = 5\n"
            "PYVRP_MAX_ITERATIONS = 100\n"
            "PULP_TIME_LIMIT_SECONDS = 60\n"
            "FULL_RUN_PULP_TIME_LIMIT_SECONDS = 300\n"
            "OUTPUT_DIR = PROJECT_ROOT / 'data' / 'benchmarks' / 'operacao_sob_pressao_subsample'\n"
            "WITH_BASEMAP = False\n"
            "display(Markdown(\n"
            "    f'**Benchmark ativo**: cenario=`{BASE_SCENARIO}`, shares=`{ORDER_SHARES}`, repeticoes=`{REPETITIONS}`, rodada_exaustiva=`100%`'\n"
            "))"
        ),
        nbf.v4.new_markdown_cell("## 1. Qual recorte comparavel esta sendo executado?"),
        nbf.v4.new_code_cell(
            "{\n"
            "    'base_scenario': BASE_SCENARIO,\n"
            "    'order_shares_pct': [int(item * 100) for item in ORDER_SHARES],\n"
            "    'repetitions': REPETITIONS,\n"
            "    'pyvrp_max_iterations': PYVRP_MAX_ITERATIONS,\n"
            "    'pulp_time_limit_seconds': PULP_TIME_LIMIT_SECONDS,\n"
            "    'full_run_pulp_time_limit_seconds': FULL_RUN_PULP_TIME_LIMIT_SECONDS,\n"
            "    'sampling_policy': 'estratificada por classe_operacional com ordens aleatorias por repeticao',\n"
            "    'full_run_policy': 'rodada unica, 100% das ordens, fora das medias principais',\n"
            "    'protocol_path': PROJECT_ROOT / 'docs' / 'benchmark' / 'protocolo-experimental.md',\n"
            "    'output_dir': OUTPUT_DIR,\n"
            "}"
        ),
        nbf.v4.new_markdown_cell("## 2. Executar o benchmark e consolidar os artefatos"),
        nbf.v4.new_code_cell(
            "RUN = run_randomized_pressure_benchmark(\n"
            "    base_scenario=BASE_SCENARIO,\n"
            "    order_shares=ORDER_SHARES,\n"
            "    repetitions=REPETITIONS,\n"
            "    pyvrp_max_iterations=PYVRP_MAX_ITERATIONS,\n"
            "    pulp_time_limit_seconds=PULP_TIME_LIMIT_SECONDS,\n"
            "    full_run_pulp_time_limit_seconds=FULL_RUN_PULP_TIME_LIMIT_SECONDS,\n"
            "    output_dir=OUTPUT_DIR,\n"
            "    with_basemap=WITH_BASEMAP,\n"
            ")\n"
            "SUMMARY = load_benchmark_summary(RUN.summary_path)\n"
            "FULL_RUN = RUN.full_run\n"
            "{'results_csv': str(RUN.results_path), 'summary_json': str(RUN.summary_path), 'plots_dir': str(RUN.plots_dir)}"
        ),
        nbf.v4.new_markdown_cell("## 3. Quais medias surgiram por percentual de ordens?"),
        nbf.v4.new_code_cell(
            "display(Markdown(rows_to_markdown_table(summarize_records(SUMMARY['aggregates']))))"
        ),
        nbf.v4.new_code_cell(
            "Image(filename=str(OUTPUT_DIR / 'plots' / 'painel_tendencias.png'))"
        ),
        nbf.v4.new_markdown_cell("## 4. Como a dispersao se comporta nas repeticoes?"),
        nbf.v4.new_code_cell(
            "Image(filename=str(OUTPUT_DIR / 'plots' / 'painel_dispersao.png'))"
        ),
        nbf.v4.new_markdown_cell("## 5. Qual foi o erro relativo da funcao objetivo em relacao ao PuLP?"),
        nbf.v4.new_code_cell(
            "display(Markdown(rows_to_markdown_table(summarize_relative_objective_errors(SUMMARY['relative_objective_error_records']))))"
        ),
        nbf.v4.new_code_cell(
            "Image(filename=str(OUTPUT_DIR / 'plots' / 'erro_relativo_fo_pct.png'))"
        ),
        nbf.v4.new_markdown_cell("## 6. Qual foi a viabilidade do PuLP ao longo das escalas?"),
        nbf.v4.new_code_cell(
            "display(Markdown(rows_to_markdown_table(summarize_pulp_viability(SUMMARY))))"
        ),
        nbf.v4.new_code_cell(
            "Image(filename=str(OUTPUT_DIR / 'plots' / 'taxa_viabilidade_pulp.png'))"
        ),
        nbf.v4.new_markdown_cell("## 7. Rodada Exaustiva - 100% das Ordens"),
        nbf.v4.new_code_cell(
            "display(Markdown('**Leitura correta desta secao**: `suprimento` e `recolhimento` continuam sendo executados como experimentos isolados. "
            "Os paineis e tabelas abaixo nao devem ser lidos como uma unica escala operacional acoplada de frota.'))"
        ),
        nbf.v4.new_code_cell(
            "display(Markdown(rows_to_markdown_table(summarize_full_run(FULL_RUN))))"
        ),
        nbf.v4.new_code_cell(
            "display(Markdown(rows_to_markdown_table(summarize_full_run_by_class(FULL_RUN))))"
        ),
        nbf.v4.new_code_cell(
            "Image(filename=str(OUTPUT_DIR / 'plots' / 'rodada_exaustiva_100_rotas.png'))"
        ),
        nbf.v4.new_markdown_cell("### Rotas do PyVRP - suprimento"),
        nbf.v4.new_code_cell(
            "display(Markdown(rows_to_markdown_table(full_run_route_sequences(FULL_RUN, solver='pyvrp', classe_operacional='suprimento'))))"
        ),
        nbf.v4.new_markdown_cell("### Rotas do PyVRP - recolhimento"),
        nbf.v4.new_code_cell(
            "display(Markdown(rows_to_markdown_table(full_run_route_sequences(FULL_RUN, solver='pyvrp', classe_operacional='recolhimento'))))"
        ),
        nbf.v4.new_markdown_cell("### Rotas do PuLP - suprimento"),
        nbf.v4.new_code_cell(
            "display(Markdown(rows_to_markdown_table(full_run_route_sequences(FULL_RUN, solver='pulp', classe_operacional='suprimento'))))"
        ),
        nbf.v4.new_markdown_cell("### Rotas do PuLP - recolhimento"),
        nbf.v4.new_code_cell(
            "display(Markdown(rows_to_markdown_table(full_run_route_sequences(FULL_RUN, solver='pulp', classe_operacional='recolhimento'))))"
        ),
        nbf.v4.new_markdown_cell("## 8. Qual leitura metodologica deve ir para o slide final?"),
        nbf.v4.new_code_cell("display(Markdown(build_benchmark_takeaway(SUMMARY)))"),
    ]
    notebook = nbf.v4.new_notebook(cells=cells)
    notebook.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    notebook.metadata["language_info"] = {"name": "python", "version": "3.13"}
    return notebook


def main() -> int:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    nbf.write(build_solver_workbench(), NOTEBOOK_DIR / "modelo_solver_workbench.ipynb")
    nbf.write(build_benchmark_workbench(), NOTEBOOK_DIR / "benchmark_solver_comparison.ipynb")
    print("notebook/modelo_solver_workbench.ipynb")
    print("notebook/benchmark_solver_comparison.ipynb")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

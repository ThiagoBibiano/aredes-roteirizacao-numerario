# Benchmark PyVRP x PuLP

Este diretorio consolida a frente experimental separada do produto principal.

Objetivos:

- fixar o protocolo comparavel;
- documentar o recorte do problema;
- registrar o papel do baseline exato;
- manter a narrativa experimental desacoplada de CLI, API, auditoria e reporting.

Arquivos principais:

- `protocolo-experimental.md`: fonte normativa do experimento;
- `data/scenarios/catalog_v1.json`: catalogo declarativo dos cenarios;
- `scripts/materialize_benchmark_scenarios.py`: materializa datasets do catalogo;
- `scripts/run_solver_benchmark.py`: executa PyVRP e PuLP e grava `results.csv`, `summary.json` e plots.

Fluxo recomendado:

```bash
.venv/bin/python scripts/generate_benchmark_catalog.py
.venv/bin/python scripts/materialize_benchmark_scenarios.py
.venv/bin/python scripts/run_solver_benchmark.py
```

Saidas padronizadas:

- `data/benchmarks/results.csv`
- `data/benchmarks/summary.json`
- `data/benchmarks/plots/`

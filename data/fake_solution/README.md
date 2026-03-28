# Dataset de demonstracao solucionavel

Este dataset foi montado para servir como caminho feliz da aplicacao.

Objetivo:

- apresentar solucao completa de forma consistente;
- manter poucas ordens e baixa complexidade operacional;
- evitar outliers geograficos, valores extremos e janelas muito apertadas.

Fluxo sugerido:

```bash
.venv/bin/python scripts/build_fake_smoke_matrix.py --dataset-dir data/fake_solution

.venv/bin/python scripts/roteirizacao_cli.py materialize-snapshot \
  --date 2026-03-21 \
  --source-dir data/fake_solution/logistics_sources \
  --snapshot-dir data/fake_solution/logistics_snapshots

.venv/bin/python scripts/roteirizacao_cli.py run-planning \
  --dataset-dir data/fake_solution \
  --materialize-snapshot \
  --max-iterations 50 \
  --seed 1
```

O resultado sera gravado em `data/fake_solution/outputs/resultado-planejamento.json`.

Observacao:

- `data/fake_solution/` e o dataset de demonstracao;
- `data/fake_smoke/` continua disponivel como dataset mais agressivo para estresse e explicabilidade.

# Smoke Test Fake

Este dataset minimo existe para exercitar o fluxo operacional completo da Etapa 9.

## Comandos

Materializar o snapshot logistico fake:

```bash
.venv/bin/python scripts/roteirizacao_cli.py materialize-snapshot \
  --date 2026-03-21 \
  --source-dir data/fake_smoke/logistics_sources \
  --snapshot-dir data/fake_smoke/logistics_snapshots
```

Executar o planejamento com materializacao no inicio:

```bash
.venv/bin/python scripts/roteirizacao_cli.py run-planning \
  --dataset-dir data/fake_smoke \
  --materialize-snapshot \
  --max-iterations 50 \
  --seed 1
```

O resultado sera gravado em `data/fake_smoke/outputs/resultado-planejamento.json`.

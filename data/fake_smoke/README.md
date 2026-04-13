# Operacao Sob Pressao

Este dataset existe para exercitar o fluxo operacional completo no cenario `operacao_sob_pressao`, com maior dispersao geografica, janelas mais tensas e maior heterogeneidade de frota e demanda.

Escopo atual:

- o dataset cobre apenas `suprimento` e `recolhimento`;
- referencias antigas a `extraordinario` foram removidas do dataset-base;
- o estresse vem da combinacao de dispersao geografica, capacidades menores, valores altos e ordens com janelas mais apertadas.

Se voce quer um caminho feliz que normalmente fecha com solucao completa, use o cenario `operacao_controlada` em `data/fake_solution/`.

## Comandos

Sempre que `bases.json`, `pontos.json` ou `ordens.json` forem alterados, regenere antes a matriz sintetica de tempo/distancia do dataset fake:

```bash
.venv/bin/python scripts/build_fake_smoke_matrix.py --dataset-dir data/fake_smoke
```

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

## Observacao sobre a malha fake

O solver opera sobre **ordens de servico**, nao sobre todos os pontos cadastrados isoladamente. Por isso:

- a matriz fake sempre inclui todas as bases;
- a matriz fake inclui apenas os pontos que aparecem nas ordens do dia, materializados como nos `no-<id_ordem>`;
- se o conjunto de ordens aumentar, a matriz precisa ser regenerada para refletir os novos nos e arcos.

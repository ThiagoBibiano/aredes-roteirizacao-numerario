# Notebook do modelo

Este diretorio contem dois cadernos separados:

- `modelo_solver_workbench.ipynb`: artefato de demonstracao e apresentacao;
- `benchmark_solver_comparison.ipynb`: artefato experimental para PyVRP x PuLP.

Objetivo:

- manter a narrativa do PoC separada do pipeline de benchmark;
- executar o `DailyPlanningOrchestrator` diretamente para leitura de solucao;
- inspecionar a rede-base do cenario com `networkx`;
- exportar PNGs reaproveitaveis na apresentacao;
- rodar o benchmark comparativo em notebook proprio.

## Instalacao

Use os extras opcionais de notebook e benchmark:

```bash
.venv/bin/pip install -e '.[dev,notebook,benchmark]'
```

## Execucao

Prefira abrir o caderno com JupyterLab:

```bash
jupyter lab notebook/modelo_solver_workbench.ipynb
```

Para abrir o notebook experimental:

```bash
jupyter lab notebook/benchmark_solver_comparison.ipynb
```

Observacao:

- o repositorio possui um diretorio chamado `notebook/`, entao o modo classico `python -m notebook` nao e a melhor opcao aqui;
- se quiser abrir o `.ipynb` no VS Code, o fluxo tambem funciona.

## Cenarios suportados

- `operacao_controlada`: cenario de demonstracao com solucao completa;
- `operacao_sob_pressao`: cenario mais agressivo para estresse, gargalos e nao atendimento.

Compatibilidade:

- `fake_solution` e aceito como alias legado de `operacao_controlada`;
- `fake_smoke` e aceito como alias legado de `operacao_sob_pressao`.

## Rendering

O notebook continua tendo `networkx` como base da modelagem visual. Quando o extra `notebook` estiver instalado por completo, a renderizacao usa um basemap de fundo via `contextily`. Se o basemap nao puder ser carregado, o caderno faz fallback automatico para o desenho puro em `networkx`.

## Fluxo do notebook de apresentacao

1. configurar cenario, seed e iteracoes;
2. materializar a instancia e ler o gargalo dominante;
3. desenhar a rede-base;
4. executar o solver real;
5. desenhar a rede escolhida;
6. inspecionar KPI, sequencia e takeaway;
7. exportar os PNGs usados na apresentacao.

## Fluxo do notebook de benchmark

1. declarar `operacao_sob_pressao`, percentuais de ordens e numero de repeticoes;
2. gerar subconjuntos aleatorios estratificados por classe operacional;
3. executar PyVRP e PuLP em cada repeticao;
4. consolidar `results.csv`, `summary.json` e um painel visual em portugues;
5. ler medias, dispersao, viabilidade do PuLP e erro relativo da FO;
6. executar uma rodada separada com `100%` das ordens;
7. exibir as rotas de PyVRP e PuLP para a rodada exaustiva;
8. extrair a leitura metodologica final a partir dos resultados.

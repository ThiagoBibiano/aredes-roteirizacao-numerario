# Notebook do modelo

Este diretorio contem um caderno focado no modelo de otimizacao, sem depender da UI Streamlit nem da API HTTP.

Objetivo:

- executar o `DailyPlanningOrchestrator` diretamente;
- inspecionar a rede-base do cenario com `networkx`;
- visualizar a rede escolhida pelo solver com as rotas resultantes;
- sobrepor a rede a um basemap cartografico quando `contextily` estiver disponivel;
- validar o comportamento do modelo em um ambiente mais controlado.

## Instalacao

Use o extra opcional de notebook:

```bash
.venv/bin/pip install -e '.[dev,notebook]'
```

## Execucao

Prefira abrir o caderno com JupyterLab:

```bash
jupyter lab notebook/modelo_solver_workbench.ipynb
```

Observacao:

- o repositorio possui um diretorio chamado `notebook/`, entao o modo classico `python -m notebook` nao e a melhor opcao aqui;
- se quiser abrir o `.ipynb` no VS Code, o fluxo tambem funciona.

## Cenarios suportados

- `fake_solution`: cenario de demonstracao com solucao completa;
- `fake_smoke`: cenario mais agressivo para estresse, gargalos e nao atendimento.

## Rendering

O notebook continua tendo `networkx` como base da modelagem visual. Quando o extra `notebook` estiver instalado por completo, a renderizacao usa um basemap de fundo via `contextily`. Se o basemap nao puder ser carregado, o caderno faz fallback automatico para o desenho puro em `networkx`.

## Fluxo do caderno

1. selecionar o cenario;
2. recompilar `fake_solution` e `fake_smoke`, materializando a matriz e o snapshot local;
3. comparar rapidamente os dois cenarios;
4. carregar dados e matriz logistica do cenario selecionado;
5. desenhar a rede-base via `networkx`;
6. executar o solver real via `DailyPlanningOrchestrator`;
7. desenhar a rede escolhida pelo solver;
8. inspecionar resumo e sequencia das rotas.

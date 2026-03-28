# Sistema de Roteirizacao para Transporte de Numerario

Backend de planejamento diario de rotas para transporte de numerario, com foco em **suprimento**, **recolhimento** e tratamento prioritario de ordens especiais, usando **PyVRP** como motor de otimizacao.

Hoje o repositorio ja contem:

- contratos de dominio e validacao;
- pipeline `bruto -> validado -> classificado`;
- montagem de `InstanciaRoteirizacaoBase` solver-agnostic;
- adaptador para PyVRP;
- pos-processamento, auditoria e KPIs;
- geracao e persistencia de snapshots logísticos;
- orquestracao idempotente do planejamento diario;
- CLI operacional;
- API FastAPI para consumo por frontend externo.

## O que o sistema resolve

Para cada dia operacional, a aplicacao responde:

> Quais ordens cada viatura deve executar, em que sequencia e em qual horario, minimizando o custo total da operacao sem violar janelas, capacidades, teto segurado e regras operacionais?

O modelo contempla, no estado atual do projeto:

- janelas de atendimento;
- jornada/turno da viatura;
- capacidade financeira e volumetrica;
- teto segurado para recolhimento;
- segregacao entre suprimento e recolhimento;
- penalidades por nao atendimento e atraso;
- cancelamentos e parada improdutiva;
- trilha de auditoria e explicabilidade;
- reprocessamento seguro do mesmo cenario.

## Status atual

O projeto nao esta mais apenas em estruturacao. O nucleo executavel e o backend HTTP ja estao implementados.

Entregas principais ja concluidas:

- Etapa 1: especificacao formal dos contratos em [`docs/etapa-1/`](docs/etapa-1/)
- Etapa 2: ingestao, validacao e classificacao
- Etapa 3: instancia solver-agnostic
- Etapa 4: adaptador PyVRP
- Etapa 5: resultado de planejamento
- Etapas 6 a 8: malha, snapshots e materializacao versionada
- Etapa 9: CLI operacional
- Etapas 10 a 12: pos-processamento, auditoria e reporting
- Etapa 13: orquestracao idempotente
- Camada HTTP: FastAPI sobre o orquestrador

## Arquitetura implementada

```mermaid
flowchart LR
    A[Dados brutos] --> B[PreparationPipeline]
    B --> C[OptimizationInstanceBuilder]
    C --> D[InstanciaRoteirizacaoBase]
    D --> E[PyVRPAdapter]
    E --> F[PyVRP]
    F --> G[RoutePostProcessor]
    G --> H[PlanningAuditTrailBuilder]
    H --> I[PlanningReportingBuilder]
    I --> J[ResultadoPlanejamento]
    J --> K[CLI]
    J --> L[FastAPI]
```

Principios mantidos:

- o dominio nao depende diretamente de PyVRP;
- a linguagem do negocio e separada do solver;
- a execucao diaria e idempotente por `hash_cenario`;
- a saida final preserva auditoria, KPIs e contexto de execucao.

## Documentacao tecnica

- Contexto funcional e diretrizes do MVP em [`docs/contexto.md`](docs/contexto.md)
- API HTTP em [`docs/api.md`](docs/api.md)
- Formulacao cientifica do problema de otimizacao em [`docs/formulacao-matematica.md`](docs/formulacao-matematica.md)
- Contratos formais da etapa 1 em [`docs/etapa-1/`](docs/etapa-1/)

## Estrutura real do repositorio

```text
.
├─ README.md
├─ docs/
│  ├─ api.md
│  ├─ contexto.md
│  ├─ formulacao-matematica.md
│  └─ etapa-1/
├─ apps/
│  └─ ui_streamlit/
├─ notebook/
│  ├─ modelo_solver_workbench.ipynb
│  ├─ solver_workbench_support.py
│  └─ README.md
├─ data/
│  ├─ fake_solution/
│  ├─ fake_smoke/
│  ├─ logistics_snapshots/
│  └─ logistics_sources/
├─ scripts/
│  └─ roteirizacao_cli.py
├─ src/
│  └─ roteirizacao/
│     ├─ api/
│     ├─ application/
│     ├─ domain/
│     ├─ optimization/
│     └─ cli.py
├─ tests/
│  ├─ contract/
│  └─ ui/
├─ pyproject.toml
└─ .python-version
```

## Requisitos de ambiente

- `pyenv` com Python `3.13.7`
- ambiente virtual `.venv`
- `PyVRP` instalado para executar o planejamento completo

Versoes usadas no ambiente de desenvolvimento atual:

- Python `3.13.7`
- PyVRP `0.13.3`
- FastAPI `0.135.1`
- Uvicorn `0.42.0`

## Setup local

```bash
pyenv local 3.13.7
pyenv exec python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pip install '.[dev,ui]'
.venv/bin/pip install pyvrp==0.13.3
```

Se quiser apenas validar que o ambiente foi criado corretamente:

```bash
.venv/bin/python --version
.venv/bin/python -c "import pyvrp, fastapi, uvicorn"
```

## Como rodar os testes

```bash
.venv/bin/python -m compileall src tests
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

A suite atual cobre contratos do pipeline, adaptador do solver, snapshots, orquestracao e API HTTP.

## Smoke test com dataset fake

O repositorio inclui dois datasets de exemplo:

- [`data/fake_solution/`](data/fake_solution/): caminho feliz para demonstracao e UI
- [`data/fake_smoke/`](data/fake_smoke/): cenario mais agressivo para estresse e explicabilidade

Execucao pela CLI:

```bash
.venv/bin/python scripts/roteirizacao_cli.py run-planning \
  --dataset-dir data/fake_solution \
  --materialize-snapshot \
  --max-iterations 50 \
  --seed 1
```

Esse comando produz:

- resultado consolidado em `data/fake_solution/outputs/resultado-planejamento.json`;
- estado idempotente em `data/fake_solution/outputs/executions/`;
- reaproveitamento automatico do mesmo cenario em reexecucoes identicas.

## CLI operacional

Entry point do projeto:

```bash
roteirizacao --help
```

Ou diretamente:

```bash
.venv/bin/python scripts/roteirizacao_cli.py --help
```

Comandos disponiveis:

- `materialize-snapshot`: materializa um snapshot logístico bruto para o formato versionado do projeto
- `run-planning`: executa o planejamento diario a partir de um dataset local

Exemplo para materializar snapshot:

```bash
.venv/bin/python scripts/roteirizacao_cli.py materialize-snapshot \
  --date 2026-03-22 \
  --source-dir data/logistics_sources \
  --snapshot-dir data/logistics_snapshots
```

## API FastAPI

A API foi criada para expor o motor como backend para um frontend futuro em outro repositorio.

Subir localmente com recarga:

```bash
.venv/bin/python -m uvicorn roteirizacao.api.main:create_app --factory --reload
```

Ou via entry point instalado:

```bash
roteirizacao-api
```

A documentacao interativa fica disponivel em:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

### Endpoints principais

- `GET /health`
- `POST /api/v1/snapshots/materialize`
- `POST /api/v1/planning/run-dataset`
- `POST /api/v1/planning/run`

O endpoint `run-dataset` reutiliza um dataset existente em disco.

O endpoint `run` aceita payload inline, materializa internamente os arquivos em `data/api_runs/` e executa o mesmo orquestrador idempotente usado pela CLI.

## UI Streamlit

A interface web vive em `apps/ui_streamlit/` e consome exclusivamente a API HTTP do projeto.

Suba primeiro o backend FastAPI e, em seguida, execute a UI:

```bash
streamlit run apps/ui_streamlit/app.py
```

A UI agora carrega defaults de `apps/ui_streamlit/settings.toml` e aceita override local em `apps/ui_streamlit/settings.local.toml`.

Exemplo de override local para evitar preencher tudo manualmente a cada uso:

```toml
api_base_url = "http://127.0.0.1:8000"

[execution]
default_mode = "dataset"
auto_check_health = true

[execution.parameters]
materialize_snapshot = true
max_iterations = 50
seed = 1
collect_stats = false
display = false

[execution.dataset]
dataset_dir = "data/fake_solution"

[execution.inline.files]
contexto = "data/fake_solution/contexto.json"
bases = "data/fake_solution/bases.json"
pontos = "data/fake_solution/pontos.json"
viaturas = "data/fake_solution/viaturas.json"
ordens = "data/fake_solution/ordens.json"
```

Fluxos principais disponiveis na UI:

- execucao inline por upload dos JSONs obrigatorios
- execucao tecnica por `dataset_dir`
- resultados com KPIs, tabela de rotas, detalhe de paradas e mapa operacional
- auditoria, excecoes, exportacao e inspecao offline

A suite dedicada da UI pode ser executada com:

```bash
.venv/bin/python -m unittest discover -s tests/ui -p 'test_*.py' -v
```

Exemplo rapido de chamada HTTP com dataset existente:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/planning/run-dataset \
  -H 'Content-Type: application/json' \
  -d '{
    "dataset_dir": "data/fake_solution",
    "materialize_snapshot": true,
    "max_iterations": 50,
    "seed": 1
  }'
```

Detalhes adicionais da camada HTTP estao em [`docs/api.md`](docs/api.md).

## Notebook do modelo

O diretorio `notebook/` contem um caderno voltado ao modelo, sem depender da UI nem da API. Ele executa o orquestrador diretamente, desenha a rede-base do cenario com `networkx` e, na sequencia, sobrepoe a rede escolhida pelo solver com as rotas resultantes. Quando o stack cartografico estiver disponivel, a visualizacao usa um basemap de fundo sem abandonar o desenvolvimento em `networkx`.
O fluxo do caderno tambem recompila `data/fake_solution` e `data/fake_smoke`, materializando a matriz sintetica e o snapshot antes da comparacao dos cenarios.

Instalacao sugerida para o ambiente controlado:

```bash
.venv/bin/pip install -e '.[dev,notebook]'
```

Execucao recomendada:

```bash
jupyter lab notebook/modelo_solver_workbench.ipynb
```

Observacao:

- prefira `jupyter lab` ou VS Code; como o repositorio tem um diretorio chamado `notebook/`, o modo classico `python -m notebook` pode causar conflito de import com o pacote `notebook`.
- o notebook trabalha direto sobre `DailyPlanningOrchestrator`, entao ele e o melhor caminho para validar o modelo em isolamento.

## Idempotencia e rastreabilidade

A orquestracao principal usa um `hash_cenario` estavel a partir das entradas relevantes do planejamento.

Isso garante:

- mesma entrada relevante -> mesmo identificador de cenario;
- reexecucao segura do mesmo cenario;
- retry apos falha tecnica sem duplicar artefatos;
- recuperacao do contexto logico anterior.

Artefatos por cenario incluem:

- `cenario.json`
- `estado.json`
- `resultado-planejamento.json`
- `resultado-planejamento.pkl`
- `manifest.json`

## Dados e snapshots

Convencoes relevantes do repositorio:

- [`data/logistics_sources/README.md`](data/logistics_sources/README.md): formato esperado da fonte bruta de malha
- [`data/logistics_snapshots/README.md`](data/logistics_snapshots/README.md): formato materializado e versionado do snapshot
- [`data/fake_solution/README.md`](data/fake_solution/README.md): dataset solucionavel para demonstracao
- [`data/fake_smoke/README.md`](data/fake_smoke/README.md): dataset mais agressivo para estresse e explicabilidade

## Modulos principais

### `src/roteirizacao/domain/`

Contem enums, entidades, eventos, contratos solver-agnostic, contratos de resultado e utilitarios de serializacao.

### `src/roteirizacao/application/`

Contem os casos de uso do sistema:

- `preparation.py`
- `instance_builder.py`
- `planning.py`
- `post_processing.py`
- `audit.py`
- `reporting.py`
- `snapshot_materializer.py`
- `orchestration.py`

### `src/roteirizacao/optimization/`

Contem a fronteira com o solver e o adaptador do PyVRP.

### `src/roteirizacao/api/`

Contem a camada FastAPI, schemas HTTP e service wrapper sobre o orquestrador.

## Limitacoes atuais

Ainda nao fazem parte do escopo implementado:

- autenticacao/autorizacao da API;
- banco de dados para execucoes;
- fila assíncrona para jobs longos;
- reotimizacao com viatura em campo;
- observabilidade externa e metrics server;
- integracao nativa com fontes externas reais alem do modelo de snapshot/dataset local.

## Documentacao complementar

- [`docs/contexto.md`](docs/contexto.md)
- [`docs/api.md`](docs/api.md)
- [`docs/etapa-1/`](docs/etapa-1/)

## Proximos passos recomendados

- autenticar a API e versionar contratos HTTP;
- transformar execucoes longas em jobs assíncronos;
- persistir resultados em banco em vez de apenas filesystem;
- adicionar integracoes reais de entrada e de malha;
- criar o frontend consumidor em repositorio separado.

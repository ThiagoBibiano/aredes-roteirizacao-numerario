# API FastAPI

## Subir localmente

```bash
.venv/bin/python -m uvicorn roteirizacao.api.main:create_app --factory --reload
```

Ou via entrypoint do projeto:

```bash
.venv/bin/python -m roteirizacao.api.main
```

Tambem e possivel usar o script instalado:

```bash
roteirizacao-api
```

## Endpoints

### `GET /health`

Retorna o status basico da aplicacao.

### `POST /api/v1/snapshots/materialize`

Materializa um snapshot logistico bruto.

Exemplo de payload:

```json
{
  "data_operacao": "2026-03-22",
  "source_dir": "data/logistics_sources",
  "snapshot_dir": "data/logistics_snapshots"
}
```

### `POST /api/v1/planning/run-dataset`

Executa o planejamento a partir de um dataset ja existente em disco.

Exemplo de payload:

```json
{
  "dataset_dir": "data/fake_smoke",
  "materialize_snapshot": true,
  "max_iterations": 50,
  "seed": 1
}
```

### `POST /api/v1/planning/run`

Executa o planejamento a partir de payload inline, sem expor paths locais ao frontend.

Exemplo de payload:

```json
{
  "contexto": {
    "id_execucao": "exec-api-2026-03-22",
    "data_operacao": "2026-03-22",
    "cutoff": "2026-03-21T18:00:00+00:00",
    "timestamp_referencia": "2026-03-21T18:30:00+00:00",
    "versao_schema": "1.0"
  },
  "bases": [],
  "pontos": [],
  "viaturas": [],
  "ordens": [],
  "max_iterations": 100,
  "seed": 1
}
```

## Observacoes

- A API reutiliza o orquestrador idempotente ja existente.
- Requisicoes inline sao materializadas internamente em `data/api_runs/`.
- Repeticoes do mesmo cenario retornam o mesmo `hash_cenario` e podem reaproveitar resultado em cache.

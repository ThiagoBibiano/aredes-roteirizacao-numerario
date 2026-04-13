# Contrato de serializacao e versionamento

## 1. Forma canonica atual

O backend serializa contratos com `serialize_value()`:

- `Enum` vira `value`;
- `Decimal` vira string decimal;
- `datetime` vira ISO 8601 com offset;
- `date` vira `YYYY-MM-DD`;
- dataclasses viram dicionarios recursivos;
- `tuple`, `list`, `set` e `frozenset` viram listas;
- conjuntos sao ordenados por `str()` antes da serializacao.

## 2. JSON persistido

Artefatos persistidos em disco usam, em geral:

- `json.dumps(..., indent=2, ensure_ascii=True)` para saida legivel;
- `sort_keys=True` quando a estabilidade lexical importa para diff ou hash.

Isso vale especialmente para:

- `cenario.json`
- `estado.json`
- `manifest.json`
- `resultado-planejamento.json`
- snapshots materializados e manifests de snapshot

## 3. Datas, horarios e timezone

- `data_operacao` e sempre ISO 8601 no formato `YYYY-MM-DD`;
- `cutoff`, `timestamp_referencia`, `timestamp_criacao`, `instante_cancelamento` e eventos exigem timezone explicito;
- `ensure_datetime()` rejeita timestamps sem offset;
- o mesmo vale para `JanelaTempo` e `MatrizLogistica.timestamp_geracao`.

## 4. Numericos

- custos, capacidades, penalidades e valores monetarios sao mantidos como `Decimal` no dominio;
- na serializacao, esses valores saem como string para preservar precisao;
- inteiros operacionais como `tempo_servico`, `distancia_metros` e `tempo_segundos` permanecem numericos.

## 5. Hashes e canonicalizacao

### 5.1 `hash_cenario`

O orquestrador calcula o hash sobre JSON canonico com `sort_keys=True` e `ensure_ascii=True`. O payload inclui:

- contexto relevante da execucao;
- payloads de `bases`, `pontos`, `viaturas` e `ordens`;
- parametros do solver;
- politica de persistencia de snapshot;
- conteudo do snapshot bruto ou persistido quando isso altera a execucao.

### 5.2 `hash_matriz`

`hash_matrix_payload()` serializa a `MatrizLogistica` sem o proprio hash para obter um identificador estavel.

### 5.3 `content_hash` de snapshot

`FileSystemSnapshotRepository` normaliza:

- `generated_at`
- `strategy_name`
- `schema_version`
- `source_name`
- `materialized_at`
- `arcs` ordenados por `id_origem`, `id_destino`

Depois calcula o SHA-256 do JSON canonico.

## 6. Campos de versao presentes hoje

| Contrato | Campo |
| --- | --- |
| `ContextoExecucao` | `versao_schema` |
| `MetadadoIngestao` | `versao_schema` |
| `MetadadoRastreabilidade` | `versao_schema` |
| snapshot persistido | `schema_version` |

Defaults usados no codigo atual:

- `versao_schema = "1.0"`
- `schema_version = "1.0"`

## 7. Compatibilidade

Politica recomendada para evolucao:

- adicionar campo opcional: mudanca compativel;
- renomear ou remover campo existente: mudanca quebradora;
- mudar semantica de enum ou normalizacao: requer revisao coordenada de validacao, API, UI e testes;
- mudar a composicao do `hash_cenario` ou do `content_hash`: exige revisao explicita da politica de reprocessamento.

## 8. Regras para novos artefatos

- persistir sempre em `snake_case`;
- evitar strings vazias quando `null` ou ausencia forem semanticamente melhores;
- se o artefato participar de cache, definir de antemao se precisa de `sort_keys=True`;
- se o artefato for lido por API e UI, registrar o contrato em testes antes de alterar o schema.

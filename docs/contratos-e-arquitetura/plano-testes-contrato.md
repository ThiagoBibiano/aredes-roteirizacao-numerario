# Plano atual de testes de contrato

## Objetivo

Registrar como o repositorio protege hoje os contratos do backend. Este documento substitui a antiga visao de "testes antes da implementacao" por um mapa da cobertura existente.

## Suites principais

| Arquivo | Foco atual |
| --- | --- |
| `tests/contract/test_preparation_pipeline.py` | validacao de base, ponto, viatura, ordem e classificacao |
| `tests/contract/test_instance_builder.py` | construcao da instancia solver-agnostic, elegibilidade e custos |
| `tests/contract/test_logistics_provider.py` | snapshot persistido, cobertura da malha e fallback |
| `tests/contract/test_snapshot_materializer.py` | canonicalizacao, versionamento e manifests de snapshot |
| `tests/contract/test_pyvrp_adapter.py` | traducao da instancia para o payload do solver |
| `tests/contract/test_planning_executor.py` | execucao do solver e consolidacao do resultado |
| `tests/contract/test_post_processing.py` | rotas, paradas e ordens nao atendidas |
| `tests/contract/test_audit_builder.py` | consolidacao de eventos, erros e motivos de inviabilidade |
| `tests/contract/test_reporting_builder.py` | KPIs e relatorio de planejamento |
| `tests/contract/test_orchestration.py` | `hash_cenario`, cache, persistencia e idempotencia |
| `tests/contract/test_api.py` | contratos da API FastAPI para clientes HTTP externos |
| `tests/contract/test_cli.py` | contratos publicos da CLI |

## Criterios minimos de aceitacao

Cada area nova ou alterada deve cobrir:

1. caminho feliz com contrato valido;
2. falha estrutural ou obrigatorio ausente;
3. falha de referencia ou invariante de negocio;
4. serializacao ou persistencia coerente;
5. preservacao de auditoria e status final quando aplicavel.

## Casos que merecem regressao obrigatoria

- mudanca em normalizacao de enums ou aliases;
- mudanca em `classify_ordem` ou no tratamento de cancelamento;
- mudanca nas dimensoes de capacidade da instancia;
- mudanca na composicao do `hash_cenario`;
- mudanca na forma canonica de snapshots ou manifests;
- mudanca no schema da resposta da API consumida por clientes HTTP.

## Lacunas que continuam sensiveis

- comportamento do solver depende da biblioteca PyVRP estar instalada no ambiente;
- a suite atual valida contratos de backend e API HTTP, mas nao cobre o comportamento de um frontend especifico;
- datasets fake cobrem cenarios representativos, mas nao substituem homologacao com dados reais.

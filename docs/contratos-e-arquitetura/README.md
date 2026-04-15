# Contratos e arquitetura do backend

Este diretorio consolida a referencia tecnica do backend como ele existe hoje. O foco nao e mais registrar uma etapa historica do projeto, e sim documentar os contratos, as invariantes e as decisoes que sustentam o fluxo executavel em `src/roteirizacao/` e a API FastAPI.

## Escopo

- modelo de dominio bruto, validado e classificado;
- snapshots logisticos e resolucao da matriz de deslocamento;
- construcao da instancia solver-agnostic;
- execucao do planejamento, pos-processamento, auditoria e relatorios;
- idempotencia por `hash_cenario` e persistencia dos artefatos da execucao;
- contratos publicos usados por CLI, API e clientes HTTP externos.

## Fluxo implementado

1. `PlanningDatasetLoader` carrega `contexto.json`, `bases.json`, `pontos.json`, `viaturas.json` e `ordens.json`.
2. `PreparationPipeline` valida os contratos e classifica as ordens.
3. `OptimizationInstanceBuilder` gera uma `InstanciaRoteirizacaoBase` por `ClasseOperacional`.
4. `PlanningExecutor` adapta a instancia para PyVRP, resolve, pos-processa, audita e calcula KPIs.
5. `DailyPlanningOrchestrator` materializa snapshots quando solicitado, calcula `hash_cenario`, persiste estado e reaproveita resultado em cache quando possivel.
6. CLI e API HTTP consomem o mesmo orquestrador; clientes externos entram pela API.

## Mapa rapido de codigo

| Area | Modulos principais |
| --- | --- |
| Entradas e orquestracao | `src/roteirizacao/application/orchestration.py`, `src/roteirizacao/cli.py`, `src/roteirizacao/api/service.py` |
| Dominio e validacao | `src/roteirizacao/domain/models.py`, `src/roteirizacao/domain/services.py`, `src/roteirizacao/domain/events.py` |
| Logistica e snapshots | `src/roteirizacao/application/snapshot_materializer.py`, `src/roteirizacao/application/logistics_provider.py`, `src/roteirizacao/application/logistics_matrix.py`, `src/roteirizacao/domain/logistics.py` |
| Otimizacao | `src/roteirizacao/application/instance_builder.py`, `src/roteirizacao/domain/optimization.py`, `src/roteirizacao/optimization/pyvrp_adapter.py` |
| Saida e explicabilidade | `src/roteirizacao/application/post_processing.py`, `src/roteirizacao/application/audit.py`, `src/roteirizacao/application/reporting.py`, `src/roteirizacao/domain/results.py` |
| Consumo por clientes HTTP | `src/roteirizacao/api/main.py`, `src/roteirizacao/api/schemas.py` |

## Arquivos desta pasta

- `especificacao-contratos.md`: visao geral dos contratos efetivos do backend.
- `glossario.md`: vocabulario de negocio e de operacao usado no codigo atual.
- `enums-e-vocabularios.md`: enums, aliases e normalizacoes aceitas na ingestao.
- `invariantes.md`: regras estruturais e de negocio garantidas pelos contratos.
- `matriz-rastreabilidade.md`: como cada regra principal percorre entrada, planejamento e saida.
- `erros-e-auditoria.md`: padrao de erros, eventos de auditoria e motivos de inviabilidade.
- `serializacao-e-versionamento.md`: forma canonica dos artefatos persistidos e regras de compatibilidade.
- `plano-testes-contrato.md`: suites de teste que hoje protegem esses contratos.
- `decisoes-arquiteturais.md`: ADRs consolidadas do backend atual.

## Leitura recomendada

1. `especificacao-contratos.md`
2. `invariantes.md`
3. `erros-e-auditoria.md`
4. `serializacao-e-versionamento.md`
5. `decisoes-arquiteturais.md`

# Decisoes arquiteturais consolidadas

## ADR-001 - Dominio e instancia permanecem desacoplados do solver

Decisao:

O contrato estavel termina em `InstanciaRoteirizacaoBase`. Tudo que for especifico de PyVRP fica isolado no adaptador.

Consequencia:

O backend preserva a possibilidade de trocar de solver sem reescrever os contratos de negocio e de auditoria.

## ADR-002 - O orquestrador e a fronteira unica de execucao

Decisao:

CLI, API `run-dataset` e API `run` usam o mesmo `DailyPlanningOrchestrator`.

Consequencia:

Persistencia, idempotencia, materializacao de snapshot e estrutura de saida permanecem coerentes entre todos os canais de uso.

## ADR-003 - Idempotencia e determinada por `hash_cenario`

Decisao:

O backend considera entradas, parametros do solver e politica de snapshot ao calcular o `hash_cenario`.

Consequencia:

Reexecucoes identicas podem reutilizar cache com seguranca, e pequenas mudancas relevantes geram um novo cenario.

## ADR-004 - Snapshot persistido e preferencial, mas nunca bloqueante

Decisao:

Primeiro tenta-se carregar a malha persistida da data. Na falta dela, ou se houver cobertura incompleta, o sistema cai para um builder geometrico local.

Consequencia:

O planejamento continua executavel em ambiente de desenvolvimento e smoke tests, sem abrir mao de uma malha versionada quando ela existe.

## ADR-005 - Auditoria e relatorio fazem parte do resultado central

Decisao:

`ResultadoPlanejamento` inclui eventos, erros, motivos de inviabilidade, KPIs e relatorio no mesmo contrato.

Consequencia:

Nao existe "modo tecnico" sem explicabilidade. Toda execucao relevante produz artefato consumivel por operacao, API e UI.

## ADR-006 - Suprimento e recolhimento sao resolvidos em instancias separadas

Decisao:

A separacao por `ClasseOperacional` e obrigatoria na construcao da instancia e reaparece no resultado final.

Consequencia:

O backend evita misturar restricoes e metricas de classes operacionais diferentes na mesma rodada de solver.

## ADR-007 - Cancelamento e um estado formal com efeito de negocio

Decisao:

Cancelamento nao e booleano auxiliar. Ele interfere em elegibilidade, exclusao, impacto financeiro, auditoria e relatorio.

Consequencia:

`classify_ordem` concentra uma parte importante da semantica operacional do sistema.

## ADR-008 - Consumidores externos usam a API, nao o nucleo de planejamento

Decisao:

Clientes HTTP externos consomem a API HTTP e nao importam diretamente o orquestrador.

Consequencia:

O contrato de rede vira a fronteira real entre backend e integracoes externas, o que simplifica evolucao e testes de integracao.

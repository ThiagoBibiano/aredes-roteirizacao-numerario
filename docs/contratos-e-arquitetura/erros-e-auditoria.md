# Contrato de erro e auditoria

## Objetivo

Padronizar a forma como o backend rejeita dados, registra decisoes de negocio e explica porque um cenario terminou concluido, concluido com ressalvas ou inviavel.

## Contratos efetivos

### `ErroContrato`

Uso atual: falha estrutural de entrada, geralmente obrigatorio ausente.

Campos:

- `id_erro`
- `tipo_erro`
- `codigo_erro`
- `mensagem`
- `entidade`
- `campo`
- `valor_observado`
- `origem`
- `timestamp`
- `id_execucao`

### `ErroValidacao`

Uso atual: violacao de regra de dominio, referencia ou solver.

Campos:

- `id_erro`
- `codigo_regra`
- `mensagem`
- `entidade`
- `id_entidade`
- `campo`
- `valor_observado`
- `valor_esperado`
- `severidade`
- `timestamp`
- `id_execucao`

### `EventoAuditoria`

Uso atual: registrar fatos relevantes, inclusive quando nao ha erro tecnico.

Campos:

- `id_evento`
- `tipo_evento`
- `severidade`
- `entidade_afetada`
- `id_entidade`
- `regra_relacionada`
- `motivo`
- `timestamp_evento`
- `id_execucao`
- `campo_afetado`
- `valor_observado`
- `valor_esperado`
- `contexto_adicional`

### `MotivoInviabilidade`

Uso atual: consolidacao legivel dos fatores que impediram atendimento pleno.

Campos:

- `codigo`
- `descricao`
- `entidade`
- `id_entidade`
- `severidade`
- `origem`
- `regra_relacionada`
- `contexto`

## Taxonomia de erros observada no codigo

| Codigo | Origem tipica | Significado |
| --- | --- | --- |
| `schema.obrigatorio_ausente` | validacao de entrada | campo obrigatorio nao informado |
| `schema.enum_desconhecido` | `validate_ordem` | valor fora do vocabulario controlado |
| `referencia.entidade_ausente` | validacao de viatura ou ordem | referencia para base ou ponto inexistente |
| `dominio.invariante_violada` | validacao de dominio | valor inconsistente com o contrato |
| `negocio.inviabilidade_operacional` | construcao de instancia | classe operacional sem veiculo elegivel |
| `roteirizacao.dependencia_ausente` | executor | biblioteca PyVRP indisponivel no ambiente |
| `roteirizacao.falha_solver` | executor | falha nao tratada durante a resolucao |

## Tipos de evento efetivamente usados

| Tipo | Onde aparece hoje | Exemplo |
| --- | --- | --- |
| `ingestao` | recebimento de payload bruto | `ingestao.ordem` |
| `validacao` | validacao de contrato ou normalizacao | `dominio.ordem`, `alias.tipo_servico` |
| `classificacao` | aplicacao de cut-off e status planejavel | `classificacao.operacional` |
| `exclusao` | ordem retirada antes do planejamento | `negocio.cutoff_exclusao` |
| `cancelamento` | cancelamento tardio com impacto | `negocio.cancelamento_tardio` |
| `construcao_instancia` | geracao da matriz e da instancia | `construcao.instancia`, `carregamento.snapshot_logistico` |
| `roteirizacao` | resultado do solver e nao atendimento | `roteirizacao.pyvrp.solve`, `roteirizacao.nao_atendimento` |
| `saida` | consolidacao final e idempotencia | `saida.resultado_planejamento`, `orquestracao.idempotente` |
| `erro` | consolidacao de falhas | `auditoria.erro`, `roteirizacao.pyvrp` |

## Fluxo atual de consolidacao

1. Validacao cria `ErroContrato`, `ErroValidacao` e eventos de ingestao/validacao.
2. Classificacao cria eventos de exclusao, cancelamento e classificacao.
3. Construcao da instancia e resolucao do solver acrescentam eventos e, quando necessario, erros adicionais.
4. `PlanningAuditTrailBuilder` consolida tudo, garante evento de erro para cada falha relevante e deriva `MotivoInviabilidade`.
5. `DailyPlanningOrchestrator` acrescenta o evento `orquestracao.idempotente` ao resultado final.

## Regras operacionais

- erro tecnico nao substitui evento de auditoria;
- exclusao e cancelamento devem ser explicados mesmo sem excecao;
- um mesmo problema pode aparecer como erro e tambem como motivo de inviabilidade;
- eventos sao ordenados por `timestamp_evento` e `id_evento` antes de entrar no resultado;
- o contrato de auditoria deve bastar para explicar por que a ordem foi aceita, excluida, cancelada ou nao atendida.

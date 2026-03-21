# Contrato de erro e auditoria

## Objetivo

Padronizar a forma como o sistema rejeita, explica e rastreia dados e decisoes relevantes ao longo do pipeline.

## Principios

- nenhum erro relevante deve ser silencioso;
- rejeicao de dado deve ser distinguida de exclusao por regra de negocio;
- erro tecnico nao deve apagar contexto de negocio;
- auditoria deve ser serializavel, ordenavel e reprocessavel.

## Contratos previstos

### ErroContrato

Uso: falha estrutural ou de schema.

Campos minimos:

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

Exemplos:

- tipo invalido em campo obrigatorio;
- enum desconhecido;
- schema compativel ausente.

### ErroValidacao

Uso: violacao de regra de dominio ou de referencia.

Campos minimos:

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

Exemplos:

- ordem com `valor_estimado < 0`;
- ordem apontando para `id_ponto` inexistente;
- viatura sem `teto_segurado`.

### EventoAuditoria

Uso: registrar fato relevante, inclusive quando nao ha erro tecnico.

Campos minimos:

- `id_evento`
- `tipo_evento`
- `severidade`
- `entidade_afetada`
- `id_entidade`
- `regra_relacionada`
- `motivo`
- `timestamp_evento`
- `id_execucao`

Campos recomendados:

- `campo_afetado`
- `valor_observado`
- `valor_esperado`
- `contexto_adicional`

## Taxonomia minima de erros

| Codigo | Categoria | Significado |
| --- | --- | --- |
| `schema.obrigatorio_ausente` | schema | campo obrigatorio nao informado |
| `schema.tipo_invalido` | schema | valor em tipo logico incorreto |
| `schema.enum_desconhecido` | schema | valor fora do vocabulario controlado |
| `referencia.entidade_ausente` | referencia | entidade referenciada nao existe |
| `dominio.invariante_violada` | dominio | contrato recebeu valor proibido |
| `negocio.cutoff_exclusao` | negocio | item excluido por regra temporal |
| `negocio.cancelamento_tardio` | negocio | cancelamento com impacto operacional |
| `negocio.inviabilidade_operacional` | negocio | cenario impossivel dado o conjunto de restricoes |

## Taxonomia minima de eventos de auditoria

| Tipo | Uso |
| --- | --- |
| `ingestao` | registro de recebimento de dado bruto |
| `validacao` | sucesso ou falha em regra estrutural |
| `classificacao` | atribuicao de classe, elegibilidade ou exclusao |
| `cancelamento` | mudanca de status de cancelamento |
| `construcao_instancia` | transformacao para problema solver-agnostic |
| `roteirizacao` | resultado relevante do processo de planejamento |
| `saida` | consolidacao do resultado final |
| `erro` | falha tecnica ou estrutural relevante |

## Regras de uso

- `ErroContrato` e `ErroValidacao` podem impedir progressao de um item no pipeline.
- `EventoAuditoria` nao pressupoe falha; ele registra decisao ou fato relevante.
- exclusao por regra de negocio deve gerar `EventoAuditoria` mesmo quando nao houver excecao tecnica.
- uma ordem cancelada apos cut-off pode nao produzir `ErroValidacao`, mas deve produzir `EventoAuditoria`.

## Decisoes de fronteira

- logs de aplicacao nao substituem `EventoAuditoria`;
- stack trace nao substitui `ErroContrato`;
- o contrato de auditoria deve ser suficiente para explicar por que uma ordem foi rejeitada, excluida, mantida ou roteirizada.

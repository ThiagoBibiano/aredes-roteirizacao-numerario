# Glossario do backend

## Contexto de execucao

Contrato que fixa `id_execucao`, `data_operacao`, `cutoff` e `timestamp_referencia` para toda a rodada de planejamento.

## Dataset local

Conjunto de arquivos JSON em disco usado pela CLI e pelo endpoint `run-dataset`.

## Payload inline

Forma de execucao da API em que os JSONs de entrada sao enviados no corpo da requisicao e gravados temporariamente em `data/api_runs/`.

## Base

Deposito operacional de partida e retorno da viatura.

## Ponto

Cadastro do local de atendimento. Permanece separado da demanda do dia.

## Ordem

Demanda operacional de uma data especifica, associada a um ponto.

## Ordem classificada

Ordem ja interpretada pelas regras de cut-off e cancelamento, pronta para entrar ou sair do planejamento.

## Ordem excluida

Ordem retirada antes da roteirizacao, normalmente por cancelamento ate o `cutoff`.

## Ordem cancelada

Ordem cancelada apos o `cutoff`, com impacto operacional ou financeiro preservado.

## Ordem nao atendida

Ordem valida e planejavel que permaneceu opcional no solver e nao entrou em nenhuma rota.

## Viatura

Recurso operacional com base de origem, turno, custos, capacidades e compatibilidades.

## Snapshot logistico bruto

Arquivo JSON com `arcs` entre localizacoes, usado como fonte para materializacao de um snapshot versionado.

## Snapshot persistido

Representacao canonica da malha em `logistics_snapshots/<data>.json`, com manifesto versionado por data.

## Matriz logistica

Conjunto completo de trechos entre depositos e nos de atendimento usados por uma instancia.

## Instancia solver-agnostic

Contrato `InstanciaRoteirizacaoBase` que descreve o problema sem depender de classes nativas do PyVRP.

## Classe operacional

Eixo que separa o planejamento em familias independentes, hoje `suprimento` e `recolhimento`.

## Hash de cenario

Hash deterministico calculado sobre entradas relevantes, parametros do solver e politica de snapshot. E a chave da idempotencia da execucao.

## Cache de execucao

Persistencia por `hash_cenario` de `cenario.json`, `estado.json`, `resultado-planejamento.json` e `resultado-planejamento.pkl`.

## Reuso de cache

Situacao em que o orquestrador encontra um resultado completo para o mesmo `hash_cenario` e apenas reexpone o artefato sem reprocessar o solver.

## Recuperacao de contexto

Situacao em que um `cenario.json` ja existe para o mesmo `hash_cenario` e o backend reaproveita o contexto persistido da execucao anterior.

## Output alias

Arquivo `resultado-planejamento.json` no caminho de saida solicitado, mantido como copia legivel do resultado consolidado do cenario.

## Evento de auditoria

Registro estruturado de ingestao, validacao, classificacao, roteirizacao, saida ou erro.

## Motivo de inviabilidade

Sintese de erro, exclusao, cancelamento ou nao atendimento usada para explicar porque o cenario nao foi plenamente atendido.

## Log de planejamento

Resumo de execucao com status final, contagens e parametros de planejamento.

## Relatorio de planejamento

Resumo gerencial derivado do resultado, com contagens consolidadas, custo total e destaques.

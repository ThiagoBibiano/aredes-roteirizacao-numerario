# Catalogo de enums e vocabularios controlados

Este documento fecha os vocabularios minimos permitidos na Etapa 1. Novos valores so devem ser adicionados por decisao registrada.

## TipoServico

Uso: natureza operacional do atendimento.

Valores iniciais:

- `suprimento`
- `recolhimento`
- `extraordinario`

Observacao: `especial` nao pertence a este enum.

## ClassePlanejamento

Uso: prioridade temporal ou comercial.

Valores iniciais:

- `padrao`
- `especial`

## ClasseOperacional

Uso: segregacao estrutural da instancia.

Valores iniciais:

- `suprimento`
- `recolhimento`

## Criticidade

Uso: severidade operacional da ordem.

Valores iniciais:

- `baixa`
- `media`
- `alta`
- `critica`

## StatusOrdem

Uso: estado da ordem no pipeline.

Valores iniciais:

- `recebida`
- `validada`
- `classificada`
- `planejavel`
- `planejada`
- `nao_atendida`
- `excluida`
- `cancelada`

## StatusCancelamento

Uso: estado detalhado de cancelamento.

Valores iniciais:

- `nao_cancelada`
- `cancelamento_solicitado`
- `cancelada_antes_cutoff`
- `cancelada_apos_cutoff`
- `cancelada_com_parada_improdutiva`

## TipoPonto

Uso: classificacao cadastral do local.

Valores iniciais:

- `agencia`
- `cliente`
- `terminal`
- `base_apoio`
- `outro`

## TipoViatura

Uso: classificacao operacional do recurso.

Valores iniciais:

- `leve`
- `media`
- `pesada`
- `especializada`

Observacao: nomes finais dependem do catalogo operacional da empresa, mas o contrato exige a existencia deste eixo.

## TipoEventoAuditoria

Uso: classificacao do fato auditavel.

Valores iniciais:

- `ingestao`
- `validacao`
- `classificacao`
- `exclusao`
- `cancelamento`
- `construcao_instancia`
- `roteirizacao`
- `saida`
- `erro`

## SeveridadeEvento

Uso: peso do evento auditavel.

Valores iniciais:

- `info`
- `aviso`
- `erro`
- `critico`

## TipoPenalidade

Uso: natureza da penalidade modelada.

Valores iniciais:

- `nao_atendimento`
- `atraso`
- `cancelamento_tardio`
- `parada_improdutiva`
- `uso_viatura_adicional`

## SeveridadeContratual

Uso: ordenacao comparavel entre impactos de negocio.

Valores iniciais:

- `muito_baixa`
- `baixa`
- `media`
- `alta`
- `muito_alta`

## RegraCompatibilidade

Uso: eixo de elegibilidade entre viatura, ponto e ordem.

Valores iniciais:

- `servico`
- `setor`
- `tipo_ponto`
- `restricao_acesso`
- `seguranca`

## StatusExecucaoPlanejamento

Uso: estado final do resultado agregado.

Valores iniciais:

- `concluida`
- `concluida_com_ressalvas`
- `inviavel`
- `falha`

## Convencoes gerais

- Enums devem usar identificadores estaveis em `snake_case`.
- Campos expostos externamente nao devem depender de labels de interface.
- Valores desconhecidos nao devem ser silenciosamente aceitos; devem gerar erro ou evento de auditoria conforme a etapa.

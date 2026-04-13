# Catalogo de enums e vocabularios controlados

Este documento descreve os enums efetivos do codigo atual em `src/roteirizacao/domain/enums.py` e as normalizacoes aceitas na camada de validacao em `src/roteirizacao/domain/services.py`.

## Enums canonicos

### `TipoServico`

- `suprimento`
- `recolhimento`
- `extraordinario`

### `ClassePlanejamento`

- `padrao`
- `especial`
- `eventual`

### `ClasseOperacional`

- `suprimento`
- `recolhimento`

### `Criticidade`

- `baixa`
- `media`
- `alta`
- `critica`

### `StatusOrdem`

- `recebida`
- `validada`
- `classificada`
- `planejavel`
- `planejada`
- `nao_atendida`
- `excluida`
- `cancelada`

### `StatusCancelamento`

- `nao_cancelada`
- `cancelamento_solicitado`
- `cancelada_antes_cutoff`
- `cancelada_apos_cutoff`
- `cancelada_com_parada_improdutiva`

### `TipoPonto`

- `agencia`
- `cliente`
- `terminal`
- `base_apoio`
- `outro`

### `TipoViatura`

- `leve`
- `media`
- `pesada`
- `especializada`

### `TipoEventoAuditoria`

- `ingestao`
- `validacao`
- `classificacao`
- `exclusao`
- `cancelamento`
- `construcao_instancia`
- `roteirizacao`
- `saida`
- `erro`

### `SeveridadeEvento`

- `info`
- `aviso`
- `erro`
- `critico`

### `SeveridadeContratual`

- `muito_baixa`
- `baixa`
- `media`
- `alta`
- `muito_alta`

### `RegraCompatibilidade`

- `servico`
- `setor`
- `tipo_ponto`
- `restricao_acesso`
- `seguranca`

### `StatusExecucaoPlanejamento`

- `concluida`
- `concluida_com_ressalvas`
- `inviavel`
- `falha`

## Aliases aceitos na ingestao

### `tipo_servico`

| Valor recebido | Valor normalizado |
| --- | --- |
| `especial` | `extraordinario` |

### `classe_planejamento`

| Valor recebido | Valor normalizado |
| --- | --- |
| `padrão` | `padrao` |
| `padrao` | `padrao` |

### `criticidade`

| Valor recebido | Valor normalizado |
| --- | --- |
| `obrigatoria` | `critica` |
| `prioritaria` | `alta` |
| `adiavel` | `media` |

### `tipo_ponto`

| Valor recebido | Valor normalizado |
| --- | --- |
| `atm` | `terminal` |
| `cofre_inteligente` | `outro` |
| `varejista` | `cliente` |
| `cliente_corporativo` | `cliente` |

## Convencoes de normalizacao

- textos passam por `normalize_token`, que remove acento, converte para minusculas e troca espacos e hifens por `_`;
- enums sao persistidos e expostos como `snake_case`;
- valores desconhecidos devem falhar com erro de schema ou validacao, nunca ser aceitos silenciosamente;
- `status_ativo` aceita alguns atalhos textuais para inativo: `false`, `0`, `inativo`, `nao`, `nao_ativo`.

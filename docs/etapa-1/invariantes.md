# Invariantes por contrato

## Base

| Regra | Tipo |
| --- | --- |
| `id_base` deve ser unico e estavel | dominio |
| `localizacao` e obrigatoria e valida | dominio |
| `janela_operacao` deve ter inicio menor ou igual ao fim | dominio |
| base sem referencia geografica e invalida | dominio |

## Ponto

| Regra | Tipo |
| --- | --- |
| `id_ponto` deve ser unico | dominio |
| `localizacao` e obrigatoria | dominio |
| `tempo_padrao_servico >= 0` quando informado | dominio |
| janelas padrao devem ser coerentes | dominio |
| ponto inativo nao pode originar ordem planeavel sem decisao explicita | negocio |

## OrdemBruta

| Regra | Tipo |
| --- | --- |
| deve preservar identificadores e campos da fonte | rastreabilidade |
| pode carregar tipos frouxos e nomes originais | ingestao |
| deve possuir `MetadadoIngestao` associado | rastreabilidade |

## Ordem

| Regra | Tipo |
| --- | --- |
| `id_ordem` e obrigatorio | dominio |
| `id_ponto` deve referenciar ponto conhecido | referencia |
| `valor_estimado >= 0` | dominio |
| `volume_estimado >= 0` | dominio |
| `tempo_servico >= 0` | dominio |
| `janela_efetiva` deve ser coerente | dominio |
| `tipo_servico` deve pertencer ao vocabulario controlado | dominio |
| `classe_planejamento` deve pertencer ao vocabulario controlado | dominio |
| `classe_operacional` deve pertencer ao vocabulario controlado | dominio |
| `criticidade` deve pertencer ao vocabulario controlado | dominio |
| `penalidade_nao_atendimento >= 0` | dominio |
| `penalidade_atraso >= 0` | dominio |
| `taxa_improdutiva >= 0` | dominio |
| se houver cancelamento, o estado deve ter carimbo temporal coerente | negocio |

## OrdemClassificada

| Regra | Tipo |
| --- | --- |
| deve explicitar a classe operacional final | negocio |
| deve explicitar elegibilidade no cut-off | negocio |
| deve explicitar impacto de cancelamento quando houver | negocio |
| nao pode misturar significado de validacao com classificacao | arquitetura |

## Viatura

| Regra | Tipo |
| --- | --- |
| `id_base_origem` e obrigatorio | dominio |
| `turno` e obrigatorio | dominio |
| `custo_fixo >= 0` | dominio |
| `custo_variavel >= 0` | dominio |
| `capacidade_financeira > 0` no cenario de recolhimento | negocio |
| `capacidade_volumetrica > 0` quando aplicavel ao recurso | negocio |
| `teto_segurado` deve existir no MVP | negocio |
| compatibilidades devem ser explicitadas | negocio |

## MatrizLogistica

| Regra | Tipo |
| --- | --- |
| todo no deve possuir indice estavel | estrutura |
| matriz de tempo deve ser coerente com cardinalidade de nos | estrutura |
| matriz de distancia deve ser coerente com cardinalidade de nos | estrutura |
| tempos e distancias nao podem ser negativos | dominio |
| trechos indisponiveis devem referenciar nos existentes | referencia |

## InstanciaRoteirizacaoBase

| Regra | Tipo |
| --- | --- |
| deve conter ao menos um deposito | dominio |
| todos os nos referenciados devem existir | referencia |
| todos os veiculos devem ter capacidades explicitas | negocio |
| toda demanda deve ter penalidade associada | negocio |
| `classe_operacional` deve isolar o problema | arquitetura |
| recolhimento deve suportar acumulacao financeira | negocio |
| nenhum elemento deve depender de classe nativa de solver | arquitetura |

## RotaPlanejada

| Regra | Tipo |
| --- | --- |
| deve referenciar viatura existente | referencia |
| deve referenciar base existente | referencia |
| deve manter coerencia entre sequencia e horarios | dominio |
| deve respeitar circuito fechado no escopo do MVP | negocio |
| uso de limite segurado deve ser sinalizado quando aplicavel | negocio |

## EventoAuditoria

| Regra | Tipo |
| --- | --- |
| evento deve possuir identificador unico | estrutura |
| tipo e severidade devem pertencer ao vocabulario controlado | dominio |
| eventos de erro, exclusao e rejeicao exigem motivo | negocio |
| evento deve ser ordenavel no tempo | auditoria |

## ResultadoPlanejamento

| Regra | Tipo |
| --- | --- |
| deve conter `id_execucao` | estrutura |
| deve conter `hash_cenario` para reproducao | auditoria |
| `status_final` deve pertencer ao vocabulario controlado | dominio |
| ordens excluidas devem ser explicaveis | auditoria |
| ordens nao atendidas devem ser explicaveis | auditoria |
| resultado deve permitir reprocessamento | arquitetura |

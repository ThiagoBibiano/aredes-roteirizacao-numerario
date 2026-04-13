# Invariantes por contrato

## Contexto e value objects

| Contrato | Invariantes atuais |
| --- | --- |
| `ContextoExecucao` | `cutoff` e `timestamp_referencia` devem conter timezone |
| `Coordenada` | latitude entre `-90` e `90`; longitude entre `-180` e `180` |
| `JanelaTempo` | `inicio` e `fim` com timezone; `fim >= inicio` |
| `MetadadoRastreabilidade` | todo item validado carrega `id_execucao`, `origem`, `timestamp_referencia` e `versao_schema` |

## Entrada bruta

| Contrato | Invariantes atuais |
| --- | --- |
| `BaseBruta`, `PontoBruto`, `ViaturaBruta`, `OrdemBruta` | preservam `payload` original e `metadado_ingestao` |
| `MetadadoIngestao` | deve existir para toda entrada carregada pelo `PlanningDatasetLoader` |

## Dominio validado

| Contrato | Invariantes atuais |
| --- | --- |
| `Base` | `id_base`, `nome`, coordenada e janela de operacao sao obrigatorios |
| `Ponto` | `id_ponto`, `tipo_ponto`, coordenada e `setor_geografico` sao obrigatorios |
| `Ponto` | `tempo_padrao_servico`, quando informado, nao pode ser negativo |
| `Viatura` | `id_base_origem` deve referenciar base existente |
| `Viatura` | `custo_fixo` e `custo_variavel` nao podem ser negativos |
| `Viatura` | `capacidade_financeira`, `capacidade_volumetrica` e `teto_segurado` devem ser positivos |
| `Ordem` | `id_ponto` deve referenciar ponto existente |
| `Ordem` | `data_operacao` deve coincidir com a do `ContextoExecucao` |
| `Ordem` | `valor_estimado`, `volume_estimado`, `tempo_servico`, `penalidade_nao_atendimento`, `penalidade_atraso` e `taxa_improdutiva` nao podem ser negativos |
| `Ordem` | cancelamento diferente de `nao_cancelada` exige `instante_cancelamento` ou `janela_cancelamento` coerente |
| `Ordem` | `tipo_servico = extraordinario` exige `classe_operacional` explicita |

## Classificacao

| Contrato | Invariantes atuais |
| --- | --- |
| `OrdemClassificada` | ordem cancelada ate o `cutoff` vira `excluida` |
| `OrdemClassificada` | ordem cancelada apos o `cutoff` vira `cancelada` e carrega impacto financeiro previsto |
| `OrdemClassificada` | ordem sem cancelamento segue `planeavel = true` |
| `OrdemClassificada` | toda classificacao gera evento de auditoria com `classe_operacional`, `status_ordem` e `planeavel` |

## Logistica

| Contrato | Invariantes atuais |
| --- | --- |
| `TrechoLogistico` | trecho disponivel exige `distancia_metros`, `tempo_segundos` e `custo` nao negativos |
| `TrechoLogistico` | trecho indisponivel pode ter campos nulos, mas nunca negativos |
| `MatrizLogistica` | `timestamp_geracao` deve conter timezone |
| `MatrizLogistica` | `ids_localizacao` devem ser unicos |
| `MatrizLogistica` | a matriz deve cobrir todos os pares ordenados entre as localizacoes |
| `MatrizLogistica` | nao pode haver trechos duplicados nem referencias a localizacao inexistente |
| Snapshot persistido | deve cobrir todos os pares solicitados para a instancia, ou o provedor cai em fallback |

## Instancia solver-agnostic

| Contrato | Invariantes atuais |
| --- | --- |
| `InstanciaRoteirizacaoBase` | deve conter ao menos um deposito, um veiculo e um no de atendimento |
| `InstanciaRoteirizacaoBase` | `matriz_logistica.ids_localizacao` deve seguir a ordem canonica `depositos -> nos` |
| `InstanciaRoteirizacaoBase` | `janelas_tempo` e `tempos_servico` devem cobrir todos os nos |
| `InstanciaRoteirizacaoBase` | todo veiculo deve declarar exatamente as mesmas dimensoes de capacidade da instancia |
| `InstanciaRoteirizacaoBase` | deve existir ao menos uma penalidade por no |
| `InstanciaRoteirizacaoBase` | restricoes de elegibilidade so podem referenciar nos e veiculos existentes |
| `InstanciaRoteirizacaoBase` | `custos_por_arco` so pode usar trechos disponiveis da matriz |
| `OptimizationInstanceBuilder` | nao gera instancia para classe operacional sem veiculo elegivel |

## Saida

| Contrato | Invariantes atuais |
| --- | --- |
| `ParadaPlanejada` | `sequencia >= 1`; horarios com timezone; `fim_previsto >= inicio_previsto` |
| `RotaPlanejada` | horarios com timezone; `fim_previsto >= inicio_previsto` |
| `ResultadoPlanejamento` | agrega status final, KPIs, auditoria, erros, hashes e relatorio em um unico artefato serializavel |

## Orquestracao e persistencia

| Artefato | Invariantes atuais |
| --- | --- |
| `hash_cenario` | e calculado sobre entradas, parametros do solver e politica de snapshot |
| cache de execucao | so e reutilizado quando `estado.json` marca `completed` e o pickle do resultado existe |
| `manifest.json` de execucoes | mantem `latest_hash_cenario` e lista ordenada por `updated_at` |
| `resultado-planejamento.json` no `output_path` | sempre espelha o resultado consolidado da execucao atual ou do cache |

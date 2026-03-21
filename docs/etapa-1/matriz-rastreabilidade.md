# Matriz de rastreabilidade

| Regra de negocio | Contrato afetado | Campo(s) necessarios | Etapa de aplicacao |
| --- | --- | --- | --- |
| Janela de atendimento | `Ordem`, `InstanciaRoteirizacaoBase`, `RotaPlanejada` | `janela_efetiva`, `janelas_tempo`, `horarios_previstos` | validacao, construcao da instancia, saida |
| Jornada maxima | `Viatura`, `InstanciaRoteirizacaoBase`, `RotaPlanejada` | `turno`, `restricoes_jornada`, `indicadores_restricao` | validacao, construcao da instancia, saida |
| Capacidade financeira | `Viatura`, `InstanciaRoteirizacaoBase`, `RotaPlanejada` | `capacidade_financeira`, `dimensoes_capacidade`, `carga_acumulada` | validacao, construcao da instancia, saida |
| Capacidade volumetrica | `Viatura`, `InstanciaRoteirizacaoBase`, `RotaPlanejada` | `capacidade_volumetrica`, `dimensoes_capacidade`, `carga_acumulada` | validacao, construcao da instancia, saida |
| Teto segurado | `Viatura`, `InstanciaRoteirizacaoBase`, `RotaPlanejada` | `teto_segurado`, `dimensoes_capacidade`, `uso_limite_segurado` | validacao, construcao da instancia, saida |
| Isolamento entre suprimento e recolhimento | `OrdemClassificada`, `InstanciaRoteirizacaoBase`, `ResultadoPlanejamento` | `classe_operacional`, `classe_operacional`, `rotas_suprimento`, `rotas_recolhimento` | classificacao, construcao da instancia, saida |
| Compatibilidade operacional | `Ponto`, `Ordem`, `Viatura`, `InstanciaRoteirizacaoBase` | `compatibilidades_minimas`, `compatibilidade_requerida`, `compatibilidade_servico`, `elegibilidade_veiculo_no` | validacao, classificacao, construcao da instancia |
| Circuito fechado | `Base`, `InstanciaRoteirizacaoBase`, `RotaPlanejada` | `id_base`, `depositos`, `id_base`, `sequencia_paradas` | modelagem, construcao da instancia, saida |
| Penalidade de nao atendimento | `Ordem`, `InstanciaRoteirizacaoBase`, `ResultadoPlanejamento` | `penalidade_nao_atendimento`, `penalidades`, `ordens_nao_atendidas` | validacao, construcao da instancia, saida |
| Penalidade por atraso | `Ordem`, `InstanciaRoteirizacaoBase`, `RotaPlanejada` | `penalidade_atraso`, `penalidades`, `indicadores_restricao` | validacao, construcao da instancia, saida |
| Uso de viatura adicional | `Viatura`, `InstanciaRoteirizacaoBase`, `ResultadoPlanejamento` | `custo_fixo`, `custos`, `kpis` | validacao, construcao da instancia, saida |
| Cancelamento tardio | `Ordem`, `EventoAuditoria`, `ResultadoPlanejamento` | `status_cancelamento`, `instante_cancelamento`, `motivo`, `auditoria` | classificacao, auditoria, saida |
| Parada improdutiva | `Ordem`, `EventoAuditoria`, `ResultadoPlanejamento` | `taxa_improdutiva`, `tipo_evento`, `kpis` | classificacao, auditoria, saida |
| Exclusao por cut-off | `OrdemClassificada`, `EventoAuditoria`, `ResultadoPlanejamento` | `elegivel_no_cutoff`, `motivo_exclusao`, `regra_relacionada`, `ordens_excluidas` | classificacao, auditoria, saida |
| Reprocessamento e auditoria | `MetadadoIngestao`, `MatrizLogistica`, `EventoAuditoria`, `ResultadoPlanejamento` | `origem`, `data_referencia`, `id_execucao`, `hash_cenario` | ingestao, construcao da instancia, auditoria, saida |

## Leitura obrigatoria desta matriz

- Toda regra relevante deve aparecer em ao menos um contrato.
- Toda regra com impacto operacional deve aparecer em ao menos uma etapa de aplicacao.
- Ausencia de campo estrutural para uma regra significa lacuna de modelagem e bloqueia implementacao segura.

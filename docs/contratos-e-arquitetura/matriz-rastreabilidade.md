# Matriz de rastreabilidade

| Regra ou requisito | Onde nasce | Contratos e campos | Estado atual |
| --- | --- | --- | --- |
| Data operacional unica da rodada | `contexto.json` / API inline | `ContextoExecucao.data_operacao`, `Ordem.data_operacao` | validada em `PlanningDatasetLoader` e `validate_ordem` |
| Separacao entre cadastro e demanda do dia | dataset | `Ponto`, `Ordem` | mantida durante todo o pipeline |
| Cancelamento antes do cut-off exclui a ordem | `Ordem.status_cancelamento` | `OrdemClassificada.status_ordem`, `motivo_exclusao` | aplicado em `classify_ordem` |
| Cancelamento apos o cut-off preserva impacto | `Ordem.status_cancelamento`, `taxa_improdutiva` | `OrdemClassificada.impacto_financeiro_previsto`, `impacto_operacional` | aplicado em `classify_ordem` e consolidado em auditoria e relatorio |
| Segregacao entre suprimento e recolhimento | `tipo_servico` e `classe_operacional` | `Ordem.classe_operacional`, `InstanciaRoteirizacaoBase.classe_operacional`, `ResultadoPlanejamento.rotas_suprimento`, `rotas_recolhimento` | implementado em `OptimizationInstanceBuilder` e `PlanningExecutor` |
| Compatibilidade entre viatura e atendimento | payloads de viatura e ponto | `compatibilidade_servico`, `compatibilidade_setor`, `compatibilidade_ponto`, `RestricaoElegibilidade` | avaliada na construcao da instancia |
| Teto segurado em recolhimento | `Viatura.teto_segurado` | `VeiculoRoteirizacao.capacidades["financeiro"]`, `RotaPlanejada.atingiu_limite_segurado` | aplicado na adaptacao da viatura e sinalizado na saida |
| Penalidade por nao atendimento | `Ordem.penalidade_nao_atendimento` | `PenalidadeRoteirizacao`, `OrdemNaoAtendida.penalidade_aplicada` | modelada na instancia e refletida no pos-processamento |
| Penalidade por atraso | `Ordem.penalidade_atraso` | `PenalidadeRoteirizacao`, `ParadaPlanejada.atraso_segundos` | carregada na instancia e observada na saida |
| Malha prioriza snapshot persistido | `logistics_snapshots/<data>.json` | `MatrizLogistica`, `SnapshotMaterializationResult` | `PersistedSnapshotLogisticsMatrixProvider` tenta carregar antes do fallback |
| Fallback local quando snapshot falha | ausencia ou cobertura incompleta do snapshot | `MatrizLogistica.estrategia_geracao`, eventos de auditoria | `FallbackLogisticsMatrixProvider` gera matriz `haversine_v1` |
| Idempotencia da execucao | entradas + parametros do solver + politica de snapshot | `hash_cenario`, `cenario.json`, `estado.json`, `resultado-planejamento.pkl` | implementada em `DailyPlanningOrchestrator` |
| Reaproveitamento do resultado | estado persistido por cenario | `reused_cached_result`, `attempt_number`, `manifest.json` | cache so e reutilizado para execucao concluida |
| Explicabilidade de erros e exclusoes | validacao, classificacao, solver e auditoria | `ErroContrato`, `ErroValidacao`, `EventoAuditoria`, `MotivoInviabilidade` | consolidada em `PlanningAuditTrailBuilder` |
| Exposicao unica para CLI, API e UI | interfaces publicas | `DatasetPlanningRequest`, `PlanningRunResponse` | todos convergem para o mesmo orquestrador |

## Como ler esta matriz

- Se uma regra aparece aqui, ela deve ser localizavel no codigo e em pelo menos um contrato serializavel.
- Se uma regra afeta decisao operacional, ela deve reaparecer em auditoria, relatorio ou status final.
- Se uma regra nao tiver contrato associado, trata-se de lacuna de modelagem.

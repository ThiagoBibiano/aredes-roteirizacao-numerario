# Especificacao de contratos do backend

## 1. Objetivo

Documentar os contratos que de fato sustentam o backend executavel de planejamento diario. Esta referencia cobre o fluxo compartilhado por CLI, API HTTP e UI Streamlit, sem repetir detalhes internos do PyVRP.

## 2. Fronteiras atuais do sistema

| Camada | Papel | Contratos principais |
| --- | --- | --- |
| Contexto de execucao | Fixar data operacional, corte e rastreabilidade da rodada | `ContextoExecucao` |
| Entrada bruta | Preservar payload de origem com metadados de ingestao | `BaseBruta`, `PontoBruto`, `ViaturaBruta`, `OrdemBruta`, `MetadadoIngestao` |
| Dominio validado | Representar entidades coerentes para o negocio | `Base`, `Ponto`, `Viatura`, `Ordem`, `MetadadoRastreabilidade` |
| Dominio classificado | Traduzir regras de cut-off e cancelamento para o planejamento | `OrdemClassificada` |
| Logistica | Representar a malha usada pela instancia | `TrechoLogistico`, `MatrizLogistica`, `SnapshotMaterializationResult` |
| Otimizacao generica | Descrever o problema sem depender do solver | `DepositoRoteirizacao`, `NoRoteirizacao`, `VeiculoRoteirizacao`, `PenalidadeRoteirizacao`, `RestricaoElegibilidade`, `InstanciaRoteirizacaoBase` |
| Saida | Consolidar rotas, nao atendimento, auditoria e relatorios | `ParadaPlanejada`, `RotaPlanejada`, `ResumoOperacional`, `KpiOperacional`, `KpiGerencial`, `LogPlanejamento`, `MotivoInviabilidade`, `RelatorioPlanejamento`, `ResultadoPlanejamento` |
| Orquestracao | Persistir cenario, cache e caminhos de saida | `DatasetPlanningRequest`, `OrchestrationResult` |

## 3. Modos de entrada

### 3.1 Dataset local

O orquestrador espera um diretorio com:

- `contexto.json`
- `bases.json`
- `pontos.json`
- `viaturas.json`
- `ordens.json`

Arquivos auxiliares opcionais:

- `logistics_sources/<data_operacao>.json`: fonte bruta para materializacao do snapshot.
- `logistics_snapshots/<data_operacao>.json`: snapshot persistido pronto para consumo.

### 3.2 Payload inline pela API

`POST /api/v1/planning/run` recebe `contexto`, `bases`, `pontos`, `viaturas` e `ordens` inline. A API grava esse material em `data/api_runs/<token>/dataset/` e delega a execucao para o mesmo `DailyPlanningOrchestrator`.

### 3.3 Parametros de execucao

Os tres consumidores publicos convergem para o mesmo conjunto de parametros:

- `materialize_snapshot`
- `max_iterations`
- `seed`
- `collect_stats`
- `display`

Esses campos participam do `hash_cenario` e, portanto, alteram a identidade da execucao.

## 4. Contratos de contexto e ingestao

### 4.1 `ContextoExecucao`

Campos obrigatorios:

- `id_execucao`
- `data_operacao`
- `cutoff`
- `timestamp_referencia`
- `versao_schema`

Uso atual:

- fixa a data operacional de toda a rodada;
- fornece timezone obrigatorio para comparacoes temporais;
- alimenta IDs e timestamps de eventos, erros, relatorios e hashes.

### 4.2 `MetadadoIngestao`

Campos:

- `origem`
- `timestamp_ingestao`
- `versao_schema`
- `identificador_externo`

Uso atual:

- acompanha cada payload bruto;
- permite rastrear a origem logica (`dataset.bases`, `dataset.ordens`, API inline, arquivo externo);
- e convertido para `MetadadoRastreabilidade` no dominio validado.

### 4.3 Contratos brutos

`BaseBruta`, `PontoBruto`, `ViaturaBruta` e `OrdemBruta` preservam o payload original em `payload` e os metadados de origem em `metadado_ingestao`.

Esses contratos nao impem schema forte. A validacao estrutural e de negocio acontece em `validate_base`, `validate_ponto`, `validate_viatura` e `validate_ordem`.

## 5. Contratos de dominio validado

### 5.1 `Base`

Campos obrigatorios no codigo atual:

- `id_base`
- `nome`
- `localizacao`
- `janela_operacao`
- `status_ativo`
- `metadados`

Campos opcionais:

- `capacidade_expedicao`
- `codigo_externo`
- `atributos_operacionais`

### 5.2 `Ponto`

Campos obrigatorios:

- `id_ponto`
- `tipo_ponto`
- `localizacao`
- `status_ativo`
- `setor_geografico`
- `metadados`

Campos opcionais mais usados:

- `janelas_padrao`
- `tempo_padrao_servico`
- `restricoes_acesso`
- `compatibilidades_minimas`
- `endereco_textual`

### 5.3 `Viatura`

Campos obrigatorios:

- `id_viatura`
- `tipo_viatura`
- `id_base_origem`
- `turno`
- `custo_fixo`
- `custo_variavel`
- `capacidade_financeira`
- `capacidade_volumetrica`
- `teto_segurado`
- `compatibilidade_servico`
- `status_ativo`
- `metadados`

Campos opcionais:

- `compatibilidade_ponto`
- `compatibilidade_setor`
- `restricoes_jornada`
- `atributos_operacionais`

### 5.4 `Ordem`

Campos obrigatorios de dominio:

- `id_ordem`
- `origem_ordem`
- `data_operacao`
- `versao_ordem`
- `timestamp_criacao`
- `id_ponto`
- `tipo_servico`
- `classe_planejamento`
- `classe_operacional`
- `criticidade`
- `valor_estimado`
- `volume_estimado`
- `tempo_servico`
- `janela_efetiva`
- `penalidade_nao_atendimento`
- `penalidade_atraso`
- `status_ordem`
- `status_cancelamento`
- `taxa_improdutiva`
- `metadados`

Campos opcionais:

- `sla`
- `compatibilidade_requerida`
- `instante_cancelamento`
- `elegivel_no_cutoff`
- `motivo_exclusao`
- `impacto_financeiro_previsto`
- `severidade_contratual`
- `janela_cancelamento`

Observacoes importantes do codigo atual:

- `classe_operacional` e inferida a partir de `tipo_servico` para `suprimento` e `recolhimento`.
- `tipo_servico = extraordinario` exige `classe_operacional` explicita.
- `classe_planejamento` pode ser normalizada por antecedencia e virar `eventual`.
- cancelamento sem instante ou janela coerente e rejeitado.

## 6. Contrato de classificacao

### 6.1 `OrdemClassificada`

Campos:

- `ordem`
- `status_ordem`
- `elegivel_no_cutoff`
- `planeavel`
- `motivo_exclusao`
- `impacto_financeiro_previsto`
- `impacto_operacional`

Regras fechadas hoje:

- cancelamento ate o `cutoff` produz `status_ordem = excluida`;
- cancelamento apos o `cutoff` produz `status_ordem = cancelada`;
- ordem sem cancelamento segue como `planejavel`;
- toda classificacao gera `EventoAuditoria`.

## 7. Contratos logisticos

### 7.1 Snapshot bruto de malha

Formato esperado em `logistics_sources/<data>.json`:

- `generated_at`
- `arcs`

Campos opcionais:

- `snapshot_id`
- `strategy_name`
- `schema_version`
- `source_name`

Cada item de `arcs` usa:

- `id_origem`
- `id_destino`
- `distancia_metros`
- `tempo_segundos`
- `custo`
- `disponivel`
- `restricao`

### 7.2 `SnapshotMaterializationResult`

Artefato retornado pela materializacao:

- `data_operacao`
- `snapshot_id`
- `content_hash`
- `snapshot_path`
- `version_path`
- `manifest_path`

### 7.3 `TrechoLogistico` e `MatrizLogistica`

Responsabilidades:

- representar todos os pares ordenados entre depositos e nos;
- diferenciar trecho disponivel de trecho bloqueado;
- manter `hash_matriz` rastreavel;
- permitir carregamento de snapshot persistido ou fallback geometrico local.

O provedor atual segue a estrategia:

1. tenta `PersistedSnapshotLogisticsMatrixProvider`;
2. se o snapshot estiver ausente, incompleto ou invalido, usa `FallbackLogisticsMatrixProvider`;
3. o fallback delega para `LogisticsMatrixBuilder` com estrategia `haversine_v1`.

## 8. Contratos de otimizacao

### 8.1 `InstanciaRoteirizacaoBase`

Uma instancia e gerada por `ClasseOperacional` e contem:

- `depositos`
- `nos_atendimento`
- `veiculos`
- `matriz_logistica`
- `dimensoes_capacidade`
- `janelas_tempo`
- `tempos_servico`
- `custos`
- `penalidades`
- `elegibilidade_veiculo_no`
- `parametros_construcao`
- `metadados`
- `custos_por_arco`
- `restricoes_extras`
- `hash_cenario`

Decisoes importantes do codigo atual:

- as dimensoes canonicas hoje sao `volume` e `financeiro`;
- recolhimento limita a capacidade financeira ao menor valor entre `capacidade_financeira` e `teto_segurado`;
- suprimento e recolhimento nao compartilham a mesma instancia;
- a elegibilidade do par `veiculo x no` considera servico, setor, ponto e restricoes minimas do ponto.

### 8.2 Adaptacao para solver

O backend congela o contrato ate `InstanciaRoteirizacaoBase`. A traducao para PyVRP fica restrita ao adaptador em `src/roteirizacao/optimization/pyvrp_adapter.py`.

## 9. Contratos de saida

### 9.1 Rotas e nao atendimento

O pos-processamento gera:

- `ParadaPlanejada`
- `RotaPlanejada`
- `OrdemNaoAtendida`
- `ResumoOperacional`

Esses contratos carregam horarios previstos, carga acumulada, custo estimado, violacao de janela, excesso de capacidade e sinalizacao de limite segurado.

### 9.2 Resultado consolidado

`ResultadoPlanejamento` agrega:

- status final;
- rotas de suprimento e recolhimento;
- ordens nao atendidas, excluidas e canceladas;
- eventos de auditoria;
- erros consolidados;
- `hashes_cenario`;
- `log_planejamento`;
- `motivos_inviabilidade`;
- `relatorio_planejamento`.

### 9.3 Artefatos de orquestracao

`OrchestrationResult` expone:

- caminhos persistidos (`output_path`, `result_path`, `state_path`, `scenario_path`, `manifest_path`);
- `hash_cenario`;
- `reused_cached_result`;
- `recovered_previous_context`;
- `attempt_number`;
- `snapshot_materialization`.

## 10. Persistencia operacional

Para cada `hash_cenario`, o orquestrador grava em `state_dir/<hash>/`:

- `cenario.json`
- `estado.json`
- `resultado-planejamento.json`
- `resultado-planejamento.pkl`

Tambem mantem:

- `manifest.json` no diretorio de execucoes;
- `output_path` como alias legivel do ultimo resultado consolidado;
- snapshots versionados em `logistics_snapshots/versions/<data>/`.

## 11. Interfaces publicas

### 11.1 CLI

Comandos:

- `materialize-snapshot`
- `run-planning`

### 11.2 API HTTP

Endpoints:

- `GET /health`
- `POST /api/v1/snapshots/materialize`
- `POST /api/v1/planning/run-dataset`
- `POST /api/v1/planning/run`

### 11.3 UI Streamlit

A UI nao executa o solver localmente. Ela conversa com a API e trabalha sobre o mesmo contrato de resposta de `PlanningRunResponse`, transformado em view models apenas para visualizacao, filtros e exportacao offline.

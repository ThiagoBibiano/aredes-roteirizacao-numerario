# Especificacao formal da Etapa 1

## 1. Objetivo

A Etapa 1 define a verdade estrutural do sistema. O foco nao e modelar classes em funcao de tecnologia, mas formalizar contratos de dados que estabilizam a comunicacao entre modulos e preservam o dominio contra acoplamento precoce com solver, banco, CSV ou APIs externas.

Esta etapa deve produzir uma linguagem unica para o sistema e criar base para:

- implementacao incremental com TDD;
- testes de contrato desde o inicio;
- rastreabilidade de decisoes e exclusoes;
- reprocessamento de execucoes;
- adaptacao futura a diferentes solvers.

## 2. Principios obrigatorios

1. O centro da aplicacao e o processo de planejamento operacional.
2. O dominio nao conhece PyVRP, banco, API de malha ou formato de ingestao.
3. Cada estagio do pipeline tem fronteira semantica propria.
4. Todo dado relevante deve ser rastreavel por origem, tempo de referencia e execucao.
5. Restricoes reais do negocio devem estar representadas nos contratos.
6. A auditoria deve ser um requisito estrutural, nao um efeito colateral.

## 3. Fronteiras do pipeline

Os contratos da Etapa 1 sao agrupados por papel no fluxo:

| Camada | Papel | Exemplos |
| --- | --- | --- |
| Entrada bruta | Preservar dado de origem e metadados de ingestao | `BaseBruta`, `PontoBruto`, `ViaturaBruta`, `OrdemBruta`, `MetadadoIngestao` |
| Dominio validado | Representar entidades coerentes e utilizaveis pelo negocio | `Base`, `Ponto`, `Viatura`, `Ordem` |
| Dominio enriquecido | Representar entidades classificadas para planejamento | `OrdemClassificada`, `OrdemPlanejavel`, `OrdemCancelada`, `RegraAplicada`, `ImpactoCancelamento` |
| Otimizacao generica | Traduzir o problema para uma linguagem solver-agnostic | `NoRoteirizacao`, `VeiculoRoteirizacao`, `PenalidadeRoteirizacao`, `RestricaoElegibilidade`, `InstanciaRoteirizacaoBase` |
| Saida | Expor o produto util do sistema | `ParadaPlanejada`, `RotaPlanejada`, `ResumoOperacional`, `KpiOperacional`, `KpiGerencial`, `EventoAuditoria`, `ResultadoPlanejamento` |

## 4. Decisoes semanticas fechadas nesta etapa

### 4.1 Tipo de servico versus classe de planejamento

- `tipo_servico` representa a natureza operacional do atendimento.
- `classe_planejamento` representa prioridade temporal ou comercial.
- `classe_operacional` representa o eixo estrutural que isola cenarios de suprimento e recolhimento.

Decisao: o termo `especial` nao deve ser usado como `tipo_servico`. Ele pertence a `classe_planejamento`.

Exemplo aceito:

- `tipo_servico = extraordinario`
- `classe_planejamento = especial`
- `classe_operacional = suprimento`

### 4.2 Ponto versus ordem

- `Ponto` representa cadastro do local e caracteristicas persistentes.
- `Ordem` representa demanda operacional do dia.

Decisao: janela efetiva e tempo de servico efetivo pertencem a `Ordem`. `Ponto` pode manter valores padrao e restricoes cadastrais.

### 4.3 Cancelamento como estado

Cancelamento nao pode ser um booleano solto. Deve haver:

- status;
- instante de referencia;
- impacto operacional;
- impacto financeiro;
- elegibilidade para exclusao;
- motivo rastreavel.

### 4.4 Compatibilidade operacional explicita

Compatibilidade entre viatura, servico, ponto, setor ou outra restricao equivalente deve existir como dado contratual. Nao pode ficar escondida em logica futura.

## 5. Entidades, value objects e contratos

### 5.1 Entidades centrais

- `Base`: deposito operacional de partida e retorno.
- `Ponto`: local de atendimento reutilizavel por varias ordens.
- `Ordem`: demanda operacional planeavel ou excluivel.
- `Viatura`: recurso operacional com custos, jornada e capacidades.

### 5.2 Value objects recomendados

- `Coordenada`
- `JanelaTempo`
- `PeriodoOperacional`
- `Capacidade`
- `Penalidade`
- `CompatibilidadeOperacional`
- `MetadadoRastreabilidade`
- `IdentificadorExecucao`

### 5.3 Contratos de transporte e saida

- `MatrizLogistica`
- `InstanciaRoteirizacaoBase`
- `ParadaPlanejada`
- `RotaPlanejada`
- `ResumoOperacional`
- `EventoAuditoria`
- `ResultadoPlanejamento`

## 6. Especificacao dos contratos principais

### 6.1 Base

**Papel**

Representar o deposito operacional do circuito fechado do MVP.

**Campos obrigatorios**

- `id_base`
- `nome`
- `localizacao`
- `janela_operacao`
- `status_ativo`
- `metadados`

**Campos opcionais**

- `capacidade_expedicao`
- `codigo_externo`
- `atributos_operacionais`

**Invariantes**

- identificador unico e estavel;
- localizacao obrigatoria e valida;
- horario de operacao coerente;
- base inativa nao pode ser usada para gerar instancia roteirizavel sem decisao explicita da etapa seguinte.

### 6.2 Ponto

**Papel**

Representar o local de atendimento e seus atributos cadastrais.

**Campos obrigatorios**

- `id_ponto`
- `tipo_ponto`
- `localizacao`
- `status_ativo`
- `setor_geografico`
- `metadados`

**Campos opcionais**

- `janelas_padrao`
- `tempo_padrao_servico`
- `restricoes_acesso`
- `compatibilidades_minimas`
- `endereco_textual`

**Invariantes**

- identificador unico;
- localizacao definida;
- janelas padrao coerentes, quando informadas;
- tempo padrao de servico nao negativo;
- ponto pode existir sem ordem, mas ordem nao pode existir sem ponto referenciado.

### 6.3 Ordem

**Papel**

Representar a demanda operacional do dia e seu ciclo de vida no planejamento.

**Estagios**

- `OrdemBruta`
- `Ordem`
- `OrdemClassificada`
- `OrdemPlanejavel`
- `OrdemCancelada`

**Campos obrigatorios minimos de dominio validado**

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

**Campos opcionais relevantes**

- `sla`
- `compatibilidade_requerida`
- `instante_cancelamento`
- `elegivel_no_cutoff`
- `motivo_exclusao`
- `impacto_financeiro_previsto`
- `severidade_contratual`
- `janela_cancelamento`

**Invariantes**

- `valor_estimado >= 0`;
- `volume_estimado >= 0`;
- `tempo_servico >= 0`;
- `fim_janela >= inicio_janela`;
- `tipo_servico` pertence ao vocabulario controlado;
- `classe_planejamento` pertence ao vocabulario controlado;
- `criticidade` pertence ao vocabulario controlado;
- penalidades e taxa improdutiva nao podem ser negativas;
- cancelamento exige estado explicito e temporalidade coerente;
- ordem validada sempre referencia um ponto existente.

### 6.4 Viatura

**Papel**

Representar o recurso operacional disponivel para o planejamento.

**Campos obrigatorios**

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

**Campos opcionais**

- `compatibilidade_ponto`
- `compatibilidade_setor`
- `restricoes_jornada`
- `atributos_operacionais`

**Invariantes**

- viatura deve possuir base de origem;
- viatura deve possuir turno;
- custos nao podem ser negativos;
- capacidades devem estar explicitas;
- teto segurado e obrigatorio no escopo do MVP;
- viatura sem compatibilidade suficiente nao pode ser elegivel para determinados nos na instancia.

### 6.5 MatrizLogistica

**Papel**

Representar a malha diaria usada para construcao do problema.

**Campos obrigatorios**

- `id_matriz`
- `data_referencia`
- `nos`
- `indice_por_no`
- `matriz_tempo`
- `matriz_distancia`
- `metadados_geracao`

**Campos opcionais**

- `matriz_custo`
- `trechos_indisponiveis`
- `fonte_malha`
- `hash_conteudo`

**Invariantes**

- todos os nos devem possuir indice estavel;
- as matrizes devem ter dimensao coerente com os nos;
- tempos e distancias nao podem ser negativos;
- trechos indisponiveis devem referenciar nos existentes;
- metadados devem permitir reproducao do cenario.

### 6.6 InstanciaRoteirizacaoBase

**Papel**

Representar o problema diario em formato neutro de solver.

**Campos obrigatorios**

- `id_cenario`
- `classe_operacional`
- `depositos`
- `nos_atendimento`
- `veiculos`
- `dimensoes_capacidade`
- `janelas_tempo`
- `tempos_servico`
- `custos`
- `penalidades`
- `elegibilidade_veiculo_no`
- `parametros_construcao`
- `metadados`

**Campos opcionais**

- `custos_por_arco`
- `restricoes_extras`
- `hash_cenario`

**Invariantes**

- ao menos um deposito deve existir;
- todos os nos referenciados devem existir no mapa interno;
- todos os veiculos devem ter capacidades explicitas;
- toda demanda convertida deve ter penalidade definida;
- isolamento entre suprimento e recolhimento deve estar refletido na instancia;
- cenarios de recolhimento devem carregar dimensao financeira compativel com teto segurado.

### 6.7 RotaPlanejada

**Papel**

Representar a rota operacional planejada por viatura.

**Campos obrigatorios**

- `id_rota`
- `id_execucao`
- `id_viatura`
- `id_base`
- `classe_operacional`
- `sequencia_paradas`
- `horarios_previstos`
- `carga_acumulada`
- `custo_estimado`
- `indicadores_restricao`

**Campos opcionais**

- `folgas_operacionais`
- `uso_limite_segurado`
- `observacoes`

**Invariantes**

- rota deve iniciar e terminar em base quando o cenario exigir circuito fechado;
- sequencia de paradas deve ser coerente com os horarios;
- carga acumulada nao pode violar capacidades sem que a violacao esteja sinalizada em contrato apropriado;
- classe operacional deve coincidir com a instancia origem.

### 6.8 EventoAuditoria

**Papel**

Representar fatos relevantes, decisoes, violacoes e exclusoes do pipeline.

**Campos obrigatorios**

- `id_evento`
- `tipo_evento`
- `severidade`
- `entidade_afetada`
- `id_entidade`
- `regra_relacionada`
- `motivo`
- `timestamp_evento`
- `id_execucao`

**Campos opcionais**

- `campo_afetado`
- `valor_observado`
- `valor_esperado`
- `contexto_adicional`

**Invariantes**

- evento sempre referencia entidade ou execucao identificavel;
- tipo e severidade pertencem ao vocabulario controlado;
- eventos de exclusao ou rejeicao exigem motivo;
- evento deve ser serializavel e ordenavel no tempo.

### 6.9 ResultadoPlanejamento

**Papel**

Representar o agregado final da execucao.

**Campos obrigatorios**

- `id_execucao`
- `hash_cenario`
- `status_final`
- `resumo_executivo`
- `rotas_suprimento`
- `rotas_recolhimento`
- `ordens_nao_atendidas`
- `ordens_excluidas`
- `kpis`
- `auditoria`

**Campos opcionais**

- `avisos`
- `estatisticas_solver`
- `referencias_reprocessamento`

**Invariantes**

- resultado final deve ser suficiente para auditoria e reprocessamento;
- status final deve ser coerente com presenca ou ausencia de rotas;
- ordens excluidas e nao atendidas devem ser explicaveis.

## 7. Regras de modelagem obrigatorias

As regras abaixo devem estar representadas estruturalmente em pelo menos um contrato:

- janela de atendimento;
- jornada maxima;
- capacidade financeira;
- capacidade volumetrica;
- teto segurado;
- isolamento entre suprimento e recolhimento;
- compatibilidade operacional;
- circuito fechado;
- penalidade por nao atendimento;
- penalidade por atraso;
- custo de viatura adicional;
- cancelamento tardio;
- parada improdutiva.

## 8. Entregaveis de aceite da Etapa 1

A Etapa 1 so deve ser considerada pronta quando:

1. a semantica do dominio estiver estabilizada;
2. os contratos centrais estiverem especificados;
3. as invariantes estiverem explicitas;
4. as regras de negocio tiverem representacao estrutural;
5. o dominio estiver desacoplado de PyVRP;
6. os testes de contrato estiverem definidos;
7. os criterios de serializacao e versionamento estiverem registrados.

## 9. Dependencias para etapas seguintes

As etapas de validacao, classificacao, construcao de instancia, auditoria e adaptacao para solver dependem diretamente desta especificacao. Nenhuma implementacao dessas etapas deve assumir significado nao definido aqui.

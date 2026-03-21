# Glossario do dominio

## Base operacional

Deposito operacional de partida e retorno da viatura no cenario do MVP.

Exemplo valido: base que inicia e encerra rotas de suprimento de um dia operacional.

Contraexemplo: centro administrativo sem funcao logistica na execucao.

## Ponto atendido

Local fisico ou operacional elegivel para receber uma ordem.

Exemplo valido: agencia, cliente, terminal ou unidade com coordenada e identificador estavel.

Contraexemplo: a propria ordem do dia.

## Ordem

Demanda operacional associada a um ponto em uma data de operacao.

Exemplo valido: recolhimento estimado em um ponto com janela efetiva e penalidade de nao atendimento.

Contraexemplo: cadastro mestre do local.

## Viatura

Recurso operacional com jornada, custos, capacidades e compatibilidades.

Exemplo valido: carro-forte associado a uma base e com teto segurado.

Contraexemplo: regra de negocio abstrata sem identidade operacional.

## Capacidade

Limite mensuravel consumido durante a execucao de uma rota.

Exemplo valido: capacidade volumetrica e capacidade financeira.

Contraexemplo: criticidade da ordem.

## Janela de atendimento

Intervalo temporal permitido para execucao do servico.

Exemplo valido: inicio e fim de atendimento aceitavel para a ordem do dia.

Contraexemplo: duracao de turno da viatura.

## Tempo de servico

Duracao prevista da operacao executada em uma parada.

Exemplo valido: minutos necessarios para atendimento no ponto.

Contraexemplo: tempo de deslocamento entre dois nos.

## Classe de planejamento

Classificacao de prioridade temporal ou comercial da ordem para o processo decisorio.

Exemplo valido: `padrao`, `especial`.

Contraexemplo: `suprimento`.

## Tipo de servico

Natureza operacional do atendimento.

Exemplo valido: `suprimento`, `recolhimento`, `extraordinario`.

Contraexemplo: `especial`.

## Classe operacional

Eixo estrutural usado para isolar o problema em familias compativeis de roteirizacao.

Exemplo valido: `suprimento`, `recolhimento`.

Contraexemplo: severidade de penalidade.

## Criticidade

Medida da relevancia operacional ou contratual da ordem.

Exemplo valido: `baixa`, `media`, `alta`, `critica`.

Contraexemplo: distancia ate a base.

## Cancelamento

Estado operacional da ordem que altera elegibilidade, impacto financeiro e auditoria.

Exemplo valido: ordem cancelada apos cut-off, com parada improdutiva registrada.

Contraexemplo: flag booleana sem motivo ou timestamp.

## Parada improdutiva

Impacto operacional ou financeiro causado por atendimento frustrado, deslocamento inutil ou cancelamento tardio.

Exemplo valido: viatura deslocada ate ponto cancelado sem tempo habil para replanejamento.

Contraexemplo: atraso comum absorvido pela folga da rota.

## Evento de auditoria

Registro estruturado de fato relevante ocorrido no pipeline.

Exemplo valido: exclusao de ordem por violacao de schema ou regra de cut-off.

Contraexemplo: log textual sem entidade, motivo ou timestamp.

## Instancia de roteirizacao

Representacao solver-agnostic do problema diario.

Exemplo valido: conjunto de depositos, nos, veiculos, janelas, capacidades e penalidades.

Contraexemplo: objeto nativo do PyVRP.

## Rota planejada

Sequencia operacional de paradas atribuida a uma viatura.

Exemplo valido: rota com horarios, carga acumulada e custo estimado.

Contraexemplo: lista de ordens sem associacao com recurso e horario.

## Resultado do planejamento

Agregado final da execucao contendo rotas, ordens atendidas, ordens excluidas, KPIs e auditoria.

Exemplo valido: artefato completo para consumo operacional e reprocessamento.

Contraexemplo: apenas o conjunto de rotas retornado por um solver.

## Cut-off

Marco temporal a partir do qual cancelamentos e alteracoes passam a ter consequencias especificas no planejamento.

Exemplo valido: cancelamento apos cut-off que gera impacto financeiro ou parada improdutiva.

Contraexemplo: horario de abertura da base.

## Teto segurado

Limite financeiro aceito para acumulacao em rota ou viatura no contexto do MVP.

Exemplo valido: valor maximo suportado por viatura em cenario de recolhimento.

Contraexemplo: custo operacional da rota.

## Circuito fechado

Regra segundo a qual a rota parte de uma base e retorna a essa base no escopo do MVP.

Exemplo valido: rota diaria iniciada e encerrada no mesmo deposito.

Contraexemplo: sequencia aberta de atendimentos sem retorno.

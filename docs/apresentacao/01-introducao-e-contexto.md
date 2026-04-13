# 1. Introdução e Contexto

## O problema

No transporte de valores, planejar uma operação não significa apenas ligar pontos da rede.

É preciso definir:

- quais **ordens** serão atendidas;
- quais **viaturas** executarão cada circuito;
- em que sequência os atendimentos ocorrerão;
- como respeitar restrições de tempo, capacidade e risco.

Cada decisão altera o custo da operação, o uso da frota e a viabilidade do atendimento.

---

## A rede analisada

Nesta apresentação, a rede é representada por poucos elementos centrais:

- **base**: origem e retorno das viaturas;
- **ordens**: demandas de atendimento distribuídas na rede;
- **viaturas**: recursos operacionais disponíveis;
- **rotas**: circuitos construídos para atender as ordens.

O interesse aqui não está em descrever uma operação isolada, mas em observar como essa rede responde quando a pressão operacional aumenta.

**[DEIXA PARA IMAGEM]**
Inserir uma imagem simples da rede-base com:
- base destacada;
- pontos de atendimento;
- indicação visual de ordens distribuídas no espaço.

---

## Dois tipos de operação

O problema foi analisado em dois contextos operacionais:

### Suprimento
A viatura parte da base carregada e realiza entregas ao longo da rota.

### Recolhimento
A viatura percorre a rede acumulando valores ao longo do circuito.

Essa separação é importante porque muda a interpretação de capacidade, risco e ocupação da viatura.

Nesta apresentação, `suprimento` e `recolhimento` são lidos como **experimentos isolados**.

---

## O foco desta apresentação

O objetivo aqui não é mostrar código nem detalhar implementação.

O foco é analisar, sobre a mesma rede de transporte de valores, o comportamento de duas abordagens de resolução:

- **PyVRP**
- **PuLP**

A comparação busca responder uma questão prática:

> como a qualidade da solução e a viabilidade computacional mudam quando cresce a quantidade de ordens na rede?

---

## Recorte experimental

O benchmark parte do cenário **`operacao_sob_pressao`**.

A partir dele, são geradas amostras aleatórias de ordens em diferentes escalas:

- **20%**
- **40%**
- **60%**
- **80%**

Ao final, há ainda uma **rodada exaustiva com 100% das ordens**.

Esse desenho permite observar a rede de forma progressiva, comparando os solvers em situações de complexidade crescente.

**[DEIXA PARA GIF]**
Inserir um gif mostrando o aumento gradual da quantidade de ordens sobre a mesma rede:
20% → 40% → 60% → 80% → 100%.

---

## O que será observado

A análise comparativa se apoia em quatro leituras principais:

- **médias por percentual de ordens**;
- **dispersão entre repetições**;
- **erro relativo da função objetivo do PyVRP em relação ao PuLP**;
- **viabilidade do PuLP conforme a escala cresce**.

Assim, a apresentação não discute apenas “qual solver resolve”, mas **como cada abordagem se comporta sob aumento de escala**.

---

## Interpretação esperada

Em problemas de roteirização, encontrar uma solução viável é apenas parte da questão.

Também é necessário avaliar:

- se a solução mantém boa qualidade;
- se o tempo de processamento permanece aceitável;
- se a abordagem continua utilizável quando a rede cresce.

Esse é o ponto central da análise apresentada a seguir.

---

## Síntese da abertura

Esta apresentação investiga a roteirização em redes de transporte de valores a partir de um benchmark comparativo.

O interesse principal está em entender o equilíbrio entre:

- **custo da solução**;
- **estabilidade dos resultados**;
- **capacidade prática de resolução**.

A partir daqui, a rede deixa de ser vista apenas como um conjunto de rotas possíveis e passa a ser analisada como um problema de decisão sob pressão operacional.

[Próxima ➡️](./02-elementos-da-rede-grafica.md)

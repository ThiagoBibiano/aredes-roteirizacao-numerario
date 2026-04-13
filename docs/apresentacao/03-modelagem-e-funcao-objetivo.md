# 3. Modelagem e Função Objetivo

## Da rede ao problema de decisão

Depois de representar a operação como uma rede, o passo seguinte é definir **como decidir** quais conexões serão usadas.

Em termos de modelagem, o problema passa a ser:

- escolher quais **ordens** serão atendidas;
- decidir quais **viaturas** serão ativadas;
- determinar a sequência de atendimento em cada rota;
- minimizar o custo total da operação sem violar as restrições.

A formulação matemática organiza essas escolhas de forma explícita.

---

## O que define uma boa solução

Uma solução boa não é apenas uma rota curta.

Ela precisa ser, ao mesmo tempo:

- **viável no tempo**;
- **viável na capacidade**;
- **coerente com o tipo de operação**;
- **eficiente em custo**.

Por isso, o modelo não procura somente o menor caminho: ele procura a melhor combinação entre atendimento, deslocamento e uso de viaturas. A página atual já estrutura essa ideia nesses quatro critérios, e vale mantê-los porque eles sintetizam bem a lógica do problema. :contentReference[oaicite:1]{index=1}

---

## Blocos da modelagem

A formulação pode ser lida em três blocos principais:

### 1. Viaturas
Cada viatura possui características operacionais próprias, como:

- custo fixo de ativação;
- turno disponível;
- capacidade volumétrica;
- limite financeiro segurado.

### 2. Ordens
Cada ordem representa uma demanda da operação e carrega atributos como:

- volume;
- valor;
- tempo de serviço;
- janela de atendimento.

### 3. Rede de deslocamento
A rede conecta base e pontos de atendimento por meio de arestas com atributos como:

- distância;
- tempo de deslocamento;
- custo associado ao percurso.

Esses três blocos formam a base da decisão: **quem atende, o que atende e por onde atende**.

**[DEIXA PARA IMAGEM]**
Inserir uma imagem simples relacionando:
- viatura;
- base;
- ordens;
- setas de deslocamento;
- legenda curta com “custos”, “tempo” e “capacidade”.

---

## Variáveis de decisão

A formulação usa variáveis para representar escolhas operacionais.

De forma simples:

- `x_{ij}^k` indica se a **viatura k** percorre o arco do ponto `i` para o ponto `j`;
- `y_k` indica se a **viatura k** foi ativada;
- `u_i` indica se a **ordem i** não foi atendida.

Essas variáveis permitem transformar a operação em um problema de otimização.

---

## Função objetivo

A função objetivo resume o que o modelo procura minimizar. No material atual, ela aparece como a soma de quatro componentes: custo fixo de viatura, custo de deslocamento, custo de duração e penalidade por não atendimento. :contentReference[oaicite:2]{index=2}

$$
\min Z =
\underbrace{\sum_{k \in K} F_k y_k}_{\text{custo fixo de viatura}}
+
\underbrace{\sum_{k \in K}\sum_{(i,j)\in A} C_{ij}^k x_{ij}^k}_{\text{custo de deslocamento}}
+
\underbrace{\sum_{k \in K}\sum_{(i,j)\in A} T_{ij} x_{ij}^k}_{\text{custo de duração}}
+
\underbrace{\sum_{i \in N} P_i u_i}_{\text{penalidade por não atendimento}}
$$

---

## Como ler essa equação

Essa expressão pode ser entendida em quatro perguntas simples:

### Quantas viaturas foram usadas?
O termo
$$\sum_{k \in K} F_k y_k$$
representa o custo fixo de ativar viaturas.

Quanto mais viaturas forem colocadas em operação, maior tende a ser esse custo.

### Quanto foi gasto em deslocamento?
O termo
$$\sum_{k \in K}\sum_{(i,j)\in A} C_{ij}^k x_{ij}^k$$
mede o custo associado aos trechos percorridos.

Ele traduz o efeito espacial da rede sobre a solução.

### Quanto tempo operacional foi consumido?
O termo
$$\sum_{k \in K}\sum_{(i,j)\in A} T_{ij} x_{ij}^k$$
incorpora o impacto da duração das rotas.

Mesmo quando duas soluções têm distâncias parecidas, elas podem diferir em tempo total.

### Houve ordens não atendidas?
O termo
$$\sum_{i \in N} P_i u_i$$
aplica penalidade para ordens que ficam fora da solução.

Isso impede que o modelo “barateie” a operação simplesmente deixando demandas de lado.

---

## O sentido da função objetivo

Em linguagem simples, a formulação tenta encontrar uma solução que:

- use a frota com parcimônia;
- evite deslocamentos desnecessários;
- contenha a duração das rotas;
- preserve a cobertura das ordens.

Ou seja:

> a melhor solução não é a que apenas percorre menos distância, mas a que equilibra custo, tempo e atendimento dentro das restrições da operação.

---

## Restrições que estruturam o problema

A página atual já destaca as restrições essenciais, e elas devem permanecer porque são exatamente as que tornam a solução operacionalmente válida. :contentReference[oaicite:3]{index=3}

### Atendimento único
Uma ordem não pode ser atendida mais de uma vez.

### Capacidade da viatura
Cada viatura precisa respeitar:
- capacidade volumétrica;
- limite financeiro segurado.

### Janela de tempo e turno
O atendimento precisa ocorrer dentro da janela prevista, e a rota deve caber no turno operacional.

### Partida e retorno à base
Toda rota válida sai da base e retorna à base.

### Separação entre tipos de operação
`suprimento` e `recolhimento` permanecem isolados.

Essa última condição é especialmente importante no benchmark, porque a comparação experimental não mistura as duas classes na mesma leitura analítica. A própria documentação atual enfatiza esse ponto. :contentReference[oaicite:4]{index=4}

---

## O que a modelagem permite comparar

Essa formulação é importante porque transforma a operação em algo comparável entre solvers.

Com a mesma estrutura de custo e restrições, torna-se possível observar:

- se as soluções permanecem viáveis;
- como varia o custo total;
- como muda o uso das viaturas;
- até que ponto cada abordagem continua prática quando o número de ordens cresce.

No benchmark, o valor comparado entre PyVRP e PuLP é recalculado fora do solver como `objective_common`, justamente para manter uma base comum de comparação. :contentReference[oaicite:5]{index=5}

**[DEIXA PARA GIF]**
Inserir um gif curto mostrando:
- rede inicial;
- ativação de uma ou duas viaturas;
- seleção progressiva de arcos;
- ordens atendidas e eventual ordem não atendida destacada.

---

## Síntese

A modelagem transforma a rede em um problema de otimização.

Com isso, a análise deixa de perguntar apenas “qual rota parece boa” e passa a perguntar:

- qual solução minimiza custo total;
- quais restrições limitam a operação;
- como diferentes métodos se comportam diante da mesma formulação.

Essa base é o que permite, na sequência, comparar PyVRP e PuLP de forma coerente.

[⬅️ Anterior](./02-elementos-da-rede-grafica.md) | [Próxima ➡️](./04-tecnologia-solucao.md)

# 2. Elementos da Rede Gráfica

## Da operação para a rede

Para analisar a roteirização, o espaço operacional é convertido em uma rede.

Nessa leitura:

- a **base** organiza a saída e o retorno das viaturas;
- as **ordens** se materializam em pontos de atendimento;
- as **viaturas** percorrem circuitos sobre essa estrutura;
- as **rotas** passam a ser caminhos escolhidos dentro da rede.

A representação gráfica reduz a complexidade do mapa físico e destaca apenas os elementos que influenciam a decisão.

---

## Estrutura básica da rede

A rede pode ser lida a partir de três componentes:

### Nós
Representam os pontos relevantes da operação:
- base;
- clientes;
- pontos de coleta ou entrega;
- locais associados às ordens.

### Arestas
Representam os deslocamentos possíveis entre dois pontos da rede.

### Atributos
Qualificam nós e arestas com informações operacionais, como:
- tempo de deslocamento;
- distância;
- custo;
- tempo de serviço;
- janela de atendimento;
- demanda associada à ordem.

**[DEIXA PARA IMAGEM]**
Inserir a imagem da rede-base com marcações simples:
- base em destaque;
- ordens distribuídas como nós;
- conexões sugeridas entre pontos.

![Mapa sintetizado da rede-base](./assets/generated/operacao_sob_pressao_rede_base.png)

---

## O que a visualização permite perceber

Antes de qualquer solver ser executado, a rede já revela aspectos importantes da operação:

- concentração ou dispersão espacial das ordens;
- proximidade entre pontos de atendimento;
- regiões com maior pressão de atendimento;
- efeito da posição da base sobre os circuitos possíveis.

Essa leitura é importante porque o problema não depende apenas da quantidade de ordens, mas também de **como elas se distribuem na rede**.

---

## O que cada elemento informa

Cada **nó** da rede carrega informação sobre o atendimento:

- onde a ordem está localizada;
- quando pode ser atendida;
- quanto tempo consome;
- que carga operacional impõe à viatura.

Cada **aresta** informa o custo do deslocamento entre dois pontos:

- quanto tempo será gasto;
- qual distância será percorrida;
- qual impacto isso gera no custo total da rota.

Assim, a solução não escolhe apenas “quais pontos visitar”, mas também **como atravessar a rede de forma viável**.

---

## Leitura gráfica da operação

Em termos de análise de redes de transporte, a solução final pode ser entendida como:

> um subconjunto orientado da rede original, selecionado para atender ordens com menor custo possível e sob restrições operacionais.

Isso significa que a rede completa contém muitas conexões possíveis, mas apenas parte delas será utilizada por cada viatura.

**[DEIXA PARA GIF]**
Inserir um gif mostrando:
- a rede completa mais difusa no início;
- depois o aparecimento de poucas conexões destacadas;
- por fim, a formação de uma ou mais rotas válidas.

---

## Rede potencial e rede realizada

Há uma diferença importante entre duas leituras:

### Rede potencial
É o conjunto de conexões que poderiam ser usadas.

### Rede realizada
É o conjunto de conexões efetivamente selecionadas na solução.

Essa distinção ajuda a interpretar os resultados do benchmark:
o solver não cria a rede do zero, mas escolhe, entre várias possibilidades, os circuitos que melhor atendem às ordens disponíveis.

---

## Relação com o benchmark

No benchmark desta apresentação, o que varia não é apenas o solver.

Também varia a pressão imposta sobre a rede, à medida que cresce a quantidade de ordens consideradas.

Com isso, a visualização da rede passa a apoiar três perguntas:

- como os circuitos mudam quando o volume de ordens aumenta;
- como a ocupação espacial da rede afeta a solução;
- em que ponto a complexidade começa a comprometer a resolução.

---

## Síntese

A representação gráfica da rede organiza o problema em uma forma analisável.

Ela permite observar:

- os pontos que precisam ser conectados;
- os custos associados a cada deslocamento;
- a diferença entre possibilidades da rede e rotas efetivamente construídas.

A partir daqui, o passo seguinte é definir **como essa rede é modelada como problema de decisão** e quais critérios permitem comparar soluções.

[⬅️ Anterior](./01-introducao-e-contexto.md) | [Próxima ➡️](./03-modelagem-e-funcao-objetivo.md)

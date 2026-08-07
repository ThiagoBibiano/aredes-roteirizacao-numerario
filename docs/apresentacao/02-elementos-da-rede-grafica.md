# 2. Elementos da Rede Gráfica

## Da operação para os dados

Para que o algoritmo analise a roteirização, o mapa físico é abstraído e convertido em uma **rede matemática**.

Nesta modelagem:

- a **base** é o nó central, organizando o despacho e o regresso da frota;
- as **ordens** tornam-se pontos de atendimento (demanda);
- as **viaturas** são os recursos que navegam por esta malha;
- as **rotas** são os circuitos otimizados selecionados pelo solver.

Essa abstração gráfica limpa o ruído geográfico e isola apenas as variáveis que impactam a decisão matemática.

---

## Estrutura da malha

A rede é construída sobre três componentes fundamentais:

### Nós (Vértices)
Representam os locais de interesse da operação:
- a base operacional;
- os pontos de `recolhimento` (coleta) ou `suprimento` (entrega).

### Arestas (Conexões)
Representam os deslocamentos viáveis entre dois nós quaisquer.

### Atributos (Pesos e Restrições)
Qualificam os nós e as arestas com parâmetros reais do negócio:
- **Nas arestas:** tempo de viagem, distância, custo de pedágio/deslocamento.
- **Nos nós:** tempo de serviço (SLA), janela de atendimento, volume da demanda.

![Mapa sintetizado da rede-base](./assets/generated/operacao_sob_pressao_rede_base.png)

---

## A anatomia da decisão

Para o solver, a rede é um mapa de custos e limites.

O **nó** dita as regras de parada:
- *Onde* a ordem está;
- *Quando* a viatura pode chegar (janela temporal);
- *Quanto* da capacidade do baú será ocupada.

A **aresta** dita o custo de transição:
- *Quanto* tempo de rota será consumido;
- *Qual* a penalidade financeira desse deslocamento.

Portanto, resolver o problema é decidir não apenas "quem atender", mas **"como atravessar a malha de forma viável e barata"**.

---

## O Espaço de Busca vs. A Solução

Em análise de redes, a solução final é definida como:

> Um subconjunto orientado da rede original, selecionado para cobrir a demanda com o menor custo possível, sem violar restrições físicas ou temporais.

A rede inicial é densa e altamente conectada. O papel do solver é "podar" o excesso e isolar apenas os caminhos ótimos.

[⬅️ Anterior](./01-introducao-e-contexto.md) | [Próxima ➡️](./03-modelagem-e-funcao-objetivo.md)

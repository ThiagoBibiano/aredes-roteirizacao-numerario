# 3. Modelagem e Função Objetivo

## Da rede ao problema de decisão

A rede nos mostra o que *pode* ser feito. A modelagem define o que *deve* ser feito.

Transformamos o caos geográfico em um problema de otimização onde o motor precisa responder:
- Quais **ordens** priorizar?
- Quais **viaturas** tirar da garagem?
- Qual a **sequência** exata de visitas?

---

## O que define o "Sucesso" (A Solução Ótima)

Uma boa solução no transporte de valores vai muito além do "caminho mais curto". O modelo busca o ponto de equilíbrio perfeito entre quatro eixos:

1. ⏱️ **Viabilidade Temporal:** Respeito absoluto às janelas das agências.
2. 📦 **Viabilidade de Carga:** O baú não estica e o limite do seguro não muda.
3. 🔄 **Coerência de Rota:** Não se mistura `suprimento` (distribuição) com `recolhimento` (coleta).
4. 💸 **Eficiência de Custo:** Fazer tudo isso gastando o mínimo possível.

---

## Os Três Pilares da Modelagem

O algoritmo cruza três conjuntos de dados para tomar a decisão:

1. **🛻 Viaturas:** Carregam o *custo de ativação*, capacidade volumétrica e limite financeiro (seguro).
2. **📍 Ordens:** Carregam a *demanda* (volume/valor), tempo de serviço na porta giratória e janela de atendimento rígida.
3. **🛤️ Malha:** Carrega o *custo de transição* (distância física e tempo de deslocamento no trânsito).

---

## As Variáveis de Decisão (A linguagem do motor)

Para o computador resolver o problema, as escolhas viram variáveis binárias e contínuas:

* $x_{ij}^k$: A viatura $k$ viajou do nó $i$ para o nó $j$? *(1 se Sim, 0 se Não)*
* $y_k$: A viatura $k$ precisou sair da base? *(1 se Sim, 0 se Não)*
* $u_i$: A ordem $i$ foi abandonada/não atendida? *(1 se Sim, 0 se Não)*

---

## A Função Objetivo

A Equação de Minimização ($Z$) é o "coração" do modelo. Ela pune o algoritmo financeiramente por ineficiências. O modelo é treinado para buscar o menor $Z$ possível.

$$
\min Z = \underbrace{\sum_{k \in K} F_k y_k}_{\text{Custo Fixo}} + \underbrace{\sum_{k \in K}\sum_{(i,j)\in A} C_{ij}^k x_{ij}^k}_{\text{Deslocamento}} + \underbrace{\sum_{k \in K}\sum_{(i,j)\in A} T_{ij} x_{ij}^k}_{\text{Tempo}} + \underbrace{\sum_{i \in N} P_i u_i}_{\text{Penalidade SLA}}
$$

### Lendo a equação em "regras de negócio":

1. **Custo Fixo da Frota:** *Ligou o motor da viatura, pagou.* Força o algoritmo a tentar consolidar a carga em menos caminhões em vez de despachar a frota inteira vazia.
2. **Custo de Deslocamento:** O gasto real (combustível, pedágio) para transitar pelas arestas da rede.
3. **Custo de Tempo/Duração:** Mesmo que a quilometragem seja curta, se a rota for muito demorada (trânsito pesado), o risco e o custo da hora-homem sobem.
4. **Penalidade por Quebra de SLA:** Se o algoritmo não atender uma agência ($u_i = 1$), ele recebe uma "multa matemática" gigantesca. Isso impede que o solver finja ter achado uma solução barata simplesmente ignorando clientes difíceis.

---

## As Restrições Operacionais (Os limites inquebráveis)

A função objetivo tenta baratear tudo, mas as **restrições** impedem soluções irreais. O solver é obrigado a respeitar:

* **Atendimento Único:** Uma agência só recebe um carro-forte. Nada de dividir ordens.
* **Teto de Capacidade:** A soma dos malotes e do dinheiro na rota não pode ultrapassar a física do baú ou o teto da apólice de seguro do carro.
* **Viagem no Tempo Proibida:** É obrigatório chegar depois que a janela da agência abre e antes dela fechar.
* **Conservação de Fluxo:** Todo circuito tem que nascer na Base e morrer na Base. Nenhuma viatura pode "desaparecer".

[⬅️ Anterior](./02-elementos-da-rede-grafica.md) | [Próxima ➡️](./04-tecnologia-solucao.md)

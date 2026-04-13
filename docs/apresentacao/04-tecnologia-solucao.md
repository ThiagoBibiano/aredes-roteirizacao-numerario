# 4. Tecnologia da Solução

## Como resolver a matemática na prática?

Com a rede montada e as restrições definidas, o problema precisa de força computacional para ser resolvido.

Nesta análise, implementamos dois motores de roteirização (*solvers*) com propósitos complementares:
- **PyVRP:** O motor focado na operação de rua (Heurística).
- **PuLP:** O juiz focado na perfeição matemática (Exato).

---

## O Motor Operacional: PyVRP

O **PyVRP** é o coração da solução escalável. Ele não busca a perfeição irrefutável; ele busca a **melhor rota possível no tempo disponível**.

Ele foi escolhido por sua aderência nativa a problemas complexos do mundo real (*Rich VRP*):
- ⏱️ Lida perfeitamente com **janelas de atendimento**.
- 🛻 Suporta **frota heterogênea** (veículos de tamanhos/custos diferentes).
- 📦 Gerencia **restrições de capacidade** simultâneas.

Na prática do transporte de valores, a agilidade salva a operação. O PyVRP entra para provar que a solução sobrevive quando o mapa lota de ordens e o tempo de planejamento encurta.

---

## O Juiz de Qualidade: PuLP

Se o PyVRP é tão rápido, por que usar o **PuLP**?

O PuLP atua como nosso **laboratório de controle**. Ele roda algoritmos exatos de Programação Linear. Se deixado rodar tempo suficiente, ele **garante a solução matematicamente perfeita**.

No benchmark, ele recebe exatamente as mesmas regras:
- A mesma malha;
- As mesmas viaturas;
- A mesma função objetivo.

**A pergunta que o PuLP responde é:**
> *"Ao escolhermos a velocidade do PyVRP, quanto dinheiro ou distância estamos deixando na mesa em comparação à rota perfeita?"*

---

## O Campo de Provas (Protocolo Experimental)

Para garantir que a comparação seja justa e rigorosa, montei um **Teste de Stress** usando o cenário de rede `operacional`.

Aumentei a carga operacional gradativamente para observar quando a complexidade quebra os algoritmos:
- **Escalas:** 20% → 40% → 60% → 80% das ordens.
- **Rigor:** 5 repetições para cada nível (para medir a estabilidade/dispersão).
- **A Prova de Fogo:** Uma rodada exaustiva final com **100% da operação**.

[⬅️ Anterior](./03-modelagem-e-funcao-objetivo.md) | [Próxima ➡️](./05-resultados-e-analise.md)

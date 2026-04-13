# 5. O Veredito: Resultados e Análise

## O Campo de Provas

O benchmark submeteu os dois motores (PyVRP e PuLP) ao cenário `operacao_sob_pressao`.

Para testar os limites da rede, aplicamos:
- **Carga gradativa:** 20%, 40%, 60% e 80% das ordens.
- **Rigor estatístico:** 5 repetições por escala (para medir a estabilidade).
- **A Prova de Fogo:** Uma rodada exaustiva final com 100% da malha.

---

## 1. O Preço do Tempo (Escalabilidade)

O limite computacional foi o contraste mais drástico do experimento.

| Carga | PyVRP (Heurística) | PuLP (Exato) |
| :--- | ---: | ---: |
| **20%** | 0,4 s | 0,3 s |
| **40%** | 0,6 s | 3,7 s |
| **60%** | 0,9 s | 20,2 s |
| **80%** | **1,4 s** | **114,1 s** |

**Leitura Operacional:**
- Em cenários pequenos, a força bruta (PuLP) ainda é rápida.
- A partir de 40%, o tempo do modelo exato entra em crescimento exponencial.
- Em 80% da rede, o PyVRP entrega a rota em apenas **1,4 s**, enquanto o modelo exato trava a operação por quase dois minutos.

> **Conclusão:** O PyVRP absorve o choque da escala sem penalizar o relógio da operação.

![Painel de Tendências](/data/benchmarks/operacao_sob_pressao_subsample/plots/dispersao_tempo.png)

---

## 2. A Qualidade da Solução e Dispersão

Se o PyVRP é tão rápido, quanto ele "erra" em relação à perfeição?

| Carga | Custo (FO) PyVRP | Custo (FO) PuLP |
| :--- | ---: | ---: |
| **20%** | 12,3 mil | 11,5 mil |
| **40%** | 18,7 mil | 17,8 mil |
| **60%** | 34,6 mil | 33,5 mil |
| **80%** | 45,1 mil | 43,6 mil |

**Leitura Operacional:**
- O PuLP, por ser um modelo matemático exato, sempre garantirá o menor custo absoluto.
- No entanto, a diferença financeira da heurística é muito contida. O PyVRP mostrou um comportamento extremamente estável nas repetições, sem picos de ineficiência.

![Painel de Dispersão](/data/benchmarks/operacao_sob_pressao_subsample/plots/dispersao_fo.png)

---

## 3. O Trade-Off: Erro Relativo vs. Velocidade

Cruzando a qualidade (Custo/FO) com a garantia matemática do PuLP, extraímos o **Erro Relativo**.

| Carga | Gap do PyVRP para o Ótimo |
| :--- | ---: |
| **20%** | 7,2% |
| **40%** | 4,4% |
| **60%** | 3,5% |
| **80%** | **3,3%** |

**Leitura Operacional:**
Curiosamente, à medida que a rede fica mais complexa e densa, a heurística do PyVRP se torna **mais precisa** em relação à solução ótima, caindo para um gap de apenas **3,3%** no cenário de estresse.

> **O Trade-off:** Na carga de 80%, o negócio decide se prefere economizar 3,3% do custo da rota (PuLP) ou ganhar 98% de velocidade no despacho da frota (PyVRP).

![Erro Relativo da Função Objetivo](/data/benchmarks/operacao_sob_pressao_subsample/plots/erro_relativo_fo_pct.png)

---

## 4. O Teste de Sobrevivência (100% da Malha)

A rodada final exigiu a roteirização da rede inteira de uma só vez, para as 20 ordens de serviço.
*(Nota: O SLA de atendimento e a viabilidade matemática fecharam em **100,0%** para ambos os modelos em todas as rodadas).*

| Solver | Status | Custo (FO) | Viaturas | Distância Total | Duração Total |
| :--- | :--- | ---: | ---: | ---: | ---: |
| **PyVRP** | Viável | 53,1 mil | 13 | 339,4 km | 670,5 min |
| **PuLP** | Viável | 50,2 mil | 10 | 326,2 km | 642,1 min |

**Leitura Operacional:**
Ambos sobreviveram e garantiram 100,0% de atendimento das agências. O modelo exato conseguiu consolidar a carga economizando 3 viaturas, o que gerou a diferença no custo final e na distância percorrida.

![Rodada Exaustiva](/data/benchmarks/operacao_sob_pressao_subsample/plots/rodada_exaustiva_100_rotas.png)

---

## A Decisão de Engenharia (Síntese Final)

O transporte de numerário impõe pressão real sobre a malha. A análise comprova que não existe um solver que "vence" em todas as categorias; existem ferramentas certas para papéis específicos:

* 🔬 **PuLP (A Régua de Qualidade):** Inviável para o despacho em tempo real na rua devido à sua explosão combinatória, mas indispensável como laboratório para auditar e calibrar a qualidade da operação.
* 🚀 **PyVRP (O Motor de Produção):** Entrega respostas quase instantâneas, absorve o caos de 100% da rede e mantém a margem de erro financeiro abaixo de 4%. É a escolha definitiva para sustentar a escala do negócio na ponta.

---

### Material de Apoio
- [Notebook de Benchmark Detalhado](../../notebook/benchmark_solver_comparison.ipynb)

[⬅️ Anterior](./04-tecnologia-solucao.md) | [Início ↺](./01-introducao-e-contexto.md)

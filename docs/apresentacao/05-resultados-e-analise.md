# 5. Resultados e Análise

## O que foi comparado

O benchmark observou o comportamento de **PyVRP** e **PuLP** no cenário `operacao_sob_pressao`, com:

- **20%**, **40%**, **60%** e **80%** das ordens;
- **5 repetições** por escala;
- uma **rodada exaustiva final com 100% das ordens**.

As leituras principais foram:

- tempo de processamento;
- função objetivo;
- dispersão entre repetições;
- erro relativo do PyVRP em relação ao PuLP;
- viabilidade computacional.

---

## 1. Tempo de processamento

O crescimento do tempo de execução foi o contraste mais visível entre as abordagens.

| Escala | PyVRP | PuLP |
| --- | ---: | ---: |
| 20% | 0,4 s | 0,3 s |
| 40% | 0,6 s | 3,7 s |
| 60% | 0,9 s | 20,2 s |
| 80% | 1,4 s | 114,1 s |

### Leitura
- Em escalas pequenas, os dois solvers ainda aparecem próximos.
- A partir de **40%**, o tempo do **PuLP** cresce rapidamente.
- Em **80%**, o **PyVRP** resolve em cerca de **1,4 s**, enquanto o **PuLP** precisa de cerca de **114,1 s**.

> O principal ganho do PyVRP aparece na **escalabilidade**.

**[DEIXA PARA IMAGEM]**
Inserir gráfico de linhas com tempo médio por escala para PyVRP e PuLP.

---

## 2. Qualidade da solução

A função objetivo média aumentou com a escala para os dois métodos, como esperado.

| Escala | FO média PyVRP | FO média PuLP |
| --- | ---: | ---: |
| 20% | 12,3 mil | 11,5 mil |
| 40% | 18,7 mil | 17,8 mil |
| 60% | 34,6 mil | 33,5 mil |
| 80% | 45,1 mil | 43,6 mil |

### Leitura
- O **PuLP** manteve valores médios menores de função objetivo em todas as escalas observadas.
- A diferença, porém, permaneceu relativamente contida.
- O **PyVRP** ficou próximo da referência exata, mesmo com tempos muito menores nas maiores escalas.

> O benchmark não mostra perda brusca de qualidade no PyVRP.
> Mostra, sobretudo, um **trade-off favorável entre custo e tempo**.

---

## 3. Atendimento e viabilidade

Em todas as escalas amostrais observadas:

- o atendimento médio foi de **100,0%** para **PyVRP**;
- o atendimento médio foi de **100,0%** para **PuLP**;
- a viabilidade do **PuLP** foi de **100,0%** nas repetições válidas até **80%** das ordens.

### Leitura
Isso é importante porque a comparação não está sendo feita entre uma solução completa e outra incompleta.

Até **80%** das ordens, os dois métodos:

- atenderam integralmente as ordens amostradas;
- produziram soluções viáveis;
- diferiram principalmente em **tempo** e em **nível de otimalidade**.

---

## 4. Dispersão entre repetições

A análise não observou apenas médias.

Também foi importante verificar a **dispersão** dos resultados entre repetições, porque o benchmark usa amostragem aleatória estratificada por classe operacional. :contentReference[oaicite:1]{index=1}

### Leitura
- O **PyVRP** apresentou tempos médios baixos e comportamento estável nas escalas observadas.
- O **PuLP** mostrou aumento forte de tempo e maior sensibilidade conforme a escala cresceu.
- Em função objetivo, os dois acompanharam o aumento da complexidade, mas com vantagem sistemática do **PuLP**.

**[DEIXA PARA IMAGEM]**
Inserir painel de dispersão por escala:
- tempo;
- função objetivo;
- destaque visual para crescimento do PuLP.

---

## 5. Erro relativo do PyVRP em relação ao PuLP

Quando comparado apenas às execuções com referência válida do PuLP, o erro relativo médio da função objetivo do PyVRP foi:

| Escala | Erro relativo médio |
| --- | ---: |
| 20% | 7,2% |
| 40% | 4,4% |
| 60% | 3,5% |
| 80% | 3,3% |

### Leitura
- O erro relativo **não aumentou** com a escala observada.
- Ao contrário, ele **diminuiu** ao longo das escalas amostrais.
- Em **80%** das ordens, o PyVRP ficou em torno de **3,3%** da referência do PuLP.

> Isso reforça a ideia de que o PyVRP manteve boa qualidade mesmo quando o problema ficou mais exigente.

**[DEIXA PARA IMAGEM]**
Inserir gráfico de barras ou linha com erro relativo médio por escala.

---

## 6. Rodada exaustiva com 100% das ordens

A rodada final com **100% das ordens** foi lida separadamente das médias amostrais.

| Solver | Status | FO | Atendimento | Viaturas | Distância total | Duração total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| PyVRP | feasible | 53,1 mil | 100,0% | 13 | 339,4 km | 670,5 min |
| PuLP | feasible | 50,2 mil | 100,0% | 10 | 326,2 km | 642,1 min |

### Leitura
- Na rodada completa, os dois solvers encontraram solução viável.
- O **PuLP** produziu a melhor função objetivo.
- O **PyVRP** manteve atendimento total e solução viável, mas com:
  - mais viaturas;
  - maior distância total;
  - maior duração total.

Ainda assim, a diferença deve ser lida junto com o papel de cada método:

- o **PuLP** aparece como referência de maior controle de otimalidade;
- o **PyVRP** aparece como abordagem prática para manter resposta rápida em crescimento de escala.

---

## 7. Leitura final do benchmark

O benchmark confirma o comportamento esperado para esse tipo de problema:

- o **PuLP** tende a produzir soluções melhores em função objetivo;
- o **PyVRP** tende a responder muito melhor em tempo computacional;
- até **80%** das ordens, o **PyVRP** manteve atendimento total e erro relativo baixo;
- na rodada com **100%**, os dois continuaram viáveis, mas com vantagem de custo para o **PuLP**.

A principal conclusão não é que um método “vence” o outro em todos os critérios.

A conclusão é que eles ocupam papéis diferentes:

- **PuLP** é mais forte como referência de qualidade;
- **PyVRP** é mais forte como solução escalável para uso operacional.

> Em redes de transporte de valores, o ganho mais relevante do PyVRP está na capacidade de preservar boa qualidade com tempo de resposta muito menor.

---

## Síntese da apresentação

Ao longo desta análise, a roteirização foi observada como um problema de decisão em rede sob restrições operacionais.

A comparação experimental mostrou que:

- a modelagem representa adequadamente a operação;
- a rede responde de forma distinta conforme a escala cresce;
- a escolha do solver depende do equilíbrio desejado entre:
  - **qualidade da solução**;
  - **tempo de processamento**;
  - **uso prático em escala**.

Assim, para o contexto analisado, o **PyVRP** se destaca como alternativa robusta para cenários operacionais mais amplos, enquanto o **PuLP** permanece valioso como referência exata de comparação.

---

## Material de apoio

- [Notebook de benchmark](../../notebook/benchmark_solver_comparison.ipynb)

[⬅️ Anterior](./04-tecnologia-solucao.md) | [Início ↺](./01-introducao-e-contexto.md)

# 1. Introdução e Contexto

## O Desafio Operacional

No transporte de valores, o planejamento logístico transcende a simples conexão de pontos em um mapa. Trata-se de uma orquestração complexa que exige a definição precisa de:

* 📦 **Ordens**: Quais demandas de atendimento serão supridas ou recolhidas.
* 🛻 **Viaturas**: Quais recursos operacionais (blindados) executarão cada circuito.
* ⏱️ **Sequência**: A ordem exata dos atendimentos para maximizar a eficiência.
* 🛡️ **Restrições**: Como garantir conformidade com janelas de tempo, limites de capacidade do baú e gerenciamento de risco.

Cada decisão impacta diretamente o custo total, a taxa de ocupação da frota e a viabilidade da operação.

---

## A Rede em Análise

Nesta análise, represento a operação através de seus quatro elementos centrais, simplificando a complexidade geográfica para focar na lógica da rede:

1.  🔴 **Base**: O ponto de origem, processamento de valores e retorno obrigatório das viaturas.
2.  📍 **Pontos**: Locais físicos (agências, ATMs, varejistas, ...) onde as demandas estão localizadas.
3.  📦 **Ordens**: As demandas específicas de atendimento distribuídas espacialmente na rede.
4.  🛤️ **Rotas**: Os circuitos otimizados construídos para conectar a base às ordens.

---

## Contextos Operacionais: Experimentos Isolados

A análise do problema foi conduzida sob dois cenários operacionais distintos e independentes:

### 📦 Suprimento
Cenário de **distribuição**. A viatura parte da Base com carga máxima e realiza entregas fracionadas ao longo do circuito, terminando a rota vazia.

### 💰 Recolhimento
Cenário de **coleta**. A viatura percorre a rede acumulando valores ao longo da rota, terminando o circuito com carga máxima ao retornar à Base.

Esta distinção é fundamental, pois altera drasticamente a dinâmica de ocupação do veículo, a exposição ao risco e o gerenciamento da capacidade ao longo da rota.
> **Nota**: Para fins desta apresentação, `suprimento` e `recolhimento` são tratados como **experimentos independentes**.
> **Nota**: Para fins desta apresentação, não foram utilizados dados reais. Na prática operacional, o motorista desconhece a rota até o momento do embarque, o que justifica o uso de dados simulados para esta análise.

[Próxima ➡️](./02-elementos-da-rede-grafica.md)

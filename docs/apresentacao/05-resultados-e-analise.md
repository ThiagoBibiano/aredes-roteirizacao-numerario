# 5. Resultados e Análise

## Resultado operacional

Com o cenário **operação sob pressão**, a saída do projeto fica mais rica para interpretação: há mais ordens, mais dispersão e mais tensão entre cobertura, frota e custo.

O bloco operacional pode ser lido em quatro camadas:

1. mapa da rede escolhida;
2. tabela de sequências por viatura;
3. painel de indicadores;
4. comparação entre rede-base e rede planejada.

![Mapa das rotas geradas pelo projeto](./assets/generated/operacao_sob_pressao_solucao.png)

![Painel com indicadores de custo, tempo e atendimento](./assets/generated/operacao_sob_pressao_kpis.png)

![Tabela com veículo, sequência de paradas e horários](./assets/generated/operacao_sob_pressao_rotas_tabela.png)

![Comparação visual entre rede-base e rede escolhida pelo solver](./assets/generated/operacao_sob_pressao_antes_depois.png)

## O que o benchmark mede

Para comparar PyVRP e PuLP, o experimento congela um núcleo comum:

- uma classe operacional por vez;
- mesmas ordens, viaturas, janelas e capacidades;
- mesma `objective_common`.

As métricas principais são:

- tempo de solução;
- função objetivo comum;
- taxa de atendimento;
- viaturas acionadas.

![Recorte comparável do benchmark](./assets/metodologia-experimental.svg)

## O que apareceu nas escalas amostrais

No benchmark com `20%`, `40%`, `60%` e `80%` das ordens, com `5` repetições por escala, a leitura ficou clara:

- o **PyVRP** permanece muito rápido em todas as escalas;
- o **PuLP** entrega referência de custo melhor, mas seu tempo cresce fortemente;
- a dispersão aumenta quando a escala sobe;
- o erro relativo da FO do PyVRP cresce nas instâncias mais pressionadas.

Alguns números do cenário atual:

- em `40%` das ordens, ambos atingiram `100%` de atendimento; PyVRP em `0,1088 s` e PuLP em `5,7748 s`;
- em `80%`, o PyVRP ficou em `0,2793 s`, enquanto o PuLP subiu para `155,5691 s`;
- em `100%`, ambos ficaram viáveis, mas com custo computacional muito diferente: PyVRP em `0,3645 s` e PuLP em `1047,5703 s`.

![Painel de tendências do benchmark](./assets/generated/benchmark_painel_tendencias.png)

![Painel de dispersão das repetições](./assets/generated/benchmark_painel_dispersao.png)

![Erro relativo da função objetivo em relação ao PuLP](./assets/generated/benchmark_erro_relativo_fo.png)

![Taxa de viabilidade do PuLP por escala](./assets/generated/benchmark_taxa_viabilidade_pulp.png)

## Rodada exaustiva de 100%

O fechamento mais forte do benchmark é a rodada com `100%` das ordens. Ela mostra que:

- `suprimento` e `recolhimento` continuam isolados;
- o PyVRP continua rápido;
- o PuLP ainda entrega uma referência melhor de custo;
- o trade-off real está entre escalabilidade e controle de otimalidade.

Na execução atual:

- **PyVRP**: `13` viaturas, `100%` de atendimento, `FO = 40057,51`;
- **PuLP**: `10` viaturas, `100%` de atendimento, `FO = 37812,97`.

![Painel da rodada exaustiva de 100% das ordens](./assets/generated/benchmark_rodada_exaustiva_100_rotas.png)

## Mensagem final

O projeto mostrou três pontos principais:

1. a operação pode ser traduzida para uma rede;
2. a rede pode ser modelada com custo e restrições;
3. a comparação entre PyVRP e PuLP revela um trade-off claro entre velocidade operacional e controle de otimalidade.

[⬅️ Anterior](./04-tecnologia-solucao.md) | [Início ↺](./01-introducao-e-contexto.md)

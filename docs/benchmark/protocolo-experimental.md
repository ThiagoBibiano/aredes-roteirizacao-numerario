# Protocolo Experimental PyVRP x PuLP

## 1. Problema comparavel

O comparativo e sempre feito sobre um unico subproblema por vez:

- `suprimento`; ou
- `recolhimento`.

Cada execucao compara os dois solvers sobre a mesma `InstanciaRoteirizacaoBase`, com:

- mesmas ordens;
- mesmas viaturas;
- mesmas janelas de tempo;
- mesmas capacidades;
- mesma malha logistica;
- mesmos custos-base por viatura e por arco.

Ficam explicitamente fora do comparativo:

- pos-processamento;
- auditoria;
- reporting;
- qualquer regra hoje documentada como fora do solver;
- qualquer acoplamento global entre `suprimento` e `recolhimento`.

## 2. Funcao objetivo comum

O benchmark mede um objetivo comum recalculado fora do solver:

```text
objective_common =
  custo_fixo_viaturas_usadas
  + custo_de_arco
  + custo_de_duracao
  + penalidade_por_nao_atendimento
```

Onde:

- `custo_fixo_viaturas_usadas`: soma dos custos fixos das viaturas acionadas;
- `custo_de_arco`: soma de `custos_por_arco` da instancia solver-agnostic;
- `custo_de_duracao`: soma dos tempos de deslocamento dos arcos usados;
- `penalidade_por_nao_atendimento`: soma das penalidades `nao_atendimento` das ordens omitidas.

Esse objetivo e o alvo metodologico do comparativo. O custo interno do PyVRP nao e usado como metrica cientifica principal.

## 3. Metricas comparadas

Metricas primarias:

- `runtime_s`
- `objective_common`
- `service_rate`
- `feasible`

Metricas secundarias:

- `vehicles_used`
- `distance_total_m`
- `duration_total_s`
- `best_bound`
- `gap_pct`

Nao se usa igualdade exata de sequencia de nos como metrica principal. A comparacao e feita por equivalencia operacional:

- cobertura;
- custo;
- uso de frota;
- distancia;
- duracao;
- viabilidade.

## 4. Catalogo e escalas

Familias v1:

- `balanced_control`
- `tight_windows`
- `volume_pressure`
- `cash_pressure`

Camadas:

- `didatica`: `6` ordens por classe, `3` viaturas, `1` seed;
- `benchmark`: `10` ordens por classe, `5` viaturas, `3` seeds;
- `estresse`: `20` ordens por classe, `8` viaturas, `3` seeds.

Metadados obrigatorios por cenario:

- `scenario_id`
- `family`
- `layer`
- `seed`
- `classe_operacional`
- `n_orders`
- `n_vehicles`
- `window_profile`
- `volume_pressure`
- `cash_pressure`
- `priority_ratio`
- `geo_density`
- `pedagogical_hypothesis`
- `dataset_dir`

## 5. Politica de execucao

PyVRP:

- `didatica`: `50` iteracoes;
- `benchmark`: `100` iteracoes;
- `estresse`: `150` iteracoes.

PuLP + `PULP_CBC_CMD`:

- `didatica`: `time_limit = 120s`, `gap_pct_target = 1%`;
- `benchmark`: `time_limit = 300s`, `gap_pct_target = 1%`;
- `estresse`: `time_limit = 600s`, `gap_pct_target = 1%`.

## 6. Evidencia valida

Uma afirmacao comparativa so e valida quando:

- os dois solvers rodam sobre a mesma classe operacional;
- o `scenario_id` e o `seed` sao os mesmos;
- o objetivo comum e recalculado com a mesma regra;
- a politica de parada da camada e a mesma;
- o resultado cita explicitamente limitacoes do baseline exato.

## 7. O que o comparativo mede e o que ele nao mede

O benchmark mede:

- qualidade relativa da solucao no nucleo compartilhado do problema;
- cobertura e custo operacional sob o mesmo recorte;
- degradacao de tempo/viabilidade com aumento de escala.

O benchmark nao mede:

- fidelidade do produto completo de ponta a ponta;
- auditoria, explicabilidade ou qualidade do reporting;
- efeito de regras fora do solver;
- competencia entre solvers sobre o sistema inteiro do repositorio.

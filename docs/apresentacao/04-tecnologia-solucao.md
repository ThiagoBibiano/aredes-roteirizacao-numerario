# 4. Tecnologia da Solucao

## Da formulacao para a busca de boas rotas

Depois de formular o problema, surge a pergunta natural:

> Como encontrar boas rotas em um problema com tantas combinacoes possiveis?

Em redes pequenas, ainda e possivel experimentar manualmente algumas alternativas. Mas, em redes reais, o numero de sequencias possiveis explode rapidamente.

## Por que nao resolver "no braco"?

Considere apenas alguns elementos:

- varios clientes;
- mais de um veiculo;
- diferentes ordens de visita;
- janelas de tempo;
- capacidades;
- possibilidade de nao atender alguns pontos.

O numero de combinacoes cresce muito rapidamente. Por isso, problemas de roteirizacao exigem metodos de busca eficientes.

## Por que Python ajuda no ambiente academico?

Python e uma escolha natural para sala de aula e pesquisa porque oferece:

- leitura simples;
- escrita rapida de prototipos;
- integracao forte com bibliotecas cientificas;
- facilidade para testar cenarios e visualizar resultados.

Em ambiente academico, isso e valioso porque permite focar mais em:

- modelagem;
- analise da rede;
- interpretacao da solucao.

## Por que usar PyVRP?

PyVRP e uma biblioteca moderna voltada para problemas de roteamento de veiculos.

Ela e adequada ao caso estudado porque facilita:

- janelas de tempo;
- frota heterogenea;
- clientes opcionais;
- capacidades em mais de uma dimensao;
- busca de solucoes boas sem programar toda a heuristica do zero.

No contexto desta apresentacao, ele aparece como o solver heuristico de referencia operacional.

## A ideia do HGS

O PyVRP utiliza uma abordagem baseada em HGS, Hybrid Genetic Search.

Em linguagem simples, a ideia e:

1. gerar varias solucoes candidatas;
2. combinar boas caracteristicas dessas solucoes;
3. melhorar localmente as rotas;
4. manter diversidade para nao ficar preso cedo demais em uma solucao ruim.

```mermaid
flowchart LR
    A[Solucoes iniciais] --> B[Combinacao]
    B --> C[Melhoria local]
    C --> D[Selecao]
    D --> E[Nova populacao]
    E --> F[Melhores rotas encontradas]
```

## O que isso significa para a disciplina?

Do ponto de vista didatico, a biblioteca nao substitui a modelagem.

Ela entra depois que o problema ja foi:

- traduzido para rede;
- descrito por custos e restricoes;
- organizado em um formato computacional.

Ou seja:

> o solver nao "inventa" o problema. Ele procura boas solucoes para o problema que a modelagem definiu.

## Onde entra o PuLP no experimento?

PuLP nao entra aqui como substituto do backend nem como novo motor do produto.

Ele entra como **baseline exato e controlado** para o subproblema compartilhado:

- uma classe operacional por vez;
- mesmas ordens;
- mesmas viaturas;
- mesmas janelas;
- mesmas capacidades;
- mesmo objetivo comum recalculado fora do solver.

Essa separacao e importante porque o PyVRP e o solver mais adequado para escala e operacao, enquanto o PuLP ajuda a validar qualidade em instancias pequenas.

## O que foi rodado de fato no benchmark

No estado atual do projeto, o notebook experimental foi organizado assim:

- cenario-base: **operacao_sob_pressao**;
- benchmark amostral com `20%`, `40%`, `60%` e `80%` das ordens;
- `5` repeticoes por escala;
- amostragem aleatoria independente, estratificada por `classe_operacional`;
- rodada exaustiva separada com `100%` das ordens.

Isso permite contar a historia certa:

- em pequena e media escala, o PuLP ajuda a validar cobertura e custo comum;
- conforme a escala cresce, o custo computacional do baseline sobe rapidamente;
- o PyVRP continua muito mais aderente ao uso operacional em tempo de resposta.

![Recorte comparavel e protocolo do experimento](./assets/metodologia-experimental.svg)

## Leitura visual da solucao computacional

```mermaid
flowchart TD
    A[Dados da rede] --> B[Modelo de roteirizacao]
    B --> C[PyVRP]
    C --> D[Busca heuristica]
    D --> E[Rotas candidatas]
    E --> F[Melhor conjunto de rotas]
```

![Fluxo visual entre dados da rede, modelo e solver](./assets/solver-fluxo.svg)

## O ganho pedagogico

Usar uma biblioteca especializada permite que o foco da aula permaneça onde interessa:

- formulacao do problema;
- leitura de restricoes logisticas;
- comparacao entre solucoes;
- analise dos resultados sobre a rede.

![Leitura visual da comparacao em diferentes escalas](./assets/gifs/benchmark-escala.gif)

## O ganho metodologico

Separar **solver operacional** e **baseline exato** melhora muito a qualidade da argumentacao:

- o PyVRP pode ser defendido pelo que ele faz bem: buscar solucoes boas muito rapido;
- o PuLP pode ser defendido pelo que ele faz bem: servir como referencia controlada de qualidade;
- a apresentacao deixa de parecer "competicao de ferramenta" e passa a mostrar um **trade-off entre otimalidade controlada e escalabilidade**.

[⬅️ Anterior](./03-modelagem-e-funcao-objetivo.md) | [Próxima ➡️](./05-resultados-e-analise.md)

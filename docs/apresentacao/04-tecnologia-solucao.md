# 4. Tecnologia da Solução

## Como as rotas são encontradas

Depois da modelagem, o projeto resolve o problema em duas camadas:

- **PyVRP**: solver heurístico usado como referência operacional;
- **PuLP**: baseline exato usado apenas no núcleo comparável do benchmark.

Essa separação evita comparar o sistema inteiro com um modelo matemático simplificado.

## Por que PyVRP

O PyVRP é a escolha principal para a operação porque foi desenhado para problemas de roteirização de veículos com alto desempenho. Segundo Wouda, Lan e Kool, o pacote implementa uma abordagem de **Hybrid Genetic Search**, combina a flexibilidade do Python com trechos críticos em C++ e foi projetado para VRP com janelas de tempo, com extensão natural para outras variantes ricas do problema. Referência: [PyVRP: a high-performance VRP solver package](https://arxiv.org/abs/2403.13795).

Na prática, isso é importante aqui porque o problema tratado envolve:

- janelas de tempo;
- frota heterogênea;
- clientes opcionais;
- capacidade em mais de uma dimensão;
- necessidade de resposta rápida.

## Papel do PuLP

O PuLP entra como referência controlada:

- uma classe operacional por vez;
- mesmas ordens e mesmas viaturas;
- mesmo objetivo comum;
- foco em pequena e média escala.

Ou seja, ele não substitui o backend. Ele ajuda a validar qualidade.

## Protocolo do benchmark

O benchmark da apresentação usa:

- `operação sob pressão`;
- `20%`, `40%`, `60%` e `80%` das ordens;
- `5` repetições por escala;
- uma rodada exaustiva separada com `100%`.

Essa combinação sustenta a leitura principal do experimento:

- o PuLP ajuda a medir qualidade;
- o PyVRP sustenta escalabilidade operacional.

[⬅️ Anterior](./03-modelagem-e-funcao-objetivo.md) | [Próxima ➡️](./05-resultados-e-analise.md)

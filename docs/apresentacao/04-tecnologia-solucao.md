# 4. Tecnologia da Solução

## Como a solução é obtida

Depois da modelagem, o problema passa a ser resolvido por duas abordagens distintas:

- **PyVRP**, como solução principal de roteirização;
- **PuLP**, como referência exata no benchmark comparativo.

Essa separação é importante porque a apresentação não compara apenas ferramentas, mas **papéis diferentes dentro da análise**.

Uma abordagem sustenta a solução operacional.
A outra ajuda a medir qualidade em um ambiente controlado.

---

## Papel do PyVRP

O **PyVRP** é a base principal da solução de roteirização apresentada neste projeto.

Ele é utilizado porque oferece uma combinação importante para problemas desse tipo:

- boa qualidade de solução;
- tempo de resposta compatível com uso prático;
- aderência a problemas ricos de roteirização.

No contexto desta apresentação, isso é relevante porque a rede analisada envolve:

- **janelas de atendimento**;
- **frota heterogênea**;
- **ordens opcionais**;
- **restrições de capacidade**;
- necessidade de resposta eficiente à medida que o problema cresce.

Assim, o PyVRP representa a abordagem voltada à **escalabilidade operacional**.

---

## Por que ele é adequado aqui

Na prática, o transporte de valores não exige apenas uma rota correta.

Exige uma solução que continue utilizável quando aumentam:

- a quantidade de ordens;
- a dispersão espacial da rede;
- a pressão sobre viaturas e tempo operacional.

Por isso, nesta apresentação, o PyVRP aparece como a abordagem mais próxima de um cenário de uso efetivo: ele não entra apenas para resolver, mas para mostrar **como a solução se comporta quando a rede se torna mais exigente**.

**[DEIXA PARA IMAGEM]**
Inserir uma imagem simples com dois blocos:
- PyVRP → escalabilidade, rapidez, boa qualidade;
- PuLP → referência exata, controle, comparação.

---

## Papel do PuLP

O **PuLP** não substitui a solução principal.

Seu papel nesta apresentação é outro: funcionar como uma **referência controlada** para comparação.

No benchmark, ele é usado sob condições alinhadas com o PyVRP:

- mesma classe operacional por experimento;
- mesmas ordens;
- mesmas viaturas;
- mesma base de comparação para a função objetivo.

Com isso, o PuLP ajuda a responder uma pergunta importante:

> quão próxima a solução heurística fica de uma referência exata quando observamos o mesmo problema?

---

## O que essa comparação permite

A presença das duas abordagens permite separar duas dimensões da análise:

### Qualidade da solução
O PuLP ajuda a verificar o quanto o resultado do PyVRP se aproxima de uma referência exata.

### Viabilidade computacional
O PyVRP mostra até que ponto a solução permanece prática quando a escala cresce.

Essa leitura é central para o benchmark, porque o objetivo não é apenas encontrar uma solução, mas observar o equilíbrio entre:

- **qualidade**;
- **tempo de resolução**;
- **capacidade de continuar operando em escala**.

---

## Base comum de comparação

Para que a comparação faça sentido, os resultados são lidos sobre uma base comum.

Isso evita confundir diferenças de implementação com diferenças reais de desempenho.

Em termos analíticos, a lógica é simples:

- o **PyVRP** representa a solução heurística aplicada ao problema;
- o **PuLP** representa uma referência exata em escala controlada;
- ambos são observados sob o mesmo recorte experimental.

Essa estrutura permite interpretar os resultados de forma mais justa e mais clara.

---

## Protocolo experimental

A comparação apresentada adota o cenário **`operacao_sob_pressao`** como base.

A análise é feita em diferentes escalas de ordens:

- **20%**
- **40%**
- **60%**
- **80%**

Para cada escala, são realizadas **5 repetições**.

Ao final, é executada ainda uma **rodada exaustiva com 100% das ordens**, tratada separadamente das médias principais.

Essa organização permite observar não apenas um resultado isolado, mas o comportamento das abordagens ao longo do aumento de escala.

**[DEIXA PARA GIF]**
Inserir um gif curto mostrando a progressão:
20% → 40% → 60% → 80% → 100%,
com indicação visual de que a comparação é repetida em cada etapa.

---

## Leitura esperada desta etapa

Com essa estrutura, a tecnologia da solução deixa de ser apenas uma descrição de ferramentas.

Ela passa a cumprir uma função analítica:

- **PyVRP** sustenta a leitura de escalabilidade;
- **PuLP** sustenta a leitura de referência comparativa.

Em conjunto, os dois permitem discutir o problema de roteirização em redes de transporte de valores de forma mais completa.

---

## Síntese

Nesta apresentação, a tecnologia da solução é importante não apenas pelo que resolve, mas pelo que permite comparar.

O arranjo adotado organiza a análise em dois eixos:

- **resolver bem**;
- **continuar resolvendo quando a rede cresce**.

É essa distinção que prepara a leitura dos resultados do benchmark na próxima etapa.

[⬅️ Anterior](./03-modelagem-e-funcao-objetivo.md) | [Próxima ➡️](./05-resultados-e-analise.md)

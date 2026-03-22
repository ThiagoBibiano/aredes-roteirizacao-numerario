# Plano de testes de contrato

## Objetivo

Definir os cenarios minimos de aceitacao da Etapa 1 antes da implementacao.

## Estrategia

Cada contrato central deve possuir ao menos cinco grupos de testes:

1. criacao valida;
2. falha por obrigatorio ausente;
3. falha por tipo incorreto;
4. falha por regra de dominio;
5. serializacao e desserializacao consistentes.

## Matriz minima por contrato

| Contrato | Cenarios obrigatorios |
| --- | --- |
| `Base` | cria valido; rejeita base sem coordenada; rejeita janela invalida; serializa de forma estavel |
| `Ponto` | cria valido; rejeita localizacao ausente; rejeita tempo padrao negativo; serializa de forma estavel |
| `OrdemBruta` | preserva campos de origem; aceita metadados de ingestao; rejeita ausencia de identificador de rastreio |
| `Ordem` | cria valido; rejeita ponto inexistente; rejeita janela invalida; rejeita penalidade negativa; serializa de forma estavel |
| `OrdemClassificada` | classifica elegivel; marca exclusao por cut-off; representa cancelamento com impacto; serializa de forma estavel |
| `Viatura` | cria valido; rejeita ausencia de base; rejeita capacidade ausente; rejeita teto segurado ausente; serializa de forma estavel |
| `MatrizLogistica` | cria valido; rejeita dimensao incoerente; rejeita distancia negativa; preserva metadados de reproducao |
| `InstanciaRoteirizacaoBase` | cria valido; rejeita ausencia de deposito; rejeita demanda sem penalidade; rejeita mistura indevida de classe operacional; serializa de forma estavel |
| `RotaPlanejada` | cria valido; rejeita sequencia inconsistente; rejeita base ausente; representa uso de limite segurado quando aplicavel |
| `EventoAuditoria` | cria valido; rejeita tipo desconhecido; exige motivo em exclusao; serializa de forma estavel |
| `ResultadoPlanejamento` | cria valido; exige identificador de execucao; exige coerencia do status final; preserva rotas e auditoria na serializacao |

## Cenarios transversais obrigatorios

- um mesmo cenario deve provar a separacao entre `OrdemBruta`, `Ordem`, `OrdemClassificada` e `OrdemPlanejavel`;
- um cenario de recolhimento deve provar a existencia da dimensao financeira na instancia;
- um cenario de cancelamento apos cut-off deve provar geracao de evento de auditoria;
- um cenario de isolamento deve provar que suprimento e recolhimento nao se misturam na mesma instancia base.

## Criterios de aceite da suite

- toda falha deve apontar campo, regra ou motivo identificavel;
- testes devem ser deterministas;
- fixtures devem ser pequenas e semanticamente claras;
- todo contrato central deve ter exemplos validos e invalidos;
- toda fixture deve declarar `versao_schema`.

## Fora do escopo desta etapa

- teste de desempenho;
- teste de solver;
- teste de integracao com banco ou API externa;
- teste de UI.

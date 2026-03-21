# Decisoes arquiteturais da Etapa 1

## ADR-001 - Dominio desacoplado de solver

Decisao:

Os contratos centrais do dominio e da instancia de roteirizacao nao devem referenciar classes, nomes ou limitacoes nativas do PyVRP.

Motivacao:

Preservar independencia arquitetural e permitir adaptadores futuros.

Consequencia:

`InstanciaRoteirizacaoBase` passa a ser a unica fronteira candidata a adaptacao solver-specific.

## ADR-002 - Separacao por estagio semantico

Decisao:

Os dados devem existir em estagios distintos: bruto, validado, enriquecido, otimizacao generica e saida.

Motivacao:

Evitar mudanca silenciosa de significado dentro da mesma estrutura.

Consequencia:

Uma `OrdemBruta` nao pode ser tratada como `OrdemPlanejavel` sem transformacao explicita.

## ADR-003 - Cancelamento como estado formal

Decisao:

Cancelamento deve ser modelado como estado com temporalidade, impacto e motivacao.

Motivacao:

Cancelamentos afetam elegibilidade, penalidade, parada improdutiva e auditoria.

Consequencia:

Flags booleanas isoladas nao sao suficientes para o contrato.

## ADR-004 - Especial pertence a classe de planejamento

Decisao:

`especial` e valor de `classe_planejamento`, nao de `tipo_servico`.

Motivacao:

Evitar colisoes semanticas entre prioridade comercial e natureza fisica da operacao.

Consequencia:

Quando necessario, o servico extraordinario deve ser modelado em `tipo_servico`, preservando a prioridade em `classe_planejamento`.

## ADR-005 - Ponto e ordem possuem responsabilidades distintas

Decisao:

`Ponto` representa cadastro e `Ordem` representa demanda operacional do dia.

Motivacao:

Separar dado mestre de dado operacional evita conflito de atributos e regras duplicadas.

Consequencia:

Janela efetiva e tempo de servico efetivo pertencem a `Ordem`, mesmo quando derivados de valores padrao do `Ponto`.

## ADR-006 - Auditoria como requisito estrutural

Decisao:

`EventoAuditoria` e parte obrigatoria do nucleo da etapa.

Motivacao:

O sistema precisa explicar exclusoes, rejeicoes, cancelamentos e restricoes dominantes.

Consequencia:

Logs tecnicos nao substituem o contrato de auditoria.

## ADR-007 - Restricoes centrais entram no contrato desde o inicio

Decisao:

Capacidade financeira, capacidade volumetrica, teto segurado, compatibilidade operacional e circuito fechado devem aparecer nos contratos da Etapa 1.

Motivacao:

Essas restricoes sao centrais no problema do MVP e nao podem ser empurradas para refatoracao futura.

Consequencia:

Modelos sem essas dimensoes devem ser considerados incompletos.

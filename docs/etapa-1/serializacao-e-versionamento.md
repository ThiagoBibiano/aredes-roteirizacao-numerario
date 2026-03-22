# Contrato de serializacao e versionamento

## Objetivo

Garantir estabilidade para persistencia, integracao, testes de contrato e reprocessamento.

## Formato canonico

- serializacao logica em JSON para contratos internos e artefatos de teste;
- chaves em `snake_case`;
- valores enum em `snake_case`;
- listas ordenadas apenas quando a ordem fizer parte do significado do contrato;
- campos opcionais ausentes devem ser preferidos a preenchimento com strings vazias.

## Datas e horarios

- datas sem horario devem usar ISO 8601 no formato `YYYY-MM-DD`;
- timestamps devem usar ISO 8601 com offset explicito;
- horarios operacionais locais devem carregar timezone de referencia da execucao;
- comparacoes temporais devem ocorrer sobre instantes normalizados.

## Valores monetarios

- contratos devem explicitar unidade monetaria quando houver integracao externa;
- internamente, valores monetarios devem ser serializados em decimal canonico e nunca em texto formatado para exibicao;
- arredondamento e escala devem ser definidos antes da implementacao.

## Unidades fisicas

- volume deve ter unidade explicita do dominio adotado;
- tempo de servico e deslocamento devem usar unidade temporal unica por contrato;
- capacidades devem identificar a dimensao a que pertencem.

## Metadados obrigatorios de rastreabilidade

Todo contrato relevante para reprocessamento deve prever:

- `id_execucao`;
- `origem` ou `fonte`;
- `timestamp_referencia`;
- `versao_schema`;
- `hash_conteudo` quando aplicavel.

## Versionamento de schema

- cada contrato serializavel deve possuir `versao_schema`;
- a politica de versao deve seguir `major.minor`;
- mudancas `major` quebram compatibilidade;
- mudancas `minor` so podem adicionar campos opcionais ou ampliar vocabulario de forma controlada.

## Politica de backward compatibility

- remocao ou renomeacao de campo obrigatorio exige mudanca `major`;
- tornar obrigatorio um campo antes opcional exige mudanca `major`;
- adicionar campo opcional permite `minor`;
- adicionar novo enum so permite `minor` se consumidores puderem rejeitar ou ignorar explicitamente o novo valor;
- consumidores nunca devem assumir aceitacao silenciosa de campos desconhecidos sem regra documentada.

## Regras para testes de contrato

- serializar e desserializar deve preservar significado;
- ordem logica de campos nao deve alterar o resultado semantico;
- hashes de conteudo devem ser calculados sobre forma canonica do contrato;
- cenarios de fixture devem declarar a versao de schema usada.

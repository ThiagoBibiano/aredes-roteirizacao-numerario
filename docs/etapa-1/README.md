# Etapa 1 - Definicao dos contratos de dados

Este diretorio consolida os artefatos formais da Etapa 1 do projeto. O objetivo desta etapa e estabilizar a linguagem do dominio e os contratos que conectam ingestao, validacao, enriquecimento, montagem da instancia de roteirizacao, auditoria e saida final.

## Escopo da etapa

- estabelecer a taxonomia do dominio;
- definir contratos por camada do pipeline;
- explicitar invariantes e restricoes estruturais;
- mapear regras de negocio para contratos e campos;
- padronizar erro, auditoria, serializacao e versionamento;
- fechar a especificacao dos testes de contrato;
- registrar as decisoes arquiteturais da etapa.

## Artefatos

- `especificacao-contratos.md`: documento principal da etapa.
- `glossario.md`: vocabulario controlado do dominio.
- `enums-e-vocabularios.md`: catalogo de classificacoes e enums.
- `invariantes.md`: invariantes e regras de aceitacao por contrato.
- `matriz-rastreabilidade.md`: relacao entre regra de negocio, contrato, campo e etapa.
- `erros-e-auditoria.md`: padrao de erros, violacoes e eventos de auditoria.
- `serializacao-e-versionamento.md`: convencoes de schema, datas, unidades e compatibilidade.
- `plano-testes-contrato.md`: cenarios de teste de contrato.
- `decisoes-arquiteturais.md`: decisoes formais registradas para a etapa.

## Resultado esperado

Ao final da Etapa 1, o projeto deve possuir uma linguagem unica do sistema, um nucleo de contratos desacoplado de solver e infraestrutura, e criterios de aceite claros para implementacao e TDD nas etapas seguintes.

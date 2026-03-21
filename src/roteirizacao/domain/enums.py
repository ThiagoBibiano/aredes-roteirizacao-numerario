from __future__ import annotations

from enum import StrEnum


class TipoServico(StrEnum):
    SUPRIMENTO = "suprimento"
    RECOLHIMENTO = "recolhimento"
    EXTRAORDINARIO = "extraordinario"


class ClassePlanejamento(StrEnum):
    PADRAO = "padrao"
    ESPECIAL = "especial"


class ClasseOperacional(StrEnum):
    SUPRIMENTO = "suprimento"
    RECOLHIMENTO = "recolhimento"


class Criticidade(StrEnum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class StatusOrdem(StrEnum):
    RECEBIDA = "recebida"
    VALIDADA = "validada"
    CLASSIFICADA = "classificada"
    PLANEJAVEL = "planejavel"
    PLANEJADA = "planejada"
    NAO_ATENDIDA = "nao_atendida"
    EXCLUIDA = "excluida"
    CANCELADA = "cancelada"


class StatusCancelamento(StrEnum):
    NAO_CANCELADA = "nao_cancelada"
    CANCELAMENTO_SOLICITADO = "cancelamento_solicitado"
    CANCELADA_ANTES_CUTOFF = "cancelada_antes_cutoff"
    CANCELADA_APOS_CUTOFF = "cancelada_apos_cutoff"
    CANCELADA_COM_PARADA_IMPRODUTIVA = "cancelada_com_parada_improdutiva"


class TipoPonto(StrEnum):
    AGENCIA = "agencia"
    CLIENTE = "cliente"
    TERMINAL = "terminal"
    BASE_APOIO = "base_apoio"
    OUTRO = "outro"


class TipoViatura(StrEnum):
    LEVE = "leve"
    MEDIA = "media"
    PESADA = "pesada"
    ESPECIALIZADA = "especializada"


class TipoEventoAuditoria(StrEnum):
    INGESTAO = "ingestao"
    VALIDACAO = "validacao"
    CLASSIFICACAO = "classificacao"
    EXCLUSAO = "exclusao"
    CANCELAMENTO = "cancelamento"
    CONSTRUCAO_INSTANCIA = "construcao_instancia"
    ROTEIRIZACAO = "roteirizacao"
    SAIDA = "saida"
    ERRO = "erro"


class SeveridadeEvento(StrEnum):
    INFO = "info"
    AVISO = "aviso"
    ERRO = "erro"
    CRITICO = "critico"


class SeveridadeContratual(StrEnum):
    MUITO_BAIXA = "muito_baixa"
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    MUITO_ALTA = "muito_alta"


class RegraCompatibilidade(StrEnum):
    SERVICO = "servico"
    SETOR = "setor"
    TIPO_PONTO = "tipo_ponto"
    RESTRICAO_ACESSO = "restricao_acesso"
    SEGURANCA = "seguranca"


class StatusExecucaoPlanejamento(StrEnum):
    CONCLUIDA = "concluida"
    CONCLUIDA_COM_RESSALVAS = "concluida_com_ressalvas"
    INVIAVEL = "inviavel"
    FALHA = "falha"

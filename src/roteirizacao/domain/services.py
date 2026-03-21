from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from itertools import count
from typing import Any, Iterable, Mapping

from roteirizacao.domain.enums import (
    ClasseOperacional,
    ClassePlanejamento,
    Criticidade,
    SeveridadeContratual,
    SeveridadeEvento,
    StatusCancelamento,
    StatusOrdem,
    TipoEventoAuditoria,
    TipoPonto,
    TipoServico,
    TipoViatura,
)
from roteirizacao.domain.events import ErroContrato, ErroValidacao, EventoAuditoria
from roteirizacao.domain.models import (
    Base,
    BaseBruta,
    CompatibilidadeOperacional,
    Coordenada,
    JanelaTempo,
    MetadadoIngestao,
    MetadadoRastreabilidade,
    Ordem,
    OrdemBruta,
    OrdemClassificada,
    Ponto,
    PontoBruto,
    Viatura,
    ViaturaBruta,
)
from roteirizacao.domain.serialization import ensure_date, ensure_datetime, ensure_decimal, ensure_string, normalize_token

ALIASES_TIPO_SERVICO = {"especial": TipoServico.EXTRAORDINARIO}
ALIASES_CLASSE_PLANEJAMENTO = {"padrão": ClassePlanejamento.PADRAO, "padrao": ClassePlanejamento.PADRAO}
ALIASES_CRITICIDADE = {
    "obrigatoria": Criticidade.CRITICA,
    "prioritaria": Criticidade.ALTA,
    "adiavel": Criticidade.MEDIA,
}
ALIASES_TIPO_PONTO = {
    "atm": TipoPonto.TERMINAL,
    "cofre_inteligente": TipoPonto.OUTRO,
    "varejista": TipoPonto.CLIENTE,
    "cliente_corporativo": TipoPonto.CLIENTE,
}


@dataclass(slots=True, frozen=True)
class ContextoExecucao:
    id_execucao: str
    data_operacao: date
    cutoff: datetime
    timestamp_referencia: datetime
    versao_schema: str = "1.0"

    def __post_init__(self) -> None:
        if self.cutoff.tzinfo is None or self.timestamp_referencia.tzinfo is None:
            raise ValueError("contexto de execucao deve usar timezone")


class _FactoryErrosEventos:
    def __init__(self) -> None:
        self._counter = count(1)

    def erro_contrato(
        self,
        *,
        contexto: ContextoExecucao,
        entidade: str,
        campo: str | None,
        valor_observado: Any,
        origem: str,
        codigo_erro: str,
        mensagem: str,
    ) -> ErroContrato:
        return ErroContrato(
            id_erro=f"err-{next(self._counter):06d}",
            tipo_erro="schema",
            codigo_erro=codigo_erro,
            mensagem=mensagem,
            entidade=entidade,
            campo=campo,
            valor_observado=valor_observado,
            origem=origem,
            timestamp=contexto.timestamp_referencia,
            id_execucao=contexto.id_execucao,
        )

    def erro_validacao(
        self,
        *,
        contexto: ContextoExecucao,
        entidade: str,
        id_entidade: str | None,
        campo: str | None,
        valor_observado: Any,
        valor_esperado: Any,
        mensagem: str,
        codigo_regra: str = "dominio.invariante_violada",
        severidade: SeveridadeEvento = SeveridadeEvento.ERRO,
    ) -> ErroValidacao:
        return ErroValidacao(
            id_erro=f"err-{next(self._counter):06d}",
            codigo_regra=codigo_regra,
            mensagem=mensagem,
            entidade=entidade,
            id_entidade=id_entidade,
            campo=campo,
            valor_observado=valor_observado,
            valor_esperado=valor_esperado,
            severidade=severidade,
            timestamp=contexto.timestamp_referencia,
            id_execucao=contexto.id_execucao,
        )

    def evento(
        self,
        *,
        contexto: ContextoExecucao,
        tipo_evento: TipoEventoAuditoria,
        entidade_afetada: str,
        id_entidade: str | None,
        regra_relacionada: str,
        motivo: str,
        severidade: SeveridadeEvento = SeveridadeEvento.INFO,
        campo_afetado: str | None = None,
        valor_observado: Any = None,
        valor_esperado: Any = None,
        contexto_adicional: dict[str, Any] | None = None,
    ) -> EventoAuditoria:
        return EventoAuditoria(
            id_evento=f"evt-{next(self._counter):06d}",
            tipo_evento=tipo_evento,
            severidade=severidade,
            entidade_afetada=entidade_afetada,
            id_entidade=id_entidade,
            regra_relacionada=regra_relacionada,
            motivo=motivo,
            timestamp_evento=contexto.timestamp_referencia,
            id_execucao=contexto.id_execucao,
            campo_afetado=campo_afetado,
            valor_observado=valor_observado,
            valor_esperado=valor_esperado,
            contexto_adicional=contexto_adicional,
        )


_FACTORY = _FactoryErrosEventos()


def _metadados(raw: MetadadoIngestao, contexto: ContextoExecucao) -> MetadadoRastreabilidade:
    return MetadadoRastreabilidade(
        id_execucao=contexto.id_execucao,
        origem=raw.origem,
        timestamp_referencia=contexto.timestamp_referencia,
        versao_schema=contexto.versao_schema,
        hash_conteudo=raw.identificador_externo,
    )


def _missing_required_fields(
    payload: Mapping[str, Any],
    required_fields: Iterable[str],
    *,
    entidade: str,
    origem: str,
    contexto: ContextoExecucao,
) -> list[ErroContrato]:
    errors: list[ErroContrato] = []
    for field_name in required_fields:
        value = payload.get(field_name)
        if value is None or value == "":
            errors.append(
                _FACTORY.erro_contrato(
                    contexto=contexto,
                    entidade=entidade,
                    campo=field_name,
                    valor_observado=value,
                    origem=origem,
                    codigo_erro="schema.obrigatorio_ausente",
                    mensagem=f"campo obrigatorio ausente: {field_name}",
                )
            )
    return errors


def _coordenada(payload: Mapping[str, Any]) -> Coordenada:
    if "coordenadas" in payload:
        coord = payload["coordenadas"]
        latitude = float(coord["latitude"])
        longitude = float(coord["longitude"])
    else:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
    return Coordenada(latitude=latitude, longitude=longitude)


def _janela(
    payload: Mapping[str, Any],
    start_field: str,
    end_field: str,
) -> JanelaTempo:
    return JanelaTempo(
        inicio=ensure_datetime(payload[start_field], start_field),
        fim=ensure_datetime(payload[end_field], end_field),
    )


def _status_ativo(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return True
    token = normalize_token(str(value))
    return token not in {"false", "0", "inativo", "nao", "nao_ativo"}


def _parse_enum(enum_type: type, raw_value: Any, field_name: str) -> Any:
    token = normalize_token(ensure_string(str(raw_value), field_name))
    try:
        return enum_type(token)
    except ValueError as exc:
        raise ValueError(f"campo '{field_name}' fora do vocabulario controlado") from exc


def _parse_tipo_servico(raw_value: Any) -> tuple[TipoServico, bool]:
    token = normalize_token(ensure_string(str(raw_value), "tipo_servico"))
    if token in ALIASES_TIPO_SERVICO:
        return ALIASES_TIPO_SERVICO[token], True
    return TipoServico(token), False


def _parse_classe_planejamento(raw_value: Any) -> ClassePlanejamento:
    token = normalize_token(ensure_string(str(raw_value), "classe_planejamento"))
    return ALIASES_CLASSE_PLANEJAMENTO.get(token, ClassePlanejamento(token))


def _parse_criticidade(raw_value: Any) -> Criticidade:
    token = normalize_token(ensure_string(str(raw_value), "criticidade"))
    return ALIASES_CRITICIDADE.get(token, Criticidade(token))


def _parse_tipo_ponto(raw_value: Any) -> TipoPonto:
    token = normalize_token(ensure_string(str(raw_value), "tipo_ponto"))
    return ALIASES_TIPO_PONTO.get(token, TipoPonto(token) if token in {item.value for item in TipoPonto} else TipoPonto.OUTRO)


def _classe_operacional(payload: Mapping[str, Any], tipo_servico: TipoServico) -> ClasseOperacional:
    explicit = payload.get("classe_operacional")
    if explicit is not None and explicit != "":
        return ClasseOperacional(normalize_token(str(explicit)))
    if tipo_servico == TipoServico.SUPRIMENTO:
        return ClasseOperacional.SUPRIMENTO
    if tipo_servico == TipoServico.RECOLHIMENTO:
        return ClasseOperacional.RECOLHIMENTO
    raise ValueError("classe_operacional obrigatoria para tipo_servico extraordinario")


def _compatibilidade_servico(value: Any) -> frozenset[TipoServico]:
    if value in (None, ""):
        return frozenset()
    if isinstance(value, str):
        items = [value]
    else:
        items = list(value)
    return frozenset(TipoServico(normalize_token(str(item))) for item in items)


def _tuple_strings(value: Any) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


def _frozenset_strings(value: Any) -> frozenset[str]:
    if value in (None, ""):
        return frozenset()
    if isinstance(value, str):
        return frozenset({value})
    return frozenset(str(item) for item in value)


def validate_base(raw: BaseBruta, contexto: ContextoExecucao) -> tuple[Base | None, list[ErroContrato | ErroValidacao], list[EventoAuditoria]]:
    payload = dict(raw.payload)
    events = [
        _FACTORY.evento(
            contexto=contexto,
            tipo_evento=TipoEventoAuditoria.INGESTAO,
            entidade_afetada="BaseBruta",
            id_entidade=str(payload.get("id_base")) if payload.get("id_base") else None,
            regra_relacionada="ingestao.base",
            motivo="base bruta recebida",
        )
    ]
    errors = _missing_required_fields(
        payload,
        ["id_base", "nome", "inicio_operacao", "fim_operacao"],
        entidade="Base",
        origem=raw.metadado_ingestao.origem,
        contexto=contexto,
    )
    if "coordenadas" not in payload and (payload.get("latitude") is None or payload.get("longitude") is None):
        errors.append(
            _FACTORY.erro_contrato(
                contexto=contexto,
                entidade="Base",
                campo="coordenadas",
                valor_observado=payload.get("coordenadas"),
                origem=raw.metadado_ingestao.origem,
                codigo_erro="schema.obrigatorio_ausente",
                mensagem="campo obrigatorio ausente: coordenadas",
            )
        )
    if errors:
        return None, errors, events

    try:
        base = Base(
            id_base=ensure_string(payload["id_base"], "id_base"),
            nome=ensure_string(payload["nome"], "nome"),
            localizacao=_coordenada(payload),
            janela_operacao=_janela(payload, "inicio_operacao", "fim_operacao"),
            status_ativo=_status_ativo(payload.get("status_ativo", True)),
            metadados=_metadados(raw.metadado_ingestao, contexto),
            capacidade_expedicao=int(payload["capacidade_expedicao"]) if payload.get("capacidade_expedicao") is not None else None,
            codigo_externo=str(payload["codigo_externo"]) if payload.get("codigo_externo") is not None else None,
            atributos_operacionais=dict(payload.get("atributos_operacionais", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        return None, [
            _FACTORY.erro_validacao(
                contexto=contexto,
                entidade="Base",
                id_entidade=str(payload.get("id_base")) if payload.get("id_base") else None,
                campo=None,
                valor_observado=payload,
                valor_esperado="contrato Base valido",
                mensagem=str(exc),
            )
        ], events

    events.append(
        _FACTORY.evento(
            contexto=contexto,
            tipo_evento=TipoEventoAuditoria.VALIDACAO,
            entidade_afetada="Base",
            id_entidade=base.id_base,
            regra_relacionada="dominio.base",
            motivo="base validada",
        )
    )
    return base, [], events


def validate_ponto(raw: PontoBruto, contexto: ContextoExecucao) -> tuple[Ponto | None, list[ErroContrato | ErroValidacao], list[EventoAuditoria]]:
    payload = dict(raw.payload)
    events = [
        _FACTORY.evento(
            contexto=contexto,
            tipo_evento=TipoEventoAuditoria.INGESTAO,
            entidade_afetada="PontoBruto",
            id_entidade=str(payload.get("id_ponto")) if payload.get("id_ponto") else None,
            regra_relacionada="ingestao.ponto",
            motivo="ponto bruto recebido",
        )
    ]
    errors = _missing_required_fields(
        payload,
        ["id_ponto", "tipo_ponto", "setor_geografico"],
        entidade="Ponto",
        origem=raw.metadado_ingestao.origem,
        contexto=contexto,
    )
    if "coordenadas" not in payload and (payload.get("latitude") is None or payload.get("longitude") is None):
        errors.append(
            _FACTORY.erro_contrato(
                contexto=contexto,
                entidade="Ponto",
                campo="coordenadas",
                valor_observado=payload.get("coordenadas"),
                origem=raw.metadado_ingestao.origem,
                codigo_erro="schema.obrigatorio_ausente",
                mensagem="campo obrigatorio ausente: coordenadas",
            )
        )
    if errors:
        return None, errors, events

    try:
        janelas_padrao: tuple[JanelaTempo, ...] = ()
        if payload.get("inicio_janela") and payload.get("fim_janela"):
            janelas_padrao = (_janela(payload, "inicio_janela", "fim_janela"),)

        ponto = Ponto(
            id_ponto=ensure_string(payload["id_ponto"], "id_ponto"),
            tipo_ponto=_parse_tipo_ponto(payload["tipo_ponto"]),
            localizacao=_coordenada(payload),
            status_ativo=_status_ativo(payload.get("status_ativo", True)),
            setor_geografico=ensure_string(payload["setor_geografico"], "setor_geografico"),
            metadados=_metadados(raw.metadado_ingestao, contexto),
            janelas_padrao=janelas_padrao,
            tempo_padrao_servico=int(payload["tempo_servico"]) if payload.get("tempo_servico") is not None else None,
            restricoes_acesso=_tuple_strings(payload.get("restricoes_acesso")),
            compatibilidades_minimas=CompatibilidadeOperacional(
                servicos=_compatibilidade_servico(payload.get("compatibilidade_servico")),
                setores=_frozenset_strings(payload.get("compatibilidade_setor")),
            ),
            endereco_textual=str(payload["endereco_textual"]) if payload.get("endereco_textual") else None,
        )
        if ponto.tempo_padrao_servico is not None and ponto.tempo_padrao_servico < 0:
            raise ValueError("tempo_padrao_servico nao pode ser negativo")
    except (KeyError, TypeError, ValueError) as exc:
        return None, [
            _FACTORY.erro_validacao(
                contexto=contexto,
                entidade="Ponto",
                id_entidade=str(payload.get("id_ponto")) if payload.get("id_ponto") else None,
                campo=None,
                valor_observado=payload,
                valor_esperado="contrato Ponto valido",
                mensagem=str(exc),
            )
        ], events

    events.append(
        _FACTORY.evento(
            contexto=contexto,
            tipo_evento=TipoEventoAuditoria.VALIDACAO,
            entidade_afetada="Ponto",
            id_entidade=ponto.id_ponto,
            regra_relacionada="dominio.ponto",
            motivo="ponto validado",
        )
    )
    return ponto, [], events


def validate_viatura(
    raw: ViaturaBruta,
    contexto: ContextoExecucao,
    *,
    bases_existentes: set[str],
) -> tuple[Viatura | None, list[ErroContrato | ErroValidacao], list[EventoAuditoria]]:
    payload = dict(raw.payload)
    events = [
        _FACTORY.evento(
            contexto=contexto,
            tipo_evento=TipoEventoAuditoria.INGESTAO,
            entidade_afetada="ViaturaBruta",
            id_entidade=str(payload.get("id_viatura")) if payload.get("id_viatura") else None,
            regra_relacionada="ingestao.viatura",
            motivo="viatura bruta recebida",
        )
    ]
    errors = _missing_required_fields(
        payload,
        [
            "id_viatura",
            "tipo_viatura",
            "id_base_origem",
            "inicio_turno",
            "fim_turno",
            "custo_fixo",
            "custo_variavel",
            "capacidade_financeira",
            "capacidade_volumetrica",
            "teto_segurado",
        ],
        entidade="Viatura",
        origem=raw.metadado_ingestao.origem,
        contexto=contexto,
    )
    if errors:
        return None, errors, events

    try:
        compatibilidade_servico = _compatibilidade_servico(payload.get("compatibilidade_servico", ["suprimento", "recolhimento", "extraordinario"]))
        viatura = Viatura(
            id_viatura=ensure_string(payload["id_viatura"], "id_viatura"),
            tipo_viatura=TipoViatura(normalize_token(str(payload["tipo_viatura"]))),
            id_base_origem=ensure_string(payload["id_base_origem"], "id_base_origem"),
            turno=_janela(payload, "inicio_turno", "fim_turno"),
            custo_fixo=ensure_decimal(payload["custo_fixo"], "custo_fixo"),
            custo_variavel=ensure_decimal(payload["custo_variavel"], "custo_variavel"),
            capacidade_financeira=ensure_decimal(payload["capacidade_financeira"], "capacidade_financeira"),
            capacidade_volumetrica=ensure_decimal(payload["capacidade_volumetrica"], "capacidade_volumetrica"),
            teto_segurado=ensure_decimal(payload["teto_segurado"], "teto_segurado"),
            compatibilidade_servico=compatibilidade_servico,
            status_ativo=_status_ativo(payload.get("status_ativo", True)),
            metadados=_metadados(raw.metadado_ingestao, contexto),
            compatibilidade_ponto=_frozenset_strings(payload.get("compatibilidade_ponto")),
            compatibilidade_setor=_frozenset_strings(payload.get("compatibilidade_setor")),
            restricoes_jornada=_tuple_strings(payload.get("restricoes_jornada")),
            atributos_operacionais=dict(payload.get("atributos_operacionais", {})),
        )
        if viatura.id_base_origem not in bases_existentes:
            raise ValueError("id_base_origem deve referenciar base existente")
        if viatura.custo_fixo < 0 or viatura.custo_variavel < 0:
            raise ValueError("custos nao podem ser negativos")
        if viatura.capacidade_financeira <= 0 or viatura.capacidade_volumetrica <= 0 or viatura.teto_segurado <= 0:
            raise ValueError("capacidades e teto segurado devem ser positivos")
    except (KeyError, TypeError, ValueError) as exc:
        return None, [
            _FACTORY.erro_validacao(
                contexto=contexto,
                entidade="Viatura",
                id_entidade=str(payload.get("id_viatura")) if payload.get("id_viatura") else None,
                campo=None,
                valor_observado=payload,
                valor_esperado="contrato Viatura valido",
                mensagem=str(exc),
                codigo_regra="referencia.entidade_ausente" if "base existente" in str(exc) else "dominio.invariante_violada",
            )
        ], events

    events.append(
        _FACTORY.evento(
            contexto=contexto,
            tipo_evento=TipoEventoAuditoria.VALIDACAO,
            entidade_afetada="Viatura",
            id_entidade=viatura.id_viatura,
            regra_relacionada="dominio.viatura",
            motivo="viatura validada",
        )
    )
    return viatura, [], events


def validate_ordem(
    raw: OrdemBruta,
    contexto: ContextoExecucao,
    *,
    pontos_existentes: set[str],
) -> tuple[Ordem | None, list[ErroContrato | ErroValidacao], list[EventoAuditoria]]:
    payload = dict(raw.payload)
    events = [
        _FACTORY.evento(
            contexto=contexto,
            tipo_evento=TipoEventoAuditoria.INGESTAO,
            entidade_afetada="OrdemBruta",
            id_entidade=str(payload.get("id_ordem")) if payload.get("id_ordem") else None,
            regra_relacionada="ingestao.ordem",
            motivo="ordem bruta recebida",
        )
    ]
    errors = _missing_required_fields(
        payload,
        [
            "id_ordem",
            "data_operacao",
            "tipo_servico",
            "classe_planejamento",
            "id_ponto",
            "valor_estimado",
            "volume_estimado",
            "inicio_janela",
            "fim_janela",
            "tempo_servico",
            "criticidade",
            "penalidade_nao_atendimento",
            "penalidade_atraso",
            "taxa_improdutiva",
        ],
        entidade="Ordem",
        origem=raw.metadado_ingestao.origem,
        contexto=contexto,
    )
    if errors:
        return None, errors, events

    try:
        tipo_servico, used_alias = _parse_tipo_servico(payload["tipo_servico"])
        classe_operacional = _classe_operacional(payload, tipo_servico)
        instante_cancelamento = None
        janela_cancelamento = None
        if payload.get("instante_cancelamento"):
            instante_cancelamento = ensure_datetime(payload["instante_cancelamento"], "instante_cancelamento")
        elif payload.get("janela_cancelamento"):
            cancel_window = payload["janela_cancelamento"]
            janela_cancelamento = JanelaTempo(
                inicio=ensure_datetime(cancel_window["inicio"], "janela_cancelamento.inicio"),
                fim=ensure_datetime(cancel_window["fim"], "janela_cancelamento.fim"),
            )
            instante_cancelamento = janela_cancelamento.inicio

        status_cancelamento = StatusCancelamento(
            normalize_token(str(payload.get("status_cancelamento", StatusCancelamento.NAO_CANCELADA.value)))
        )

        ordem = Ordem(
            id_ordem=ensure_string(payload["id_ordem"], "id_ordem"),
            origem_ordem=ensure_string(str(payload.get("origem_ordem", raw.metadado_ingestao.origem)), "origem_ordem"),
            data_operacao=ensure_date(payload["data_operacao"], "data_operacao"),
            versao_ordem=str(payload.get("versao_ordem", "1")),
            timestamp_criacao=ensure_datetime(payload.get("timestamp_criacao", contexto.timestamp_referencia), "timestamp_criacao"),
            id_ponto=ensure_string(payload["id_ponto"], "id_ponto"),
            tipo_servico=tipo_servico,
            classe_planejamento=_parse_classe_planejamento(payload["classe_planejamento"]),
            classe_operacional=classe_operacional,
            criticidade=_parse_criticidade(payload["criticidade"]),
            valor_estimado=ensure_decimal(payload["valor_estimado"], "valor_estimado"),
            volume_estimado=ensure_decimal(payload["volume_estimado"], "volume_estimado"),
            tempo_servico=int(payload["tempo_servico"]),
            janela_efetiva=_janela(payload, "inicio_janela", "fim_janela"),
            penalidade_nao_atendimento=ensure_decimal(payload["penalidade_nao_atendimento"], "penalidade_nao_atendimento"),
            penalidade_atraso=ensure_decimal(payload["penalidade_atraso"], "penalidade_atraso"),
            status_ordem=StatusOrdem.VALIDADA,
            status_cancelamento=status_cancelamento,
            taxa_improdutiva=ensure_decimal(payload["taxa_improdutiva"], "taxa_improdutiva"),
            metadados=_metadados(raw.metadado_ingestao, contexto),
            sla=str(payload["sla"]) if payload.get("sla") else None,
            compatibilidade_requerida=_tuple_strings(payload.get("compatibilidade_requerida")),
            instante_cancelamento=instante_cancelamento,
            severidade_contratual=(
                SeveridadeContratual(normalize_token(str(payload["severidade_contratual"])))
                if payload.get("severidade_contratual")
                else None
            ),
            janela_cancelamento=janela_cancelamento,
        )
        if ordem.id_ponto not in pontos_existentes:
            raise ValueError("id_ponto deve referenciar ponto existente")
        if ordem.data_operacao != contexto.data_operacao:
            raise ValueError("data_operacao difere da execucao")
        if ordem.valor_estimado < 0 or ordem.volume_estimado < 0:
            raise ValueError("valor_estimado e volume_estimado devem ser nao negativos")
        if ordem.tempo_servico < 0:
            raise ValueError("tempo_servico nao pode ser negativo")
        if ordem.penalidade_nao_atendimento < 0 or ordem.penalidade_atraso < 0 or ordem.taxa_improdutiva < 0:
            raise ValueError("penalidades e taxa_improdutiva devem ser nao negativas")
        if ordem.status_cancelamento != StatusCancelamento.NAO_CANCELADA and ordem.instante_cancelamento is None:
            raise ValueError("cancelamento exige instante ou janela coerente")
    except (KeyError, TypeError, ValueError) as exc:
        code = "referencia.entidade_ausente" if "ponto existente" in str(exc) else "dominio.invariante_violada"
        if "vocabulario" in str(exc):
            code = "schema.enum_desconhecido"
        return None, [
            _FACTORY.erro_validacao(
                contexto=contexto,
                entidade="Ordem",
                id_entidade=str(payload.get("id_ordem")) if payload.get("id_ordem") else None,
                campo=None,
                valor_observado=payload,
                valor_esperado="contrato Ordem valido",
                mensagem=str(exc),
                codigo_regra=code,
            )
        ], events

    if used_alias:
        events.append(
            _FACTORY.evento(
                contexto=contexto,
                tipo_evento=TipoEventoAuditoria.VALIDACAO,
                entidade_afetada="Ordem",
                id_entidade=ordem.id_ordem,
                regra_relacionada="alias.tipo_servico",
                motivo="tipo_servico 'especial' normalizado para 'extraordinario'",
                severidade=SeveridadeEvento.AVISO,
                campo_afetado="tipo_servico",
                valor_observado=payload.get("tipo_servico"),
                valor_esperado=TipoServico.EXTRAORDINARIO.value,
            )
        )

    events.append(
        _FACTORY.evento(
            contexto=contexto,
            tipo_evento=TipoEventoAuditoria.VALIDACAO,
            entidade_afetada="Ordem",
            id_entidade=ordem.id_ordem,
            regra_relacionada="dominio.ordem",
            motivo="ordem validada",
        )
    )
    return ordem, [], events


def classify_ordem(ordem: Ordem, contexto: ContextoExecucao) -> tuple[OrdemClassificada, list[EventoAuditoria]]:
    events: list[EventoAuditoria] = []
    impacto_financeiro = Decimal("0")
    impacto_operacional: str | None = None
    motivo_exclusao: str | None = None
    elegivel_no_cutoff = True
    planeavel = True
    status_ordem = StatusOrdem.PLANEJAVEL

    if ordem.status_cancelamento != StatusCancelamento.NAO_CANCELADA:
        elegivel_no_cutoff = False
        planeavel = False
        cancelamento_antes_cutoff = ordem.instante_cancelamento is not None and ordem.instante_cancelamento <= contexto.cutoff
        if cancelamento_antes_cutoff:
            status_ordem = StatusOrdem.EXCLUIDA
            motivo_exclusao = "cancelada_antes_cutoff"
            events.append(
                _FACTORY.evento(
                    contexto=contexto,
                    tipo_evento=TipoEventoAuditoria.EXCLUSAO,
                    entidade_afetada="Ordem",
                    id_entidade=ordem.id_ordem,
                    regra_relacionada="negocio.cutoff_exclusao",
                    motivo="ordem excluida por cancelamento antes do cut-off",
                    campo_afetado="status_cancelamento",
                    valor_observado=ordem.status_cancelamento.value,
                    valor_esperado=StatusCancelamento.NAO_CANCELADA.value,
                )
            )
        else:
            status_ordem = StatusOrdem.CANCELADA
            motivo_exclusao = "cancelada_apos_cutoff"
            impacto_financeiro = ordem.taxa_improdutiva if ordem.taxa_improdutiva > 0 else ordem.penalidade_nao_atendimento
            impacto_operacional = (
                "parada_improdutiva"
                if ordem.taxa_improdutiva > 0 or ordem.status_cancelamento == StatusCancelamento.CANCELADA_COM_PARADA_IMPRODUTIVA
                else "cancelamento_tardio"
            )
            events.append(
                _FACTORY.evento(
                    contexto=contexto,
                    tipo_evento=TipoEventoAuditoria.CANCELAMENTO,
                    entidade_afetada="Ordem",
                    id_entidade=ordem.id_ordem,
                    regra_relacionada="negocio.cancelamento_tardio",
                    motivo="ordem cancelada apos cut-off",
                    severidade=SeveridadeEvento.AVISO,
                    campo_afetado="status_cancelamento",
                    valor_observado=ordem.status_cancelamento.value,
                    contexto_adicional={
                        "impacto_financeiro_previsto": str(impacto_financeiro),
                        "impacto_operacional": impacto_operacional,
                    },
                )
            )

    classified = OrdemClassificada(
        ordem=ordem,
        status_ordem=status_ordem,
        elegivel_no_cutoff=elegivel_no_cutoff,
        planeavel=planeavel,
        motivo_exclusao=motivo_exclusao,
        impacto_financeiro_previsto=impacto_financeiro,
        impacto_operacional=impacto_operacional,
    )
    events.append(
        _FACTORY.evento(
            contexto=contexto,
            tipo_evento=TipoEventoAuditoria.CLASSIFICACAO,
            entidade_afetada="OrdemClassificada",
            id_entidade=ordem.id_ordem,
            regra_relacionada="classificacao.operacional",
            motivo="ordem classificada para planejamento",
            contexto_adicional={
                "classe_operacional": ordem.classe_operacional.value,
                "status_ordem": status_ordem.value,
                "planeavel": planeavel,
            },
        )
    )
    return classified, events

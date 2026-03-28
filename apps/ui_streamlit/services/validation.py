from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


REQUIRED_INLINE_FILES = (
    "contexto.json",
    "bases.json",
    "pontos.json",
    "viaturas.json",
    "ordens.json",
)


@dataclass(slots=True, frozen=True)
class InlinePayloadBuildResult:
    payload: dict[str, Any] | None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class DatasetPayloadLoadResult:
    input_payload: dict[str, Any] | None
    warnings: tuple[str, ...] = ()


def parse_json_document(content: bytes | str, source_name: str) -> Any:
    try:
        decoded = content.decode("utf-8") if isinstance(content, bytes) else content
        return json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Arquivo '{source_name}' nao contem JSON valido.") from exc


def build_inline_payload_from_documents(
    documents: Mapping[str, bytes | str],
    execution_parameters: Mapping[str, Any],
) -> InlinePayloadBuildResult:
    errors: list[str] = []
    warnings: list[str] = []
    parsed: dict[str, Any] = {}

    for filename in REQUIRED_INLINE_FILES:
        if filename not in documents:
            errors.append(f"Arquivo obrigatorio ausente: {filename}.")

    for filename, content in documents.items():
        try:
            parsed[filename] = parse_json_document(content, filename)
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        return InlinePayloadBuildResult(payload=None, errors=tuple(errors), warnings=tuple(warnings))

    errors.extend(_validate_inline_documents(parsed))
    if errors:
        return InlinePayloadBuildResult(payload=None, errors=tuple(errors), warnings=tuple(warnings))

    payload = {
        "contexto": parsed["contexto.json"],
        "bases": parsed["bases.json"],
        "pontos": parsed["pontos.json"],
        "viaturas": parsed["viaturas.json"],
        "ordens": parsed["ordens.json"],
        **_normalize_execution_parameters(execution_parameters),
    }

    snapshot_source = parsed.get("snapshot_source.json")
    if snapshot_source is not None:
        payload["snapshot_source"] = snapshot_source
        if not payload["materialize_snapshot"]:
            payload["materialize_snapshot"] = True
            warnings.append(
                "snapshot_source.json carregado: materialize_snapshot sera enviado como true na execucao inline."
            )

    return InlinePayloadBuildResult(payload=payload, errors=tuple(errors), warnings=tuple(warnings))


def build_dataset_payload(
    dataset_dir: str,
    execution_parameters: Mapping[str, Any],
    path_parameters: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_dataset_dir = dataset_dir.strip()
    if not resolved_dataset_dir:
        raise ValueError("dataset_dir deve ser informado no modo tecnico.")

    payload = {
        "dataset_dir": resolved_dataset_dir,
        **_normalize_execution_parameters(execution_parameters),
    }
    for key in ("output_path", "snapshot_dir", "source_dir", "state_dir"):
        value = "" if path_parameters is None else str(path_parameters.get(key) or "").strip()
        if value:
            payload[key] = value
    return payload


def load_dataset_payload_from_directory(dataset_dir: str | Path) -> DatasetPayloadLoadResult:
    base_path = Path(dataset_dir)
    warnings: list[str] = []
    payload: dict[str, Any] = {}
    for filename in REQUIRED_INLINE_FILES:
        file_path = base_path / filename
        if not file_path.exists():
            warnings.append(f"Arquivo local nao encontrado para enriquecimento visual: {file_path}.")
            continue
        try:
            payload_key = filename.replace(".json", "")
            payload[payload_key] = parse_json_document(file_path.read_text(encoding="utf-8"), filename)
        except (OSError, ValueError) as exc:
            warnings.append(str(exc))
    return DatasetPayloadLoadResult(input_payload=payload or None, warnings=tuple(warnings))


def _validate_inline_documents(parsed: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    contexto = parsed.get("contexto.json")
    if not isinstance(contexto, dict):
        errors.append("contexto.json deve conter um objeto JSON.")
    else:
        if not contexto.get("id_execucao"):
            errors.append("campo obrigatorio ausente: contexto.id_execucao.")
        if not contexto.get("data_operacao"):
            errors.append("campo obrigatorio ausente: contexto.data_operacao.")

    for filename in ("bases.json", "pontos.json", "viaturas.json", "ordens.json"):
        if not isinstance(parsed.get(filename), list):
            errors.append(f"{filename} deve conter uma lista JSON.")
    return errors


def _normalize_execution_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "materialize_snapshot": bool(parameters.get("materialize_snapshot", False)),
        "max_iterations": int(parameters.get("max_iterations", 100) or 100),
        "seed": int(parameters.get("seed", 1) or 1),
        "collect_stats": bool(parameters.get("collect_stats", False)),
        "display": bool(parameters.get("display", False)),
    }

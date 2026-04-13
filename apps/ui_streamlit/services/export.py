from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from apps.ui_streamlit import UI_VERSION
from apps.ui_streamlit.services.view_models import (
    InspectionSnapshotViewModel,
    inspection_snapshot_from_dict,
    inspection_snapshot_to_dict,
)


ENRICHED_EXPORT_FORMAT = "enriched_inspection_snapshot"


@dataclass(slots=True, frozen=True)
class OfflineLoadResult:
    raw_response: dict[str, Any]
    input_payload: dict[str, Any] | None
    inspection_snapshot: InspectionSnapshotViewModel | None
    source_kind: str
    api_base_url: str
    warnings: tuple[str, ...] = ()


def build_raw_export(raw_response: dict[str, Any]) -> str:
    return json.dumps(raw_response, indent=2, ensure_ascii=True) + "\n"


def build_enriched_export(
    raw_response: dict[str, Any],
    *,
    input_payload: dict[str, Any] | None,
    inspection_snapshot: InspectionSnapshotViewModel,
    source_kind: str,
    api_base_url: str,
    ui_version: str = UI_VERSION,
) -> str:
    payload = {
        "export_format": ENRICHED_EXPORT_FORMAT,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "ui_version": ui_version,
        "source_kind": source_kind,
        "api_base_url": api_base_url,
        "input_payload": input_payload,
        "raw_response": raw_response,
        "inspection_snapshot": inspection_snapshot_to_dict(inspection_snapshot),
    }
    return json.dumps(payload, indent=2, ensure_ascii=True) + "\n"


def load_exported_payload(content: bytes | str) -> OfflineLoadResult:
    payload = json.loads(content.decode("utf-8") if isinstance(content, bytes) else content)
    if not isinstance(payload, dict):
        raise ValueError("O arquivo informado nao contem um objeto JSON suportado.")

    if payload.get("export_format") == ENRICHED_EXPORT_FORMAT:
        raw_response = payload.get("raw_response")
        if not isinstance(raw_response, dict):
            raise ValueError("Export enriquecido sem raw_response valido.")
        inspection_snapshot = None
        if isinstance(payload.get("inspection_snapshot"), dict):
            inspection_snapshot = inspection_snapshot_from_dict(payload["inspection_snapshot"])
        return OfflineLoadResult(
            raw_response=raw_response,
            input_payload=payload.get("input_payload") if isinstance(payload.get("input_payload"), dict) else None,
            inspection_snapshot=inspection_snapshot,
            source_kind=str(payload.get("source_kind") or "offline_enriched"),
            api_base_url=str(payload.get("api_base_url") or "offline"),
        )

    if "result" in payload and "hash_cenario" in payload:
        warnings = ()
        if not isinstance(payload.get("result"), dict):
            warnings = ("O arquivo bruto carregado nao contem um objeto result valido.",)
        return OfflineLoadResult(
            raw_response=payload,
            input_payload=None,
            inspection_snapshot=None,
            source_kind="offline_raw",
            api_base_url="offline",
            warnings=warnings,
        )

    raise ValueError("Formato de arquivo nao suportado para inspecao offline.")

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from roteirizacao.domain.serialization import ensure_datetime


@dataclass(slots=True, frozen=True)
class SnapshotMaterializationResult:
    data_operacao: date
    snapshot_id: str
    content_hash: str
    snapshot_path: Path
    version_path: Path
    manifest_path: Path


class LogisticsSnapshotSource:
    def fetch(self, data_operacao: date) -> dict[str, Any]:
        raise NotImplementedError


class JsonFileLogisticsSnapshotSource(LogisticsSnapshotSource):
    def __init__(self, source_dir: Path) -> None:
        self.source_dir = Path(source_dir)

    def fetch(self, data_operacao: date) -> dict[str, Any]:
        source_path = self.source_dir / f"{data_operacao.isoformat()}.json"
        if not source_path.exists():
            raise FileNotFoundError(f"fonte de malha nao encontrada: {source_path}")
        return json.loads(source_path.read_text())


class FileSystemSnapshotRepository:
    def __init__(self, snapshot_dir: Path) -> None:
        self.snapshot_dir = Path(snapshot_dir)

    def store(self, data_operacao: date, snapshot_payload: dict[str, Any]) -> SnapshotMaterializationResult:
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

        canonical_payload = self._canonical_payload(snapshot_payload)
        content_hash = sha256(
            json.dumps(canonical_payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        snapshot_id = str(canonical_payload.get("snapshot_id") or f"snap-{data_operacao.isoformat()}-{content_hash[:12]}")
        canonical_payload["snapshot_id"] = snapshot_id

        snapshot_path = self.snapshot_dir / f"{data_operacao.isoformat()}.json"
        version_dir = self.snapshot_dir / "versions" / data_operacao.isoformat()
        version_dir.mkdir(parents=True, exist_ok=True)
        version_path = version_dir / f"{snapshot_id}.json"
        manifest_path = version_dir / "manifest.json"

        formatted = json.dumps(canonical_payload, indent=2, sort_keys=True, ensure_ascii=True)
        snapshot_path.write_text(formatted + "\n")
        version_path.write_text(formatted + "\n")
        self._update_manifest(
            manifest_path,
            data_operacao=data_operacao,
            snapshot_id=snapshot_id,
            content_hash=content_hash,
            version_path=version_path,
            materialized_at=canonical_payload["materialized_at"],
            source_name=str(canonical_payload.get("source_name", "unknown")),
        )

        return SnapshotMaterializationResult(
            data_operacao=data_operacao,
            snapshot_id=snapshot_id,
            content_hash=content_hash,
            snapshot_path=snapshot_path,
            version_path=version_path,
            manifest_path=manifest_path,
        )

    def _canonical_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("payload de snapshot deve ser um objeto JSON")

        generated_at = ensure_datetime(payload.get("generated_at"), "generated_at")
        arcs = payload.get("arcs")
        if not isinstance(arcs, list):
            raise ValueError("payload de snapshot deve conter lista de arcos")

        normalized_arcs: list[dict[str, Any]] = []
        for arc in arcs:
            if not isinstance(arc, dict):
                raise ValueError("cada arco do snapshot deve ser um objeto JSON")
            normalized_arcs.append(
                {
                    "id_origem": str(arc.get("id_origem")),
                    "id_destino": str(arc.get("id_destino")),
                    "distancia_metros": arc.get("distancia_metros"),
                    "tempo_segundos": arc.get("tempo_segundos"),
                    "custo": None if arc.get("custo") is None else str(arc.get("custo")),
                    "disponivel": bool(arc.get("disponivel", True)),
                    "restricao": arc.get("restricao"),
                }
            )
        normalized_arcs.sort(key=lambda arc: (arc["id_origem"], arc["id_destino"]))

        return {
            "snapshot_id": payload.get("snapshot_id"),
            "generated_at": generated_at.isoformat(),
            "strategy_name": str(payload.get("strategy_name", "snapshot_json_v1")),
            "schema_version": str(payload.get("schema_version", "1.0")),
            "source_name": str(payload.get("source_name", "json_file_source")),
            "materialized_at": datetime.now(timezone.utc).isoformat(),
            "arcs": normalized_arcs,
        }

    def _update_manifest(
        self,
        manifest_path: Path,
        *,
        data_operacao: date,
        snapshot_id: str,
        content_hash: str,
        version_path: Path,
        materialized_at: str,
        source_name: str,
    ) -> None:
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
        else:
            manifest = {
                "data_operacao": data_operacao.isoformat(),
                "latest_snapshot_id": None,
                "versions": [],
            }

        versions = [entry for entry in manifest.get("versions", []) if entry.get("snapshot_id") != snapshot_id]
        versions.append(
            {
                "snapshot_id": snapshot_id,
                "content_hash": content_hash,
                "version_path": str(version_path),
                "materialized_at": materialized_at,
                "source_name": source_name,
            }
        )
        versions.sort(key=lambda entry: entry["materialized_at"])
        manifest["latest_snapshot_id"] = snapshot_id
        manifest["versions"] = versions
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n")


class LogisticsSnapshotMaterializer:
    def __init__(self, source: LogisticsSnapshotSource, repository: FileSystemSnapshotRepository) -> None:
        self.source = source
        self.repository = repository

    def materialize(self, data_operacao: date) -> SnapshotMaterializationResult:
        source_payload = self.source.fetch(data_operacao)
        return self.repository.store(data_operacao, source_payload)

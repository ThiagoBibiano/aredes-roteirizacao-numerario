from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from roteirizacao.application import DailyPlanningOrchestrator, DatasetPlanningRequest
from roteirizacao.application.snapshot_materializer import (
    FileSystemSnapshotRepository,
    JsonFileLogisticsSnapshotSource,
    LogisticsSnapshotMaterializer,
)
from roteirizacao.domain.serialization import ensure_date, serialize_value, normalize_token


@dataclass(slots=True, frozen=True)
class ApiSettings:
    api_runs_dir: Path = Path("data/api_runs")
    host: str = "0.0.0.0"
    port: int = 8000

    @classmethod
    def from_env(cls) -> "ApiSettings":
        api_runs_dir = Path(os.getenv("ROTEIRIZACAO_API_RUNS_DIR", "data/api_runs"))
        host = os.getenv("ROTEIRIZACAO_API_HOST", "0.0.0.0")
        port = int(os.getenv("ROTEIRIZACAO_API_PORT", "8000"))
        return cls(api_runs_dir=api_runs_dir, host=host, port=port)


class ApiPlanningService:
    def __init__(self, settings: ApiSettings | None = None, *, orchestrator: DailyPlanningOrchestrator | None = None) -> None:
        self.settings = settings or ApiSettings.from_env()
        self.orchestrator = orchestrator or DailyPlanningOrchestrator()

    def materialize_snapshot(self, *, data_operacao: str, source_dir: str, snapshot_dir: str) -> dict[str, Any]:
        parsed_date = ensure_date(data_operacao, "data_operacao")
        materializer = LogisticsSnapshotMaterializer(
            JsonFileLogisticsSnapshotSource(Path(source_dir)),
            FileSystemSnapshotRepository(Path(snapshot_dir)),
        )
        result = materializer.materialize(parsed_date)
        return {
            "data_operacao": result.data_operacao.isoformat(),
            "snapshot_id": result.snapshot_id,
            "content_hash": result.content_hash,
            "snapshot_path": str(result.snapshot_path),
            "version_path": str(result.version_path),
            "manifest_path": str(result.manifest_path),
        }

    def run_dataset(
        self,
        *,
        dataset_dir: str,
        output_path: str | None = None,
        snapshot_dir: str | None = None,
        source_dir: str | None = None,
        state_dir: str | None = None,
        materialize_snapshot: bool = False,
        max_iterations: int = 100,
        seed: int = 1,
        collect_stats: bool = False,
        display: bool = False,
    ) -> dict[str, Any]:
        orchestration = self.orchestrator.run(
            DatasetPlanningRequest(
                dataset_dir=Path(dataset_dir),
                output_path=Path(output_path) if output_path else None,
                snapshot_dir=Path(snapshot_dir) if snapshot_dir else None,
                source_dir=Path(source_dir) if source_dir else None,
                state_dir=Path(state_dir) if state_dir else None,
                materialize_snapshot=materialize_snapshot,
                max_iterations=max_iterations,
                seed=seed,
                collect_stats=collect_stats,
                display=display,
            )
        )
        return self._serialize_orchestration(orchestration)

    def run_inline(
        self,
        *,
        contexto: dict[str, Any],
        bases: list[dict[str, Any]],
        pontos: list[dict[str, Any]],
        viaturas: list[dict[str, Any]],
        ordens: list[dict[str, Any]],
        snapshot_source: dict[str, Any] | None = None,
        materialize_snapshot: bool = False,
        max_iterations: int = 100,
        seed: int = 1,
        collect_stats: bool = False,
        display: bool = False,
    ) -> dict[str, Any]:
        id_execucao = str(contexto.get("id_execucao") or "")
        if not id_execucao.strip():
            raise ValueError("campo 'contexto.id_execucao' e obrigatorio")
        data_operacao = str(contexto.get("data_operacao") or "")
        if not data_operacao:
            raise ValueError("campo 'contexto.data_operacao' e obrigatorio")

        execution_dir = self.settings.api_runs_dir / self._execution_token(id_execucao)
        dataset_dir = execution_dir / "dataset"
        source_dir = dataset_dir / "logistics_sources"
        self._write_json(dataset_dir / "contexto.json", contexto)
        self._write_json(dataset_dir / "bases.json", bases)
        self._write_json(dataset_dir / "pontos.json", pontos)
        self._write_json(dataset_dir / "viaturas.json", viaturas)
        self._write_json(dataset_dir / "ordens.json", ordens)

        should_materialize = materialize_snapshot or snapshot_source is not None
        if snapshot_source is not None:
            self._write_json(source_dir / f"{data_operacao}.json", snapshot_source)

        orchestration = self.orchestrator.run(
            DatasetPlanningRequest(
                dataset_dir=dataset_dir,
                source_dir=source_dir,
                materialize_snapshot=should_materialize,
                max_iterations=max_iterations,
                seed=seed,
                collect_stats=collect_stats,
                display=display,
            )
        )
        return self._serialize_orchestration(orchestration)

    def _execution_token(self, id_execucao: str) -> str:
        token = normalize_token(id_execucao)
        return token or "execucao"

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")

    def _serialize_orchestration(self, orchestration) -> dict[str, Any]:
        result = orchestration.resultado_planejamento
        return {
            "id_execucao": result.id_execucao,
            "hash_cenario": orchestration.hash_cenario,
            "status_final": result.status_final.value,
            "reused_cached_result": orchestration.reused_cached_result,
            "recovered_previous_context": orchestration.recovered_previous_context,
            "attempt_number": orchestration.attempt_number,
            "output_path": str(orchestration.output_path),
            "result_path": str(orchestration.result_path),
            "state_path": str(orchestration.state_path),
            "scenario_path": str(orchestration.scenario_path),
            "manifest_path": str(orchestration.manifest_path),
            "snapshot_materialization": None
            if orchestration.snapshot_materialization is None
            else serialize_value(orchestration.snapshot_materialization),
            "result": serialize_value(result),
        }

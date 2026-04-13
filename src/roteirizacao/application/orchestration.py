from __future__ import annotations

import json
import pickle
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

from roteirizacao.application.instance_builder import OptimizationInstanceBuilder
from roteirizacao.application.logistics_matrix import LogisticsMatrixBuilder
from roteirizacao.application.logistics_provider import (
    FallbackLogisticsMatrixProvider,
    PersistedSnapshotLogisticsMatrixProvider,
)
from roteirizacao.application.planning import PlanningExecutor
from roteirizacao.application.preparation import PreparationPipeline
from roteirizacao.application.snapshot_materializer import (
    FileSystemSnapshotRepository,
    JsonFileLogisticsSnapshotSource,
    LogisticsSnapshotMaterializer,
    SnapshotMaterializationResult,
)
from roteirizacao.domain import BaseBruta, ContextoExecucao, EventoAuditoria, MetadadoIngestao, OrdemBruta, PontoBruto, ResultadoPlanejamento, ViaturaBruta
from roteirizacao.domain.enums import SeveridadeEvento, TipoEventoAuditoria
from roteirizacao.domain.results import LogPlanejamento, RelatorioPlanejamento
from roteirizacao.domain.serialization import ensure_date, ensure_datetime, serialize_value


@dataclass(slots=True, frozen=True)
class DatasetPlanningRequest:
    dataset_dir: Path
    output_path: Path | None = None
    snapshot_dir: Path | None = None
    source_dir: Path | None = None
    state_dir: Path | None = None
    materialize_snapshot: bool = False
    max_iterations: int = 100
    seed: int = 1
    collect_stats: bool = False
    display: bool = False


@dataclass(slots=True, frozen=True)
class OrchestrationResult:
    resultado_planejamento: ResultadoPlanejamento
    hash_cenario: str
    output_path: Path
    result_path: Path
    state_path: Path
    scenario_path: Path
    manifest_path: Path
    recovered_previous_context: bool
    reused_cached_result: bool
    attempt_number: int
    snapshot_materialization: SnapshotMaterializationResult | None = None


@dataclass(slots=True, frozen=True)
class LoadedDatasetPayloads:
    contexto_payload: dict[str, Any]
    bases_payload: list[Any]
    pontos_payload: list[Any]
    viaturas_payload: list[Any]
    ordens_payload: list[Any]


class PlanningDatasetLoader:
    def load_payloads(self, dataset_dir: Path) -> LoadedDatasetPayloads:
        dataset_dir = Path(dataset_dir)
        contexto_payload = self._load_json(dataset_dir / "contexto.json")
        bases_payload = self._load_json(dataset_dir / "bases.json")
        pontos_payload = self._load_json(dataset_dir / "pontos.json")
        viaturas_payload = self._load_json(dataset_dir / "viaturas.json")
        ordens_payload = self._load_json(dataset_dir / "ordens.json")

        if not isinstance(contexto_payload, dict):
            raise ValueError("contexto.json deve conter um objeto JSON")
        for name, payload in (
            ("bases.json", bases_payload),
            ("pontos.json", pontos_payload),
            ("viaturas.json", viaturas_payload),
            ("ordens.json", ordens_payload),
        ):
            if not isinstance(payload, list):
                raise ValueError(f"{name} deve conter uma lista JSON")

        return LoadedDatasetPayloads(
            contexto_payload=contexto_payload,
            bases_payload=bases_payload,
            pontos_payload=pontos_payload,
            viaturas_payload=viaturas_payload,
            ordens_payload=ordens_payload,
        )

    def load_context(self, contexto_payload: dict[str, Any]) -> ContextoExecucao:
        return ContextoExecucao(
            id_execucao=str(contexto_payload["id_execucao"]),
            data_operacao=ensure_date(contexto_payload["data_operacao"], "data_operacao"),
            cutoff=ensure_datetime(contexto_payload["cutoff"], "cutoff"),
            timestamp_referencia=ensure_datetime(contexto_payload["timestamp_referencia"], "timestamp_referencia"),
            versao_schema=str(contexto_payload.get("versao_schema", "1.0")),
        )

    def load_raw_records(self, payload: list[Any], *, raw_cls, default_origin: str, id_field: str, contexto: ContextoExecucao) -> list[Any]:
        records: list[Any] = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("registro invalido no dataset")

            if "payload" in item:
                raw_payload = item["payload"]
                metadata_payload = item.get("metadado_ingestao", {})
            else:
                raw_payload = item
                metadata_payload = {}

            if not isinstance(raw_payload, dict):
                raise ValueError("payload invalido no dataset")
            if not isinstance(metadata_payload, dict):
                raise ValueError("metadado_ingestao invalido no dataset")

            metadado_ingestao = MetadadoIngestao(
                origem=str(metadata_payload.get("origem", default_origin)),
                timestamp_ingestao=ensure_datetime(
                    metadata_payload.get("timestamp_ingestao", contexto.timestamp_referencia),
                    "timestamp_ingestao",
                ),
                versao_schema=str(metadata_payload.get("versao_schema", "1.0")),
                identificador_externo=str(
                    metadata_payload.get("identificador_externo")
                    or raw_payload.get(id_field)
                    or ""
                )
                or None,
            )
            records.append(raw_cls(payload=raw_payload, metadado_ingestao=metadado_ingestao))
        return records

    def _load_json(self, path: Path) -> Any:
        if not path.exists():
            raise FileNotFoundError(f"arquivo nao encontrado: {path}")
        return json.loads(path.read_text())


class FileSystemExecutionRepository:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = Path(state_dir)

    def manifest_path(self) -> Path:
        return self.state_dir / "manifest.json"

    def scenario_dir(self, hash_cenario: str) -> Path:
        return self.state_dir / hash_cenario

    def scenario_path(self, hash_cenario: str) -> Path:
        return self.scenario_dir(hash_cenario) / "cenario.json"

    def state_path(self, hash_cenario: str) -> Path:
        return self.scenario_dir(hash_cenario) / "estado.json"

    def result_json_path(self, hash_cenario: str) -> Path:
        return self.scenario_dir(hash_cenario) / "resultado-planejamento.json"

    def result_pickle_path(self, hash_cenario: str) -> Path:
        return self.scenario_dir(hash_cenario) / "resultado-planejamento.pkl"

    def load_scenario_payload(self, hash_cenario: str) -> dict[str, Any] | None:
        path = self.scenario_path(hash_cenario)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def load_state(self, hash_cenario: str) -> dict[str, Any] | None:
        path = self.state_path(hash_cenario)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def load_cached_result(self, hash_cenario: str) -> ResultadoPlanejamento | None:
        state = self.load_state(hash_cenario)
        result_path = self.result_pickle_path(hash_cenario)
        if not state or state.get("status") != "completed" or not result_path.exists():
            return None
        with result_path.open("rb") as stream:
            loaded = pickle.load(stream)
        if not isinstance(loaded, ResultadoPlanejamento):
            raise ValueError("artefato de resultado em cache invalido")
        return loaded

    def store_scenario_payload(self, hash_cenario: str, payload: dict[str, Any]) -> Path:
        scenario_dir = self.scenario_dir(hash_cenario)
        scenario_dir.mkdir(parents=True, exist_ok=True)
        path = self.scenario_path(hash_cenario)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n")
        return path

    def mark_running(self, *, hash_cenario: str, id_execucao: str, output_path: Path) -> dict[str, Any]:
        existing = self.load_state(hash_cenario) or {}
        now = datetime.now(timezone.utc).isoformat()
        state = {
            "hash_cenario": hash_cenario,
            "id_execucao": id_execucao,
            "status": "in_progress",
            "attempts": int(existing.get("attempts", 0)) + 1,
            "cache_hits": int(existing.get("cache_hits", 0)),
            "created_at": existing.get("created_at", now),
            "updated_at": now,
            "last_error": None,
            "output_path": str(output_path),
            "scenario_path": str(self.scenario_path(hash_cenario)),
            "result_path": str(self.result_json_path(hash_cenario)),
        }
        self._write_state(hash_cenario, state)
        return state

    def register_cache_hit(self, *, hash_cenario: str, id_execucao: str, output_path: Path) -> dict[str, Any]:
        existing = self.load_state(hash_cenario) or {}
        now = datetime.now(timezone.utc).isoformat()
        state = {
            "hash_cenario": hash_cenario,
            "id_execucao": id_execucao,
            "status": existing.get("status", "completed"),
            "attempts": int(existing.get("attempts", 0)),
            "cache_hits": int(existing.get("cache_hits", 0)) + 1,
            "created_at": existing.get("created_at", now),
            "updated_at": now,
            "last_error": existing.get("last_error"),
            "output_path": str(output_path),
            "scenario_path": str(self.scenario_path(hash_cenario)),
            "result_path": str(self.result_json_path(hash_cenario)),
        }
        self._write_state(hash_cenario, state)
        return state

    def mark_completed(
        self,
        *,
        hash_cenario: str,
        id_execucao: str,
        output_path: Path,
        result: ResultadoPlanejamento,
    ) -> dict[str, Any]:
        existing = self.load_state(hash_cenario) or {}
        scenario_dir = self.scenario_dir(hash_cenario)
        scenario_dir.mkdir(parents=True, exist_ok=True)

        result_json_path = self.result_json_path(hash_cenario)
        result_json_path.write_text(json.dumps(serialize_value(result), indent=2, ensure_ascii=True) + "\n")
        with self.result_pickle_path(hash_cenario).open("wb") as stream:
            pickle.dump(result, stream)

        now = datetime.now(timezone.utc).isoformat()
        state = {
            "hash_cenario": hash_cenario,
            "id_execucao": id_execucao,
            "status": "completed",
            "attempts": int(existing.get("attempts", 0)),
            "cache_hits": int(existing.get("cache_hits", 0)),
            "created_at": existing.get("created_at", now),
            "updated_at": now,
            "last_error": None,
            "output_path": str(output_path),
            "scenario_path": str(self.scenario_path(hash_cenario)),
            "result_path": str(result_json_path),
        }
        self._write_state(hash_cenario, state)
        return state

    def mark_failed(self, *, hash_cenario: str, id_execucao: str, output_path: Path, error_message: str) -> dict[str, Any]:
        existing = self.load_state(hash_cenario) or {}
        now = datetime.now(timezone.utc).isoformat()
        state = {
            "hash_cenario": hash_cenario,
            "id_execucao": id_execucao,
            "status": "failed",
            "attempts": int(existing.get("attempts", 0)),
            "cache_hits": int(existing.get("cache_hits", 0)),
            "created_at": existing.get("created_at", now),
            "updated_at": now,
            "last_error": error_message,
            "output_path": str(output_path),
            "scenario_path": str(self.scenario_path(hash_cenario)),
            "result_path": str(self.result_json_path(hash_cenario)),
        }
        self._write_state(hash_cenario, state)
        return state

    def _write_state(self, hash_cenario: str, state: dict[str, Any]) -> None:
        scenario_dir = self.scenario_dir(hash_cenario)
        scenario_dir.mkdir(parents=True, exist_ok=True)
        self.state_path(hash_cenario).write_text(json.dumps(state, indent=2, sort_keys=True, ensure_ascii=True) + "\n")
        self._update_manifest(state)

    def _update_manifest(self, state: dict[str, Any]) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        path = self.manifest_path()
        if path.exists():
            manifest = json.loads(path.read_text())
        else:
            manifest = {
                "latest_hash_cenario": None,
                "scenarios": [],
            }

        scenarios = [item for item in manifest.get("scenarios", []) if item.get("hash_cenario") != state["hash_cenario"]]
        scenarios.append(
            {
                "hash_cenario": state["hash_cenario"],
                "id_execucao": state["id_execucao"],
                "status": state["status"],
                "attempts": state["attempts"],
                "cache_hits": state["cache_hits"],
                "updated_at": state["updated_at"],
                "scenario_path": state["scenario_path"],
                "result_path": state["result_path"],
            }
        )
        scenarios.sort(key=lambda item: item["updated_at"])
        manifest["latest_hash_cenario"] = state["hash_cenario"]
        manifest["scenarios"] = scenarios
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n")


class DailyPlanningOrchestrator:
    def __init__(
        self,
        *,
        dataset_loader: PlanningDatasetLoader | None = None,
        execution_repository_factory: Callable[[Path], FileSystemExecutionRepository] | None = None,
        executor_factory: Callable[[ContextoExecucao, DatasetPlanningRequest], PlanningExecutor] | None = None,
    ) -> None:
        self.dataset_loader = dataset_loader or PlanningDatasetLoader()
        self.execution_repository_factory = execution_repository_factory or FileSystemExecutionRepository
        self.executor_factory = executor_factory or self._default_executor

    def run(self, request: DatasetPlanningRequest) -> OrchestrationResult:
        resolved_request = self._resolve_request(request)
        dataset_payloads = self.dataset_loader.load_payloads(resolved_request.dataset_dir)
        input_context = self.dataset_loader.load_context(dataset_payloads.contexto_payload)
        hash_payload = self._build_hash_payload(dataset_payloads, input_context, resolved_request)
        hash_cenario = self._hash_cenario(hash_payload)

        repository = self.execution_repository_factory(resolved_request.state_dir)
        stored_scenario = repository.load_scenario_payload(hash_cenario)
        recovered_previous_context = stored_scenario is not None
        effective_context = input_context
        if stored_scenario is not None:
            stored_context = stored_scenario.get("contexto")
            if not isinstance(stored_context, dict):
                raise ValueError("cenario persistido sem contexto valido")
            effective_context = self.dataset_loader.load_context(stored_context)

        scenario_payload = {
            "hash_cenario": hash_cenario,
            "contexto": serialize_value(effective_context),
            "entradas_relevantes": hash_payload,
            "dataset_dir": str(resolved_request.dataset_dir),
            "output_path": str(resolved_request.output_path),
            "snapshot_dir": str(resolved_request.snapshot_dir),
            "source_dir": str(resolved_request.source_dir),
        }
        scenario_path = repository.store_scenario_payload(hash_cenario, scenario_payload)

        cached_result = repository.load_cached_result(hash_cenario)
        if cached_result is not None:
            state = repository.register_cache_hit(
                hash_cenario=hash_cenario,
                id_execucao=effective_context.id_execucao,
                output_path=resolved_request.output_path,
            )
            self._write_output_alias(resolved_request.output_path, cached_result)
            return OrchestrationResult(
                resultado_planejamento=cached_result,
                hash_cenario=hash_cenario,
                output_path=resolved_request.output_path,
                result_path=repository.result_json_path(hash_cenario),
                state_path=repository.state_path(hash_cenario),
                scenario_path=scenario_path,
                manifest_path=repository.manifest_path(),
                recovered_previous_context=recovered_previous_context,
                reused_cached_result=True,
                attempt_number=int(state["attempts"]),
                snapshot_materialization=None,
            )

        state = repository.mark_running(
            hash_cenario=hash_cenario,
            id_execucao=effective_context.id_execucao,
            output_path=resolved_request.output_path,
        )

        try:
            snapshot_materialization = self._materialize_snapshot_if_requested(resolved_request, effective_context)
            bases = self.dataset_loader.load_raw_records(
                dataset_payloads.bases_payload,
                raw_cls=BaseBruta,
                default_origin="dataset.bases",
                id_field="id_base",
                contexto=effective_context,
            )
            pontos = self.dataset_loader.load_raw_records(
                dataset_payloads.pontos_payload,
                raw_cls=PontoBruto,
                default_origin="dataset.pontos",
                id_field="id_ponto",
                contexto=effective_context,
            )
            viaturas = self.dataset_loader.load_raw_records(
                dataset_payloads.viaturas_payload,
                raw_cls=ViaturaBruta,
                default_origin="dataset.viaturas",
                id_field="id_viatura",
                contexto=effective_context,
            )
            ordens = self.dataset_loader.load_raw_records(
                dataset_payloads.ordens_payload,
                raw_cls=OrdemBruta,
                default_origin="dataset.ordens",
                id_field="id_ordem",
                contexto=effective_context,
            )

            pipeline = PreparationPipeline(effective_context)
            preparation = pipeline.run(
                bases_brutas=bases,
                pontos_brutos=pontos,
                viaturas_brutas=viaturas,
                ordens_brutas=ordens,
            )
            provider = FallbackLogisticsMatrixProvider(
                effective_context,
                primary=PersistedSnapshotLogisticsMatrixProvider(
                    effective_context,
                    snapshot_dir=resolved_request.snapshot_dir,
                ),
                fallback=LogisticsMatrixBuilder(effective_context),
            )
            instance_builder = OptimizationInstanceBuilder(effective_context, matrix_provider=provider)
            instance_result = instance_builder.build(preparation)
            executor = self.executor_factory(effective_context, resolved_request)
            result = executor.run(preparation, instance_result)
            result = self._enrich_result(
                result,
                hash_cenario=hash_cenario,
                output_path=resolved_request.output_path,
                recovered_previous_context=recovered_previous_context,
            )
            repository.mark_completed(
                hash_cenario=hash_cenario,
                id_execucao=effective_context.id_execucao,
                output_path=resolved_request.output_path,
                result=result,
            )
            self._write_output_alias(resolved_request.output_path, result)
            final_state = repository.load_state(hash_cenario) or state
            return OrchestrationResult(
                resultado_planejamento=result,
                hash_cenario=hash_cenario,
                output_path=resolved_request.output_path,
                result_path=repository.result_json_path(hash_cenario),
                state_path=repository.state_path(hash_cenario),
                scenario_path=scenario_path,
                manifest_path=repository.manifest_path(),
                recovered_previous_context=recovered_previous_context,
                reused_cached_result=False,
                attempt_number=int(final_state["attempts"]),
                snapshot_materialization=snapshot_materialization,
            )
        except Exception as exc:
            repository.mark_failed(
                hash_cenario=hash_cenario,
                id_execucao=effective_context.id_execucao,
                output_path=resolved_request.output_path,
                error_message=str(exc),
            )
            raise

    def _resolve_request(self, request: DatasetPlanningRequest) -> DatasetPlanningRequest:
        dataset_dir = Path(request.dataset_dir)
        output_path = Path(request.output_path) if request.output_path else dataset_dir / "outputs" / "resultado-planejamento.json"
        snapshot_dir = Path(request.snapshot_dir) if request.snapshot_dir else dataset_dir / "logistics_snapshots"
        source_dir = Path(request.source_dir) if request.source_dir else dataset_dir / "logistics_sources"
        state_dir = Path(request.state_dir) if request.state_dir else output_path.parent / "executions"
        return replace(
            request,
            dataset_dir=dataset_dir,
            output_path=output_path,
            snapshot_dir=snapshot_dir,
            source_dir=source_dir,
            state_dir=state_dir,
        )

    def _materialize_snapshot_if_requested(
        self,
        request: DatasetPlanningRequest,
        contexto: ContextoExecucao,
    ) -> SnapshotMaterializationResult | None:
        if not request.materialize_snapshot:
            return None
        materializer = LogisticsSnapshotMaterializer(
            JsonFileLogisticsSnapshotSource(request.source_dir),
            FileSystemSnapshotRepository(request.snapshot_dir),
        )
        return materializer.materialize(contexto.data_operacao)

    def _build_hash_payload(
        self,
        dataset_payloads: LoadedDatasetPayloads,
        contexto: ContextoExecucao,
        request: DatasetPlanningRequest,
    ) -> dict[str, Any]:
        source_snapshot_payload = None
        persisted_snapshot_payload = None
        source_path = request.source_dir / f"{contexto.data_operacao.isoformat()}.json"
        snapshot_path = request.snapshot_dir / f"{contexto.data_operacao.isoformat()}.json"
        if request.materialize_snapshot:
            if source_path.exists():
                source_snapshot_payload = json.loads(source_path.read_text())
        elif snapshot_path.exists():
            persisted_snapshot_payload = json.loads(snapshot_path.read_text())

        return {
            "id_execucao": contexto.id_execucao,
            "data_operacao": contexto.data_operacao.isoformat(),
            "cutoff": contexto.cutoff.isoformat(),
            "versao_schema": contexto.versao_schema,
            "bases": dataset_payloads.bases_payload,
            "pontos": dataset_payloads.pontos_payload,
            "viaturas": dataset_payloads.viaturas_payload,
            "ordens": dataset_payloads.ordens_payload,
            "solver": {
                "max_iterations": request.max_iterations,
                "seed": request.seed,
                "collect_stats": request.collect_stats,
                "display": request.display,
                "service_policy": PlanningExecutor.SERVICE_POLICY_NAME,
            },
            "politicas_persistencia": {
                "materialize_snapshot": request.materialize_snapshot,
                "snapshot_source_payload": source_snapshot_payload,
                "snapshot_persisted_payload": persisted_snapshot_payload,
                "fallback_strategy": "haversine_v1",
            },
        }

    def _hash_cenario(self, payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return sha256(canonical.encode("utf-8")).hexdigest()

    def _write_output_alias(self, output_path: Path, result: ResultadoPlanejamento) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(serialize_value(result), indent=2, ensure_ascii=True) + "\n")

    def _enrich_result(
        self,
        result: ResultadoPlanejamento,
        *,
        hash_cenario: str,
        output_path: Path,
        recovered_previous_context: bool,
    ) -> ResultadoPlanejamento:
        eventos = list(result.eventos_auditoria)
        eventos.append(
            EventoAuditoria(
                id_evento=f"evt-orq-{hash_cenario[:12]}",
                tipo_evento=TipoEventoAuditoria.SAIDA,
                severidade=SeveridadeEvento.INFO,
                entidade_afetada="Orquestrador",
                id_entidade=result.id_execucao,
                regra_relacionada="orquestracao.idempotente",
                motivo="execucao diaria consolidada por hash de cenario estavel",
                timestamp_evento=result.log_planejamento.timestamp_referencia if result.log_planejamento else ensure_datetime(
                    serialize_value(result.data_operacao) + "T00:00:00+00:00",
                    "timestamp_evento",
                ),
                id_execucao=result.id_execucao,
                contexto_adicional={
                    "hash_cenario": hash_cenario,
                    "output_path": str(output_path),
                    "recovered_previous_context": recovered_previous_context,
                },
            )
        )
        hashes_cenario = dict(result.hashes_cenario)
        hashes_cenario["orquestracao"] = hash_cenario

        log_planejamento = result.log_planejamento
        if log_planejamento is not None:
            parametros = dict(log_planejamento.parametros_planejamento)
            parametros["hash_cenario_orquestracao"] = hash_cenario
            parametros["output_path"] = str(output_path)
            parametros["recovered_previous_context"] = recovered_previous_context
            log_planejamento = replace(
                log_planejamento,
                total_eventos=len(eventos),
                parametros_planejamento=parametros,
            )
        else:
            log_planejamento = LogPlanejamento(
                id_execucao=result.id_execucao,
                data_operacao=result.data_operacao,
                status_final=result.status_final,
                cutoff=ensure_datetime(serialize_value(result.data_operacao) + "T00:00:00+00:00", "cutoff"),
                timestamp_referencia=ensure_datetime(serialize_value(result.data_operacao) + "T00:00:00+00:00", "timestamp_referencia"),
                total_eventos=len(eventos),
                total_erros=len(result.erros),
                total_motivos_inviabilidade=len(result.motivos_inviabilidade),
                parametros_planejamento={
                    "hash_cenario_orquestracao": hash_cenario,
                    "output_path": str(output_path),
                    "recovered_previous_context": recovered_previous_context,
                },
            )

        relatorio = result.relatorio_planejamento
        if relatorio is not None:
            destaques = list(relatorio.destaques)
            marcador = "reexecucao_contexto_recuperado" if recovered_previous_context else "execucao_inicial_idempotente"
            if marcador not in destaques:
                destaques.append(marcador)
            relatorio = replace(
                relatorio,
                total_eventos_auditoria=len(eventos),
                destaques=tuple(destaques),
            )
        else:
            relatorio = RelatorioPlanejamento(
                id_execucao=result.id_execucao,
                data_operacao=result.data_operacao,
                status_final=result.status_final,
                total_ordens_atendidas=0,
                total_ordens_especiais_atendidas=0,
                total_ordens_nao_atendidas=result.resumo_operacional.total_ordens_nao_atendidas,
                total_ordens_excluidas=result.resumo_operacional.total_ordens_excluidas,
                total_ordens_canceladas=result.resumo_operacional.total_ordens_canceladas,
                total_viaturas_acionadas=0,
                total_eventos_auditoria=len(eventos),
                total_motivos_inviabilidade=len(result.motivos_inviabilidade),
                classes_processadas=tuple(sorted(hash for hash in result.hashes_cenario if hash != "orquestracao")),
                destaques=("execucao_inicial_idempotente",),
            )

        return replace(
            result,
            eventos_auditoria=tuple(eventos),
            hashes_cenario=hashes_cenario,
            log_planejamento=log_planejamento,
            relatorio_planejamento=relatorio,
        )

    def _default_executor(self, contexto: ContextoExecucao, request: DatasetPlanningRequest) -> PlanningExecutor:
        return PlanningExecutor(
            contexto,
            max_iterations=request.max_iterations,
            seed=request.seed,
            collect_stats=request.collect_stats,
            display=request.display,
        )

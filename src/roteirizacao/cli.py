from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from roteirizacao.application import (
    FallbackLogisticsMatrixProvider,
    FileSystemSnapshotRepository,
    JsonFileLogisticsSnapshotSource,
    LogisticsMatrixBuilder,
    LogisticsSnapshotMaterializer,
    OptimizationInstanceBuilder,
    PersistedSnapshotLogisticsMatrixProvider,
    PlanningExecutor,
    PreparationPipeline,
)
from roteirizacao.domain import BaseBruta, ContextoExecucao, MetadadoIngestao, OrdemBruta, PontoBruto, ViaturaBruta
from roteirizacao.domain.serialization import ensure_date, ensure_datetime, serialize_value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Interface operacional da roteirizacao de numerario")
    subparsers = parser.add_subparsers(dest="command", required=True)

    materialize = subparsers.add_parser("materialize-snapshot", help="Materializa um snapshot logistico bruto")
    materialize.add_argument("--date", required=True, dest="data_operacao")
    materialize.add_argument("--source-dir", default="data/logistics_sources")
    materialize.add_argument("--snapshot-dir", default="data/logistics_snapshots")
    materialize.set_defaults(handler=_handle_materialize_snapshot)

    planning = subparsers.add_parser("run-planning", help="Executa o planejamento a partir de um dataset local")
    planning.add_argument("--dataset-dir", required=True)
    planning.add_argument("--output", default=None)
    planning.add_argument("--snapshot-dir", default=None)
    planning.add_argument("--source-dir", default=None)
    planning.add_argument("--materialize-snapshot", action="store_true")
    planning.add_argument("--max-iterations", type=int, default=100)
    planning.add_argument("--seed", type=int, default=1)
    planning.set_defaults(handler=_handle_run_planning)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except Exception as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2


def _handle_materialize_snapshot(args: argparse.Namespace) -> int:
    data_operacao = ensure_date(args.data_operacao, "date")
    source_dir = Path(args.source_dir)
    snapshot_dir = Path(args.snapshot_dir)

    materializer = LogisticsSnapshotMaterializer(
        JsonFileLogisticsSnapshotSource(source_dir),
        FileSystemSnapshotRepository(snapshot_dir),
    )
    result = materializer.materialize(data_operacao)
    print(
        json.dumps(
            {
                "data_operacao": data_operacao.isoformat(),
                "snapshot_id": result.snapshot_id,
                "content_hash": result.content_hash,
                "snapshot_path": str(result.snapshot_path),
                "version_path": str(result.version_path),
                "manifest_path": str(result.manifest_path),
            },
            indent=2,
            ensure_ascii=True,
        )
    )
    return 0


def _handle_run_planning(args: argparse.Namespace) -> int:
    dataset_dir = Path(args.dataset_dir)
    contexto = _load_context(dataset_dir / "contexto.json")
    snapshot_dir = Path(args.snapshot_dir) if args.snapshot_dir else dataset_dir / "logistics_snapshots"
    source_dir = Path(args.source_dir) if args.source_dir else dataset_dir / "logistics_sources"
    output_path = Path(args.output) if args.output else dataset_dir / "outputs" / "resultado-planejamento.json"

    if args.materialize_snapshot:
        materializer = LogisticsSnapshotMaterializer(
            JsonFileLogisticsSnapshotSource(source_dir),
            FileSystemSnapshotRepository(snapshot_dir),
        )
        materializer.materialize(contexto.data_operacao)

    bases = _load_raw_records(
        dataset_dir / "bases.json",
        raw_cls=BaseBruta,
        default_origin="dataset.bases",
        id_field="id_base",
        default_timestamp=contexto.timestamp_referencia,
    )
    pontos = _load_raw_records(
        dataset_dir / "pontos.json",
        raw_cls=PontoBruto,
        default_origin="dataset.pontos",
        id_field="id_ponto",
        default_timestamp=contexto.timestamp_referencia,
    )
    viaturas = _load_raw_records(
        dataset_dir / "viaturas.json",
        raw_cls=ViaturaBruta,
        default_origin="dataset.viaturas",
        id_field="id_viatura",
        default_timestamp=contexto.timestamp_referencia,
    )
    ordens = _load_raw_records(
        dataset_dir / "ordens.json",
        raw_cls=OrdemBruta,
        default_origin="dataset.ordens",
        id_field="id_ordem",
        default_timestamp=contexto.timestamp_referencia,
    )

    provider = FallbackLogisticsMatrixProvider(
        contexto,
        primary=PersistedSnapshotLogisticsMatrixProvider(contexto, snapshot_dir=snapshot_dir),
        fallback=LogisticsMatrixBuilder(contexto),
    )
    pipeline = PreparationPipeline(contexto)
    preparation = pipeline.run(
        bases_brutas=bases,
        pontos_brutos=pontos,
        viaturas_brutas=viaturas,
        ordens_brutas=ordens,
    )
    builder = OptimizationInstanceBuilder(contexto, matrix_provider=provider)
    instance_result = builder.build(preparation)
    executor = PlanningExecutor(
        contexto,
        max_iterations=args.max_iterations,
        seed=args.seed,
    )
    result = executor.run(preparation, instance_result)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(serialize_value(result), indent=2, ensure_ascii=True) + "\n")
    print(
        json.dumps(
            {
                "dataset_dir": str(dataset_dir),
                "output": str(output_path),
                "status_final": result.status_final.value,
                "total_rotas": result.resumo_operacional.total_rotas,
                "total_ordens_planejadas": result.resumo_operacional.total_ordens_planejadas,
                "total_ordens_nao_atendidas": result.resumo_operacional.total_ordens_nao_atendidas,
                "total_erros": len(result.erros),
            },
            indent=2,
            ensure_ascii=True,
        )
    )
    return 0


def _load_context(path: Path) -> ContextoExecucao:
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("contexto.json deve conter um objeto JSON")
    return ContextoExecucao(
        id_execucao=str(payload["id_execucao"]),
        data_operacao=ensure_date(payload["data_operacao"], "data_operacao"),
        cutoff=ensure_datetime(payload["cutoff"], "cutoff"),
        timestamp_referencia=ensure_datetime(payload["timestamp_referencia"], "timestamp_referencia"),
        versao_schema=str(payload.get("versao_schema", "1.0")),
    )


def _load_raw_records(
    path: Path,
    *,
    raw_cls,
    default_origin: str,
    id_field: str,
    default_timestamp,
) -> list[Any]:
    payload = _load_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"{path.name} deve conter uma lista JSON")

    records: list[Any] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError(f"registro invalido em {path.name}")

        if "payload" in item:
            raw_payload = item["payload"]
            metadata_payload = item.get("metadado_ingestao", {})
        else:
            raw_payload = item
            metadata_payload = {}

        if not isinstance(raw_payload, dict):
            raise ValueError(f"payload invalido em {path.name}")
        if not isinstance(metadata_payload, dict):
            raise ValueError(f"metadado_ingestao invalido em {path.name}")

        metadado_ingestao = MetadadoIngestao(
            origem=str(metadata_payload.get("origem", default_origin)),
            timestamp_ingestao=ensure_datetime(
                metadata_payload.get("timestamp_ingestao", default_timestamp),
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


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"arquivo nao encontrado: {path}")
    return json.loads(path.read_text())


if __name__ == "__main__":
    raise SystemExit(main())

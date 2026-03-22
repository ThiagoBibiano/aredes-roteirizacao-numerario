from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from roteirizacao.application import (
    DailyPlanningOrchestrator,
    DatasetPlanningRequest,
    FileSystemSnapshotRepository,
    JsonFileLogisticsSnapshotSource,
    LogisticsSnapshotMaterializer,
)
from roteirizacao.domain.serialization import ensure_date


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
    planning.add_argument("--state-dir", default=None)
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
    orchestrator = DailyPlanningOrchestrator()
    orchestration = orchestrator.run(
        DatasetPlanningRequest(
            dataset_dir=Path(args.dataset_dir),
            output_path=Path(args.output) if args.output else None,
            snapshot_dir=Path(args.snapshot_dir) if args.snapshot_dir else None,
            source_dir=Path(args.source_dir) if args.source_dir else None,
            state_dir=Path(args.state_dir) if args.state_dir else None,
            materialize_snapshot=bool(args.materialize_snapshot),
            max_iterations=args.max_iterations,
            seed=args.seed,
        )
    )
    result = orchestration.resultado_planejamento

    print(
        json.dumps(
            {
                "dataset_dir": str(args.dataset_dir),
                "output": str(orchestration.output_path),
                "hash_cenario": orchestration.hash_cenario,
                "reused_cached_result": orchestration.reused_cached_result,
                "recovered_previous_context": orchestration.recovered_previous_context,
                "attempt_number": orchestration.attempt_number,
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


if __name__ == "__main__":
    raise SystemExit(main())

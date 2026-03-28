from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


UI_SETTINGS_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists())
DEFAULT_SETTINGS_FILE = UI_SETTINGS_DIR / "settings.toml"
LOCAL_SETTINGS_FILE = UI_SETTINGS_DIR / "settings.local.toml"
INLINE_FILENAME_MAP = {
    "contexto": "contexto.json",
    "bases": "bases.json",
    "pontos": "pontos.json",
    "viaturas": "viaturas.json",
    "ordens": "ordens.json",
    "snapshot_source": "snapshot_source.json",
}


@dataclass(slots=True, frozen=True)
class UiExecutionParametersSettings:
    materialize_snapshot: bool = False
    max_iterations: int = 100
    seed: int = 1
    collect_stats: bool = False
    display: bool = False


@dataclass(slots=True, frozen=True)
class UiDatasetSettings:
    dataset_dir: str = "data/fake_solution"
    output_path: str = ""
    snapshot_dir: str = ""
    source_dir: str = ""
    state_dir: str = ""


@dataclass(slots=True, frozen=True)
class UiInlineFilesSettings:
    contexto: str = ""
    bases: str = ""
    pontos: str = ""
    viaturas: str = ""
    ordens: str = ""
    snapshot_source: str = ""

    def as_path_mapping(self) -> dict[str, str]:
        return {
            INLINE_FILENAME_MAP["contexto"]: self.contexto,
            INLINE_FILENAME_MAP["bases"]: self.bases,
            INLINE_FILENAME_MAP["pontos"]: self.pontos,
            INLINE_FILENAME_MAP["viaturas"]: self.viaturas,
            INLINE_FILENAME_MAP["ordens"]: self.ordens,
            INLINE_FILENAME_MAP["snapshot_source"]: self.snapshot_source,
        }


@dataclass(slots=True, frozen=True)
class UiSettings:
    api_base_url: str
    default_mode: str
    auto_check_health: bool
    parameters: UiExecutionParametersSettings
    dataset: UiDatasetSettings
    inline_files: UiInlineFilesSettings
    sources: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class InlineSettingsLoadResult:
    documents: dict[str, bytes]
    configured_paths: dict[str, str]
    warnings: tuple[str, ...] = ()


def load_ui_settings(
    settings_files: tuple[Path, ...] | None = None,
) -> UiSettings:
    resolved_files = settings_files or default_settings_files()
    payload: dict[str, Any] = {}
    loaded_sources: list[str] = []
    for settings_file in resolved_files:
        if not settings_file.exists():
            continue
        with settings_file.open("rb") as handle:
            loaded_payload = tomllib.load(handle)
        payload = _deep_merge(payload, loaded_payload)
        loaded_sources.append(str(settings_file))
    settings = build_ui_settings(payload)
    return UiSettings(
        api_base_url=settings.api_base_url,
        default_mode=settings.default_mode,
        auto_check_health=settings.auto_check_health,
        parameters=settings.parameters,
        dataset=settings.dataset,
        inline_files=settings.inline_files,
        sources=tuple(loaded_sources),
    )


def build_ui_settings(payload: Mapping[str, Any] | None) -> UiSettings:
    root = dict(payload or {})
    execution = dict(root.get("execution") or {})
    parameters = dict(execution.get("parameters") or {})
    dataset = dict(execution.get("dataset") or {})
    inline = dict(execution.get("inline") or {})
    inline_files = dict(inline.get("files") or {})
    default_mode = str(execution.get("default_mode") or "dataset").strip() or "dataset"
    if default_mode not in {"inline", "dataset"}:
        default_mode = "dataset"
    return UiSettings(
        api_base_url=str(root.get("api_base_url") or "http://127.0.0.1:8000").strip() or "http://127.0.0.1:8000",
        default_mode=default_mode,
        auto_check_health=bool(execution.get("auto_check_health", False)),
        parameters=UiExecutionParametersSettings(
            materialize_snapshot=bool(parameters.get("materialize_snapshot", False)),
            max_iterations=max(1, int(parameters.get("max_iterations", 100) or 100)),
            seed=max(1, int(parameters.get("seed", 1) or 1)),
            collect_stats=bool(parameters.get("collect_stats", False)),
            display=bool(parameters.get("display", False)),
        ),
        dataset=UiDatasetSettings(
            dataset_dir=str(dataset.get("dataset_dir") or "data/fake_solution"),
            output_path=str(dataset.get("output_path") or ""),
            snapshot_dir=str(dataset.get("snapshot_dir") or ""),
            source_dir=str(dataset.get("source_dir") or ""),
            state_dir=str(dataset.get("state_dir") or ""),
        ),
        inline_files=UiInlineFilesSettings(
            contexto=str(inline_files.get("contexto") or ""),
            bases=str(inline_files.get("bases") or ""),
            pontos=str(inline_files.get("pontos") or ""),
            viaturas=str(inline_files.get("viaturas") or ""),
            ordens=str(inline_files.get("ordens") or ""),
            snapshot_source=str(inline_files.get("snapshot_source") or ""),
        ),
    )


def load_inline_documents_from_settings(settings: UiSettings) -> InlineSettingsLoadResult:
    documents: dict[str, bytes] = {}
    configured_paths: dict[str, str] = {}
    warnings: list[str] = []
    for filename, raw_path in settings.inline_files.as_path_mapping().items():
        resolved_path = str(raw_path).strip()
        if not resolved_path:
            continue
        configured_paths[filename] = resolved_path
        path = Path(resolved_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if not path.exists():
            warnings.append(f"Arquivo configurado no settings nao encontrado: {path}.")
            continue
        try:
            documents[filename] = path.read_bytes()
        except OSError as exc:
            warnings.append(f"Falha ao ler arquivo configurado no settings: {path} ({exc}).")
    return InlineSettingsLoadResult(
        documents=documents,
        configured_paths=configured_paths,
        warnings=tuple(warnings),
    )


def default_settings_files() -> tuple[Path, ...]:
    paths = [DEFAULT_SETTINGS_FILE, LOCAL_SETTINGS_FILE]
    extra = os.getenv("UI_STREAMLIT_SETTINGS_FILE", "").strip()
    if extra:
        paths.append(Path(extra))
    return tuple(paths)


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _deep_merge(dict(result[key]), value)
        else:
            result[key] = value
    return result

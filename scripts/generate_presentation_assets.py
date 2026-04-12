#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = PROJECT_ROOT / "notebook"
import sys

if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
if str(NOTEBOOK_DIR) not in sys.path:
    sys.path.insert(0, str(NOTEBOOK_DIR))

from solver_workbench_support import (
    compile_scenario,
    export_presentation_bundle,
    load_scenario_artifacts,
    route_sequences,
    run_scenario,
)


ASSETS_DIR = PROJECT_ROOT / "docs" / "apresentacao" / "assets"
GENERATED_DIR = ASSETS_DIR / "generated"
GIFS_DIR = ASSETS_DIR / "gifs"
BENCHMARK_OUTPUT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "operacao_sob_pressao_subsample"


def main() -> int:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    GIFS_DIR.mkdir(parents=True, exist_ok=True)

    scenario_name = "operacao_sob_pressao"
    compile_scenario(scenario_name)
    artifacts = load_scenario_artifacts(scenario_name)
    orchestration = run_scenario(scenario_name, max_iterations=500, seed=1, materialize_snapshot=True)
    bundle = export_presentation_bundle(orchestration, artifacts, output_dir=GENERATED_DIR, with_basemap=False)

    _generate_route_table_png(orchestration, GENERATED_DIR / "operacao_sob_pressao_rotas_tabela.png")
    _generate_before_after_png(
        before_path=Path(bundle["base_map"]),
        after_path=Path(bundle["solution_map"]),
        output_path=GENERATED_DIR / "operacao_sob_pressao_antes_depois.png",
    )
    _generate_solution_gif(
        before_path=Path(bundle["base_map"]),
        after_path=Path(bundle["solution_map"]),
        output_path=GIFS_DIR / "rede-base-para-solucao.gif",
    )

    plots_dir = BENCHMARK_OUTPUT_DIR / "plots"
    _copy_benchmark_plots(plots_dir)
    _generate_benchmark_panel(plots_dir, GENERATED_DIR / "benchmark_comparison_panel.png")
    _generate_benchmark_gif(
        plots_dir=plots_dir,
        output_path=GIFS_DIR / "benchmark-escala.gif",
    )
    print(GENERATED_DIR)
    print(GIFS_DIR)
    return 0


def _generate_route_table_png(orchestration, output_path: Path) -> None:
    import matplotlib.pyplot as plt

    sequences = route_sequences(orchestration)
    headers = ["Rota", "Viatura", "Classe", "Inicio", "Fim", "Sequencia"]
    rows = []
    for sequence in sequences:
        rows.append(
            [
                sequence["id_rota"].rsplit("-", 1)[-1],
                sequence["id_viatura"],
                sequence["classe_operacional"],
                sequence["inicio_previsto"][11:16],
                sequence["fim_previsto"][11:16],
                sequence["sequencia"],
            ]
        )

    figure, axis = plt.subplots(figsize=(16, 3.6 + max(len(rows), 1) * 0.45))
    axis.axis("off")
    table = axis.table(cellText=rows, colLabels=headers, loc="center", cellLoc="left")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.0, 1.5)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#143642")
            cell.set_text_props(color="white", weight="bold")
        else:
            cell.set_facecolor("#f8fafc" if row % 2 else "#e8f1f2")
    figure.tight_layout()
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def _generate_before_after_png(*, before_path: Path, after_path: Path, output_path: Path) -> None:
    before = Image.open(before_path).convert("RGB")
    after = Image.open(after_path).convert("RGB")
    target_height = max(before.height, after.height)
    before = _resize_to_height(before, target_height)
    after = _resize_to_height(after, target_height)

    canvas = Image.new("RGB", (before.width + after.width + 80, target_height + 110), "#f7fafc")
    draw = ImageDraw.Draw(canvas)
    font_title = ImageFont.load_default()
    canvas.paste(before, (20, 70))
    canvas.paste(after, (before.width + 60, 70))
    draw.text((20, 24), "Antes: rede-base", fill="#143642", font=font_title)
    draw.text((before.width + 60, 24), "Depois: rede escolhida pelo solver", fill="#143642", font=font_title)
    canvas.save(output_path)


def _generate_solution_gif(*, before_path: Path, after_path: Path, output_path: Path) -> None:
    before = Image.open(before_path).convert("P", palette=Image.ADAPTIVE)
    after = Image.open(after_path).convert("P", palette=Image.ADAPTIVE)
    frames = [before, before, after, after]
    frames[0].save(output_path, save_all=True, append_images=frames[1:], duration=[700, 700, 1100, 1100], loop=0)


def _generate_benchmark_panel(plots_dir: Path, output_path: Path) -> None:
    runtime = Image.open(plots_dir / "painel_tendencias.png").convert("RGB")
    objective = Image.open(plots_dir / "painel_dispersao.png").convert("RGB")
    service = Image.open(plots_dir / "erro_relativo_fo_pct.png").convert("RGB")
    vehicles = Image.open(plots_dir / "taxa_viabilidade_pulp.png").convert("RGB")
    width = max(runtime.width, objective.width)
    height = max(runtime.height, objective.height)
    runtime = runtime.resize((width, height))
    objective = objective.resize((width, height))
    service = service.resize((width, height))
    vehicles = vehicles.resize((width, height))

    canvas = Image.new("RGB", (width * 2 + 60, height * 2 + 60), "#ffffff")
    canvas.paste(runtime, (20, 20))
    canvas.paste(objective, (width + 40, 20))
    canvas.paste(service, (20, height + 40))
    canvas.paste(vehicles, (width + 40, height + 40))
    canvas.save(output_path)


def _generate_benchmark_gif(*, plots_dir: Path, output_path: Path) -> None:
    trends = Image.open(plots_dir / "painel_tendencias.png").convert("P", palette=Image.ADAPTIVE)
    dispersion = Image.open(plots_dir / "painel_dispersao.png").convert("P", palette=Image.ADAPTIVE)
    error = Image.open(plots_dir / "erro_relativo_fo_pct.png").convert("P", palette=Image.ADAPTIVE)
    full_run = Image.open(plots_dir / "rodada_exaustiva_100_rotas.png").convert("P", palette=Image.ADAPTIVE)
    frames = [trends, dispersion, error, full_run]
    frames[0].save(output_path, save_all=True, append_images=frames[1:], duration=[900, 900, 900, 1100], loop=0)


def _copy_benchmark_plots(plots_dir: Path) -> None:
    copies = {
        "painel_tendencias.png": GENERATED_DIR / "benchmark_painel_tendencias.png",
        "painel_dispersao.png": GENERATED_DIR / "benchmark_painel_dispersao.png",
        "erro_relativo_fo_pct.png": GENERATED_DIR / "benchmark_erro_relativo_fo.png",
        "taxa_viabilidade_pulp.png": GENERATED_DIR / "benchmark_taxa_viabilidade_pulp.png",
        "rodada_exaustiva_100_rotas.png": GENERATED_DIR / "benchmark_rodada_exaustiva_100_rotas.png",
    }
    for source_name, target_path in copies.items():
        shutil.copyfile(plots_dir / source_name, target_path)


def _resize_to_height(image: Image.Image, height: int) -> Image.Image:
    if image.height == height:
        return image
    width = int(image.width * (height / image.height))
    return image.resize((width, height))


if __name__ == "__main__":
    raise SystemExit(main())

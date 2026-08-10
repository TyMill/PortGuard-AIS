"""Command-line interface."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from portguard_ais.config import PortGuardConfig
from portguard_ais.evaluation.benchmark import run_article_benchmark, run_synthetic_benchmark
from portguard_ais.evaluation.synthetic import article_scenarios, synthetic_scenarios
from portguard_ais.ingestion.readers import read_ais_csv
from portguard_ais.pipeline import PortGuardPipeline
from portguard_ais.preprocessing.cleaning import clean_ais_frame
from portguard_ais.reporting import write_html_report
from portguard_ais.serialization import export_bundle, write_csv

app = typer.Typer(no_args_is_help=True, help="Explainable AIS collision-risk analytics.")
console = Console()


@app.command()
def validate(
    input_csv: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
) -> None:
    """Validate and clean an AIS CSV without running risk assessment."""
    _, report = clean_ais_frame(read_ais_csv(input_csv), PortGuardConfig().input)
    console.print_json(json.dumps(report.model_dump(mode="json")))


@app.command()
def assess(
    input_csv: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")] = Path("outputs"),
) -> None:
    """Assess all snapshots and export the standard result bundle."""
    pipeline = PortGuardPipeline()
    result = pipeline.process_csv(input_csv)
    paths = export_bundle(
        result.assessments,
        result.alerts,
        result.near_misses,
        output_dir,
        trends=result.trends,
        hotspots=result.hotspots,
    )
    paths["html_report"] = write_html_report(result, output_dir / "report.html")

    table = Table(title="PortGuard-AIS processing summary")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Clean AIS rows", str(result.validation.output_rows))
    table.add_row("Assessments", str(len(result.assessments)))
    table.add_row("Emitted alerts", str(sum(alert.emitted for alert in result.alerts)))
    table.add_row("Near misses", str(len(result.near_misses)))
    table.add_row("Hotspot cells", str(len(result.hotspots)))
    console.print(table)
    for name, path in paths.items():
        console.print(f"[green]{name}[/green]: {path}")


@app.command(name="near-misses")
def near_misses(
    input_csv: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("near_misses.csv"),
) -> None:
    """Mine and export historical near-miss candidates."""
    result = PortGuardPipeline().process_csv(input_csv)
    write_csv(result.near_misses, output)
    console.print(f"Exported {len(result.near_misses)} events to {output}")


@app.command()
def synthetic(
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("synthetic_ais.csv"),
    steps: Annotated[int, typer.Option(min=2)] = 8,
) -> None:
    """Generate deterministic synthetic AIS scenarios."""
    output.parent.mkdir(parents=True, exist_ok=True)
    synthetic_scenarios(steps=steps).to_csv(output, index=False)
    console.print(f"Generated synthetic AIS data: {output}")


@app.command()
def benchmark(
    steps: Annotated[int, typer.Option(min=2)] = 12,
) -> None:
    """Run the deterministic end-to-end synthetic benchmark."""
    result = run_synthetic_benchmark(steps=steps)
    console.print_json(json.dumps(result.__dict__))


@app.command(name="article-data")
def article_data(
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("article_scenarios.csv"),
    steps: Annotated[int, typer.Option(min=2)] = 12,
    interval_seconds: Annotated[int, typer.Option(min=1)] = 30,
) -> None:
    """Generate isolated Rule 14, Rule 15 and Rule 13 demonstration scenarios."""
    output.parent.mkdir(parents=True, exist_ok=True)
    article_scenarios(steps=steps, interval_seconds=interval_seconds).to_csv(output, index=False)
    console.print(f"Generated SoftwareX article scenarios: {output}")


@app.command(name="article-benchmark")
def article_benchmark(
    steps: Annotated[int, typer.Option(min=2)] = 12,
    interval_seconds: Annotated[int, typer.Option(min=1)] = 30,
) -> None:
    """Run the deterministic Rule 14/15/13 SoftwareX benchmark."""
    result = run_article_benchmark(steps=steps, interval_seconds=interval_seconds)
    console.print_json(json.dumps(result.to_dict()))


if __name__ == "__main__":
    app()

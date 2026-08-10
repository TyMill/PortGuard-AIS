from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from portguard_ais.cli import app
from portguard_ais.evaluation.synthetic import synthetic_scenarios

runner = CliRunner()


def test_validate_command(tmp_path: Path) -> None:
    path = tmp_path / "ais.csv"
    synthetic_scenarios(steps=2).to_csv(path, index=False)
    result = runner.invoke(app, ["validate", str(path)])
    assert result.exit_code == 0
    assert '"output_rows": 8' in result.stdout


def test_assess_command(tmp_path: Path) -> None:
    path = tmp_path / "ais.csv"
    output = tmp_path / "out"
    synthetic_scenarios(steps=3).to_csv(path, index=False)
    result = runner.invoke(app, ["assess", str(path), "--output-dir", str(output)])
    assert result.exit_code == 0
    assert (output / "assessments.json").is_file()


def test_article_data_command(tmp_path: Path) -> None:
    path = tmp_path / "article.csv"
    result = runner.invoke(
        app,
        ["article-data", "--output", str(path), "--steps", "4", "--interval-seconds", "30"],
    )
    assert result.exit_code == 0
    assert path.is_file()
    assert len(pd.read_csv(path)) == 24


def test_article_benchmark_command() -> None:
    result = runner.invoke(
        app,
        ["article-benchmark", "--steps", "4", "--interval-seconds", "30"],
    )
    assert result.exit_code == 0
    assert '"unique_vessels": 6' in result.stdout
    assert '"overtaking"' in result.stdout

#!/usr/bin/env bash
set -Eeuo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3.13}"
VENV_DIR="${VENV_DIR:-.venv}"

echo "==> Python"
"${PYTHON_BIN}" --version

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "==> Creating virtual environment"
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,viz]"

echo "==> Ruff format"
python -m ruff format src tests examples
python -m ruff format --check src tests examples

echo "==> Ruff lint"
python -m ruff check src tests examples

echo "==> mypy strict"
python -m mypy src/portguard_ais

echo "==> Tests"
python -m pytest

echo "==> Generate article dataset"
portguard-ais article-data --steps 12 --interval-seconds 30 --output article_run_v1/cli_article_scenarios.csv

echo "==> Validate article dataset"
portguard-ais validate article_run_v1/cli_article_scenarios.csv | tee article_run_v1/cli_validation.txt

echo "==> Run full CLI assessment"
portguard-ais assess article_run_v1/cli_article_scenarios.csv --output-dir article_run_v1/cli_outputs \
  | tee article_run_v1/cli_assessment.txt

echo "==> Article benchmark"
portguard-ais article-benchmark --steps 12 --interval-seconds 30 \
  | tee article_run_v1/cli_article_benchmark.json

echo "==> Generate SoftwareX reproducibility pack"
python examples/softwarex_article_run.py | tee article_run_v1/article_run_console.txt

echo "==> Build"
python -m build

echo "==> Dependency audit"
python -m pip_audit

echo
echo "============================================================"
echo "PORTGUARD-AIS SOFTWAREX ARTICLE RUN COMPLETED"
echo "============================================================"
echo "Use: article_run_v1/softwarex_article_summary.json"
echo "Use: article_run_v1/outputs/softwarex_scenario_summary.csv"
echo "Use: article_run_v1/figures/*.png"

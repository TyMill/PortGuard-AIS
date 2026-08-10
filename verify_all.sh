#!/usr/bin/env bash
set -Eeuo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3.13}"
VENV_DIR="${VENV_DIR:-.venv_verify}"

printf '\n============================================================\n'
printf ' PortGuard-AIS 1.0.0 - CLEAN VERIFICATION\n'
printf '============================================================\n\n'

"${PYTHON_BIN}" --version
"${PYTHON_BIN}" - <<'PY'
import sys
assert sys.version_info >= (3, 13), sys.version
print("Python >= 3.13: PASS")
PY

rm -rf "${VENV_DIR}"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,viz]"

printf '\n==> Ruff format check\n'
python -m ruff format --check src tests

printf '\n==> Ruff lint\n'
python -m ruff check src tests

printf '\n==> mypy strict\n'
python -m mypy src/portguard_ais

printf '\n==> pytest + branch coverage\n'
python -m pytest

printf '\n==> CLI smoke test\n'
portguard-ais --help >/dev/null

printf '\n==> Deterministic SoftwareX benchmark\n'
rm -rf article_run_verify
mkdir -p article_run_verify
portguard-ais article-data --steps 12 --output article_run_verify/article_scenarios.csv
portguard-ais article-benchmark --steps 12 | tee article_run_verify/article_benchmark.txt

printf '\n==> Full SoftwareX artifact generation\n'
bash scripts/run_softwarex_article.sh

printf '\n==> Build wheel + sdist\n'
rm -rf dist build
python -m build

printf '\n==> Dependency audit\n'
python -m pip_audit

printf '\n==> Clean wheel installation\n'
deactivate
rm -rf .venv_wheel_verify
"${PYTHON_BIN}" -m venv .venv_wheel_verify
# shellcheck disable=SC1091
source .venv_wheel_verify/bin/activate
python -m pip install --upgrade pip
WHEEL="$(find dist -maxdepth 1 -name 'portguard_ais-1.0.0-*.whl' -print -quit)"
if [[ -z "${WHEEL}" ]]; then
  echo "Wheel not found in dist/" >&2
  exit 1
fi
python -m pip install "${WHEEL}[viz]"
python - <<'PY'
import portguard_ais
assert portguard_ais.__version__ == "1.0.0"
print("Wheel import/version: PASS")
PY
portguard-ais article-benchmark --steps 12 | tee article_run_verify/wheel_article_benchmark.txt

printf '\n============================================================\n'
printf ' PORTGUARD-AIS 1.0.0 - ALL VERIFICATION STEPS PASSED\n'
printf '============================================================\n'

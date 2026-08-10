# PortGuard-AIS

[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg)](https://docs.astral.sh/ruff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**PortGuard-AIS** is a modular Python 3.13 framework for explainable collision-risk
assessment, vessel-encounter classification, near-miss mining, and stateful alerts from AIS data.
It is intended for restricted port waters, approaches, anchorages, and other traffic-dense areas.

## Scientific scope

PortGuard-AIS answers four operational questions:

1. Which vessel pairs are on potentially conflicting motion vectors?
2. What encounter geometry is present and what COLREG context applies?
3. How severe and how immediate is the risk?
4. Why was an alert emitted, suppressed, escalated, or resolved?

The project deliberately **does not design fairways, generate routes, optimize waterways,
create waypoints, or prescribe autonomous avoidance trajectories**.

## Features

- validated AIS input model, configurable cleaning and kinematic anomaly detection;
- snapshot and historical processing;
- pairwise spatial pre-filtering;
- CPA/TCPA and relative-motion geometry;
- head-on, crossing, overtaking, being-overtaken, parallel and indeterminate classes;
- rule-context mapping for COLREG Rules 13–17;
- speed- and length-aware elliptical vessel domain;
- transparent multi-component collision-risk score;
- alert lifecycle with hysteresis, persistence, cooldown and deduplication;
- explicit machine-readable rationale for every assessment;
- historical near-miss event mining, risk trends and spatial hotspot aggregation;
- CSV, JSON, GeoJSON and standalone HTML reporting;
- Typer CLI, MkDocs documentation, strict mypy, Ruff, pytest and GitHub Actions.

## Installation

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[viz]"
```

For development:

```bash
python -m pip install -e ".[dev,viz]"
pre-commit install
make quality
```

Using `uv`:

```bash
uv sync --all-extras
uv run portguard-ais validate examples/data/sample_ais.csv
uv run portguard-ais assess examples/data/sample_ais.csv --output-dir outputs
```

## Python API

```python
from portguard_ais.config import PortGuardConfig
from portguard_ais.pipeline import PortGuardPipeline

pipeline = PortGuardPipeline(PortGuardConfig())
result = pipeline.process_csv("examples/data/sample_ais.csv")

print(result.assessments[0].model_dump(mode="json"))
```

## CLI

```bash
portguard-ais validate INPUT.csv
portguard-ais assess INPUT.csv --output-dir outputs
portguard-ais near-misses INPUT.csv --output outputs/near_misses.csv
portguard-ais synthetic --output examples/data/generated_scenarios.csv
portguard-ais benchmark --steps 12
```

## Input schema

Required columns:

| Column | Meaning | Unit |
|---|---|---|
| `timestamp` | timezone-aware observation time | ISO 8601 |
| `mmsi` | Maritime Mobile Service Identity | integer |
| `lat` | latitude | decimal degrees |
| `lon` | longitude | decimal degrees |
| `sog` | speed over ground | knots |
| `cog` | course over ground | degrees, true |

Optional columns include `heading`, `rot`, `length_m`, `beam_m`, `vessel_type`,
`position_accuracy_m`, and `source`.

## Repository quality gates

```bash
make format-check
make lint
make typecheck
make test
make audit
make build
```

## Safety notice

PortGuard-AIS is research and decision-support software. It is not certified navigational
equipment and must not replace COLREG-compliant watchkeeping, VTS procedures, bridge systems,
or the judgement of qualified maritime personnel.

## License

MIT. See [LICENSE](LICENSE).

## SoftwareX reproducibility suite

The publication-oriented benchmark is intentionally separate from the legacy four-vessel
regression dataset. It contains three spatially isolated and physically consistent encounter
pairs so that each expected geometry can be evaluated without cross-scenario pairing:

- `head-on` - reciprocal courses, COLREG Rule 14 context;
- `crossing` - target on the own vessel's starboard side, Rule 15 context;
- `overtaking` - faster own vessel approaching from abaft the target's beam, Rule 13 context.

Generate the dataset and compact benchmark directly from the CLI:

```bash
portguard-ais article-data --steps 12 --interval-seconds 30 --output article_scenarios.csv
portguard-ais article-benchmark --steps 12 --interval-seconds 30
```

Generate the complete SoftwareX evidence pack, including CSV/JSON/GeoJSON exports, the HTML
report, manuscript-ready scenario table, encounter figures and the stateful risk timeline:

```bash
python examples/softwarex_article_run.py
```

For a clean development environment that also executes Ruff, strict mypy, pytest, package build
and dependency audit, use:

```bash
bash scripts/run_softwarex_article.sh
```

The reference run is written to `article_run_v1/`. Classification consistency reported by this
suite is a deterministic regression check against controlled scenario geometry; it is **not** a
claim of real-world classifier accuracy.

# Changelog

All notable changes are documented here.

## 1.0.0 — 2026-08-03

### SoftwareX article reproducibility pack - 2026-08-10

- Added isolated, physically consistent Rule 14 head-on, Rule 15 crossing and Rule 13 overtaking scenarios.
- Added an article-specific benchmark with per-scenario classification consistency, CPA/TCPA, alert and near-miss summaries.
- Added publication-oriented trajectory/CPA figures and an alert-aware risk timeline.
- Added manuscript-ready CSV/JSON evidence generation and input SHA-256 recording.
- Added `article-data` and `article-benchmark` CLI commands and an end-to-end SoftwareX run script.
- Preserved the original four-vessel synthetic dataset as a regression fixture.

- Production-oriented Python 3.13 package with `src` layout.
- Validated AIS observation and assessment models.
- Cleaning, deduplication, resampling and interpolation utilities.
- Relative-motion, CPA/TCPA and dynamic vessel-domain calculations.
- Encounter classification and COLREG Rules 13–17 context.
- Explainable multi-component risk model.
- Stateful alert lifecycle with persistence, hysteresis and cooldown.
- Historical near-miss mining, ranking and multi-vessel conflict grouping.
- CSV, JSON and GeoJSON export.
- CLI, synthetic scenarios, MkDocs documentation and examples.
- Ruff, mypy, pytest coverage gate, pre-commit, dependency audit and CI workflows.

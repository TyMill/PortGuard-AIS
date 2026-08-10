# Reproducibility

- Python version is constrained to 3.13 or newer.
- CI resolves the declared dependency ranges on Python 3.13; release environments may additionally generate and retain an `uv.lock`.
- The legacy synthetic regression dataset is preserved for backwards-compatible tests.
- The SoftwareX article suite adds isolated Rule 14 head-on, Rule 15 crossing and Rule 13 overtaking scenarios.
- Article trajectories are generated from SOG/COG and elapsed time rather than arbitrary coordinate increments.
- The article runner records a SHA-256 digest of the exact input CSV and writes all numerical values to JSON and CSV before they are used in a manuscript.
- Unit and integration tests enforce an 85% branch-aware coverage floor.
- Ruff, strict mypy, package build and strict MkDocs build run in CI.
- Dependency audit runs for pushes, pull requests and weekly schedules.

A complete publication run is available through:

```bash
bash scripts/run_softwarex_article.sh
```

The lighter artifact-only command is:

```bash
python examples/softwarex_article_run.py
```

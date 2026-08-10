# SoftwareX benchmark

The article benchmark is designed for reproducibility rather than ecological realism. It uses
three deterministic, physically consistent AIS encounter pairs located in separate latitude bands.
The default 6 NM candidate-pair filter therefore produces exactly one intended pair per scenario
and no cross-scenario interactions.

| Scenario | Expected class | COLREG context | Design |
|---|---|---|---|
| Head-on | `head-on` | Rule 14 | Reciprocal east-west courses |
| Crossing | `crossing-starboard` | Rule 15 | Eastbound own vessel, northbound target |
| Overtaking | `overtaking` | Rule 13 | Faster own vessel closes from abaft the target's beam |

The trajectories are generated from declared SOG/COG and elapsed time using the same local-plane
scale convention used in PortGuard-AIS geometry. This avoids a mismatch between reported AIS
kinematics and synthetic positions.

## Generate the input

```bash
portguard-ais article-data --steps 12 --interval-seconds 30 --output article_scenarios.csv
```

## Run the benchmark

```bash
portguard-ais article-benchmark --steps 12 --interval-seconds 30
```

## Generate publication artifacts

```bash
python examples/softwarex_article_run.py
```

This produces `article_run_v1/` with:

- the exact input CSV and SHA-256 digest;
- complete assessment, alert, near-miss, trend and hotspot exports;
- a standalone HTML report;
- `softwarex_scenario_summary.csv` for manuscript tables;
- one trajectory/CPA figure for each scenario;
- a stateful risk timeline for the head-on scenario;
- `softwarex_article_summary.json` containing the exact values used in the manuscript.

## Interpretation boundary

`classification_consistency` is computed only for the converging phase of each controlled scenario
and compares the rule-based classifier with the scenario definition. A value of 1.0 demonstrates
internal deterministic consistency for these synthetic cases. It must not be presented as external
accuracy, generalization performance, or navigational safety effectiveness.

# CLI

```bash
portguard-ais validate data.csv
portguard-ais assess data.csv --output-dir outputs
portguard-ais near-misses data.csv --output events.csv
portguard-ais synthetic --output synthetic.csv --steps 12
portguard-ais benchmark --steps 12
portguard-ais article-data --output article_scenarios.csv --steps 12 --interval-seconds 30
portguard-ais article-benchmark --steps 12 --interval-seconds 30
```

The assessment command exports assessments, alerts and near misses in both machine-readable and
analysis-friendly formats. The `article-*` commands operate on the isolated deterministic
SoftwareX scenario suite and are intended for reproducibility and regression testing.

# Architecture

```text
AIS CSV / DataFrame
        │
        ▼
ingestion → cleaning → optional resampling
        │
        ▼
timestamp snapshots → candidate pair pre-filter
        │
        ▼
relative motion → encounter class → ship domain → risk score → COLREG context
        │
        ├── assessment export
        ├── stateful alert engine
        └── historical near-miss miner
```

Modules are separated by responsibility so that future statistical or learned components can be
benchmarked without replacing input validation, state management or explainability.

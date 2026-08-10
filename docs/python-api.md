# Python API

```python
from portguard_ais import PortGuardConfig, PortGuardPipeline

config = PortGuardConfig()
pipeline = PortGuardPipeline(config)
result = pipeline.process_csv("ais.csv")
```

For streaming prototypes, validate observations externally and call `process_snapshot()` with one
common timestamp. The alert state machine remains attached to the pipeline instance.

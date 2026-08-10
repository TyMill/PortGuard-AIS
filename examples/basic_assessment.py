from pathlib import Path

from portguard_ais.pipeline import PortGuardPipeline
from portguard_ais.serialization import export_bundle

result = PortGuardPipeline().process_csv(Path("examples/data/sample_ais.csv"))
export_bundle(
    result.assessments,
    result.alerts,
    result.near_misses,
    "outputs",
    trends=result.trends,
    hotspots=result.hotspots,
)
print(f"assessments={len(result.assessments)}, near_misses={len(result.near_misses)}")

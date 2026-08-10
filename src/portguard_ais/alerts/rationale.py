"""Deterministic, machine-readable alert rationale."""

from portguard_ais.enums import EncounterType, RiskLevel
from portguard_ais.models import DomainAssessment, RelativeMotion, RiskComponents


def build_rationale(
    encounter_type: EncounterType,
    level: RiskLevel,
    motion: RelativeMotion,
    domain: DomainAssessment,
    components: RiskComponents,
) -> tuple[str, ...]:
    """Explain the principal physical and model factors behind an assessment."""
    reasons = [f"encounter geometry classified as {encounter_type.value}"]
    if not motion.converging:
        reasons.append("relative motion is not converging")
    if motion.tcpa_min <= 10.0 and motion.converging:
        reasons.append("closest point of approach is expected within 10 minutes")
    if motion.dcpa_nm < 0.5:
        reasons.append("predicted closest passing distance is below 0.5 nautical miles")
    if motion.current_distance_nm < 1.0:
        reasons.append("current separation is below 1 nautical mile")
    if domain.violated:
        reasons.append("predicted CPA enters the configured own-vessel domain")
    dominant_name, dominant_value = max(
        components.model_dump().items(),
        key=lambda item: item[1],
    )
    reasons.append(f"dominant normalized risk component is {dominant_name} ({dominant_value:.3f})")
    if level in {RiskLevel.WARNING, RiskLevel.CRITICAL}:
        reasons.append(f"combined score exceeds the {level.value} threshold")
    return tuple(reasons)

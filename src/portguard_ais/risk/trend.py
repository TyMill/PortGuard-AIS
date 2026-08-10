"""Risk-trend estimation across repeated assessments."""

from collections.abc import Sequence

from portguard_ais.enums import RiskTrend
from portguard_ais.models import EncounterAssessment, RiskTrendAssessment


def estimate_risk_trend(
    assessments: Sequence[EncounterAssessment],
    stable_slope_per_min: float = 0.002,
) -> RiskTrendAssessment:
    """Estimate an ordinary least-squares score slope over elapsed minutes."""
    if stable_slope_per_min < 0.0:
        raise ValueError("stable_slope_per_min cannot be negative")
    if not assessments:
        raise ValueError("at least one assessment is required")

    ordered = sorted(assessments, key=lambda item: item.timestamp)
    encounter_ids = {item.encounter_id for item in ordered}
    if len(encounter_ids) != 1:
        raise ValueError("all assessments must belong to one encounter")

    if len(ordered) < 2:
        return RiskTrendAssessment(
            encounter_id=ordered[0].encounter_id,
            trend=RiskTrend.INSUFFICIENT,
            slope_per_min=0.0,
            score_delta=0.0,
            observation_count=1,
        )

    start = ordered[0].timestamp
    x = [(item.timestamp - start).total_seconds() / 60.0 for item in ordered]
    y = [item.risk_score for item in ordered]
    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)
    denominator = sum((value - x_mean) ** 2 for value in x)
    slope = (
        0.0
        if denominator == 0.0
        else sum(
            (x_value - x_mean) * (y_value - y_mean) for x_value, y_value in zip(x, y, strict=True)
        )
        / denominator
    )

    if slope > stable_slope_per_min:
        trend = RiskTrend.INCREASING
    elif slope < -stable_slope_per_min:
        trend = RiskTrend.DECREASING
    else:
        trend = RiskTrend.STABLE

    return RiskTrendAssessment(
        encounter_id=ordered[0].encounter_id,
        trend=trend,
        slope_per_min=round(slope, 6),
        score_delta=round(y[-1] - y[0], 6),
        observation_count=len(ordered),
    )

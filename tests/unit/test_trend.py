from datetime import UTC, datetime

import pytest

from portguard_ais.enums import RiskTrend
from portguard_ais.evaluation.synthetic import synthetic_scenarios
from portguard_ais.pipeline import PortGuardPipeline
from portguard_ais.risk.trend import estimate_risk_trend


def test_increasing_risk_trend() -> None:
    result = PortGuardPipeline().process_frame(synthetic_scenarios(steps=3))
    base = result.assessments[0]
    sequence = [
        base.model_copy(
            update={"timestamp": datetime(2026, 8, 3, 12, 0, tzinfo=UTC), "risk_score": 0.2}
        ),
        base.model_copy(
            update={"timestamp": datetime(2026, 8, 3, 12, 1, tzinfo=UTC), "risk_score": 0.5}
        ),
        base.model_copy(
            update={"timestamp": datetime(2026, 8, 3, 12, 2, tzinfo=UTC), "risk_score": 0.8}
        ),
    ]
    trend = estimate_risk_trend(sequence)
    assert trend.trend == RiskTrend.INCREASING
    assert trend.slope_per_min > 0


def test_single_observation_is_insufficient() -> None:
    base = PortGuardPipeline().process_frame(synthetic_scenarios(steps=2)).assessments[0]
    assert estimate_risk_trend([base]).trend == RiskTrend.INSUFFICIENT


def test_mixed_encounter_ids_are_rejected() -> None:
    base = PortGuardPipeline().process_frame(synthetic_scenarios(steps=2)).assessments[0]
    other = base.model_copy(update={"encounter_id": "different"})
    with pytest.raises(ValueError):
        estimate_risk_trend([base, other])


def test_invalid_stability_threshold_is_rejected() -> None:
    base = PortGuardPipeline().process_frame(synthetic_scenarios(steps=2)).assessments[0]
    with pytest.raises(ValueError):
        estimate_risk_trend([base], stable_slope_per_min=-1)

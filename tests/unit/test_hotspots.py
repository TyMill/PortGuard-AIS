import pytest

from portguard_ais.evaluation.synthetic import synthetic_scenarios
from portguard_ais.near_miss.hotspots import aggregate_hotspots
from portguard_ais.pipeline import PortGuardPipeline


def test_hotspots_are_sorted_by_risk() -> None:
    assessments = PortGuardPipeline().process_frame(synthetic_scenarios(steps=5)).assessments
    hotspots = aggregate_hotspots(assessments, minimum_score=0.2, cell_size_deg=0.01)
    assert hotspots
    assert hotspots[0].maximum_risk_score >= hotspots[-1].maximum_risk_score


def test_invalid_hotspot_parameters() -> None:
    with pytest.raises(ValueError):
        aggregate_hotspots([], minimum_score=2)
    with pytest.raises(ValueError):
        aggregate_hotspots([], cell_size_deg=0)

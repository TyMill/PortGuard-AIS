from portguard_ais.enums import EncounterType
from portguard_ais.evaluation.synthetic import ARTICLE_SCENARIOS, article_scenarios
from portguard_ais.pipeline import PortGuardPipeline


def test_article_scenarios_are_isolated_and_complete() -> None:
    frame = article_scenarios(steps=4)
    result = PortGuardPipeline().process_frame(frame)

    assert len(frame) == 24
    assert frame["mmsi"].nunique() == 6
    assert len(result.assessments) == 12

    expected_pairs = {(item.own_mmsi, item.target_mmsi) for item in ARTICLE_SCENARIOS}
    observed_pairs = {(item.own_mmsi, item.target_mmsi) for item in result.assessments}
    assert observed_pairs == expected_pairs


def test_article_suite_contains_rule_13_overtaking() -> None:
    frame = article_scenarios(steps=8)
    result = PortGuardPipeline().process_frame(frame)
    overtaking = [
        item
        for item in result.assessments
        if item.own_mmsi == 261300001 and item.target_mmsi == 261300002
    ]

    converging = [item for item in overtaking if item.relative_motion.converging]
    assert converging
    assert all(item.encounter_type == EncounterType.OVERTAKING for item in converging)
    assert all(item.colreg.rule == "Rule 13" for item in converging)

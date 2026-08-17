from portguard_ais.evaluation.jmse_benchmark import run_jmse_benchmark
from portguard_ais.evaluation.jmse_scenarios import jmse_scenarios


def test_jmse_scenario_suite_has_sixteen_cases() -> None:
    scenarios = jmse_scenarios(steps=12)
    assert len(scenarios) == 16
    assert len({scenario.name for scenario in scenarios}) == 16
    assert all(len(scenario.snapshots) == 12 for scenario in scenarios)


def test_transient_false_positive_has_no_ground_truth_hazard() -> None:
    scenarios = {scenario.name: scenario for scenario in jmse_scenarios(steps=12)}
    transient = scenarios["transient-false-positive"]
    assert transient.hazardous_steps == frozenset()


def test_degraded_scenarios_contain_assurance_injections() -> None:
    scenarios = {scenario.name: scenario for scenario in jmse_scenarios(steps=12)}
    delayed = scenarios["delayed-ais"]
    dropout = scenarios["message-dropout"]
    mixed = scenarios["mixed-confidence-scene"]
    assert any(item.stale_fraction >= 0.75 for item in delayed.evidence_overrides)
    assert any(item.coverage_ratio < 1.0 for item in dropout.evidence_overrides)
    assert any(item.mean_pairwise_confidence is not None for item in mixed.evidence_overrides)


def test_controlled_benchmark_returns_all_progressive_methods() -> None:
    result = run_jmse_benchmark(steps=12)
    names = [item.method for item in result.methods]
    assert names == [
        "B0_CPA_TCPA",
        "B1_PAIRWISE_STATIC",
        "B2_PAIRWISE_TEMPORAL",
        "B3_SCENE_STATIC",
        "B4_SCENE_TEMPORAL",
        "OURS_ASSURED",
    ]
    assert result.records
    assert result.assurance.degraded_steps > 0
    assert result.assurance.overconfident_critical_steps == 0
    assert result.assurance.inappropriate_fallback_steps == 0

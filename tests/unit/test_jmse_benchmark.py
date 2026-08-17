from portguard_ais.evaluation.jmse_benchmark import run_jmse_benchmark
from portguard_ais.evaluation.jmse_robustness import jitter_scenarios
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


def test_seeded_geometry_jitter_is_reproducible_and_seed_sensitive() -> None:
    canonical = jmse_scenarios(steps=12, seed=20260817)
    first = jitter_scenarios(canonical, seed=101, position_jitter_nm=0.08)
    repeat = jitter_scenarios(canonical, seed=101, position_jitter_nm=0.08)
    different = jitter_scenarios(canonical, seed=102, position_jitter_nm=0.08)

    first_observation = first[0].snapshots[0][0]
    repeated_observation = repeat[0].snapshots[0][0]
    different_observation = different[0].snapshots[0][0]

    assert first_observation.lat == repeated_observation.lat
    assert first_observation.lon == repeated_observation.lon
    assert (
        first_observation.lat != different_observation.lat
        or first_observation.lon != different_observation.lon
    )


def test_controlled_benchmark_accepts_injected_geometry_ensemble() -> None:
    canonical = jmse_scenarios(steps=12, seed=20260817)
    perturbed = jitter_scenarios(canonical, seed=20260817, position_jitter_nm=0.08)
    result = run_jmse_benchmark(steps=12, scenarios=perturbed)
    assert result.records
    assert len({record.scenario for record in result.records}) == 16


def test_controlled_benchmark_returns_progressive_detection_and_assured_output() -> None:
    result = run_jmse_benchmark(steps=12)
    names = [item.method for item in result.methods]
    assert names == [
        "B0_CPA_TCPA",
        "B1_PAIRWISE_STATIC",
        "B2_PAIRWISE_TEMPORAL",
        "B3_SCENE_STATIC",
        "B4_SCENE_TEMPORAL",
        "OURS_ASSURED_OUTPUT",
    ]
    assert result.records
    assert result.assurance.degraded_steps > 0
    assert result.assurance.degraded_steps_detected == result.assurance.degraded_steps
    assert result.assurance.degraded_input_detection_rate == 1.0
    assert result.assurance.overconfident_critical_steps == 0
    assert result.assurance.overconfident_critical_rate == 0.0
    assert result.assurance.inappropriate_intervention_steps == 0
    assert result.assurance.inappropriate_fallback_steps == 0


def test_fallback_preserves_latent_hazard_state_separately_from_output_authority() -> None:
    result = run_jmse_benchmark(steps=12)
    fallback_records = [record for record in result.records if record.fallback]
    assert fallback_records
    assert all(record.assurance_intervened for record in fallback_records)
    assert any(record.hazard_state_detected and not record.ours_assured for record in fallback_records)

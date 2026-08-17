#!/usr/bin/env python3
"""Verify hysteresis on a threshold-chatter scene-risk sequence."""

from datetime import UTC, datetime, timedelta

from portguard_ais.assurance.config import SceneTemporalConfig
from portguard_ais.assurance.models import SceneRiskAssessment
from portguard_ais.assurance.temporal import SceneTemporalMonitor


def _assessment(step: int, score: float) -> SceneRiskAssessment:
    return SceneRiskAssessment(
        timestamp=datetime(2026, 8, 17, 10, 0, tzinfo=UTC) + timedelta(seconds=30 * step),
        peak_pairwise_risk=score,
        top_k_mean_risk=score,
        coupling_score=0.5,
        scene_risk_score=score,
        uncertainty_score=0.0,
        conservative_upper_score=score,
        rationale=("threshold-chatter probe",),
    )


def _run(release_margin: float) -> tuple[list[str], int]:
    monitor = SceneTemporalMonitor(
        SceneTemporalConfig(
            persistence_updates=1,
            resolving_updates=1,
            release_margin=release_margin,
        )
    )
    scores = [0.52, 0.49, 0.51, 0.48, 0.53, 0.47, 0.52, 0.46, 0.54, 0.45]
    states: list[str] = []
    transitions = 0
    for step, score in enumerate(scores):
        result = monitor.update(_assessment(step, score))
        states.append(result.current_state.value)
        transitions += int(result.changed)
    return states, transitions


def main() -> None:
    with_hysteresis, transitions_with = _run(0.08)
    without_hysteresis, transitions_without = _run(0.0)
    print("JMSE hysteresis mechanism probe")
    print(f"with_hysteresis_transitions={transitions_with}")
    print(f"without_hysteresis_transitions={transitions_without}")
    print("with_hysteresis_states=" + ",".join(with_hysteresis))
    print("without_hysteresis_states=" + ",".join(without_hysteresis))
    if transitions_with >= transitions_without:
        raise SystemExit("hysteresis probe did not reduce threshold chatter")


if __name__ == "__main__":
    main()

"""Temporal state machine for scene-level maritime risk."""

from dataclasses import dataclass

from portguard_ais.assurance.config import SceneTemporalConfig
from portguard_ais.assurance.models import SceneRiskAssessment, SceneStateTransition
from portguard_ais.enums import RiskLevel


@dataclass
class _SceneTracker:
    state: RiskLevel = RiskLevel.SAFE
    candidate: RiskLevel = RiskLevel.SAFE
    candidate_count: int = 0
    resolving_count: int = 0


class SceneTemporalMonitor:
    """Apply persistence and hysteresis to scene-level risk."""

    def __init__(self, config: SceneTemporalConfig) -> None:
        self._config = config
        self._tracker = _SceneTracker()

    def reset(self) -> None:
        """Reset temporal scene state."""
        self._tracker = _SceneTracker()

    def update(self, assessment: SceneRiskAssessment) -> SceneStateTransition:
        """Advance scene state from one risk assessment."""
        tracker = self._tracker
        previous = tracker.state
        desired = self._desired_state(assessment.scene_risk_score, tracker.state)

        if desired == RiskLevel.SAFE and tracker.state != RiskLevel.SAFE:
            tracker.resolving_count += 1
            tracker.candidate = RiskLevel.SAFE
            tracker.candidate_count = 0
            if tracker.resolving_count >= self._config.resolving_updates:
                tracker.state = RiskLevel.SAFE
                tracker.resolving_count = 0
        elif desired != tracker.state:
            tracker.resolving_count = 0
            if desired == tracker.candidate:
                tracker.candidate_count += 1
            else:
                tracker.candidate = desired
                tracker.candidate_count = 1
            if tracker.candidate_count >= self._config.persistence_updates:
                tracker.state = desired
                tracker.candidate_count = 0
        else:
            tracker.candidate = desired
            tracker.candidate_count = 0
            tracker.resolving_count = 0

        changed = tracker.state != previous
        if changed:
            event = f"{previous.value}->{tracker.state.value}"
        elif desired != tracker.state:
            event = f"pending-{desired.value}"
        elif tracker.resolving_count > 0:
            event = "pending-safe"
        else:
            event = "stable"
        return SceneStateTransition(
            timestamp=assessment.timestamp,
            previous_state=previous,
            current_state=tracker.state,
            changed=changed,
            event=event,
        )

    def _desired_state(self, score: float, current: RiskLevel) -> RiskLevel:
        margin = self._config.release_margin
        if current == RiskLevel.CRITICAL and score >= self._config.critical - margin:
            return RiskLevel.CRITICAL
        if current == RiskLevel.WARNING and score >= self._config.warning - margin:
            if score >= self._config.critical:
                return RiskLevel.CRITICAL
            return RiskLevel.WARNING
        if current == RiskLevel.WATCH and score >= self._config.watch - margin:
            if score >= self._config.critical:
                return RiskLevel.CRITICAL
            if score >= self._config.warning:
                return RiskLevel.WARNING
            return RiskLevel.WATCH
        return self._score_state(score)

    def _score_state(self, score: float) -> RiskLevel:
        if score >= self._config.critical:
            return RiskLevel.CRITICAL
        if score >= self._config.warning:
            return RiskLevel.WARNING
        if score >= self._config.watch:
            return RiskLevel.WATCH
        return RiskLevel.SAFE

"""Stateful alert lifecycle with persistence, hysteresis and cooldown."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from portguard_ais.config import AlertConfig, RiskThresholds
from portguard_ais.enums import AlertState
from portguard_ais.models import AlertDecision, EncounterAssessment


@dataclass
class _Tracker:
    state: AlertState = AlertState.SAFE
    candidate: AlertState = AlertState.SAFE
    candidate_count: int = 0
    resolving_count: int = 0
    last_emitted_at: datetime | None = None


class AlertStateMachine:
    """Track alert state independently for every vessel pair."""

    def __init__(self, config: AlertConfig, thresholds: RiskThresholds) -> None:
        self._config = config
        self._thresholds = thresholds
        self._trackers: dict[str, _Tracker] = {}

    def reset(self) -> None:
        """Discard all tracked encounter state."""
        self._trackers.clear()

    def update(self, assessment: EncounterAssessment) -> AlertDecision:
        """Advance one encounter and decide whether to emit an alert event."""
        tracker = self._trackers.setdefault(assessment.encounter_id, _Tracker())
        previous = tracker.state
        desired = self._desired_with_hysteresis(assessment.risk_score, tracker.state)

        if desired == AlertState.SAFE and tracker.state not in {AlertState.SAFE, AlertState.CLOSED}:
            tracker.resolving_count += 1
            tracker.candidate_count = 0
            tracker.state = AlertState.RESOLVING
            if tracker.resolving_count >= self._config.resolving_updates:
                tracker.state = AlertState.CLOSED
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

        emitted, event = self._emission_decision(previous, tracker, assessment.timestamp)
        if emitted:
            tracker.last_emitted_at = assessment.timestamp

        rationale = (
            *assessment.rationale,
            f"alert state transitioned from {previous.value} to {tracker.state.value}",
            f"state event: {event}",
        )
        return AlertDecision(
            encounter_id=assessment.encounter_id,
            timestamp=assessment.timestamp,
            previous_state=previous,
            current_state=tracker.state,
            emitted=emitted,
            event=event,
            rationale=rationale,
        )

    def _desired_with_hysteresis(self, score: float, current: AlertState) -> AlertState:
        margin = self._thresholds.release_margin
        if current == AlertState.CRITICAL and score >= self._thresholds.critical - margin:
            return AlertState.CRITICAL
        if current == AlertState.WARNING and score >= self._thresholds.warning - margin:
            if score >= self._thresholds.critical:
                return AlertState.CRITICAL
            return AlertState.WARNING
        if current == AlertState.WATCH and score >= self._thresholds.watch - margin:
            if score >= self._thresholds.critical:
                return AlertState.CRITICAL
            if score >= self._thresholds.warning:
                return AlertState.WARNING
            return AlertState.WATCH
        return self._score_state(score)

    def _score_state(self, score: float) -> AlertState:
        if score >= self._thresholds.critical:
            return AlertState.CRITICAL
        if score >= self._thresholds.warning:
            return AlertState.WARNING
        if score >= self._thresholds.watch:
            return AlertState.WATCH
        return AlertState.SAFE

    def _emission_decision(
        self,
        previous: AlertState,
        tracker: _Tracker,
        timestamp: datetime,
    ) -> tuple[bool, str]:
        current = tracker.state
        severity = {
            AlertState.SAFE: 0,
            AlertState.CLOSED: 0,
            AlertState.RESOLVING: 1,
            AlertState.WATCH: 2,
            AlertState.WARNING: 3,
            AlertState.CRITICAL: 4,
        }
        if current != previous:
            if current == AlertState.CLOSED:
                return True, "closed"
            if current == AlertState.RESOLVING:
                return False, "resolving"
            if previous in {AlertState.SAFE, AlertState.CLOSED, AlertState.RESOLVING}:
                return True, "opened"
            if severity[current] > severity[previous]:
                return True, "escalated"
            return True, "deescalated"

        if current == AlertState.CRITICAL and tracker.last_emitted_at is not None:
            repeat_after = timedelta(seconds=self._config.repeat_critical_seconds)
            if timestamp - tracker.last_emitted_at >= repeat_after:
                return True, "critical-repeat"

        if tracker.last_emitted_at is not None:
            cooldown = timedelta(seconds=self._config.cooldown_seconds)
            if timestamp - tracker.last_emitted_at < cooldown:
                return False, "suppressed-cooldown"
        return False, "no-transition"

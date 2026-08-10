"""Aggregate repeated encounter assessments into near-miss candidates."""

from collections import defaultdict

from portguard_ais.config import NearMissConfig
from portguard_ais.models import EncounterAssessment, NearMissEvent


def mine_near_misses(
    assessments: list[EncounterAssessment],
    config: NearMissConfig,
) -> list[NearMissEvent]:
    """Return ranked events meeting transparent score, DCPA and TCPA criteria."""
    grouped: dict[str, list[EncounterAssessment]] = defaultdict(list)
    for assessment in assessments:
        grouped[assessment.encounter_id].append(assessment)

    events: list[NearMissEvent] = []
    for encounter_id, observations in grouped.items():
        ordered = sorted(observations, key=lambda item: item.timestamp)
        if len(ordered) < config.minimum_observations:
            continue
        peak = max(item.risk_score for item in ordered)
        minimum_dcpa = min(item.relative_motion.dcpa_nm for item in ordered)
        converging_tcpa = [
            item.relative_motion.tcpa_min for item in ordered if item.relative_motion.converging
        ]
        minimum_tcpa = min(converging_tcpa, default=0.0)
        if peak < config.minimum_peak_score:
            continue
        if minimum_dcpa > config.maximum_dcpa_nm:
            continue
        if converging_tcpa and minimum_tcpa > config.maximum_tcpa_min:
            continue

        first = ordered[0]
        severity_rank = round(
            peak * 0.6
            + max(0.0, 1.0 - minimum_dcpa / config.maximum_dcpa_nm) * 0.3
            + min(len(ordered) / 10.0, 1.0) * 0.1,
            6,
        )
        events.append(
            NearMissEvent(
                encounter_id=encounter_id,
                own_mmsi=first.own_mmsi,
                target_mmsi=first.target_mmsi,
                started_at=ordered[0].timestamp,
                ended_at=ordered[-1].timestamp,
                observation_count=len(ordered),
                peak_risk_score=peak,
                minimum_dcpa_nm=minimum_dcpa,
                minimum_tcpa_min=minimum_tcpa,
                encounter_types=tuple(dict.fromkeys(item.encounter_type for item in ordered)),
                severity_rank=severity_rank,
            )
        )
    return sorted(events, key=lambda event: event.severity_rank, reverse=True)

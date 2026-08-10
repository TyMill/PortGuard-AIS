"""High-level orchestration for snapshots and historical AIS data."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha1
from pathlib import Path

import pandas as pd

from portguard_ais.alerts.rationale import build_rationale
from portguard_ais.alerts.state_machine import AlertStateMachine
from portguard_ais.colregs.context import colreg_context
from portguard_ais.config import PortGuardConfig
from portguard_ais.encounters.classifier import classify_encounter
from portguard_ais.encounters.pairing import candidate_pairs
from portguard_ais.geometry.relative_motion import solve_relative_motion
from portguard_ais.ingestion.readers import read_ais_csv, validate_ais_frame
from portguard_ais.models import (
    AlertDecision,
    EncounterAssessment,
    GeoPoint,
    HotspotCell,
    NearMissEvent,
    RiskTrendAssessment,
    ValidationReport,
    VesselObservation,
)
from portguard_ais.near_miss.hotspots import aggregate_hotspots
from portguard_ais.near_miss.miner import mine_near_misses
from portguard_ais.preprocessing.cleaning import clean_ais_frame
from portguard_ais.preprocessing.resampling import resample_tracks
from portguard_ais.risk.confidence import estimate_confidence
from portguard_ais.risk.domain import assess_ship_domain
from portguard_ais.risk.scoring import aggregate_risk, classify_risk, compute_components
from portguard_ais.risk.trend import estimate_risk_trend


@dataclass(frozen=True)
class ProcessingResult:
    """Pipeline outputs and validation metadata."""

    assessments: list[EncounterAssessment]
    alerts: list[AlertDecision]
    near_misses: list[NearMissEvent]
    trends: list[RiskTrendAssessment]
    hotspots: list[HotspotCell]
    validation: ValidationReport


class PortGuardPipeline:
    """Configurable and stateful AIS encounter-assessment pipeline."""

    def __init__(self, config: PortGuardConfig | None = None) -> None:
        self.config = config or PortGuardConfig()
        self.alerts = AlertStateMachine(self.config.alerts, self.config.thresholds)

    def process_csv(self, path: str | Path) -> ProcessingResult:
        """Read, clean and process a historical AIS CSV file."""
        return self.process_frame(read_ais_csv(path))

    def process_frame(self, frame: pd.DataFrame) -> ProcessingResult:
        """Process timestamp snapshots in chronological order."""
        cleaned, validation = clean_ais_frame(frame, self.config.input)
        if self.config.input.resample_seconds is not None:
            cleaned = resample_tracks(
                cleaned,
                seconds=self.config.input.resample_seconds,
                interpolation_limit=self.config.input.interpolate_limit,
            )
        observations = validate_ais_frame(cleaned)

        by_timestamp: dict[datetime, list[VesselObservation]] = {}
        for observation in observations:
            by_timestamp.setdefault(observation.timestamp, []).append(observation)

        assessments: list[EncounterAssessment] = []
        alerts: list[AlertDecision] = []
        for timestamp in sorted(by_timestamp):
            snapshot_assessments = self.process_snapshot(by_timestamp[timestamp])
            assessments.extend(snapshot_assessments)
            alerts.extend(self.alerts.update(item) for item in snapshot_assessments)

        near_misses = mine_near_misses(assessments, self.config.near_miss)
        grouped: dict[str, list[EncounterAssessment]] = {}
        for assessment in assessments:
            grouped.setdefault(assessment.encounter_id, []).append(assessment)
        trends = [estimate_risk_trend(items) for items in grouped.values()]
        hotspots = aggregate_hotspots(assessments, minimum_score=self.config.thresholds.warning)
        return ProcessingResult(assessments, alerts, near_misses, trends, hotspots, validation)

    def process_snapshot(
        self,
        observations: list[VesselObservation],
    ) -> list[EncounterAssessment]:
        """Assess all candidate pairs in one timestamp snapshot."""
        if not observations:
            return []
        timestamps = {observation.timestamp for observation in observations}
        if len(timestamps) != 1:
            raise ValueError("process_snapshot requires exactly one timestamp")

        results: list[EncounterAssessment] = []
        for first, second in candidate_pairs(observations, self.config.pairing):
            results.append(self.assess_pair(first, second))
        return results

    def assess_pair(
        self,
        own: VesselObservation,
        target: VesselObservation,
    ) -> EncounterAssessment:
        """Assess one ordered own/target pair."""
        motion = solve_relative_motion(own, target, self.config.thresholds.tcpa_horizon_min)
        encounter_type = classify_encounter(own, target, motion)
        domain = assess_ship_domain(own, motion, self.config.domain)
        components = compute_components(motion, domain, self.config.thresholds)
        score = aggregate_risk(components, self.config.weights)
        level = classify_risk(score, self.config.thresholds)
        rationale = build_rationale(encounter_type, level, motion, domain, components)
        encounter_id = self._encounter_id(own.mmsi, target.mmsi)
        return EncounterAssessment(
            encounter_id=encounter_id,
            timestamp=own.timestamp,
            own_mmsi=own.mmsi,
            target_mmsi=target.mmsi,
            encounter_type=encounter_type,
            risk_level=level,
            risk_score=score,
            confidence=estimate_confidence(own, target),
            own_position=GeoPoint(lat=own.lat, lon=own.lon),
            target_position=GeoPoint(lat=target.lat, lon=target.lon),
            relative_motion=motion,
            domain=domain,
            colreg=colreg_context(encounter_type),
            components=components,
            rationale=rationale,
        )

    @staticmethod
    def _encounter_id(own_mmsi: int, target_mmsi: int) -> str:
        ordered = f"{min(own_mmsi, target_mmsi)}:{max(own_mmsi, target_mmsi)}"
        digest = sha1(ordered.encode(), usedforsecurity=False).hexdigest()[:12]
        return f"enc-{digest}"

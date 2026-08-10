"""Validated domain models and result containers."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from portguard_ais.enums import AlertState, EncounterType, RiskLevel, RiskTrend, VesselRole


class DomainModel(BaseModel):
    """Strict immutable domain object."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class VesselObservation(DomainModel):
    """Single timestamped AIS observation."""

    timestamp: datetime
    mmsi: int = Field(gt=0, le=999_999_999)
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    sog: float = Field(ge=0.0)
    cog: float = Field(ge=0.0, lt=360.0)
    heading: float | None = Field(default=None, ge=0.0, lt=360.0)
    rot: float | None = None
    length_m: float | None = Field(default=None, gt=0.0)
    beam_m: float | None = Field(default=None, gt=0.0)
    vessel_type: str | None = None
    position_accuracy_m: float | None = Field(default=None, ge=0.0)
    source: str | None = None

    @field_validator("timestamp")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        """Require an explicit timezone to prevent ambiguous temporal grouping."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class GeoPoint(DomainModel):
    """Geographic point in WGS84 decimal degrees."""

    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)


class RelativeMotion(DomainModel):
    """Relative-motion solution for a vessel pair."""

    current_distance_nm: float = Field(ge=0.0)
    dcpa_nm: float = Field(ge=0.0)
    tcpa_min: float = Field(ge=0.0)
    relative_speed_kn: float = Field(ge=0.0)
    closing_speed_kn: float = Field(ge=0.0)
    converging: bool
    relative_bearing_deg: float
    cpa_east_nm: float
    cpa_north_nm: float


class DomainAssessment(DomainModel):
    """Elliptical domain dimensions and predicted intrusion."""

    forward_nm: float = Field(gt=0.0)
    aft_nm: float = Field(gt=0.0)
    lateral_nm: float = Field(gt=0.0)
    normalized_distance: float = Field(ge=0.0)
    violated: bool


class ColregContext(DomainModel):
    """Rule context, not a manoeuvre prescription."""

    rule: str | None
    own_role: VesselRole
    target_role: VesselRole
    explanation: str


class RiskComponents(DomainModel):
    """Normalized risk components before weighted aggregation."""

    dcpa: float = Field(ge=0.0, le=1.0)
    tcpa: float = Field(ge=0.0, le=1.0)
    range: float = Field(ge=0.0, le=1.0)
    closing_speed: float = Field(ge=0.0, le=1.0)
    domain: float = Field(ge=0.0, le=1.0)


class EncounterAssessment(DomainModel):
    """Complete explainable assessment for one ordered vessel pair."""

    encounter_id: str
    timestamp: datetime
    own_mmsi: int
    target_mmsi: int
    encounter_type: EncounterType
    risk_level: RiskLevel
    risk_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    own_position: GeoPoint | None = None
    target_position: GeoPoint | None = None
    relative_motion: RelativeMotion
    domain: DomainAssessment
    colreg: ColregContext
    components: RiskComponents
    rationale: tuple[str, ...]


class AlertDecision(DomainModel):
    """State-machine output for one assessment update."""

    encounter_id: str
    timestamp: datetime
    previous_state: AlertState
    current_state: AlertState
    emitted: bool
    event: str
    rationale: tuple[str, ...]


class NearMissEvent(DomainModel):
    """Aggregated historical near-miss candidate."""

    encounter_id: str
    own_mmsi: int
    target_mmsi: int
    started_at: datetime
    ended_at: datetime
    observation_count: int
    peak_risk_score: float
    minimum_dcpa_nm: float
    minimum_tcpa_min: float
    encounter_types: tuple[EncounterType, ...]
    severity_rank: float


class KinematicAnomaly(DomainModel):
    """Consecutive positions that violate a configured kinematic limit."""

    mmsi: int
    started_at: datetime
    ended_at: datetime
    implied_speed_kn: float = Field(gt=0.0)
    threshold_kn: float = Field(gt=0.0)
    reason: str


class RiskTrendAssessment(DomainModel):
    """Trend summary for one encounter timeline."""

    encounter_id: str
    trend: RiskTrend
    slope_per_min: float
    score_delta: float
    observation_count: int = Field(ge=1)


class HotspotCell(DomainModel):
    """Grid-cell aggregation of elevated-risk assessments."""

    latitude_center: float = Field(ge=-90.0, le=90.0)
    longitude_center: float = Field(ge=-180.0, le=180.0)
    cell_size_deg: float = Field(gt=0.0)
    assessment_count: int = Field(ge=1)
    unique_vessels: int = Field(ge=2)
    mean_risk_score: float = Field(ge=0.0, le=1.0)
    maximum_risk_score: float = Field(ge=0.0, le=1.0)


class ValidationReport(DomainModel):
    """Summary of input validation and cleaning."""

    input_rows: int
    output_rows: int
    invalid_rows: int
    duplicate_rows_removed: int
    filtered_speed_rows: int
    warnings: tuple[str, ...] = ()


class SerializableModel(DomainModel):
    """Generic serializable wrapper for extension points."""

    payload: dict[str, Any]

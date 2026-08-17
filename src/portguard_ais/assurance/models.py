"""Domain models for scene-level maritime risk and runtime assurance."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from portguard_ais.enums import RiskLevel


class ResearchModel(BaseModel):
    """Strict immutable base for research-domain objects."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class AssuranceMode(StrEnum):
    """Operational confidence mode selected by the runtime supervisor."""

    NOMINAL = "nominal"
    DEGRADED = "degraded"
    HUMAN_VERIFY = "human-verify"
    FALLBACK = "fallback"


class DecisionAuthority(StrEnum):
    """Maximum operational strength of a scene-level decision-support output."""

    NO_ALERT = "no-alert"
    ADVISORY = "advisory"
    WARNING = "warning"
    CRITICAL = "critical"
    HUMAN_VERIFY = "human-verify"
    FALLBACK = "fallback"


class SceneGraphEdge(ResearchModel):
    """One weighted undirected encounter edge."""

    own_mmsi: int = Field(gt=0)
    target_mmsi: int = Field(gt=0)
    risk_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    dcpa_nm: float = Field(ge=0.0)
    tcpa_min: float = Field(ge=0.0)
    relative_speed_kn: float = Field(ge=0.0)
    closing_speed_kn: float = Field(ge=0.0)
    encounter_type: str
    domain_violated: bool


class SceneGraph(ResearchModel):
    """Weighted interaction graph and derived scene descriptors."""

    timestamp: datetime
    vessels: tuple[int, ...]
    edges: tuple[SceneGraphEdge, ...]
    weighted_degree: dict[int, float]
    maximum_weighted_degree: float = Field(ge=0.0)
    weighted_density: float = Field(ge=0.0, le=1.0)
    coupling_score: float = Field(ge=0.0, le=1.0)
    conflict_components: tuple[tuple[int, ...], ...]
    maximum_component_size: int = Field(ge=0)
    low_confidence_edge_fraction: float = Field(ge=0.0, le=1.0)


class SceneEvidence(ResearchModel):
    """Quality and coverage evidence used by the assurance supervisor."""

    mean_pairwise_confidence: float = Field(ge=0.0, le=1.0)
    low_confidence_edge_fraction: float = Field(ge=0.0, le=1.0)
    stale_fraction: float = Field(default=0.0, ge=0.0, le=1.0)
    missing_optional_fraction: float = Field(default=0.0, ge=0.0, le=1.0)
    anomaly_fraction: float = Field(default=0.0, ge=0.0, le=1.0)
    coverage_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    latency_ms: float = Field(default=0.0, ge=0.0)


class SceneRiskAssessment(ResearchModel):
    """Explainable scene-level hazard and uncertainty assessment."""

    timestamp: datetime
    peak_pairwise_risk: float = Field(ge=0.0, le=1.0)
    top_k_mean_risk: float = Field(ge=0.0, le=1.0)
    coupling_score: float = Field(ge=0.0, le=1.0)
    scene_risk_score: float = Field(ge=0.0, le=1.0)
    uncertainty_score: float = Field(ge=0.0, le=1.0)
    conservative_upper_score: float = Field(ge=0.0, le=1.0)
    rationale: tuple[str, ...]


class SceneStateTransition(ResearchModel):
    """Temporal transition of the scene-level risk state."""

    timestamp: datetime
    previous_state: RiskLevel
    current_state: RiskLevel
    changed: bool
    event: str


class AssuredSceneDecision(ResearchModel):
    """Runtime-assured decision-support output for one maritime scene."""

    timestamp: datetime
    scene_state: RiskLevel
    assurance_mode: AssuranceMode
    authority: DecisionAuthority
    evidence_quality: float = Field(ge=0.0, le=1.0)
    emitted_risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    rationale: tuple[str, ...]

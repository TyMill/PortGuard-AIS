"""Configuration for scene-level risk and runtime assurance."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from portguard_ais.exceptions import ConfigurationError


class FrozenResearchModel(BaseModel):
    """Immutable configuration base for research extensions."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class SceneRiskConfig(FrozenResearchModel):
    """Weights and thresholds for interpretable scene-level risk."""

    peak_weight: float = Field(default=0.45, ge=0.0)
    top_k_weight: float = Field(default=0.30, ge=0.0)
    coupling_weight: float = Field(default=0.25, ge=0.0)
    uncertainty_upper_weight: float = Field(default=0.20, ge=0.0)
    top_k_edges: int = Field(default=3, ge=1)
    conflict_edge_threshold: float = Field(default=0.50, ge=0.0, le=1.0)
    low_confidence_threshold: float = Field(default=0.70, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_risk_weights(self) -> "SceneRiskConfig":
        """Require a positive sum for hazard-estimation weights."""
        if self.peak_weight + self.top_k_weight + self.coupling_weight <= 0.0:
            raise ConfigurationError("At least one scene-risk weight must be positive")
        return self


class SceneTemporalConfig(FrozenResearchModel):
    """Scene-state thresholds, persistence and hysteresis."""

    watch: float = Field(default=0.25, ge=0.0, le=1.0)
    warning: float = Field(default=0.50, ge=0.0, le=1.0)
    critical: float = Field(default=0.75, ge=0.0, le=1.0)
    release_margin: float = Field(default=0.08, ge=0.0, lt=0.5)
    persistence_updates: int = Field(default=2, ge=1)
    resolving_updates: int = Field(default=2, ge=1)

    @model_validator(mode="after")
    def validate_threshold_order(self) -> "SceneTemporalConfig":
        """Require monotonically increasing scene-risk thresholds."""
        if not self.watch < self.warning < self.critical:
            raise ConfigurationError("Scene thresholds must satisfy watch < warning < critical")
        return self


class AssuranceConfig(FrozenResearchModel):
    """Evidence-quality gates for decision-support authority.

    Aggregate evidence quality is complemented by explicit physical-data gates. This
    prevents a high average confidence from masking a material loss of scene coverage
    or a strong kinematic anomaly.
    """

    degraded_quality_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    human_verify_quality_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    fallback_quality_threshold: float = Field(default=0.30, ge=0.0, le=1.0)

    degraded_stale_fraction: float = Field(default=0.25, ge=0.0, le=1.0)
    fallback_stale_fraction: float = Field(default=0.75, ge=0.0, le=1.0)
    degraded_coverage_ratio: float = Field(default=0.80, ge=0.0, le=1.0)
    fallback_coverage_ratio: float = Field(default=0.50, ge=0.0, le=1.0)
    degraded_anomaly_fraction: float = Field(default=0.20, ge=0.0, le=1.0)
    human_verify_anomaly_fraction: float = Field(default=0.50, ge=0.0, le=1.0)

    deadline_ms: float = Field(default=1000.0, gt=0.0)
    missing_weight: float = Field(default=0.15, ge=0.0)
    stale_weight: float = Field(default=0.30, ge=0.0)
    anomaly_weight: float = Field(default=0.20, ge=0.0)
    coverage_weight: float = Field(default=0.20, ge=0.0)
    latency_weight: float = Field(default=0.15, ge=0.0)

    @model_validator(mode="after")
    def validate_quality_thresholds(self) -> "AssuranceConfig":
        """Ensure internally consistent evidence-quality bands and hard gates."""
        if not (
            self.fallback_quality_threshold
            < self.human_verify_quality_threshold
            < self.degraded_quality_threshold
        ):
            raise ConfigurationError(
                "Assurance quality thresholds must satisfy fallback < human_verify < degraded"
            )
        if self.degraded_stale_fraction >= self.fallback_stale_fraction:
            raise ConfigurationError("degraded stale threshold must be below fallback threshold")
        if self.degraded_coverage_ratio <= self.fallback_coverage_ratio:
            raise ConfigurationError("degraded coverage threshold must exceed fallback threshold")
        if self.degraded_anomaly_fraction >= self.human_verify_anomaly_fraction:
            raise ConfigurationError(
                "degraded anomaly threshold must be below human-verify threshold"
            )
        return self


class ResearchAssuranceConfig(FrozenResearchModel):
    """Top-level configuration for the JMSE research pipeline."""

    scene_risk: SceneRiskConfig = SceneRiskConfig()
    temporal: SceneTemporalConfig = SceneTemporalConfig()
    assurance: AssuranceConfig = AssuranceConfig()

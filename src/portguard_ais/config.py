"""Validated configuration models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from portguard_ais.exceptions import ConfigurationError


class FrozenModel(BaseModel):
    """Immutable base for runtime configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class InputConfig(FrozenModel):
    """Input validation and cleaning controls."""

    max_sog_kn: float = Field(default=60.0, gt=0.0)
    max_position_age_seconds: int = Field(default=120, ge=1)
    duplicate_keep: Literal["first", "last"] = "last"
    resample_seconds: int | None = Field(default=None, ge=1)
    interpolate_limit: int = Field(default=2, ge=0)


class PairingConfig(FrozenModel):
    """Controls for generating candidate vessel pairs."""

    max_pair_distance_nm: float = Field(default=6.0, gt=0.0)
    minimum_sog_kn: float = Field(default=0.2, ge=0.0)


class DomainConfig(FrozenModel):
    """Speed- and dimension-aware elliptical ship domain."""

    minimum_length_m: float = Field(default=30.0, gt=0.0)
    default_length_m: float = Field(default=100.0, gt=0.0)
    forward_length_factor: float = Field(default=4.0, gt=0.0)
    aft_length_factor: float = Field(default=1.5, gt=0.0)
    lateral_length_factor: float = Field(default=1.5, gt=0.0)
    speed_factor_seconds: float = Field(default=30.0, ge=0.0)


class RiskThresholds(FrozenModel):
    """Thresholds for severity and temporal relevance."""

    watch: float = Field(default=0.25, ge=0.0, le=1.0)
    warning: float = Field(default=0.50, ge=0.0, le=1.0)
    critical: float = Field(default=0.75, ge=0.0, le=1.0)
    release_margin: float = Field(default=0.08, ge=0.0, lt=0.5)
    tcpa_horizon_min: float = Field(default=45.0, gt=0.0)
    close_range_nm: float = Field(default=2.0, gt=0.0)

    @model_validator(mode="after")
    def validate_order(self) -> "RiskThresholds":
        """Ensure monotonically increasing severity thresholds."""
        if not self.watch < self.warning < self.critical:
            raise ConfigurationError("Risk thresholds must satisfy watch < warning < critical")
        return self


class RiskWeights(FrozenModel):
    """Transparent weights for risk components."""

    dcpa: float = Field(default=0.32, ge=0.0)
    tcpa: float = Field(default=0.24, ge=0.0)
    range: float = Field(default=0.14, ge=0.0)
    closing_speed: float = Field(default=0.12, ge=0.0)
    domain: float = Field(default=0.18, ge=0.0)

    @model_validator(mode="after")
    def validate_weight_sum(self) -> "RiskWeights":
        """Reject zero-sum weights."""
        if self.total <= 0.0:
            raise ConfigurationError("At least one risk weight must be positive")
        return self

    @property
    def total(self) -> float:
        """Return the sum used to normalize component weights."""
        return self.dcpa + self.tcpa + self.range + self.closing_speed + self.domain


class AlertConfig(FrozenModel):
    """Stateful alert persistence and suppression controls."""

    persistence_updates: int = Field(default=2, ge=1)
    resolving_updates: int = Field(default=2, ge=1)
    cooldown_seconds: int = Field(default=120, ge=0)
    repeat_critical_seconds: int = Field(default=300, ge=0)


class NearMissConfig(FrozenModel):
    """Historical near-miss event criteria."""

    minimum_peak_score: float = Field(default=0.50, ge=0.0, le=1.0)
    maximum_dcpa_nm: float = Field(default=0.5, gt=0.0)
    maximum_tcpa_min: float = Field(default=20.0, gt=0.0)
    minimum_observations: int = Field(default=2, ge=1)


class PortGuardConfig(FrozenModel):
    """Top-level PortGuard-AIS configuration."""

    input: InputConfig = InputConfig()
    pairing: PairingConfig = PairingConfig()
    domain: DomainConfig = DomainConfig()
    thresholds: RiskThresholds = RiskThresholds()
    weights: RiskWeights = RiskWeights()
    alerts: AlertConfig = AlertConfig()
    near_miss: NearMissConfig = NearMissConfig()

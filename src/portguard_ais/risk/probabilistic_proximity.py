"""Probabilistic projected-proximity estimation from imperfect AIS kinematics.

Research-only, opt-in extension. A sampled close approach is *not* a verified
near miss or the probability of an actual collision. The model assumes a
local tangent plane, constant course/speed over the horizon, independent
Gaussian measurement errors and independently sampled vessel states.
"""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite, sqrt

import numpy as np

from portguard_ais.geometry.geodesy import displacement_nm, velocity_kn
from portguard_ais.models import VesselObservation

METRES_PER_NAUTICAL_MILE = 1852.0
_WILSON_Z_95 = 1.959963984540054


@dataclass(frozen=True, kw_only=True)
class KinematicUncertainty:
    """Explicit 1-sigma assumptions, not inferred from the binary AIS PA flag.

    Position errors are isotropic in a local east/north plane (metres).
    SOG and COG errors are independent normal deviations (knots, degrees).
    Actual equipment errors can be biased, correlated, or non-Gaussian.
    """

    position_sigma_m: float
    sog_sigma_kn: float
    cog_sigma_deg: float

    def __post_init__(self) -> None:
        for name, value in (
            ("position_sigma_m", self.position_sigma_m),
            ("sog_sigma_kn", self.sog_sigma_kn),
            ("cog_sigma_deg", self.cog_sigma_deg),
        ):
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True, kw_only=True)
class ProximityConfig:
    """Frozen experiment settings for projected close-approach estimation."""

    samples: int = 4096
    horizon_minutes: float = 20.0
    proximity_threshold_nm: float = 0.3
    max_age_seconds: float = 120.0
    seed: int = 20261112

    def __post_init__(self) -> None:
        if isinstance(self.samples, bool) or not isinstance(self.samples, int):
            raise ValueError("samples must be an integer")
        if self.samples < 32:
            raise ValueError("samples must be at least 32")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("seed must be a non-negative integer")
        if (
            not isfinite(self.horizon_minutes)
            or self.horizon_minutes <= 0
            or not isfinite(self.proximity_threshold_nm)
            or self.proximity_threshold_nm <= 0
            or not isfinite(self.max_age_seconds)
            or self.max_age_seconds < 0
        ):
            raise ValueError("horizon and threshold must be positive; max age non-negative")


@dataclass(frozen=True)
class ProximityEstimate:
    """Conditional Monte Carlo result for one pair and one evaluation time."""

    evaluated_at: datetime
    own_age_seconds: float
    target_age_seconds: float
    samples: int
    proximity_threshold_nm: float
    horizon_minutes: float
    proximity_probability: float
    probability_ci95_lower: float
    probability_ci95_upper: float
    nominal_minimum_separation_nm: float
    nominal_time_to_minimum_minutes: float
    sampled_minimum_separation_p05_nm: float
    sampled_minimum_separation_median_nm: float
    sampled_minimum_separation_p95_nm: float


def _projected_minimum(
    r_east: np.ndarray,
    r_north: np.ndarray,
    v_east: np.ndarray,
    v_north: np.ndarray,
    horizon_hours: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Closest separation over [0,horizon] in a constant-velocity model."""
    speed_sq = v_east * v_east + v_north * v_north
    dot = r_east * v_east + r_north * v_north
    t_hours = np.zeros_like(speed_sq)
    np.divide(-dot, speed_sq, out=t_hours, where=speed_sq > 1e-12)
    t_hours = np.clip(t_hours, 0.0, horizon_hours)
    minimum_nm = np.hypot(r_east + v_east * t_hours, r_north + v_north * t_hours)
    return minimum_nm, t_hours


def _wilson_interval(successes: int, sample_count: int) -> tuple[float, float]:
    """95% Wilson binomial interval (MC sampling error, not model error)."""
    p = successes / sample_count
    z2 = _WILSON_Z_95 * _WILSON_Z_95
    denominator = 1.0 + z2 / sample_count
    centre = (p + z2 / (2.0 * sample_count)) / denominator
    margin = (
        _WILSON_Z_95
        * sqrt(p * (1.0 - p) / sample_count + z2 / (4.0 * sample_count**2))
        / denominator
    )
    return max(0.0, centre - margin), min(1.0, centre + margin)


def _sample_velocity(
    observation: VesselObservation,
    uncertainty: KinematicUncertainty,
    rng: np.random.Generator,
    samples: int,
) -> tuple[np.ndarray, np.ndarray]:
    speed = np.clip(
        rng.normal(observation.sog, uncertainty.sog_sigma_kn, size=samples),
        0.0,
        None,
    )
    course = np.deg2rad(
        rng.normal(observation.cog, uncertainty.cog_sigma_deg, size=samples) % 360.0
    )
    return speed * np.sin(course), speed * np.cos(course)


def estimate_projected_proximity(
    own: VesselObservation,
    target: VesselObservation,
    own_uncertainty: KinematicUncertainty,
    target_uncertainty: KinematicUncertainty,
    *,
    evaluated_at: datetime,
    config: ProximityConfig | None = None,
) -> ProximityEstimate:
    """Propagate explicit AIS uncertainty into projected proximity probability.

    Position errors are sampled at each vessel's *measurement time*. Velocities
    are separately sampled and advanced to evaluated_at (never backwards),
    then extrapolated over the future prediction horizon. Predictions always
    include current separation (t=0). The output is conditional on modelling
    assumptions and calibration values, and must not be called collision risk.
    """
    settings = config or ProximityConfig()
    if own.mmsi == target.mmsi:
        raise ValueError("a proximity pair must contain distinct vessels")
    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        raise ValueError("evaluated_at must be timezone-aware")
    own_age = (evaluated_at - own.timestamp).total_seconds()
    target_age = (evaluated_at - target.timestamp).total_seconds()
    if min(own_age, target_age) < 0.0:
        raise ValueError("future AIS messages are not available at evaluated_at")
    if max(own_age, target_age) > settings.max_age_seconds:
        raise ValueError("AIS message exceeds configured observation age")

    rng = np.random.default_rng(settings.seed)
    n = settings.samples
    east, north = displacement_nm(own, target)
    own_e, own_n = _sample_velocity(own, own_uncertainty, rng, n)
    target_e, target_n = _sample_velocity(target, target_uncertainty, rng, n)
    r_east = np.full(n, east)
    r_north = np.full(n, north)
    r_east += rng.normal(0.0, own_uncertainty.position_sigma_m / METRES_PER_NAUTICAL_MILE, n)
    r_north += rng.normal(0.0, own_uncertainty.position_sigma_m / METRES_PER_NAUTICAL_MILE, n)
    r_east -= rng.normal(0.0, target_uncertainty.position_sigma_m / METRES_PER_NAUTICAL_MILE, n)
    r_north -= rng.normal(0.0, target_uncertainty.position_sigma_m / METRES_PER_NAUTICAL_MILE, n)
    r_east += target_e * (target_age / 3600.0) - own_e * (own_age / 3600.0)
    r_north += target_n * (target_age / 3600.0) - own_n * (own_age / 3600.0)

    minimum, _ = _projected_minimum(
        r_east,
        r_north,
        target_e - own_e,
        target_n - own_n,
        settings.horizon_minutes / 60.0,
    )
    successes = int(np.count_nonzero(minimum <= settings.proximity_threshold_nm))
    lower, upper = _wilson_interval(successes, n)

    own_nom_e, own_nom_n = velocity_kn(own)
    target_nom_e, target_nom_n = velocity_kn(target)
    nominal_r_e = east + target_nom_e * target_age / 3600.0 - own_nom_e * own_age / 3600.0
    nominal_r_n = north + target_nom_n * target_age / 3600.0 - own_nom_n * own_age / 3600.0
    nominal_min, nominal_t = _projected_minimum(
        np.array([nominal_r_e]),
        np.array([nominal_r_n]),
        np.array([target_nom_e - own_nom_e]),
        np.array([target_nom_n - own_nom_n]),
        settings.horizon_minutes / 60.0,
    )
    p05, p50, p95 = np.quantile(minimum, [0.05, 0.5, 0.95])
    return ProximityEstimate(
        evaluated_at=evaluated_at,
        own_age_seconds=own_age,
        target_age_seconds=target_age,
        samples=n,
        proximity_threshold_nm=settings.proximity_threshold_nm,
        horizon_minutes=settings.horizon_minutes,
        proximity_probability=successes / n,
        probability_ci95_lower=lower,
        probability_ci95_upper=upper,
        nominal_minimum_separation_nm=float(nominal_min[0]),
        nominal_time_to_minimum_minutes=float(nominal_t[0] * 60.0),
        sampled_minimum_separation_p05_nm=float(p05),
        sampled_minimum_separation_median_nm=float(p50),
        sampled_minimum_separation_p95_nm=float(p95),
    )

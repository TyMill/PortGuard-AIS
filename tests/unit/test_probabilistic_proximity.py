"""Controlled checks of Monte Carlo AIS projected proximity estimates."""

from datetime import UTC, datetime, timedelta

import pytest

from portguard_ais.models import VesselObservation
from portguard_ais.risk.probabilistic_proximity import (
    KinematicUncertainty,
    ProximityConfig,
    estimate_projected_proximity,
)

T0 = datetime(2026, 8, 3, 12, tzinfo=UTC)
ZERO = KinematicUncertainty(position_sigma_m=0, sog_sigma_kn=0, cog_sigma_deg=0)
NOISY = KinematicUncertainty(position_sigma_m=30, sog_sigma_kn=0.5, cog_sigma_deg=3)


def _ship(mmsi: int, lon: float, sog: float, cog: float, at: datetime = T0) -> VesselObservation:
    return VesselObservation(
        timestamp=at,
        mmsi=mmsi,
        lat=53.5,
        lon=lon,
        sog=sog,
        cog=cog,
    )


def test_zero_uncertainty_deterministic_head_on_close_approach() -> None:
    own = _ship(1, 14.5, 10.0, 90.0)
    target = _ship(2, 14.51, 10.0, 270.0)
    estimate = estimate_projected_proximity(
        own, target, ZERO, ZERO, evaluated_at=T0,
        config=ProximityConfig(samples=256, proximity_threshold_nm=0.1),
    )
    assert estimate.proximity_probability == 1.0
    assert estimate.nominal_minimum_separation_nm < 1e-7
    assert estimate.nominal_time_to_minimum_minutes > 0
    assert estimate.probability_ci95_lower < 1


def test_zero_uncertainty_diverging_pair_is_not_projected_to_cross() -> None:
    own = _ship(1, 14.5, 10.0, 270.0)
    target = _ship(2, 14.51, 10.0, 90.0)
    estimate = estimate_projected_proximity(
        own, target, ZERO, ZERO, evaluated_at=T0,
        config=ProximityConfig(samples=256, proximity_threshold_nm=0.1),
    )
    assert estimate.proximity_probability == 0.0
    assert estimate.nominal_time_to_minimum_minutes == 0.0


def test_seed_reproducibility_and_uncertainty_effect() -> None:
    own = _ship(1, 14.5, 10.0, 90.0)
    target = _ship(2, 14.51, 10.0, 270.0)
    cfg = ProximityConfig(samples=512, proximity_threshold_nm=0.05, seed=17)
    a = estimate_projected_proximity(own, target, NOISY, NOISY, evaluated_at=T0, config=cfg)
    b = estimate_projected_proximity(own, target, NOISY, NOISY, evaluated_at=T0, config=cfg)
    assert a == b
    assert 0 <= a.proximity_probability <= 1
    assert a.sampled_minimum_separation_p05_nm <= a.sampled_minimum_separation_median_nm
    assert a.sampled_minimum_separation_median_nm <= a.sampled_minimum_separation_p95_nm


def test_rejects_future_or_stale_observation() -> None:
    own = _ship(1, 14.5, 10.0, 90.0, at=T0 + timedelta(seconds=1))
    target = _ship(2, 14.51, 10.0, 270.0)
    with pytest.raises(ValueError, match="future"):
        estimate_projected_proximity(own, target, ZERO, ZERO, evaluated_at=T0)
    old_own = _ship(1, 14.5, 10.0, 90.0, at=T0 - timedelta(seconds=121))
    with pytest.raises(ValueError, match="age"):
        estimate_projected_proximity(old_own, target, ZERO, ZERO, evaluated_at=T0)


def test_age_propagation_uses_measurement_time() -> None:
    own = _ship(1, 14.5, 10, 90, at=T0 - timedelta(seconds=60))
    target = _ship(2, 14.51, 10, 270, at=T0)
    e = estimate_projected_proximity(
        own, target, ZERO, ZERO, evaluated_at=T0,
        config=ProximityConfig(samples=128),
    )
    assert e.own_age_seconds == 60
    assert e.target_age_seconds == 0
    assert e.nominal_minimum_separation_nm >= 0


def test_invalid_configuration_and_uncertainty_rejected() -> None:
    with pytest.raises(ValueError):
        KinematicUncertainty(position_sigma_m=-1, sog_sigma_kn=0, cog_sigma_deg=0)
    with pytest.raises(ValueError):
        ProximityConfig(samples=0)
    with pytest.raises(ValueError):
        ProximityConfig(proximity_threshold_nm=0)


def test_pair_requires_distinct_vessels_and_timezone() -> None:
    own = _ship(1, 14.5, 5, 90)
    with pytest.raises(ValueError, match="distinct"):
        estimate_projected_proximity(own, own, ZERO, ZERO, evaluated_at=T0)
    target = _ship(2, 14.51, 5, 270)
    with pytest.raises(ValueError, match="timezone"):
        estimate_projected_proximity(
            own, target, ZERO, ZERO, evaluated_at=datetime(2026, 8, 3, 12),
        )

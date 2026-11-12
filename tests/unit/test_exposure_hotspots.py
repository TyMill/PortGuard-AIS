"""Controlled checks for episode-count / observed-pair-hours hotspot maps."""

from datetime import UTC, datetime, timedelta
from math import degrees, isclose

import pytest

from portguard_ais.models import VesselObservation
from portguard_ais.near_miss.episodes import NearMissEpisode
from portguard_ais.near_miss.exposure_hotspots import (
    EARTH_RADIUS_M,
    ExposureGridConfig,
    aggregate_exposure_hotspots,
)
from portguard_ais.pipeline import PortGuardPipeline

T0 = datetime(2026, 8, 3, 12, tzinfo=UTC)
GRID = ExposureGridConfig(
    origin_lat_deg=0,
    origin_lon_deg=0,
    cell_size_m=1000,
    max_pair_gap_seconds=4000,
    minimum_pair_hours=0.1,
)


def _assessment(
    seconds: int,
    east_m: float,
    *,
    pair: tuple[int, int] = (1, 2),
    north_m: float = 500.0,
):
    lat = degrees(north_m / EARTH_RADIUS_M)
    lon = degrees(east_m / EARTH_RADIUS_M)
    at = T0 + timedelta(seconds=seconds)
    own = VesselObservation(
        timestamp=at, mmsi=pair[0], lat=lat, lon=lon, sog=1.0, cog=90.0
    )
    target = VesselObservation(
        timestamp=at, mmsi=pair[1], lat=lat, lon=lon, sog=1.0, cog=90.0
    )
    return PortGuardPipeline().assess_pair(own, target)


def _event(east_m: float, *, event_id: str = "candidate-1") -> NearMissEpisode:
    return NearMissEpisode(
        episode_id=event_id,
        encounter_id="enc-test",
        own_mmsi=1,
        target_mmsi=2,
        started_at=T0,
        ended_at=T0 + timedelta(seconds=30),
        observation_count=2,
        peak_risk_score=0.8,
        minimum_dcpa_nm=0.1,
        minimum_tcpa_min=5.0,
        midpoint_lat=degrees(500.0 / EARTH_RADIUS_M),
        midpoint_lon=degrees(east_m / EARTH_RADIUS_M),
    )


def test_pair_exposure_conserved_when_crossing_grid_boundary() -> None:
    report = aggregate_exposure_hotspots(
        [_assessment(0, 500), _assessment(3600, 1500)],
        [_event(500)],
        GRID,
    )
    assert report.accepted_pair_segments == 1
    assert isclose(report.total_pair_hours, 1.0, abs_tol=1e-10)
    assert len(report.cells) == 2
    assert all(isclose(c.eligible_pair_hours, 0.5, abs_tol=1e-10) for c in report.cells)
    with_events = [c for c in report.cells if c.candidate_episode_count == 1]
    assert len(with_events) == 1
    assert with_events[0].candidate_events_per_1000_pair_hours == pytest.approx(2000.0)
    without_events = [c for c in report.cells if c.candidate_episode_count == 0]
    assert without_events[0].candidate_events_per_1000_pair_hours == 0.0


def test_unobserved_candidate_cell_has_undefined_rate() -> None:
    report = aggregate_exposure_hotspots(
        [_assessment(0, 500), _assessment(3600, 500)],
        [_event(2500)],
        GRID,
    )
    candidate = next(c for c in report.cells if c.candidate_episode_count)
    assert candidate.eligible_pair_hours == 0.0
    assert candidate.candidate_events_per_1000_pair_hours is None
    assert not candidate.exposure_sufficient


def test_pair_counts_deduplicate_identical_timestamps() -> None:
    a = _assessment(0, 500)
    b = _assessment(3600, 500)
    report = aggregate_exposure_hotspots([a, a, b], [], GRID)
    assert report.total_pair_hours == pytest.approx(1.0)
    assert report.accepted_pair_segments == 1


def test_long_missing_period_is_not_counted_as_exposure() -> None:
    config = ExposureGridConfig(
        origin_lat_deg=0, origin_lon_deg=0, max_pair_gap_seconds=120
    )
    report = aggregate_exposure_hotspots(
        [_assessment(0, 500), _assessment(3600, 500)],
        [],
        config,
    )
    assert report.total_pair_hours == 0
    assert report.excluded_pair_segments == 1


def test_reject_unrealistically_fast_midpoint_change() -> None:
    config = ExposureGridConfig(
        origin_lat_deg=0,
        origin_lon_deg=0,
        cell_size_m=500,
        max_pair_gap_seconds=120,
        max_midpoint_speed_kn=5,
    )
    report = aggregate_exposure_hotspots(
        [_assessment(0, 500), _assessment(60, 2500)],
        [],
        config,
    )
    assert report.accepted_pair_segments == 0
    assert report.excluded_pair_segments == 1
    assert report.total_pair_hours == 0


def test_eligible_observation_pair_is_not_just_risk_positive() -> None:
    report = aggregate_exposure_hotspots(
        [_assessment(0, 500), _assessment(3600, 500)],
        [],
        GRID,
    )
    assert report.total_pair_hours == pytest.approx(1)
    assert len(report.cells) == 1
    assert report.cells[0].candidate_episode_count == 0


def test_pair_hours_accumulate_across_different_vessel_pairs() -> None:
    report = aggregate_exposure_hotspots(
        [
            _assessment(0, 500, pair=(1, 2)),
            _assessment(3600, 500, pair=(1, 2)),
            _assessment(0, 500, pair=(3, 4)),
            _assessment(3600, 500, pair=(3, 4)),
        ],
        [],
        GRID,
    )
    assert report.total_pair_hours == pytest.approx(2.0)


def test_minimum_exposure_removes_unreliable_rate_but_not_count() -> None:
    config = ExposureGridConfig(
        origin_lat_deg=0,
        origin_lon_deg=0,
        max_pair_gap_seconds=120,
        minimum_pair_hours=1,
    )
    report = aggregate_exposure_hotspots(
        [_assessment(0, 500), _assessment(60, 500)],
        [_event(500)],
        config,
    )
    cell = report.cells[0]
    assert cell.candidate_episode_count == 1
    assert cell.candidate_events_per_1000_pair_hours is None


def test_duplicate_episode_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate candidate episode"):
        aggregate_exposure_hotspots([], [_event(500), _event(500)], GRID)


def test_missing_candidate_location_reported() -> None:
    missing = _event(500)
    missing = NearMissEpisode(
        **{
            **vars(missing),
            "midpoint_lat": None,
            "midpoint_lon": None,
        }
    )
    report = aggregate_exposure_hotspots([], [missing], GRID)
    assert report.unlocated_episodes == 1
    assert report.assigned_episodes == 0


def test_local_grid_validation() -> None:
    with pytest.raises(ValueError):
        ExposureGridConfig(origin_lat_deg=90, origin_lon_deg=0)
    with pytest.raises(ValueError):
        ExposureGridConfig(origin_lat_deg=0, origin_lon_deg=0, cell_size_m=0)
    with pytest.raises(ValueError, match="outside"):
        aggregate_exposure_hotspots([], [_event(100_000)], GRID)

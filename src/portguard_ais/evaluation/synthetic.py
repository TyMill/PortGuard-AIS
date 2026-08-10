"""Deterministic synthetic AIS scenarios for examples and regression tests."""

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pandas as pd

from portguard_ais.enums import EncounterType
from portguard_ais.geometry.geodesy import EARTH_RADIUS_NM


@dataclass(frozen=True)
class ArticleScenarioDefinition:
    """Metadata for one deterministic SoftwareX demonstration scenario."""

    name: str
    own_mmsi: int
    target_mmsi: int
    expected_encounter: EncounterType
    expected_colreg_rule: str
    description: str


ARTICLE_SCENARIOS: tuple[ArticleScenarioDefinition, ...] = (
    ArticleScenarioDefinition(
        name="head-on",
        own_mmsi=261100001,
        target_mmsi=261100002,
        expected_encounter=EncounterType.HEAD_ON,
        expected_colreg_rule="Rule 14",
        description="Two power-driven vessels approach on reciprocal east-west courses.",
    ),
    ArticleScenarioDefinition(
        name="crossing",
        own_mmsi=261200001,
        target_mmsi=261200002,
        expected_encounter=EncounterType.CROSSING_STARBOARD,
        expected_colreg_rule="Rule 15",
        description="An eastbound own vessel encounters a northbound target on starboard.",
    ),
    ArticleScenarioDefinition(
        name="overtaking",
        own_mmsi=261300001,
        target_mmsi=261300002,
        expected_encounter=EncounterType.OVERTAKING,
        expected_colreg_rule="Rule 13",
        description="A faster eastbound own vessel closes on a slower vessel from abaft the beam.",
    ),
)


def _position_after(
    lat: float,
    lon: float,
    sog_kn: float,
    cog_deg: float,
    elapsed_seconds: float,
) -> tuple[float, float]:
    """Advance a position with the same local-plane convention used by the library."""
    distance_nm = sog_kn * elapsed_seconds / 3600.0
    angle = math.radians(cog_deg)
    east_nm = distance_nm * math.sin(angle)
    north_nm = distance_nm * math.cos(angle)
    out_lat = lat + math.degrees(north_nm / EARTH_RADIUS_NM)
    latitude_reference = math.radians((lat + out_lat) / 2.0)
    cosine = max(abs(math.cos(latitude_reference)), 1e-9)
    out_lon = lon + math.degrees(east_nm / (EARTH_RADIUS_NM * cosine))
    return out_lat, out_lon


def _row(
    *,
    timestamp: datetime,
    mmsi: int,
    start_lat: float,
    start_lon: float,
    sog: float,
    cog: float,
    elapsed_seconds: float,
    length_m: float,
    beam_m: float,
    vessel_type: str,
) -> dict[str, object]:
    lat, lon = _position_after(start_lat, start_lon, sog, cog, elapsed_seconds)
    return {
        "timestamp": timestamp.isoformat(),
        "mmsi": mmsi,
        "lat": lat,
        "lon": lon,
        "sog": sog,
        "cog": cog,
        "heading": cog,
        "length_m": length_m,
        "beam_m": beam_m,
        "vessel_type": vessel_type,
        "position_accuracy_m": 10.0,
        "source": "synthetic-deterministic",
    }


def synthetic_scenarios(steps: int = 8, interval_seconds: int = 30) -> pd.DataFrame:
    """Generate the original four-vessel regression dataset."""
    start = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    rows: list[dict[str, object]] = []
    for step in range(steps):
        timestamp = start + timedelta(seconds=step * interval_seconds)
        rows.extend(
            [
                {
                    "timestamp": timestamp.isoformat(),
                    "mmsi": 261000001,
                    "lat": 53.4000,
                    "lon": 14.6000 + step * 0.0012,
                    "sog": 10.0,
                    "cog": 90.0,
                    "heading": 90.0,
                    "length_m": 140.0,
                    "position_accuracy_m": 10.0,
                },
                {
                    "timestamp": timestamp.isoformat(),
                    "mmsi": 261000002,
                    "lat": 53.4000,
                    "lon": 14.6400 - step * 0.0012,
                    "sog": 10.0,
                    "cog": 270.0,
                    "heading": 270.0,
                    "length_m": 120.0,
                    "position_accuracy_m": 10.0,
                },
                {
                    "timestamp": timestamp.isoformat(),
                    "mmsi": 261000003,
                    "lat": 53.3800 + step * 0.0010,
                    "lon": 14.6200,
                    "sog": 8.0,
                    "cog": 0.0,
                    "heading": 0.0,
                    "length_m": 90.0,
                    "position_accuracy_m": 15.0,
                },
                {
                    "timestamp": timestamp.isoformat(),
                    "mmsi": 261000004,
                    "lat": 53.4100,
                    "lon": 14.6000 + step * 0.0008,
                    "sog": 7.0,
                    "cog": 90.0,
                    "heading": 90.0,
                    "length_m": 70.0,
                    "position_accuracy_m": 15.0,
                },
            ]
        )
    return pd.DataFrame(rows)


def article_scenarios(steps: int = 12, interval_seconds: int = 30) -> pd.DataFrame:
    """Generate isolated, physically consistent Rule 14, 15 and 13 scenarios.

    Each pair occupies a separate latitude band more than six nautical miles from
    the others. Therefore, the default pair pre-filter yields exactly three
    independent encounter timelines at every timestamp.
    """
    if steps < 2:
        raise ValueError("steps must be at least 2")
    if interval_seconds < 1:
        raise ValueError("interval_seconds must be positive")

    start = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    rows: list[dict[str, object]] = []

    for step in range(steps):
        elapsed = float(step * interval_seconds)
        timestamp = start + timedelta(seconds=elapsed)

        # Rule 14: reciprocal courses, initial separation about 1.07 NM.
        rows.extend(
            [
                _row(
                    timestamp=timestamp,
                    mmsi=261100001,
                    start_lat=53.4000,
                    start_lon=14.5900,
                    sog=10.0,
                    cog=90.0,
                    elapsed_seconds=elapsed,
                    length_m=140.0,
                    beam_m=22.0,
                    vessel_type="cargo",
                ),
                _row(
                    timestamp=timestamp,
                    mmsi=261100002,
                    start_lat=53.4000,
                    start_lon=14.6200,
                    sog=10.0,
                    cog=270.0,
                    elapsed_seconds=elapsed,
                    length_m=120.0,
                    beam_m=20.0,
                    vessel_type="cargo",
                ),
            ]
        )

        # Rule 15: eastbound own vessel and northbound target reach the
        # intersection at nearly the same time (~3.6 min from the start).
        rows.extend(
            [
                _row(
                    timestamp=timestamp,
                    mmsi=261200001,
                    start_lat=53.6000,
                    start_lon=14.5900,
                    sog=9.0,
                    cog=90.0,
                    elapsed_seconds=elapsed,
                    length_m=110.0,
                    beam_m=18.0,
                    vessel_type="cargo",
                ),
                _row(
                    timestamp=timestamp,
                    mmsi=261200002,
                    start_lat=53.5921,
                    start_lon=14.6050,
                    sog=8.0,
                    cog=0.0,
                    elapsed_seconds=elapsed,
                    length_m=85.0,
                    beam_m=15.0,
                    vessel_type="tanker",
                ),
            ]
        )

        # Rule 13: faster vessel begins astern and overtakes on the same course.
        rows.extend(
            [
                _row(
                    timestamp=timestamp,
                    mmsi=261300001,
                    start_lat=53.8000,
                    start_lon=14.5900,
                    sog=14.0,
                    cog=90.0,
                    elapsed_seconds=elapsed,
                    length_m=100.0,
                    beam_m=17.0,
                    vessel_type="cargo",
                ),
                _row(
                    timestamp=timestamp,
                    mmsi=261300002,
                    start_lat=53.8000,
                    start_lon=14.6020,
                    sog=7.0,
                    cog=90.0,
                    elapsed_seconds=elapsed,
                    length_m=130.0,
                    beam_m=21.0,
                    vessel_type="cargo",
                ),
            ]
        )

    return pd.DataFrame(rows)

from datetime import UTC, datetime

import pandas as pd

from portguard_ais.preprocessing.resampling import resample_tracks


def test_resampling_interpolates_short_gap() -> None:
    frame = pd.DataFrame(
        [
            {
                "timestamp": datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
                "mmsi": 1,
                "lat": 53.4,
                "lon": 14.6,
                "sog": 5.0,
                "cog": 90.0,
                "vessel_type": "cargo",
                "length_m": 100.0,
            },
            {
                "timestamp": datetime(2026, 8, 3, 12, 1, tzinfo=UTC),
                "mmsi": 1,
                "lat": 53.4,
                "lon": 14.62,
                "sog": 7.0,
                "cog": 90.0,
                "vessel_type": "cargo",
                "length_m": 100.0,
            },
        ]
    )
    result = resample_tracks(frame, seconds=30, interpolation_limit=2)
    assert len(result) == 3
    middle = result.iloc[1]
    assert middle["lon"] == 14.61
    assert middle["sog"] == 6.0
    assert middle["vessel_type"] == "cargo"


def test_resampling_empty_frame() -> None:
    frame = pd.DataFrame(columns=["timestamp", "mmsi", "lat", "lon", "sog", "cog"])
    assert resample_tracks(frame, seconds=30).empty


def test_resampling_wraps_course_and_heading_across_north() -> None:
    frame = pd.DataFrame(
        [
            {
                "timestamp": datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
                "mmsi": 7,
                "lat": 53.4,
                "lon": 14.6,
                "sog": 5.0,
                "cog": 359.0,
                "heading": 358.0,
            },
            {
                "timestamp": datetime(2026, 8, 3, 12, 1, tzinfo=UTC),
                "mmsi": 7,
                "lat": 53.4,
                "lon": 14.62,
                "sog": 5.0,
                "cog": 1.0,
                "heading": 2.0,
            },
        ]
    )
    result = resample_tracks(frame, seconds=30, interpolation_limit=2)
    assert len(result) == 3
    middle = result.iloc[1]
    assert min(abs(middle["cog"]), abs(middle["cog"] - 360.0)) < 1e-8
    assert min(abs(middle["heading"]), abs(middle["heading"] - 360.0)) < 1e-8
    assert result.iloc[0]["cog"] == 359.0
    assert result.iloc[-1]["cog"] == 1.0


def test_resampling_disabled_interpolation_does_not_create_missing_data() -> None:
    frame = pd.DataFrame(
        [
            {"timestamp": datetime(2026, 8, 3, 12, tzinfo=UTC), "mmsi": 1,
             "lat": 53.4, "lon": 14.6, "sog": 5.0, "cog": 359.0},
            {"timestamp": datetime(2026, 8, 3, 12, 1, tzinfo=UTC), "mmsi": 1,
             "lat": 53.4, "lon": 14.62, "sog": 5.0, "cog": 1.0},
        ]
    )
    result = resample_tracks(frame, seconds=30, interpolation_limit=0)
    assert len(result) == 2

"""Tests for causal AIS synchronization and observation provenance."""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from portguard_ais.preprocessing.causal_alignment import align_causal_snapshots


def _row(seconds: int, mmsi: int, lon: float) -> dict[str, object]:
    return {
        "timestamp": datetime(2026, 8, 3, 12, tzinfo=UTC) + timedelta(seconds=seconds),
        "mmsi": mmsi,
        "lat": 53.5,
        "lon": lon,
        "sog": 5.0,
        "cog": 90.0,
    }


def test_causal_alignment_retains_measurement_provenance() -> None:
    frame = pd.DataFrame([_row(0, 1, 14.5), _row(10, 2, 14.6), _row(20, 1, 14.55)])
    aligned = align_causal_snapshots(frame, seconds=10, max_age_seconds=10)
    at_10 = aligned.loc[aligned["timestamp"] == pd.Timestamp("2026-08-03T12:00:10Z")]
    assert set(at_10["mmsi"].astype(int)) == {1, 2}
    stale = at_10.loc[at_10["mmsi"] == 1].iloc[0]
    assert stale["source_timestamp"] == pd.Timestamp("2026-08-03T12:00:00Z")
    assert stale["age_seconds"] == 10
    assert bool(stale["is_carried"])
    fresh = at_10.loc[at_10["mmsi"] == 2].iloc[0]
    assert fresh["age_seconds"] == 0
    assert not bool(fresh["is_carried"])


def test_never_uses_future_ais_message() -> None:
    aligned = align_causal_snapshots(
        pd.DataFrame([_row(5, 1, 14.5), _row(25, 1, 14.8)]),
        seconds=10,
        max_age_seconds=10,
    )
    assert not (aligned["source_timestamp"] > aligned["timestamp"]).any()
    at_20 = aligned.loc[aligned["timestamp"] == pd.Timestamp("2026-08-03T12:00:20Z")]
    assert at_20.empty
    at_30 = aligned.loc[aligned["timestamp"] == pd.Timestamp("2026-08-03T12:00:30Z")]
    assert at_30.iloc[0]["lon"] == 14.8


def test_stale_observation_excluded() -> None:
    aligned = align_causal_snapshots(
        pd.DataFrame([_row(0, 1, 14.5), _row(30, 2, 14.6)]),
        seconds=10,
        max_age_seconds=10,
    )
    at_30 = aligned.loc[aligned["timestamp"] == pd.Timestamp("2026-08-03T12:00:30Z")]
    assert set(at_30["mmsi"].astype(int)) == {2}


def test_alignment_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError):
        align_causal_snapshots(pd.DataFrame(), seconds=0)
    with pytest.raises(ValueError):
        align_causal_snapshots(pd.DataFrame(), max_age_seconds=-1)


def test_alignment_does_not_overwrite_original_frame() -> None:
    frame = pd.DataFrame([_row(0, 1, 14.5), _row(10, 1, 14.6)])
    before = frame.copy(deep=True)
    align_causal_snapshots(frame, seconds=10)
    pd.testing.assert_frame_equal(frame, before)

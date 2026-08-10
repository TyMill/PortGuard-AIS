from datetime import UTC, datetime, timedelta

import pytest

from portguard_ais.models import VesselObservation
from portguard_ais.preprocessing.anomalies import detect_kinematic_anomalies


def test_detects_position_jump() -> None:
    start = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    observations = [
        VesselObservation(timestamp=start, mmsi=1, lat=53.4, lon=14.6, sog=5, cog=90),
        VesselObservation(
            timestamp=start + timedelta(seconds=60),
            mmsi=1,
            lat=53.4,
            lon=15.6,
            sog=5,
            cog=90,
        ),
    ]
    anomalies = detect_kinematic_anomalies(observations, maximum_implied_speed_kn=80)
    assert len(anomalies) == 1
    assert anomalies[0].mmsi == 1
    assert anomalies[0].implied_speed_kn > anomalies[0].threshold_kn


def test_nonpositive_threshold_is_rejected() -> None:
    with pytest.raises(ValueError):
        detect_kinematic_anomalies([], maximum_implied_speed_kn=0)

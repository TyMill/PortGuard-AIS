from datetime import UTC, datetime

import pytest

from portguard_ais.models import VesselObservation


@pytest.fixture
def timestamp() -> datetime:
    return datetime(2026, 8, 3, 12, 0, tzinfo=UTC)


@pytest.fixture
def eastbound(timestamp: datetime) -> VesselObservation:
    return VesselObservation(
        timestamp=timestamp,
        mmsi=261000001,
        lat=53.4,
        lon=14.6,
        sog=10.0,
        cog=90.0,
        heading=90.0,
        length_m=140.0,
        position_accuracy_m=10.0,
    )

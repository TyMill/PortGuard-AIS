from datetime import datetime

import pytest
from pydantic import ValidationError

from portguard_ais.models import VesselObservation


def test_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError):
        VesselObservation(
            timestamp=datetime.fromisoformat("2026-08-03T12:00:00"),
            mmsi=1,
            lat=0.0,
            lon=0.0,
            sog=1.0,
            cog=0.0,
        )


def test_invalid_course_is_rejected(timestamp: datetime) -> None:
    with pytest.raises(ValidationError):
        VesselObservation(
            timestamp=timestamp,
            mmsi=1,
            lat=0.0,
            lon=0.0,
            sog=1.0,
            cog=360.0,
        )

from datetime import datetime

from portguard_ais.models import VesselObservation
from portguard_ais.risk.confidence import estimate_confidence


def test_confidence_penalizes_missing_quality_fields(timestamp: datetime) -> None:
    complete = VesselObservation(
        timestamp=timestamp,
        mmsi=1,
        lat=53.4,
        lon=14.6,
        sog=5,
        cog=90,
        heading=90,
        length_m=100,
        position_accuracy_m=10,
    )
    incomplete = VesselObservation(
        timestamp=timestamp,
        mmsi=2,
        lat=53.4,
        lon=14.61,
        sog=5,
        cog=270,
    )
    poor_accuracy = VesselObservation(
        timestamp=timestamp,
        mmsi=3,
        lat=53.4,
        lon=14.62,
        sog=5,
        cog=270,
        heading=270,
        length_m=100,
        position_accuracy_m=100,
    )
    assert estimate_confidence(complete, incomplete) < 1.0
    assert estimate_confidence(complete, poor_accuracy) < 1.0

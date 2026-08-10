from datetime import datetime

from portguard_ais.encounters.classifier import classify_encounter
from portguard_ais.enums import EncounterType
from portguard_ais.geometry.relative_motion import solve_relative_motion
from portguard_ais.models import VesselObservation


def test_head_on_classification(eastbound: VesselObservation, timestamp: datetime) -> None:
    target = VesselObservation(
        timestamp=timestamp,
        mmsi=2,
        lat=53.4,
        lon=14.66,
        sog=10.0,
        cog=270.0,
    )
    motion = solve_relative_motion(eastbound, target, 60.0)
    assert classify_encounter(eastbound, target, motion) == EncounterType.HEAD_ON


def test_diverging_classification(eastbound: VesselObservation, timestamp: datetime) -> None:
    target = VesselObservation(
        timestamp=timestamp,
        mmsi=2,
        lat=53.4,
        lon=14.59,
        sog=10.0,
        cog=270.0,
    )
    motion = solve_relative_motion(eastbound, target, 60.0)
    assert classify_encounter(eastbound, target, motion) == EncounterType.DIVERGING

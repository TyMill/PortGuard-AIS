from datetime import datetime

from portguard_ais.geometry.relative_motion import solve_relative_motion
from portguard_ais.models import VesselObservation


def test_head_on_solution_has_small_dcpa(eastbound: VesselObservation, timestamp: datetime) -> None:
    westbound = VesselObservation(
        timestamp=timestamp,
        mmsi=2,
        lat=53.4,
        lon=14.66,
        sog=10.0,
        cog=270.0,
    )
    motion = solve_relative_motion(eastbound, westbound, 60.0)
    assert motion.converging
    assert motion.dcpa_nm < 0.01
    assert motion.tcpa_min > 0.0
    assert motion.relative_speed_kn > 19.0


def test_diverging_solution_uses_current_position(
    eastbound: VesselObservation, timestamp: datetime
) -> None:
    target = VesselObservation(
        timestamp=timestamp,
        mmsi=2,
        lat=53.4,
        lon=14.59,
        sog=10.0,
        cog=270.0,
    )
    motion = solve_relative_motion(eastbound, target, 60.0)
    assert not motion.converging
    assert motion.tcpa_min == 0.0
    assert motion.dcpa_nm == motion.current_distance_nm

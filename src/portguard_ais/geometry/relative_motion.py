"""Relative-motion and closest-point calculations."""

import math

from portguard_ais.geometry.geodesy import displacement_nm, relative_bearing_deg, velocity_kn
from portguard_ais.models import RelativeMotion, VesselObservation


def solve_relative_motion(
    own: VesselObservation,
    target: VesselObservation,
    horizon_min: float,
) -> RelativeMotion:
    """Calculate CPA/TCPA using constant velocity within a bounded horizon."""
    east, north = displacement_nm(own, target)
    own_east, own_north = velocity_kn(own)
    target_east, target_north = velocity_kn(target)
    relative_east = target_east - own_east
    relative_north = target_north - own_north

    current_distance = math.hypot(east, north)
    relative_speed = math.hypot(relative_east, relative_north)
    dot = east * relative_east + north * relative_north
    converging = dot < 0.0 and relative_speed > 1e-9

    if not converging:
        tcpa_min = 0.0
        cpa_east = east
        cpa_north = north
    else:
        raw_tcpa_hours = -dot / (relative_speed * relative_speed)
        tcpa_min = min(raw_tcpa_hours * 60.0, horizon_min)
        cpa_east = east + relative_east * (tcpa_min / 60.0)
        cpa_north = north + relative_north * (tcpa_min / 60.0)

    closing_speed = 0.0
    if current_distance > 1e-9:
        closing_speed = max(0.0, -dot / current_distance)

    return RelativeMotion(
        current_distance_nm=round(current_distance, 6),
        dcpa_nm=round(math.hypot(cpa_east, cpa_north), 6),
        tcpa_min=round(tcpa_min, 6),
        relative_speed_kn=round(relative_speed, 6),
        closing_speed_kn=round(closing_speed, 6),
        converging=converging,
        relative_bearing_deg=round(relative_bearing_deg(own, target), 6),
        cpa_east_nm=round(cpa_east, 6),
        cpa_north_nm=round(cpa_north, 6),
    )

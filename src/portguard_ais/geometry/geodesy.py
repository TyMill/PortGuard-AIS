"""Local tangent-plane approximations for short port-scale separations."""

import math

from portguard_ais.models import VesselObservation

EARTH_RADIUS_NM = 3440.065


def displacement_nm(origin: VesselObservation, target: VesselObservation) -> tuple[float, float]:
    """Return east/north displacement in nautical miles."""
    latitude_reference = math.radians((origin.lat + target.lat) / 2.0)
    east = EARTH_RADIUS_NM * math.radians(target.lon - origin.lon) * math.cos(latitude_reference)
    north = EARTH_RADIUS_NM * math.radians(target.lat - origin.lat)
    return east, north


def distance_nm(origin: VesselObservation, target: VesselObservation) -> float:
    """Return short-range planar distance in nautical miles."""
    east, north = displacement_nm(origin, target)
    return math.hypot(east, north)


def velocity_kn(observation: VesselObservation) -> tuple[float, float]:
    """Convert COG/SOG to east/north velocity components in knots."""
    angle = math.radians(observation.cog)
    return observation.sog * math.sin(angle), observation.sog * math.cos(angle)


def wrap_angle_deg(angle: float) -> float:
    """Wrap an angle to [-180, 180)."""
    return (angle + 180.0) % 360.0 - 180.0


def relative_bearing_deg(own: VesselObservation, target: VesselObservation) -> float:
    """Return target bearing relative to own COG."""
    east, north = displacement_nm(own, target)
    absolute_bearing = math.degrees(math.atan2(east, north)) % 360.0
    return wrap_angle_deg(absolute_bearing - own.cog)

from datetime import datetime

import pytest

from portguard_ais.geometry.geodesy import distance_nm, relative_bearing_deg, wrap_angle_deg
from portguard_ais.models import VesselObservation


def _vessel(
    timestamp: datetime, mmsi: int, lat: float, lon: float, cog: float
) -> VesselObservation:
    return VesselObservation(timestamp=timestamp, mmsi=mmsi, lat=lat, lon=lon, sog=5.0, cog=cog)


def test_one_degree_latitude_is_about_sixty_nm(timestamp: datetime) -> None:
    first = _vessel(timestamp, 1, 0.0, 0.0, 0.0)
    second = _vessel(timestamp, 2, 1.0, 0.0, 0.0)
    assert distance_nm(first, second) == pytest.approx(60.04, rel=0.01)


def test_relative_bearing_east(timestamp: datetime) -> None:
    own = _vessel(timestamp, 1, 53.4, 14.6, 0.0)
    target = _vessel(timestamp, 2, 53.4, 14.61, 0.0)
    assert relative_bearing_deg(own, target) == pytest.approx(90.0, abs=0.1)


def test_angle_wrapping() -> None:
    assert wrap_angle_deg(190.0) == -170.0
    assert wrap_angle_deg(-190.0) == 170.0

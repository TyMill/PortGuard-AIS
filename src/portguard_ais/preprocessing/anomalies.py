"""Kinematic AIS anomaly checks for jumps, spoofing indicators and bad data."""

from collections import defaultdict
from collections.abc import Iterable
from itertools import pairwise

from portguard_ais.geometry.geodesy import distance_nm
from portguard_ais.models import KinematicAnomaly, VesselObservation


def detect_kinematic_anomalies(
    observations: Iterable[VesselObservation],
    maximum_implied_speed_kn: float = 80.0,
) -> list[KinematicAnomaly]:
    """Detect consecutive positions implying an implausibly high ground speed."""
    if maximum_implied_speed_kn <= 0.0:
        raise ValueError("maximum_implied_speed_kn must be positive")

    by_vessel: dict[int, list[VesselObservation]] = defaultdict(list)
    for observation in observations:
        by_vessel[observation.mmsi].append(observation)

    anomalies: list[KinematicAnomaly] = []
    for mmsi, track in by_vessel.items():
        ordered = sorted(track, key=lambda item: item.timestamp)
        for previous, current in pairwise(ordered):
            elapsed_hours = (current.timestamp - previous.timestamp).total_seconds() / 3600.0
            if elapsed_hours <= 0.0:
                continue
            implied_speed = distance_nm(previous, current) / elapsed_hours
            if implied_speed > maximum_implied_speed_kn:
                anomalies.append(
                    KinematicAnomaly(
                        mmsi=mmsi,
                        started_at=previous.timestamp,
                        ended_at=current.timestamp,
                        implied_speed_kn=round(implied_speed, 4),
                        threshold_kn=maximum_implied_speed_kn,
                        reason="consecutive AIS positions imply excessive ground speed",
                    )
                )
    return anomalies

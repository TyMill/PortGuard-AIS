"""Utilities for deterministic processing of observation streams."""

from collections.abc import Iterable, Iterator
from itertools import groupby

from portguard_ais.models import VesselObservation


def iter_snapshots(
    observations: Iterable[VesselObservation],
) -> Iterator[list[VesselObservation]]:
    """Yield timestamp-homogeneous snapshots in chronological order.

    The function deliberately sorts its input, making offline replay reproducible even when
    observations arrive in a different order than they were recorded.
    """
    ordered = sorted(observations, key=lambda item: (item.timestamp, item.mmsi))
    for _, group in groupby(ordered, key=lambda item: item.timestamp):
        yield list(group)

"""Candidate pair generation with a distance pre-filter."""

from collections.abc import Iterable, Iterator
from itertools import combinations

from portguard_ais.config import PairingConfig
from portguard_ais.geometry.geodesy import distance_nm
from portguard_ais.models import VesselObservation


def candidate_pairs(
    observations: Iterable[VesselObservation],
    config: PairingConfig,
) -> Iterator[tuple[VesselObservation, VesselObservation]]:
    """Yield deterministic MMSI-ordered pairs within the configured distance."""
    active = sorted(
        (observation for observation in observations if observation.sog >= config.minimum_sog_kn),
        key=lambda observation: observation.mmsi,
    )
    for first, second in combinations(active, 2):
        if distance_nm(first, second) <= config.max_pair_distance_nm:
            yield first, second

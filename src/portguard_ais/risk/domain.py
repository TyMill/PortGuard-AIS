"""Dynamic elliptical vessel-domain assessment."""

import math

from portguard_ais.config import DomainConfig
from portguard_ais.models import DomainAssessment, RelativeMotion, VesselObservation

_METRES_PER_NAUTICAL_MILE = 1852.0


def assess_ship_domain(
    own: VesselObservation,
    motion: RelativeMotion,
    config: DomainConfig,
) -> DomainAssessment:
    """Evaluate predicted CPA position in a speed- and length-aware own-ship domain."""
    length_m = max(own.length_m or config.default_length_m, config.minimum_length_m)
    speed_extension_m = own.sog * 0.514444 * config.speed_factor_seconds

    forward_nm = (length_m * config.forward_length_factor + speed_extension_m) / (
        _METRES_PER_NAUTICAL_MILE
    )
    aft_nm = (length_m * config.aft_length_factor) / _METRES_PER_NAUTICAL_MILE
    lateral_nm = (length_m * config.lateral_length_factor) / _METRES_PER_NAUTICAL_MILE

    angle = math.radians(own.cog)
    forward_component = motion.cpa_east_nm * math.sin(angle) + motion.cpa_north_nm * math.cos(angle)
    starboard_component = motion.cpa_east_nm * math.cos(angle) - motion.cpa_north_nm * math.sin(
        angle
    )
    longitudinal_radius = forward_nm if forward_component >= 0.0 else aft_nm
    normalized = math.sqrt(
        (forward_component / max(longitudinal_radius, 1e-9)) ** 2
        + (starboard_component / max(lateral_nm, 1e-9)) ** 2
    )

    return DomainAssessment(
        forward_nm=round(forward_nm, 6),
        aft_nm=round(aft_nm, 6),
        lateral_nm=round(lateral_nm, 6),
        normalized_distance=round(normalized, 6),
        violated=normalized <= 1.0,
    )

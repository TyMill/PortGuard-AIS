"""Seeded geometry perturbations for controlled JMSE robustness tests."""

import math
import random

from portguard_ais.evaluation.jmse_scenarios import JMSEScenario
from portguard_ais.geometry.geodesy import EARTH_RADIUS_NM
from portguard_ais.models import VesselObservation


def _offset_observation(
    observation: VesselObservation,
    *,
    north_nm: float,
    east_nm: float,
) -> VesselObservation:
    lat_delta = math.degrees(north_nm / EARTH_RADIUS_NM)
    cosine = max(abs(math.cos(math.radians(observation.lat))), 1e-9)
    lon_delta = math.degrees(east_nm / (EARTH_RADIUS_NM * cosine))
    return observation.model_copy(
        update={
            "lat": observation.lat + lat_delta,
            "lon": observation.lon + lon_delta,
            "source": "jmse-controlled-jittered",
        }
    )


def jitter_scenarios(
    scenarios: tuple[JMSEScenario, ...],
    *,
    seed: int,
    position_jitter_nm: float = 0.05,
) -> tuple[JMSEScenario, ...]:
    """Apply one fixed seeded position offset per vessel to each scenario trajectory."""
    if position_jitter_nm < 0.0:
        raise ValueError("position_jitter_nm must be non-negative")
    if position_jitter_nm == 0.0:
        return scenarios

    output: list[JMSEScenario] = []
    for scenario_index, scenario in enumerate(scenarios):
        rng = random.Random(seed + 1009 * (scenario_index + 1))
        mmsi_values = sorted(
            {observation.mmsi for snapshot in scenario.snapshots for observation in snapshot}
        )
        offsets = {
            mmsi: (
                rng.gauss(0.0, position_jitter_nm),
                rng.gauss(0.0, position_jitter_nm),
            )
            for mmsi in mmsi_values
        }
        snapshots = tuple(
            tuple(
                _offset_observation(
                    observation,
                    north_nm=offsets[observation.mmsi][0],
                    east_nm=offsets[observation.mmsi][1],
                )
                for observation in snapshot
            )
            for snapshot in scenario.snapshots
        )
        output.append(
            JMSEScenario(
                name=scenario.name,
                description=scenario.description,
                snapshots=snapshots,
                hazardous_steps=scenario.hazardous_steps,
                evidence_overrides=scenario.evidence_overrides,
            )
        )
    return tuple(output)

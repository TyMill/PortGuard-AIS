"""Input-quality confidence estimation."""

from portguard_ais.models import VesselObservation


def estimate_confidence(own: VesselObservation, target: VesselObservation) -> float:
    """Estimate assessment confidence from optional AIS quality information."""
    score = 1.0
    for observation in (own, target):
        if observation.position_accuracy_m is None or observation.position_accuracy_m > 50.0:
            score -= 0.08
        if observation.heading is None:
            score -= 0.04
        if observation.length_m is None:
            score -= 0.04
    return round(min(max(score, 0.0), 1.0), 4)

"""Optional static encounter geometry plot."""

from pathlib import Path

from portguard_ais.models import EncounterAssessment


def plot_encounter(assessment: EncounterAssessment, output: str | Path) -> Path:
    """Plot current vessel positions and their connecting separation line."""
    if assessment.own_position is None or assessment.target_position is None:
        raise ValueError("assessment does not contain geographic positions")
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Install PortGuard-AIS with the 'viz' extra") from exc

    own = assessment.own_position
    target = assessment.target_position
    figure, axis = plt.subplots()
    axis.scatter([own.lon, target.lon], [own.lat, target.lat])
    axis.plot([own.lon, target.lon], [own.lat, target.lat])
    axis.annotate(f"Own {assessment.own_mmsi}", (own.lon, own.lat))
    axis.annotate(f"Target {assessment.target_mmsi}", (target.lon, target.lat))
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.set_title(f"{assessment.encounter_type.value}: risk {assessment.risk_score:.3f}")
    target_path = Path(output)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(target_path, bbox_inches="tight")
    plt.close(figure)
    return target_path

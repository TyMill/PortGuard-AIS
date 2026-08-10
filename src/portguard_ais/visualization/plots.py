"""Optional time-series plotting API."""

from collections.abc import Sequence
from pathlib import Path

from portguard_ais.config import RiskThresholds
from portguard_ais.models import AlertDecision, EncounterAssessment


def plot_risk_timeline(
    assessments: Sequence[EncounterAssessment],
    output: str | Path,
    *,
    alerts: Sequence[AlertDecision] = (),
    thresholds: RiskThresholds | None = None,
) -> Path:
    """Plot collision-risk score over elapsed time with optional thresholds and alerts."""
    if not assessments:
        raise ValueError("At least one assessment is required")
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Install PortGuard-AIS with the 'viz' extra") from exc

    ordered = sorted(assessments, key=lambda item: item.timestamp)
    start = ordered[0].timestamp
    elapsed_minutes = [(item.timestamp - start).total_seconds() / 60.0 for item in ordered]
    scores = [item.risk_score for item in ordered]

    figure, axis = plt.subplots(figsize=(7.2, 4.5))
    axis.plot(elapsed_minutes, scores, marker="o", label="Risk score")

    active_thresholds = thresholds or RiskThresholds()
    for value, label in (
        (active_thresholds.watch, "WATCH"),
        (active_thresholds.warning, "WARNING"),
        (active_thresholds.critical, "CRITICAL"),
    ):
        axis.axhline(value, linestyle="--", linewidth=0.9, label=label)

    emitted = [alert for alert in alerts if alert.emitted]
    if emitted:
        alert_minutes = [(alert.timestamp - start).total_seconds() / 60.0 for alert in emitted]
        score_by_time = {item.timestamp: item.risk_score for item in ordered}
        alert_scores = [score_by_time.get(alert.timestamp, 0.0) for alert in emitted]
        axis.scatter(alert_minutes, alert_scores, marker="x", s=75, label="Emitted alert", zorder=5)
        for minute, score, alert in zip(alert_minutes, alert_scores, emitted, strict=True):
            axis.annotate(
                alert.current_state.value,
                (minute, score),
                xytext=(4, 6),
                textcoords="offset points",
                fontsize=8,
            )

    axis.set_xlabel("Elapsed time (min)")
    axis.set_ylabel("Collision-risk score")
    axis.set_ylim(0.0, 1.02)
    axis.grid(True, linestyle=":", linewidth=0.6)
    axis.legend(loc="best")
    axis.set_title("PortGuard-AIS stateful risk timeline")

    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(target, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return target

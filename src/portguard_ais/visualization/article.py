"""Publication-oriented visualizations for deterministic SoftwareX scenarios."""

import math
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from portguard_ais.geometry.geodesy import EARTH_RADIUS_NM
from portguard_ais.models import EncounterAssessment


def _local_xy_nm(
    lat: float,
    lon: float,
    reference_lat: float,
    reference_lon: float,
) -> tuple[float, float]:
    latitude_reference = math.radians((reference_lat + lat) / 2.0)
    east = EARTH_RADIUS_NM * math.radians(lon - reference_lon) * math.cos(latitude_reference)
    north = EARTH_RADIUS_NM * math.radians(lat - reference_lat)
    return east, north


def _velocity_kn(sog: float, cog: float) -> tuple[float, float]:
    angle = math.radians(cog)
    return sog * math.sin(angle), sog * math.cos(angle)


def plot_scenario_encounter(
    frame: pd.DataFrame,
    assessments: Sequence[EncounterAssessment],
    own_mmsi: int,
    target_mmsi: int,
    output: str | Path,
    *,
    title: str | None = None,
) -> Path:
    """Plot complete pair tracks and the peak-risk constant-velocity CPA projection."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Install PortGuard-AIS with the 'viz' extra") from exc

    pair_assessments = sorted(
        (
            item
            for item in assessments
            if item.own_mmsi == own_mmsi and item.target_mmsi == target_mmsi
        ),
        key=lambda item: item.timestamp,
    )
    if not pair_assessments:
        raise ValueError("No assessments found for the requested MMSI pair")

    tracks = frame.loc[frame["mmsi"].isin([own_mmsi, target_mmsi])].copy()
    tracks["timestamp"] = pd.to_datetime(tracks["timestamp"], utc=True)
    tracks = tracks.sort_values(["mmsi", "timestamp"])
    if tracks.empty:
        raise ValueError("No AIS observations found for the requested MMSI pair")

    own_track = tracks.loc[tracks["mmsi"] == own_mmsi]
    target_track = tracks.loc[tracks["mmsi"] == target_mmsi]
    if own_track.empty or target_track.empty:
        raise ValueError("Both own and target tracks are required")

    reference_lat = float(own_track.iloc[0]["lat"])
    reference_lon = float(own_track.iloc[0]["lon"])

    own_xy = [
        _local_xy_nm(float(str(row.lat)), float(str(row.lon)), reference_lat, reference_lon)
        for row in own_track.itertuples(index=False)
    ]
    target_xy = [
        _local_xy_nm(float(str(row.lat)), float(str(row.lon)), reference_lat, reference_lon)
        for row in target_track.itertuples(index=False)
    ]

    peak = max(pair_assessments, key=lambda item: item.risk_score)
    peak_time = pd.Timestamp(peak.timestamp)
    own_peak_rows = own_track.loc[own_track["timestamp"] == peak_time]
    target_peak_rows = target_track.loc[target_track["timestamp"] == peak_time]
    if own_peak_rows.empty or target_peak_rows.empty:
        raise ValueError("Peak-risk timestamp is missing from the input track")

    own_peak = own_peak_rows.iloc[0]
    target_peak = target_peak_rows.iloc[0]
    own_now = _local_xy_nm(
        float(str(own_peak["lat"])),
        float(str(own_peak["lon"])),
        reference_lat,
        reference_lon,
    )
    target_now = _local_xy_nm(
        float(str(target_peak["lat"])),
        float(str(target_peak["lon"])),
        reference_lat,
        reference_lon,
    )

    tcpa_hours = peak.relative_motion.tcpa_min / 60.0
    own_velocity = _velocity_kn(float(str(own_peak["sog"])), float(str(own_peak["cog"])))
    target_velocity = _velocity_kn(float(str(target_peak["sog"])), float(str(target_peak["cog"])))
    own_cpa = (
        own_now[0] + own_velocity[0] * tcpa_hours,
        own_now[1] + own_velocity[1] * tcpa_hours,
    )
    target_cpa = (
        target_now[0] + target_velocity[0] * tcpa_hours,
        target_now[1] + target_velocity[1] * tcpa_hours,
    )

    figure, axis = plt.subplots(figsize=(7.2, 5.2))
    axis.plot(
        [item[0] for item in own_xy],
        [item[1] for item in own_xy],
        marker="o",
        label=f"Own {own_mmsi}",
    )
    axis.plot(
        [item[0] for item in target_xy],
        [item[1] for item in target_xy],
        marker="s",
        label=f"Target {target_mmsi}",
    )

    axis.scatter([own_now[0], target_now[0]], [own_now[1], target_now[1]], s=70, zorder=4)
    axis.plot([own_now[0], own_cpa[0]], [own_now[1], own_cpa[1]], linestyle="--")
    axis.plot([target_now[0], target_cpa[0]], [target_now[1], target_cpa[1]], linestyle="--")
    axis.scatter(
        [own_cpa[0], target_cpa[0]], [own_cpa[1], target_cpa[1]], marker="x", s=80, zorder=5
    )
    axis.plot([own_cpa[0], target_cpa[0]], [own_cpa[1], target_cpa[1]], linestyle=":")

    midpoint = ((own_cpa[0] + target_cpa[0]) / 2.0, (own_cpa[1] + target_cpa[1]) / 2.0)
    axis.annotate(
        f"DCPA = {peak.relative_motion.dcpa_nm:.3f} NM\n"
        f"TCPA = {peak.relative_motion.tcpa_min:.2f} min\n"
        f"risk = {peak.risk_score:.3f}",
        midpoint,
        xytext=(8, 8),
        textcoords="offset points",
    )
    axis.annotate("start", own_xy[0], xytext=(5, 5), textcoords="offset points")
    target_start_offset = (-42, 5) if target_xy[0][0] > own_xy[0][0] else (5, 5)
    axis.annotate("start", target_xy[0], xytext=target_start_offset, textcoords="offset points")

    axis.set_xlabel("East displacement (NM)")
    axis.set_ylabel("North displacement (NM)")
    axis.set_aspect("equal", adjustable="datalim")
    axis.margins(x=0.08, y=0.12)
    axis.grid(True, linestyle=":", linewidth=0.6)
    axis.legend(loc="best")
    axis.set_title(
        title
        or f"{peak.encounter_type.value} encounter - {peak.colreg.rule or 'monitoring context'}"
    )

    target_path = Path(output)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(target_path, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return target_path

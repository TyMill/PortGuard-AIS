"""Deterministic JMSE scene scenarios for multi-vessel assurance experiments."""

import math
import random
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from portguard_ais.assurance.models import SceneEvidence
from portguard_ais.geometry.geodesy import EARTH_RADIUS_NM
from portguard_ais.models import VesselObservation


@dataclass(frozen=True)
class EvidenceOverride:
    """Injected evidence degradation for one scene update."""

    mean_pairwise_confidence: float | None = None
    low_confidence_edge_fraction: float | None = None
    stale_fraction: float = 0.0
    missing_optional_fraction: float = 0.0
    anomaly_fraction: float = 0.0
    coverage_ratio: float = 1.0
    latency_ms: float = 0.0


@dataclass(frozen=True)
class JMSEScenario:
    """Controlled scenario and expected hazardous time window."""

    name: str
    description: str
    snapshots: tuple[tuple[VesselObservation, ...], ...]
    hazardous_steps: frozenset[int]
    evidence_overrides: tuple[EvidenceOverride, ...]

    def evidence_for_step(self, step: int, base: SceneEvidence) -> SceneEvidence:
        """Apply the scenario's evidence override to a graph-derived baseline."""
        override = self.evidence_overrides[step]
        return SceneEvidence(
            mean_pairwise_confidence=(
                base.mean_pairwise_confidence
                if override.mean_pairwise_confidence is None
                else override.mean_pairwise_confidence
            ),
            low_confidence_edge_fraction=(
                base.low_confidence_edge_fraction
                if override.low_confidence_edge_fraction is None
                else override.low_confidence_edge_fraction
            ),
            stale_fraction=override.stale_fraction,
            missing_optional_fraction=override.missing_optional_fraction,
            anomaly_fraction=override.anomaly_fraction,
            coverage_ratio=override.coverage_ratio,
            latency_ms=override.latency_ms,
        )


@dataclass(frozen=True)
class _VesselSpec:
    mmsi: int
    start_lat: float
    start_lon: float
    sog_kn: float
    cog_deg: float
    length_m: float = 100.0
    beam_m: float = 18.0


def _advance(
    lat: float,
    lon: float,
    sog_kn: float,
    cog_deg: float,
    elapsed_seconds: float,
) -> tuple[float, float]:
    distance_nm = sog_kn * elapsed_seconds / 3600.0
    angle = math.radians(cog_deg)
    east_nm = distance_nm * math.sin(angle)
    north_nm = distance_nm * math.cos(angle)
    out_lat = lat + math.degrees(north_nm / EARTH_RADIUS_NM)
    latitude_reference = math.radians((lat + out_lat) / 2.0)
    cosine = max(abs(math.cos(latitude_reference)), 1e-9)
    out_lon = lon + math.degrees(east_nm / (EARTH_RADIUS_NM * cosine))
    return out_lat, out_lon


def _observation(
    spec: _VesselSpec,
    timestamp: datetime,
    elapsed_seconds: float,
    *,
    cog_deg: float | None = None,
    lat_offset: float = 0.0,
    lon_offset: float = 0.0,
    missing_optional: bool = False,
) -> VesselObservation:
    course = spec.cog_deg if cog_deg is None else cog_deg
    lat, lon = _advance(
        spec.start_lat,
        spec.start_lon,
        spec.sog_kn,
        course,
        elapsed_seconds,
    )
    return VesselObservation(
        timestamp=timestamp,
        mmsi=spec.mmsi,
        lat=lat + lat_offset,
        lon=lon + lon_offset,
        sog=spec.sog_kn,
        cog=course,
        heading=None if missing_optional else course,
        length_m=None if missing_optional else spec.length_m,
        beam_m=None if missing_optional else spec.beam_m,
        position_accuracy_m=None if missing_optional else 10.0,
        vessel_type="synthetic",
        source="jmse-controlled",
    )


def _default_overrides(steps: int) -> tuple[EvidenceOverride, ...]:
    return tuple(EvidenceOverride() for _ in range(steps))


def _generate_linear(
    specs: tuple[_VesselSpec, ...],
    *,
    steps: int,
    interval_seconds: int,
    start: datetime,
) -> tuple[tuple[VesselObservation, ...], ...]:
    snapshots: list[tuple[VesselObservation, ...]] = []
    for step in range(steps):
        elapsed = float(step * interval_seconds)
        timestamp = start + timedelta(seconds=step * interval_seconds)
        snapshots.append(tuple(_observation(spec, timestamp, elapsed) for spec in specs))
    return tuple(snapshots)


def _hazard_window(center_step: int, radius: int, steps: int) -> frozenset[int]:
    lower = max(center_step - radius, 0)
    upper = min(center_step + radius + 1, steps)
    return frozenset(range(lower, upper))


def _head_on(steps: int, interval_seconds: int, start: datetime) -> JMSEScenario:
    specs = (
        _VesselSpec(271100001, 53.4000, 14.5900, 10.0, 90.0, 140.0, 22.0),
        _VesselSpec(271100002, 53.4000, 14.6200, 10.0, 270.0, 120.0, 20.0),
    )
    return JMSEScenario(
        name="head-on",
        description="Reciprocal two-vessel encounter used as a canonical geometric baseline.",
        snapshots=_generate_linear(specs, steps=steps, interval_seconds=interval_seconds, start=start),
        hazardous_steps=_hazard_window(6, 4, steps),
        evidence_overrides=_default_overrides(steps),
    )


def _crossing(steps: int, interval_seconds: int, start: datetime) -> JMSEScenario:
    specs = (
        _VesselSpec(271200001, 53.6000, 14.5900, 9.0, 90.0, 110.0, 18.0),
        _VesselSpec(271200002, 53.5921, 14.6050, 8.0, 0.0, 85.0, 15.0),
    )
    return JMSEScenario(
        name="crossing",
        description="Perpendicular crossing encounter with a common intersection.",
        snapshots=_generate_linear(specs, steps=steps, interval_seconds=interval_seconds, start=start),
        hazardous_steps=_hazard_window(7, 4, steps),
        evidence_overrides=_default_overrides(steps),
    )


def _overtaking(steps: int, interval_seconds: int, start: datetime) -> JMSEScenario:
    specs = (
        _VesselSpec(271300001, 53.8000, 14.5900, 14.0, 90.0, 100.0, 17.0),
        _VesselSpec(271300002, 53.8000, 14.6020, 7.0, 90.0, 130.0, 21.0),
    )
    return JMSEScenario(
        name="overtaking",
        description="Faster vessel closes from abaft the beam on a slower vessel.",
        snapshots=_generate_linear(specs, steps=steps, interval_seconds=interval_seconds, start=start),
        hazardous_steps=_hazard_window(7, 4, steps),
        evidence_overrides=_default_overrides(steps),
    )


def _convergence_specs(count: int) -> tuple[_VesselSpec, ...]:
    base = [
        _VesselSpec(272000001, 53.4000, 14.5800, 9.0, 90.0, 125.0, 20.0),
        _VesselSpec(272000002, 53.4000, 14.6200, 9.0, 270.0, 115.0, 19.0),
        _VesselSpec(272000003, 53.3880, 14.6000, 9.0, 0.0, 95.0, 17.0),
        _VesselSpec(272000004, 53.4120, 14.6000, 9.0, 180.0, 105.0, 18.0),
        _VesselSpec(272000005, 53.3915, 14.5855, 9.0, 45.0, 90.0, 16.0),
    ]
    return tuple(base[:count])


def _three_vessel(steps: int, interval_seconds: int, start: datetime) -> JMSEScenario:
    return JMSEScenario(
        name="three-vessel-convergence",
        description="Three vessels approach a common interaction region from west, east, and south.",
        snapshots=_generate_linear(
            _convergence_specs(3), steps=steps, interval_seconds=interval_seconds, start=start
        ),
        hazardous_steps=_hazard_window(9, 4, steps),
        evidence_overrides=_default_overrides(steps),
    )


def _five_vessel(steps: int, interval_seconds: int, start: datetime) -> JMSEScenario:
    return JMSEScenario(
        name="five-vessel-congestion",
        description="Five-vessel dense convergence used to stress scene coupling.",
        snapshots=_generate_linear(
            _convergence_specs(5), steps=steps, interval_seconds=interval_seconds, start=start
        ),
        hazardous_steps=_hazard_window(9, 5, steps),
        evidence_overrides=_default_overrides(steps),
    )


def _narrow_entrance(steps: int, interval_seconds: int, start: datetime) -> JMSEScenario:
    specs = (
        _VesselSpec(273000001, 53.5000, 14.5850, 8.0, 90.0, 140.0, 22.0),
        _VesselSpec(273000002, 53.5008, 14.6150, 8.0, 270.0, 120.0, 20.0),
        _VesselSpec(273000003, 53.4992, 14.6150, 6.0, 270.0, 90.0, 16.0),
        _VesselSpec(273000004, 53.5015, 14.5880, 6.5, 90.0, 80.0, 15.0),
    )
    return JMSEScenario(
        name="narrow-port-entrance",
        description="Opposing traffic streams interact in a spatially compressed entrance scene.",
        snapshots=_generate_linear(specs, steps=steps, interval_seconds=interval_seconds, start=start),
        hazardous_steps=_hazard_window(7, 4, steps),
        evidence_overrides=_default_overrides(steps),
    )


def _bottleneck(steps: int, interval_seconds: int, start: datetime) -> JMSEScenario:
    specs = (
        _VesselSpec(273100001, 53.7000, 14.5800, 8.0, 90.0),
        _VesselSpec(273100002, 53.7040, 14.5820, 8.0, 105.0),
        _VesselSpec(273100003, 53.7000, 14.6200, 8.0, 270.0),
        _VesselSpec(273100004, 53.6960, 14.6180, 8.0, 285.0),
    )
    return JMSEScenario(
        name="bottleneck-convergence",
        description="Two inbound streams converge toward a common constrained traffic region.",
        snapshots=_generate_linear(specs, steps=steps, interval_seconds=interval_seconds, start=start),
        hazardous_steps=_hazard_window(9, 4, steps),
        evidence_overrides=_default_overrides(steps),
    )


def _transient_false_positive(
    steps: int,
    interval_seconds: int,
    start: datetime,
) -> JMSEScenario:
    specs = (
        _VesselSpec(273200001, 53.9000, 14.5900, 8.0, 90.0, 105.0, 18.0),
        _VesselSpec(273200002, 53.9100, 14.5900, 8.0, 90.0, 100.0, 17.0),
    )
    snapshots = [
        list(snapshot)
        for snapshot in _generate_linear(
            specs, steps=steps, interval_seconds=interval_seconds, start=start
        )
    ]
    step = min(5, len(snapshots) - 1)
    first = snapshots[step][0]
    second = snapshots[step][1]
    snapshots[step][0] = first.model_copy(
        update={"lat": second.lat - 0.0008, "lon": second.lon - 0.0008}
    )
    return JMSEScenario(
        name="transient-false-positive",
        description=(
            "Two safely separated parallel vessels receive one spurious position update "
            "that creates a transient apparent conflict."
        ),
        snapshots=tuple(tuple(snapshot) for snapshot in snapshots),
        hazardous_steps=frozenset(),
        evidence_overrides=_default_overrides(steps),
    )


def _risk_handoff(steps: int, interval_seconds: int, start: datetime) -> JMSEScenario:
    specs = _convergence_specs(3)
    snapshots = [
        list(snapshot)
        for snapshot in _generate_linear(
            specs, steps=steps, interval_seconds=interval_seconds, start=start
        )
    ]
    handoff = max(steps // 2, 1)
    for step in range(handoff, steps):
        timestamp = start + timedelta(seconds=step * interval_seconds)
        elapsed = float((step - handoff) * interval_seconds)
        pivot = snapshots[handoff - 1][1]
        spec = _VesselSpec(
            specs[1].mmsi,
            pivot.lat,
            pivot.lon,
            specs[1].sog_kn,
            180.0,
            specs[1].length_m,
            specs[1].beam_m,
        )
        snapshots[step][1] = _observation(spec, timestamp, elapsed)
    return JMSEScenario(
        name="risk-handoff",
        description="The dominant risky interaction migrates between vessel pairs while scene hazard persists.",
        snapshots=tuple(tuple(snapshot) for snapshot in snapshots),
        hazardous_steps=_hazard_window(handoff, 5, steps),
        evidence_overrides=_default_overrides(steps),
    )


def _cascading_conflict(steps: int, interval_seconds: int, start: datetime) -> JMSEScenario:
    base = _three_vessel(steps, interval_seconds, start)
    snapshots = [list(snapshot) for snapshot in base.snapshots]
    maneuver = min(steps // 2, steps - 1)
    for step in range(maneuver, steps):
        current = snapshots[step][0]
        snapshots[step][0] = current.model_copy(update={"cog": 0.0, "heading": 0.0})
    return JMSEScenario(
        name="cascading-conflict",
        description="A mid-scenario course change shifts risk from one pair into a coupled three-vessel conflict.",
        snapshots=tuple(tuple(snapshot) for snapshot in snapshots),
        hazardous_steps=_hazard_window(maneuver, 5, steps),
        evidence_overrides=_default_overrides(steps),
    )


def _degraded_from(
    base: JMSEScenario,
    *,
    name: str,
    description: str,
    kind: str,
    seed: int,
) -> JMSEScenario:
    snapshots = [list(snapshot) for snapshot in base.snapshots]
    overrides = list(_default_overrides(len(snapshots)))
    start_step = min(5, len(snapshots) - 1)
    end_step = min(start_step + 3, len(snapshots))
    rng = random.Random(seed)

    for step in range(start_step, end_step):
        if kind == "delay":
            frozen = snapshots[start_step - 1][0]
            current = snapshots[step][0]
            snapshots[step][0] = frozen.model_copy(update={"timestamp": current.timestamp})
            overrides[step] = replace(overrides[step], stale_fraction=0.80)
        elif kind == "dropout":
            if len(snapshots[step]) > 2:
                snapshots[step] = snapshots[step][:-1]
            overrides[step] = replace(overrides[step], coverage_ratio=0.60)
        elif kind == "missing":
            snapshots[step] = [
                item.model_copy(
                    update={
                        "heading": None,
                        "length_m": None,
                        "beam_m": None,
                        "position_accuracy_m": None,
                    }
                )
                for item in snapshots[step]
            ]
            overrides[step] = replace(overrides[step], missing_optional_fraction=1.0)
        elif kind == "noise":
            snapshots[step] = [
                item.model_copy(
                    update={
                        "lat": item.lat + rng.gauss(0.0, 0.0015),
                        "lon": item.lon + rng.gauss(0.0, 0.0015),
                    }
                )
                for item in snapshots[step]
            ]
            overrides[step] = replace(overrides[step], anomaly_fraction=0.25)
        elif kind == "spoof":
            item = snapshots[step][0]
            snapshots[step][0] = item.model_copy(
                update={"lat": item.lat + 0.05, "lon": item.lon + 0.05}
            )
            overrides[step] = replace(overrides[step], anomaly_fraction=0.60)
        elif kind == "mixed-confidence":
            overrides[step] = replace(
                overrides[step],
                mean_pairwise_confidence=0.50,
                low_confidence_edge_fraction=0.75,
            )
        else:
            raise ValueError(f"unsupported degradation kind: {kind}")

    return JMSEScenario(
        name=name,
        description=description,
        snapshots=tuple(tuple(snapshot) for snapshot in snapshots),
        hazardous_steps=base.hazardous_steps,
        evidence_overrides=tuple(overrides),
    )


def jmse_scenarios(
    *,
    steps: int = 18,
    interval_seconds: int = 30,
    seed: int = 20260817,
) -> tuple[JMSEScenario, ...]:
    """Return the controlled scenario suite used by the JMSE research benchmark."""
    if steps < 12:
        raise ValueError("steps must be at least 12")
    if interval_seconds < 1:
        raise ValueError("interval_seconds must be positive")

    start = datetime(2026, 8, 17, 10, 0, tzinfo=UTC)
    head_on = _head_on(steps, interval_seconds, start)
    crossing = _crossing(steps, interval_seconds, start)
    overtaking = _overtaking(steps, interval_seconds, start)
    narrow = _narrow_entrance(steps, interval_seconds, start)
    bottleneck = _bottleneck(steps, interval_seconds, start)
    three = _three_vessel(steps, interval_seconds, start)
    five = _five_vessel(steps, interval_seconds, start)
    cascading = _cascading_conflict(steps, interval_seconds, start)
    transient = _transient_false_positive(steps, interval_seconds, start)
    handoff = _risk_handoff(steps, interval_seconds, start)

    return (
        head_on,
        crossing,
        overtaking,
        narrow,
        bottleneck,
        three,
        five,
        cascading,
        transient,
        handoff,
        _degraded_from(
            three,
            name="delayed-ais",
            description="Three-vessel convergence with a frozen vessel state and high stale-data fraction.",
            kind="delay",
            seed=seed + 1,
        ),
        _degraded_from(
            five,
            name="message-dropout",
            description="Five-vessel congestion with temporary vessel dropout and reduced scene coverage.",
            kind="dropout",
            seed=seed + 2,
        ),
        _degraded_from(
            three,
            name="missing-optional-fields",
            description="Three-vessel convergence with heading, dimension, and accuracy fields removed.",
            kind="missing",
            seed=seed + 3,
        ),
        _degraded_from(
            three,
            name="noisy-positions",
            description="Three-vessel convergence with deterministic seeded position noise.",
            kind="noise",
            seed=seed + 4,
        ),
        _degraded_from(
            three,
            name="spoof-like-jump",
            description="Three-vessel convergence with an implausible position jump and anomaly evidence.",
            kind="spoof",
            seed=seed + 5,
        ),
        _degraded_from(
            three,
            name="mixed-confidence-scene",
            description="High scene hazard coincides with low aggregate evidence confidence.",
            kind="mixed-confidence",
            seed=seed + 6,
        ),
    )

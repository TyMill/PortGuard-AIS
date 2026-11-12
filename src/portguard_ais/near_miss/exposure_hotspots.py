"""Exposure-normalized mapping of candidate near-miss episodes in port waters.

The numerator is one independently segmented *candidate episode* assigned to
the peak-risk pair midpoint. The denominator is the duration (pair-hours)
during which each eligible vessel pair is represented by successive valid
assessments, allocated along the pair-midpoint trajectory.

This is an observational rate, NOT a probability of collision, not an
independently validated near-miss rate and not a substitute for traffic
coverage analysis. In particular, sparse AIS is not treated as zero risk.
"""

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from portguard_ais.models import EncounterAssessment
from portguard_ais.near_miss.episodes import NearMissEpisode

EARTH_RADIUS_M = 6_371_008.8
METRES_PER_NAUTICAL_MILE = 1852.0


@dataclass(frozen=True, kw_only=True)
class ExposureGridConfig:
    """Fixed locally metric grid and explicit pair-time eligibility rules."""

    origin_lat_deg: float
    origin_lon_deg: float
    cell_size_m: float = 500.0
    max_pair_gap_seconds: float = 120.0
    max_midpoint_speed_kn: float = 80.0
    max_radius_km: float = 50.0
    minimum_pair_hours: float = 0.25

    def __post_init__(self) -> None:
        if not (-85.0 < self.origin_lat_deg < 85.0):
            raise ValueError("origin latitude must be between -85 and 85 degrees")
        if not (-180.0 <= self.origin_lon_deg <= 180.0):
            raise ValueError("origin longitude must be between -180 and 180 degrees")
        values = (
            self.cell_size_m,
            self.max_pair_gap_seconds,
            self.max_midpoint_speed_kn,
            self.max_radius_km,
        )
        if any(not math.isfinite(v) or v <= 0.0 for v in values):
            raise ValueError("cell size, gap, speed and radius must be positive and finite")
        if not math.isfinite(self.minimum_pair_hours) or self.minimum_pair_hours < 0.0:
            raise ValueError("minimum_pair_hours must be finite and nonnegative")


@dataclass(frozen=True)
class ExposureHotspotCell:
    """Local cell-level candidate event intensity with exposure qualification."""

    lat_center: float
    lon_center: float
    cell_size_m: float
    candidate_episode_count: int
    eligible_pair_hours: float
    candidate_events_per_1000_pair_hours: float | None
    exposure_sufficient: bool


@dataclass(frozen=True)
class ExposureHotspotReport:
    """Transparent aggregates including observations not contributing exposure."""

    cells: tuple[ExposureHotspotCell, ...]
    total_pair_hours: float
    assigned_episodes: int
    unlocated_episodes: int
    accepted_pair_segments: int
    excluded_pair_segments: int
    excluded_assessments_missing_position: int


def _local_xy(lat: float, lon: float, config: ExposureGridConfig) -> tuple[float, float]:
    if not math.isfinite(lat) or not math.isfinite(lon):
        raise ValueError("coordinates must be finite")
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        raise ValueError("coordinates out of range")
    delta_lon_deg = (lon - config.origin_lon_deg + 180.0) % 360.0 - 180.0
    x = (
        EARTH_RADIUS_M
        * math.radians(delta_lon_deg)
        * math.cos(math.radians(config.origin_lat_deg))
    )
    y = EARTH_RADIUS_M * math.radians(lat - config.origin_lat_deg)
    if math.hypot(x, y) > config.max_radius_km * 1000.0:
        raise ValueError("point lies outside configured local-port map extent")
    return x, y


def _cell(x: float, y: float, cell_size_m: float) -> tuple[int, int]:
    return math.floor(x / cell_size_m), math.floor(y / cell_size_m)


def _cell_centre(
    index: tuple[int, int], config: ExposureGridConfig
) -> tuple[float, float]:
    x = (index[0] + 0.5) * config.cell_size_m
    y = (index[1] + 0.5) * config.cell_size_m
    lat = config.origin_lat_deg + math.degrees(y / EARTH_RADIUS_M)
    lon = config.origin_lon_deg + math.degrees(
        x / (EARTH_RADIUS_M * math.cos(math.radians(config.origin_lat_deg)))
    )
    lon = (lon + 180.0) % 360.0 - 180.0
    return lat, lon


def _split_segment(
    x0: float, y0: float, x1: float, y1: float, cell_size_m: float
) -> list[tuple[tuple[int, int], float]]:
    """Exactly partition straight-line pair exposure at grid boundaries.

    Each output weight is the fraction of elapsed time spent in that cell
    under constant-velocity midpoint interpolation between assessment ticks.
    """
    fractions = [0.0, 1.0]
    for start, finish in ((x0, x1), (y0, y1)):
        delta = finish - start
        if abs(delta) < 1e-12:
            continue
        first_boundary = math.floor(min(start, finish) / cell_size_m) + 1
        last_boundary = math.floor(max(start, finish) / cell_size_m)
        for boundary in range(first_boundary, last_boundary + 1):
            fraction = (boundary * cell_size_m - start) / delta
            if 0.0 < fraction < 1.0:
                fractions.append(fraction)

    fractions = sorted(set(fractions))
    result: list[tuple[tuple[int, int], float]] = []
    for begin, end in zip(fractions, fractions[1:], strict=False):
        if end - begin <= 1e-12:
            continue
        middle = (begin + end) / 2.0
        x = x0 + middle * (x1 - x0)
        y = y0 + middle * (y1 - y0)
        result.append((_cell(x, y, cell_size_m), end - begin))
    return result


def aggregate_exposure_hotspots(
    assessments: Sequence[EncounterAssessment],
    episodes: Sequence[NearMissEpisode],
    config: ExposureGridConfig,
) -> ExposureHotspotReport:
    """Compute episode counts divided by all observed *candidate pair-hours*.

    Assessments must come from the same evaluated population and time domain
    as the episode detector. Include nonhazardous pairs: conditioning the
    denominator on risk-positive updates would bias the rates.

    Pair exposure is counted only between consecutive assessments of the same
    pair with nonmissing geometry and with gaps and midpoint speed below
    explicit limits. A long AIS outage is excluded, never interpreted as
    event-free observed traffic. Do not count repeated timestamp messages as
    additional exposure. Use causal AIS alignment upstream for irregular input.
    """
    by_pair: dict[str, list[EncounterAssessment]] = defaultdict(list)
    missing_position = 0
    for item in assessments:
        by_pair[item.encounter_id].append(item)
        if item.own_position is None or item.target_position is None:
            missing_position += 1

    exposure: dict[tuple[int, int], float] = defaultdict(float)
    accepted_segments = 0
    excluded_segments = 0

    for items in by_pair.values():
        unique: dict[object, EncounterAssessment] = {}
        for item in sorted(items, key=lambda value: (value.timestamp, value.risk_score)):
            unique[item.timestamp] = item
        ordered = sorted(unique.values(), key=lambda value: value.timestamp)
        for previous, current in zip(ordered, ordered[1:], strict=False):
            dt = (current.timestamp - previous.timestamp).total_seconds()
            if dt <= 0.0 or dt > config.max_pair_gap_seconds:
                excluded_segments += 1
                continue
            if (
                previous.own_position is None
                or previous.target_position is None
                or current.own_position is None
                or current.target_position is None
            ):
                excluded_segments += 1
                continue

            prev_lat = (previous.own_position.lat + previous.target_position.lat) / 2.0
            prev_lon = (previous.own_position.lon + previous.target_position.lon) / 2.0
            curr_lat = (current.own_position.lat + current.target_position.lat) / 2.0
            curr_lon = (current.own_position.lon + current.target_position.lon) / 2.0
            x0, y0 = _local_xy(prev_lat, prev_lon, config)
            x1, y1 = _local_xy(curr_lat, curr_lon, config)
            implied_speed_kn = math.hypot(x1 - x0, y1 - y0) / METRES_PER_NAUTICAL_MILE * (
                3600.0 / dt
            )
            if implied_speed_kn > config.max_midpoint_speed_kn:
                excluded_segments += 1
                continue

            pair_hours = dt / 3600.0
            for index, fraction in _split_segment(x0, y0, x1, y1, config.cell_size_m):
                exposure[index] += pair_hours * fraction
            accepted_segments += 1

    episode_counts: dict[tuple[int, int], int] = defaultdict(int)
    seen_ids: set[str] = set()
    missing_episode_location = 0
    for episode in episodes:
        if episode.episode_id in seen_ids:
            raise ValueError(f"duplicate candidate episode: {episode.episode_id}")
        seen_ids.add(episode.episode_id)
        if episode.midpoint_lat is None or episode.midpoint_lon is None:
            missing_episode_location += 1
            continue
        x, y = _local_xy(episode.midpoint_lat, episode.midpoint_lon, config)
        episode_counts[_cell(x, y, config.cell_size_m)] += 1

    cells: list[ExposureHotspotCell] = []
    for index in set(exposure) | set(episode_counts):
        pair_hours = exposure.get(index, 0.0)
        count = episode_counts.get(index, 0)
        sufficient = pair_hours > 0.0 and pair_hours >= config.minimum_pair_hours
        latitude, longitude = _cell_centre(index, config)
        cells.append(
            ExposureHotspotCell(
                lat_center=latitude,
                lon_center=longitude,
                cell_size_m=config.cell_size_m,
                candidate_episode_count=count,
                eligible_pair_hours=pair_hours,
                candidate_events_per_1000_pair_hours=(
                    count / pair_hours * 1000.0 if sufficient else None
                ),
                exposure_sufficient=sufficient,
            )
        )

    # Unsupported rates are intentionally sorted last; they are not zeroes.
    cells.sort(
        key=lambda item: (
            item.candidate_events_per_1000_pair_hours is None,
            -(
                item.candidate_events_per_1000_pair_hours
                if item.candidate_events_per_1000_pair_hours is not None
                else 0.0
            ),
            -item.candidate_episode_count,
            item.lat_center,
            item.lon_center,
        )
    )
    return ExposureHotspotReport(
        cells=tuple(cells),
        total_pair_hours=sum(exposure.values()),
        assigned_episodes=sum(episode_counts.values()),
        unlocated_episodes=missing_episode_location,
        accepted_pair_segments=accepted_segments,
        excluded_pair_segments=excluded_segments,
        excluded_assessments_missing_position=missing_position,
    )

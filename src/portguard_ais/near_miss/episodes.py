"""Episode-based extraction of *candidate* close-quarters events from AIS assessments.

This research implementation is intentionally separate from the v1.0 near-miss
miner to preserve reproducibility of the SoftwareX reference benchmark.
It does not infer that a recorded episode is a verified real-world near miss.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from portguard_ais.config import NearMissConfig
from portguard_ais.models import EncounterAssessment


@dataclass(frozen=True)
class NearMissEpisode:
    """An independently segmented period of simultaneous risk criteria."""

    episode_id: str
    encounter_id: str
    own_mmsi: int
    target_mmsi: int
    started_at: datetime
    ended_at: datetime
    observation_count: int
    peak_risk_score: float
    minimum_dcpa_nm: float
    minimum_tcpa_min: float
    midpoint_lat: float | None
    midpoint_lon: float | None


def _qualifies(item: EncounterAssessment, config: NearMissConfig) -> bool:
    """Require the risk and CPA/TCPA predicates at the *same* update."""
    motion = item.relative_motion
    return (
        item.risk_score >= config.minimum_peak_score
        and motion.converging
        and motion.dcpa_nm <= config.maximum_dcpa_nm
        and 0.0 < motion.tcpa_min <= config.maximum_tcpa_min
    )


def segment_near_miss_episodes(
    assessments: list[EncounterAssessment],
    config: NearMissConfig,
    *,
    max_gap_seconds: float = 120.0,
) -> list[NearMissEpisode]:
    """Split qualifying vessel-pair updates into discrete episodes.

    A non-qualifying update closes an episode, as does a gap longer than
    max_gap_seconds. No interpolation of missing hazard evidence is assumed.
    Duplicate pair/timestamps are collapsed, retaining the largest risk
    score for deterministic processing. The configured minimum number of
    qualifying observations applies separately to each episode.
    """
    if max_gap_seconds <= 0.0:
        raise ValueError("max_gap_seconds must be positive")

    grouped: dict[str, list[EncounterAssessment]] = defaultdict(list)
    for item in assessments:
        grouped[item.encounter_id].append(item)

    episodes: list[NearMissEpisode] = []
    for encounter_id, observations in sorted(grouped.items()):
        # Duplicated updates must not artificially satisfy minimum_observations.
        unique_by_time: dict[datetime, EncounterAssessment] = {}
        for item in sorted(observations, key=lambda a: (a.timestamp, a.risk_score)):
            unique_by_time[item.timestamp] = item

        windows: list[list[EncounterAssessment]] = []
        current: list[EncounterAssessment] = []
        for item in sorted(unique_by_time.values(), key=lambda a: a.timestamp):
            if not _qualifies(item, config):
                if current:
                    windows.append(current)
                    current = []
                continue

            if current:
                gap = (item.timestamp - current[-1].timestamp).total_seconds()
                if gap > max_gap_seconds:
                    windows.append(current)
                    current = []
            current.append(item)
        if current:
            windows.append(current)

        for index, window in enumerate(windows, start=1):
            if len(window) < config.minimum_observations:
                continue
            peak_item = max(window, key=lambda a: a.risk_score)
            if peak_item.own_position is not None and peak_item.target_position is not None:
                midpoint_lat = (peak_item.own_position.lat + peak_item.target_position.lat) / 2.0
                midpoint_lon = (peak_item.own_position.lon + peak_item.target_position.lon) / 2.0
            else:
                midpoint_lat = None
                midpoint_lon = None

            first = window[0]
            episodes.append(
                NearMissEpisode(
                    episode_id=f"{encounter_id}:episode-{index:03d}",
                    encounter_id=encounter_id,
                    own_mmsi=first.own_mmsi,
                    target_mmsi=first.target_mmsi,
                    started_at=first.timestamp,
                    ended_at=window[-1].timestamp,
                    observation_count=len(window),
                    peak_risk_score=peak_item.risk_score,
                    minimum_dcpa_nm=min(a.relative_motion.dcpa_nm for a in window),
                    minimum_tcpa_min=min(a.relative_motion.tcpa_min for a in window),
                    midpoint_lat=midpoint_lat,
                    midpoint_lon=midpoint_lon,
                )
            )

    return sorted(episodes, key=lambda e: (e.started_at, e.encounter_id, e.episode_id))

"""Spatial aggregation of elevated-risk encounter observations."""

import math
from collections import defaultdict
from collections.abc import Sequence

from portguard_ais.models import EncounterAssessment, HotspotCell


def aggregate_hotspots(
    assessments: Sequence[EncounterAssessment],
    minimum_score: float = 0.5,
    cell_size_deg: float = 0.01,
) -> list[HotspotCell]:
    """Aggregate risky pair midpoints into deterministic geographic grid cells."""
    if not 0.0 <= minimum_score <= 1.0:
        raise ValueError("minimum_score must be within [0, 1]")
    if cell_size_deg <= 0.0:
        raise ValueError("cell_size_deg must be positive")

    grouped: dict[tuple[int, int], list[EncounterAssessment]] = defaultdict(list)
    for assessment in assessments:
        if assessment.risk_score < minimum_score:
            continue
        if assessment.own_position is None or assessment.target_position is None:
            continue
        midpoint_lat = (assessment.own_position.lat + assessment.target_position.lat) / 2.0
        midpoint_lon = (assessment.own_position.lon + assessment.target_position.lon) / 2.0
        cell = (
            math.floor(midpoint_lat / cell_size_deg),
            math.floor(midpoint_lon / cell_size_deg),
        )
        grouped[cell].append(assessment)

    hotspots: list[HotspotCell] = []
    for (lat_index, lon_index), items in grouped.items():
        vessel_ids = {item.own_mmsi for item in items} | {item.target_mmsi for item in items}
        scores = [item.risk_score for item in items]
        hotspots.append(
            HotspotCell(
                latitude_center=round((lat_index + 0.5) * cell_size_deg, 7),
                longitude_center=round((lon_index + 0.5) * cell_size_deg, 7),
                cell_size_deg=cell_size_deg,
                assessment_count=len(items),
                unique_vessels=len(vessel_ids),
                mean_risk_score=round(sum(scores) / len(scores), 6),
                maximum_risk_score=max(scores),
            )
        )
    return sorted(
        hotspots,
        key=lambda cell: (cell.maximum_risk_score, cell.assessment_count),
        reverse=True,
    )

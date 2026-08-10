"""Simple multi-vessel conflict grouping."""

from collections import defaultdict

from portguard_ais.enums import RiskLevel
from portguard_ais.models import EncounterAssessment


def conflict_clusters(
    assessments: list[EncounterAssessment],
    minimum_level: RiskLevel = RiskLevel.WARNING,
) -> list[tuple[int, ...]]:
    """Return connected MMSI components above a severity threshold."""
    order = {
        RiskLevel.SAFE: 0,
        RiskLevel.WATCH: 1,
        RiskLevel.WARNING: 2,
        RiskLevel.CRITICAL: 3,
    }
    graph: dict[int, set[int]] = defaultdict(set)
    for assessment in assessments:
        if order[assessment.risk_level] < order[minimum_level]:
            continue
        graph[assessment.own_mmsi].add(assessment.target_mmsi)
        graph[assessment.target_mmsi].add(assessment.own_mmsi)

    seen: set[int] = set()
    clusters: list[tuple[int, ...]] = []
    for node in sorted(graph):
        if node in seen:
            continue
        stack = [node]
        component: set[int] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(graph[current] - component)
        seen.update(component)
        if len(component) >= 3:
            clusters.append(tuple(sorted(component)))
    return clusters

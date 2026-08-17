"""Weighted multi-vessel interaction graph construction."""

from collections import defaultdict

from portguard_ais.assurance.config import SceneRiskConfig
from portguard_ais.assurance.models import SceneGraph, SceneGraphEdge
from portguard_ais.models import EncounterAssessment


def _connected_components(
    vessels: tuple[int, ...],
    edges: tuple[SceneGraphEdge, ...],
    minimum_risk: float,
) -> tuple[tuple[int, ...], ...]:
    adjacency: dict[int, set[int]] = defaultdict(set)
    for edge in edges:
        if edge.risk_score < minimum_risk:
            continue
        adjacency[edge.own_mmsi].add(edge.target_mmsi)
        adjacency[edge.target_mmsi].add(edge.own_mmsi)

    seen: set[int] = set()
    components: list[tuple[int, ...]] = []
    for vessel in vessels:
        if vessel in seen or vessel not in adjacency:
            continue
        stack = [vessel]
        component: set[int] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(adjacency[current] - component)
        seen.update(component)
        if len(component) >= 2:
            components.append(tuple(sorted(component)))
    return tuple(sorted(components))


def build_scene_graph(
    assessments: list[EncounterAssessment],
    config: SceneRiskConfig,
) -> SceneGraph:
    """Build one undirected weighted graph from same-timestamp pairwise assessments."""
    if not assessments:
        raise ValueError("build_scene_graph requires at least one assessment")
    timestamps = {assessment.timestamp for assessment in assessments}
    if len(timestamps) != 1:
        raise ValueError("scene graph assessments must share exactly one timestamp")

    edge_by_pair: dict[tuple[int, int], SceneGraphEdge] = {}
    vessels: set[int] = set()
    for assessment in assessments:
        first, second = sorted((assessment.own_mmsi, assessment.target_mmsi))
        vessels.update((first, second))
        edge = SceneGraphEdge(
            own_mmsi=first,
            target_mmsi=second,
            risk_score=assessment.risk_score,
            confidence=assessment.confidence,
            dcpa_nm=assessment.relative_motion.dcpa_nm,
            tcpa_min=assessment.relative_motion.tcpa_min,
            relative_speed_kn=assessment.relative_motion.relative_speed_kn,
            closing_speed_kn=assessment.relative_motion.closing_speed_kn,
            encounter_type=assessment.encounter_type.value,
            domain_violated=assessment.domain.violated,
        )
        existing = edge_by_pair.get((first, second))
        if existing is None or edge.risk_score > existing.risk_score:
            edge_by_pair[(first, second)] = edge

    ordered_vessels = tuple(sorted(vessels))
    edges = tuple(edge_by_pair[pair] for pair in sorted(edge_by_pair))
    weighted_degree = {vessel: 0.0 for vessel in ordered_vessels}
    for edge in edges:
        weighted_degree[edge.own_mmsi] += edge.risk_score
        weighted_degree[edge.target_mmsi] += edge.risk_score

    vessel_count = len(ordered_vessels)
    possible_edges = vessel_count * (vessel_count - 1) / 2
    weighted_density = (
        sum(edge.risk_score for edge in edges) / possible_edges if possible_edges > 0 else 0.0
    )
    maximum_degree = max(weighted_degree.values(), default=0.0)
    normalized_degree = maximum_degree / max(vessel_count - 1, 1)
    components = _connected_components(ordered_vessels, edges, config.conflict_edge_threshold)
    max_component_size = max((len(component) for component in components), default=0)
    component_coupling = (
        max(max_component_size - 1, 0) / max(vessel_count - 1, 1) if vessel_count > 1 else 0.0
    )
    coupling_score = min(max((normalized_degree + weighted_density + component_coupling) / 3.0, 0.0), 1.0)
    low_confidence_fraction = (
        sum(edge.confidence < config.low_confidence_threshold for edge in edges) / len(edges)
        if edges
        else 0.0
    )

    return SceneGraph(
        timestamp=assessments[0].timestamp,
        vessels=ordered_vessels,
        edges=edges,
        weighted_degree={key: round(value, 6) for key, value in weighted_degree.items()},
        maximum_weighted_degree=round(maximum_degree, 6),
        weighted_density=round(weighted_density, 6),
        coupling_score=round(coupling_score, 6),
        conflict_components=components,
        maximum_component_size=max_component_size,
        low_confidence_edge_fraction=round(low_confidence_fraction, 6),
    )

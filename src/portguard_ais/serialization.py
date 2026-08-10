"""Result export helpers."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from portguard_ais.models import AlertDecision, EncounterAssessment, NearMissEvent


class _Serializable(Protocol):
    def model_dump(self, *, mode: str) -> dict[str, Any]: ...


def _records(models: Sequence[_Serializable]) -> list[dict[str, Any]]:
    return [model.model_dump(mode="json") for model in models]


def write_json(models: Sequence[_Serializable], path: str | Path) -> Path:
    """Write Pydantic models as UTF-8 JSON."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(_records(models), ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def write_csv(models: Sequence[_Serializable], path: str | Path) -> Path:
    """Write flattened model records as UTF-8 CSV."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.json_normalize(_records(models), sep=".")
    if "rationale" in frame.columns:
        frame["rationale"] = frame["rationale"].map(
            lambda value: " | ".join(value) if isinstance(value, list) else value
        )
    frame.to_csv(output, index=False, encoding="utf-8")
    return output


def write_geojson(assessments: list[EncounterAssessment], path: str | Path) -> Path:
    """Write assessment-level properties as GeoJSON without inventing trajectories."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    features = []
    for assessment in assessments:
        properties = assessment.model_dump(mode="json")
        geometry: dict[str, Any] | None = None
        if assessment.own_position is not None and assessment.target_position is not None:
            geometry = {
                "type": "LineString",
                "coordinates": [
                    [assessment.own_position.lon, assessment.own_position.lat],
                    [assessment.target_position.lon, assessment.target_position.lat],
                ],
            }
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": properties,
            }
        )
    payload = {"type": "FeatureCollection", "features": features}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def export_bundle(
    assessments: list[EncounterAssessment],
    alerts: list[AlertDecision],
    near_misses: list[NearMissEvent],
    output_dir: str | Path,
    *,
    trends: Sequence[_Serializable] = (),
    hotspots: Sequence[_Serializable] = (),
) -> dict[str, Path]:
    """Export the standard research result bundle."""
    directory = Path(output_dir)
    return {
        "assessments_json": write_json(assessments, directory / "assessments.json"),
        "assessments_csv": write_csv(assessments, directory / "assessments.csv"),
        "assessments_geojson": write_geojson(assessments, directory / "assessments.geojson"),
        "alerts_json": write_json(alerts, directory / "alerts.json"),
        "alerts_csv": write_csv(alerts, directory / "alerts.csv"),
        "near_misses_json": write_json(near_misses, directory / "near_misses.json"),
        "near_misses_csv": write_csv(near_misses, directory / "near_misses.csv"),
        "risk_trends_json": write_json(trends, directory / "risk_trends.json"),
        "risk_trends_csv": write_csv(trends, directory / "risk_trends.csv"),
        "hotspots_json": write_json(hotspots, directory / "hotspots.json"),
        "hotspots_csv": write_csv(hotspots, directory / "hotspots.csv"),
    }

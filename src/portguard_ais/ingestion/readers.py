"""AIS tabular readers with explicit validation."""

from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import ValidationError

from portguard_ais.exceptions import InputSchemaError
from portguard_ais.ingestion.schema import OPTIONAL_COLUMNS, REQUIRED_COLUMNS
from portguard_ais.models import VesselObservation


def read_ais_csv(path: str | Path) -> pd.DataFrame:
    """Read a CSV file without silently coercing invalid timestamps."""
    input_path = Path(path)
    if not input_path.is_file():
        raise InputSchemaError(f"AIS input does not exist: {input_path}")
    try:
        frame = pd.read_csv(input_path)
    except (OSError, pd.errors.ParserError) as exc:
        raise InputSchemaError(f"Unable to parse AIS CSV: {input_path}") from exc
    return frame


def validate_ais_frame(frame: pd.DataFrame) -> list[VesselObservation]:
    """Validate every row using the canonical observation model."""
    missing = sorted(set(REQUIRED_COLUMNS).difference(frame.columns))
    if missing:
        raise InputSchemaError(f"Missing required AIS columns: {missing}")

    observations: list[VesselObservation] = []
    failures: list[str] = []
    selected = [column for column in REQUIRED_COLUMNS + OPTIONAL_COLUMNS if column in frame.columns]

    for row_number, row in enumerate(frame[selected].to_dict(orient="records"), start=2):
        cleaned: dict[str, Any] = {
            str(key): None if pd.isna(value) else value for key, value in row.items()
        }
        try:
            observations.append(VesselObservation.model_validate(cleaned))
        except ValidationError as exc:
            failures.append(f"row {row_number}: {exc.errors(include_url=False)}")

    if failures:
        preview = "; ".join(failures[:5])
        suffix = "" if len(failures) <= 5 else f"; plus {len(failures) - 5} more"
        raise InputSchemaError(f"Invalid AIS rows: {preview}{suffix}")
    return observations

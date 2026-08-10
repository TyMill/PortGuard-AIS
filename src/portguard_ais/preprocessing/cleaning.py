"""Deterministic AIS cleaning and validation reporting."""

import pandas as pd

from portguard_ais.config import InputConfig
from portguard_ais.exceptions import InputSchemaError
from portguard_ais.ingestion.schema import REQUIRED_COLUMNS
from portguard_ais.models import ValidationReport


def clean_ais_frame(
    frame: pd.DataFrame, config: InputConfig
) -> tuple[pd.DataFrame, ValidationReport]:
    """Normalize timestamps, numeric fields, duplicates and impossible speeds."""
    missing = sorted(set(REQUIRED_COLUMNS).difference(frame.columns))
    if missing:
        raise InputSchemaError(f"Missing required AIS columns: {missing}")

    cleaned = frame.copy()
    input_rows = len(cleaned)
    warnings: list[str] = []

    cleaned["timestamp"] = pd.to_datetime(cleaned["timestamp"], utc=True, errors="coerce")
    numeric_columns = ["mmsi", "lat", "lon", "sog", "cog"]
    for column in numeric_columns:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    invalid_mask = (
        cleaned[list(REQUIRED_COLUMNS)].isna().any(axis=1)
        | ~cleaned["lat"].between(-90.0, 90.0)
        | ~cleaned["lon"].between(-180.0, 180.0)
        | ~cleaned["cog"].between(0.0, 360.0, inclusive="left")
        | (cleaned["sog"] < 0.0)
        | (cleaned["mmsi"] <= 0)
    )
    invalid_rows = int(invalid_mask.sum())
    cleaned = cleaned.loc[~invalid_mask].copy()

    speed_mask = cleaned["sog"] > config.max_sog_kn
    filtered_speed_rows = int(speed_mask.sum())
    cleaned = cleaned.loc[~speed_mask].copy()

    before_duplicates = len(cleaned)
    cleaned = cleaned.drop_duplicates(
        subset=["timestamp", "mmsi"],
        keep=config.duplicate_keep,
    )
    duplicate_rows_removed = before_duplicates - len(cleaned)

    cleaned["mmsi"] = cleaned["mmsi"].astype("int64")
    cleaned = cleaned.sort_values(["timestamp", "mmsi"], kind="stable").reset_index(drop=True)

    if invalid_rows:
        warnings.append(f"removed {invalid_rows} structurally invalid rows")
    if filtered_speed_rows:
        warnings.append(f"removed {filtered_speed_rows} rows above max_sog_kn")
    if duplicate_rows_removed:
        warnings.append(f"removed {duplicate_rows_removed} duplicate timestamp/MMSI rows")

    report = ValidationReport(
        input_rows=input_rows,
        output_rows=len(cleaned),
        invalid_rows=invalid_rows,
        duplicate_rows_removed=duplicate_rows_removed,
        filtered_speed_rows=filtered_speed_rows,
        warnings=tuple(warnings),
    )
    return cleaned, report

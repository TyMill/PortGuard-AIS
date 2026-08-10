from pathlib import Path

import pandas as pd
import pytest

from portguard_ais.exceptions import InputSchemaError
from portguard_ais.ingestion.readers import read_ais_csv, validate_ais_frame


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(InputSchemaError):
        read_ais_csv(tmp_path / "missing.csv")


def test_missing_columns_raise() -> None:
    with pytest.raises(InputSchemaError):
        validate_ais_frame(pd.DataFrame([{"timestamp": "2026-08-03T12:00:00Z"}]))


def test_invalid_rows_raise() -> None:
    frame = pd.DataFrame(
        [
            {
                "timestamp": "not-a-date",
                "mmsi": 1,
                "lat": 53.4,
                "lon": 14.6,
                "sog": 5.0,
                "cog": 90.0,
            }
        ]
    )
    with pytest.raises(InputSchemaError):
        validate_ais_frame(frame)

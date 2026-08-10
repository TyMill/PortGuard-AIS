import pandas as pd

from portguard_ais.config import InputConfig
from portguard_ais.preprocessing.cleaning import clean_ais_frame


def test_cleaning_reports_invalid_duplicates_and_speed() -> None:
    frame = pd.DataFrame(
        [
            {
                "timestamp": "2026-08-03T12:00:00Z",
                "mmsi": 1,
                "lat": 53.4,
                "lon": 14.6,
                "sog": 5,
                "cog": 90,
            },
            {
                "timestamp": "2026-08-03T12:00:00Z",
                "mmsi": 1,
                "lat": 53.4,
                "lon": 14.6,
                "sog": 5,
                "cog": 90,
            },
            {"timestamp": "bad", "mmsi": 2, "lat": 53.4, "lon": 14.6, "sog": 5, "cog": 90},
            {
                "timestamp": "2026-08-03T12:00:00Z",
                "mmsi": 3,
                "lat": 53.4,
                "lon": 14.6,
                "sog": 99,
                "cog": 90,
            },
        ]
    )
    cleaned, report = clean_ais_frame(frame, InputConfig(max_sog_kn=60.0))
    assert len(cleaned) == 1
    assert report.invalid_rows == 1
    assert report.duplicate_rows_removed == 1
    assert report.filtered_speed_rows == 1

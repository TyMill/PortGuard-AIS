"""Canonical tabular AIS schema."""

REQUIRED_COLUMNS = ("timestamp", "mmsi", "lat", "lon", "sog", "cog")
OPTIONAL_COLUMNS = (
    "heading",
    "rot",
    "length_m",
    "beam_m",
    "vessel_type",
    "position_accuracy_m",
    "source",
)
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

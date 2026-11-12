"""Causal alignment of asynchronous AIS messages for offline evaluation.

For each evaluation tick, choose only the latest past AIS observation of each
vessel. The original measurement time and its age are retained as provenance.
No future observation is used and no physical vessel position is extrapolated.
"""

import pandas as pd

from portguard_ais.ingestion.schema import REQUIRED_COLUMNS


def align_causal_snapshots(
    frame: pd.DataFrame,
    *,
    seconds: int = 30,
    max_age_seconds: int = 120,
) -> pd.DataFrame:
    """Return grid-aligned, provenance-annotated rows with a bounded data age.

    The `timestamp` column becomes the decision timestamp; `source_timestamp`
    remains the actual AIS measurement time, and `age_seconds` quantifies
    observation staleness. This research utility is intentionally opt-in:
    carrying an old position forward is *not* motion extrapolation and should
    not be interpreted as equivalent to a simultaneous physical observation.
    """
    if seconds <= 0 or max_age_seconds < 0:
        raise ValueError("seconds must be positive and max_age_seconds non-negative")
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing required AIS columns: {missing}")
    if frame.empty:
        return frame.assign(
            source_timestamp=pd.Series(dtype="datetime64[ns, UTC]"),
            age_seconds=pd.Series(dtype="float64"),
            is_carried=pd.Series(dtype="bool"),
        )

    data = frame.copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="raise")
    data = data.sort_values(["mmsi", "timestamp"], kind="stable")
    # Duplicate MMSI/timestamp records require a deterministic policy.
    data = data.drop_duplicates(["mmsi", "timestamp"], keep="last")
    frequency = f"{seconds}s"
    grid = pd.date_range(
        start=data["timestamp"].min().floor(frequency),
        end=data["timestamp"].max().ceil(frequency),
        freq=frequency,
        tz="UTC",
    )
    ticks = pd.DataFrame({"timestamp": grid})
    parts: list[pd.DataFrame] = []
    for _, vessel in data.groupby("mmsi", sort=True):
        track = vessel.rename(columns={"timestamp": "source_timestamp"}).sort_values(
            "source_timestamp"
        )
        aligned = pd.merge_asof(
            ticks,
            track,
            left_on="timestamp",
            right_on="source_timestamp",
            direction="backward",
            tolerance=pd.Timedelta(seconds=max_age_seconds),
        )
        aligned = aligned.dropna(subset=["source_timestamp"])
        if aligned.empty:
            continue
        aligned["age_seconds"] = (
            aligned["timestamp"] - aligned["source_timestamp"]
        ).dt.total_seconds()
        aligned["is_carried"] = aligned["age_seconds"] > 0
        parts.append(aligned)

    if not parts:
        return data.iloc[:0].assign(
            source_timestamp=pd.Series(dtype="datetime64[ns, UTC]"),
            age_seconds=pd.Series(dtype="float64"),
            is_carried=pd.Series(dtype="bool"),
        )
    return (
        pd.concat(parts, ignore_index=True)
        .sort_values(["timestamp", "mmsi"], kind="stable")
        .reset_index(drop=True)
    )

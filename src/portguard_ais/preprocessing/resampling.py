"""Optional per-vessel track resampling and short-gap interpolation."""

import numpy as np
import pandas as pd

_NUMERIC_INTERPOLATION_COLUMNS = ("lat", "lon", "sog", "rot")
_CIRCULAR_COLUMNS = ("cog", "heading")


def resample_tracks(
    frame: pd.DataFrame,
    seconds: int,
    interpolation_limit: int = 2,
) -> pd.DataFrame:
    """Resample each MMSI independently on a regular UTC timeline."""
    if frame.empty:
        return frame.copy()

    parts: list[pd.DataFrame] = []
    frequency = f"{seconds}s"
    for _, group in frame.groupby("mmsi", sort=False):
        track = group.sort_values("timestamp").set_index("timestamp")
        resampled = track.resample(frequency).asfreq()
        resampled["mmsi"] = int(str(group["mmsi"].iloc[0]))
        available = [column for column in _NUMERIC_INTERPOLATION_COLUMNS if column in resampled]
        if available and interpolation_limit > 0:
            resampled[available] = resampled[available].interpolate(
                method="linear",
                limit=interpolation_limit,
                limit_area="inside",
            )
        # Unwrap angular measurements across 0/360 before interpolating.
        # Keep actual observed values unchanged.
        for column in _CIRCULAR_COLUMNS:
            if column not in resampled or interpolation_limit <= 0:
                continue
            original = resampled[column].copy()
            observed = original.notna()
            if observed.sum() < 2:
                continue
            unwrapped = pd.Series(float("nan"), index=original.index)
            unwrapped.loc[observed] = np.rad2deg(
                np.unwrap(np.deg2rad(original.loc[observed].to_numpy(dtype=float)))
            )
            filled = unwrapped.interpolate(
                method="linear",
                limit=interpolation_limit,
                limit_area="inside",
            )
            missing = ~observed & filled.notna()
            resampled.loc[missing, column] = filled.loc[missing] % 360.0
        categorical = [column for column in ("vessel_type", "source") if column in resampled]
        if categorical:
            resampled[categorical] = resampled[categorical].ffill().bfill()
        dimensions = [column for column in ("length_m", "beam_m") if column in resampled]
        if dimensions:
            resampled[dimensions] = resampled[dimensions].ffill().bfill()
        parts.append(resampled.reset_index())

    result = pd.concat(parts, ignore_index=True)
    return result.dropna(subset=["lat", "lon", "sog", "cog"]).sort_values(
        ["timestamp", "mmsi"], kind="stable"
    )

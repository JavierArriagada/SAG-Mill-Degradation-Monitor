"""
src/analytics/anomaly.py
────────────────────────
Anomaly detection for equipment sensor streams.

Algorithm: Rolling Z-score on a 24-hour sliding window.
  z = (x - μ_window) / σ_window
  |z| > threshold → anomaly

Returns a boolean mask and Z-score series for plotting.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_WINDOW = 24      # hours
DEFAULT_THRESHOLD = 2.5  # standard deviations


def rolling_zscore(
    series: pd.Series,
    window: int = DEFAULT_WINDOW,
    min_periods: int = 4,
) -> pd.Series:
    """
    Compute rolling Z-score for a time series.

    Args:
        series: Numeric pandas Series (indexed by time)
        window: Rolling window size (number of observations)
        min_periods: Minimum observations needed to compute score

    Returns:
        Z-score Series (NaN where window not yet full)
    """
    roll_mean = series.rolling(window=window, min_periods=min_periods).mean()
    roll_std = series.rolling(window=window, min_periods=min_periods).std()
    # Avoid division by zero
    roll_std = roll_std.replace(0.0, np.nan)
    return (series - roll_mean) / roll_std


def detect_anomalies(
    series: pd.Series,
    window: int = DEFAULT_WINDOW,
    threshold: float = DEFAULT_THRESHOLD,
) -> tuple[pd.Series, pd.Series]:
    """
    Detect anomalies in a sensor time series.

    Returns:
        (zscore_series, anomaly_mask)
        where anomaly_mask is a boolean Series (True = anomaly)
    """
    zscores = rolling_zscore(series, window=window)
    anomaly_mask = zscores.abs() > threshold
    return zscores, anomaly_mask


def annotate_anomalies(
    df: pd.DataFrame,
    variable: str,
    window: int = DEFAULT_WINDOW,
    threshold: float = DEFAULT_THRESHOLD,
) -> pd.DataFrame:
    """
    Add z-score and anomaly columns to a DataFrame for a given variable.

    Returns a copy of df with added columns:
      {variable}_zscore, {variable}_anomaly
    """
    df = df.copy()
    if variable not in df.columns:
        return df

    zscores, mask = detect_anomalies(df[variable], window=window, threshold=threshold)
    df[f"{variable}_zscore"] = zscores.round(3)
    df[f"{variable}_anomaly"] = mask
    return df


def get_anomaly_periods(
    df: pd.DataFrame,
    variable: str,
    timestamp_col: str = "timestamp",
    threshold: float = DEFAULT_THRESHOLD,
) -> list[dict]:
    """
    Extract discrete anomaly periods (start, end, peak_zscore).

    Useful for highlighting anomalous regions on trend charts.
    """
    df = annotate_anomalies(df, variable, threshold=threshold)
    anomaly_col = f"{variable}_anomaly"
    zscore_col = f"{variable}_zscore"

    if anomaly_col not in df.columns:
        return []

    periods: list[dict] = []
    in_anomaly = False
    start_ts = None
    peak_z = 0.0

    for _, row in df.iterrows():
        is_anomaly = bool(row.get(anomaly_col, False))
        z = float(row.get(zscore_col, 0.0) or 0.0)

        if is_anomaly and not in_anomaly:
            in_anomaly = True
            start_ts = row[timestamp_col]
            peak_z = abs(z)
        elif is_anomaly and in_anomaly:
            peak_z = max(peak_z, abs(z))
        elif not is_anomaly and in_anomaly:
            in_anomaly = False
            periods.append({"start": start_ts, "end": row[timestamp_col], "peak_zscore": round(peak_z, 2)})
            peak_z = 0.0

    if in_anomaly and start_ts is not None:
        periods.append({"start": start_ts, "end": df[timestamp_col].iloc[-1], "peak_zscore": round(peak_z, 2)})

    return periods

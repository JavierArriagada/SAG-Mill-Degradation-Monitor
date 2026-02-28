"""
src/analytics/thresholds.py
────────────────────────────
Dynamic threshold engine.

Provides:
  - Static ISO 10816 / equipment-config threshold lookup
  - Dynamic adaptive thresholds based on historical baseline statistics
  - Threshold band generation for Plotly chart overlays
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config.equipment import BALL_THRESHOLDS, SAG_THRESHOLDS, EquipmentThresholds


@dataclass(frozen=True)
class ThresholdBand:
    variable: str
    warning: float | None
    alert: float | None
    critical: float | None
    lower_bound: float | None = None   # e.g., minimum pressure


def get_static_thresholds(equipment_id: str, variable: str) -> ThresholdBand:
    """
    Return static threshold band for a given equipment variable.
    Based on ISO 10816 (vibration) and equipment engineering limits.
    """
    thr: EquipmentThresholds = SAG_THRESHOLDS if equipment_id == "SAG-01" else BALL_THRESHOLDS

    if variable == "vibration_mms":
        return ThresholdBand(
            variable=variable,
            warning=thr.vibration.zone_a,
            alert=thr.vibration.zone_b,
            critical=thr.vibration.zone_c,
        )
    if variable == "bearing_temp_c":
        return ThresholdBand(
            variable=variable,
            warning=thr.bearing_temp_c["warning"],
            alert=thr.bearing_temp_c["alert"],
            critical=thr.bearing_temp_c["critical"],
        )
    if variable == "hydraulic_pressure_bar":
        return ThresholdBand(
            variable=variable,
            warning=thr.hydraulic_pressure_bar["max"],
            alert=thr.hydraulic_pressure_bar["critical_high"],
            critical=None,
            lower_bound=thr.hydraulic_pressure_bar["min"],
        )
    if variable == "power_kw":
        return ThresholdBand(
            variable=variable,
            warning=thr.power_kw["nominal"] * 1.05,
            alert=thr.power_kw["max"],
            critical=None,
            lower_bound=thr.power_kw["min"],
        )
    if variable == "load_pct":
        return ThresholdBand(
            variable=variable,
            warning=thr.load_pct["opt_high"],
            alert=thr.load_pct["max"],
            critical=None,
            lower_bound=thr.load_pct["min"],
        )
    # Fallback: no thresholds defined
    return ThresholdBand(variable=variable, warning=None, alert=None, critical=None)


def compute_dynamic_thresholds(
    series: pd.Series,
    sigma_warning: float = 2.0,
    sigma_alert: float = 3.0,
    baseline_window: int = 168,  # 7 days × 24h
) -> ThresholdBand:
    """
    Compute adaptive thresholds from historical data statistics.

    Uses μ ± k×σ over the first `baseline_window` observations to establish
    normal operating bounds, then warns when recent values exceed them.

    Args:
        series: Full historical series (ascending time order)
        sigma_warning: Sigma multiplier for warning band
        sigma_alert: Sigma multiplier for alert band
        baseline_window: Observations to use for baseline stats

    Returns:
        ThresholdBand with dynamically computed levels
    """
    baseline = series.iloc[:min(baseline_window, len(series))]
    mu = float(baseline.mean())
    sigma = float(baseline.std())

    if sigma < 1e-6:
        sigma = mu * 0.05 if mu > 0 else 1.0

    return ThresholdBand(
        variable="dynamic",
        warning=round(mu + sigma_warning * sigma, 3),
        alert=round(mu + sigma_alert * sigma, 3),
        critical=None,
        lower_bound=round(mu - sigma_warning * sigma, 3),
    )


def evaluate_current_value(
    value: float,
    band: ThresholdBand,
) -> str:
    """
    Classify a current value against a ThresholdBand.

    Returns: "ok" | "warning" | "alert" | "critical"
    """
    if band.lower_bound is not None and value < band.lower_bound:
        return "alert"
    if band.critical is not None and value >= band.critical:
        return "critical"
    if band.alert is not None and value >= band.alert:
        return "alert"
    if band.warning is not None and value >= band.warning:
        return "warning"
    return "ok"


# ── Chart helpers ─────────────────────────────────────────────────────────────

STATUS_COLORS = {
    "ok": "#2ea44f",
    "warning": "#e8a020",
    "alert": "#f0883e",
    "critical": "#da3633",
}


def get_value_color(value: float, band: ThresholdBand) -> str:
    return STATUS_COLORS[evaluate_current_value(value, band)]

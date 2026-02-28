"""
src/analytics/health_index.py
──────────────────────────────
Composite Health Index (HI) calculation.

HI ∈ [0, 100] where 100 = perfect condition, 0 = failure imminent.

Weighted sub-indices (ISO 13381 guidance):
  vibration_score  30%  — ISO 10816 zone mapping
  thermal_score    25%  — bearing temperature vs thresholds
  pressure_score   20%  — hydraulic pressure vs operating range
  power_score      25%  — power draw vs nominal range

RUL (Remaining Useful Life) estimation:
  Linear extrapolation of HI trend over last 24 h → time to reach HI = 20.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config.equipment import BALL_THRESHOLDS, SAG_THRESHOLDS, EquipmentThresholds
from src.data.models import HealthSummary, SensorReading

# ── Sub-index helpers ─────────────────────────────────────────────────────────


def _vibration_score(vib: float, thr: EquipmentThresholds) -> float:
    """
    Map vibration to score using ISO 10816 zones.
    Zone A → 100, Zone B → 65, Zone C → 30, Zone D → 0.
    Linear interpolation between zone boundaries.
    """
    za, zb, zc = thr.vibration.zone_a, thr.vibration.zone_b, thr.vibration.zone_c
    if vib <= za:
        # Zone A: perfect to upper-A
        return float(100.0 - (vib / za) * 15.0)
    if vib <= zb:
        # Zone A→B: 85 → 65
        t = (vib - za) / (zb - za)
        return float(85.0 - t * 20.0)
    if vib <= zc:
        # Zone B→C: 65 → 30
        t = (vib - zb) / (zc - zb)
        return float(65.0 - t * 35.0)
    # Zone D: 30 → 0 for 2× zone_c
    t = min((vib - zc) / zc, 1.0)
    return float(30.0 - t * 30.0)


def _thermal_score(temp: float, thr: EquipmentThresholds) -> float:
    """Score bearing temperature vs warning/alert/critical thresholds."""
    warn = thr.bearing_temp_c["warning"]
    alert = thr.bearing_temp_c["alert"]
    crit = thr.bearing_temp_c["critical"]
    # Assume 20°C baseline
    baseline = 20.0
    if temp <= warn:
        t = max(0.0, (temp - baseline) / (warn - baseline))
        return float(100.0 - t * 15.0)
    if temp <= alert:
        t = (temp - warn) / (alert - warn)
        return float(85.0 - t * 35.0)
    if temp <= crit:
        t = (temp - alert) / (crit - alert)
        return float(50.0 - t * 40.0)
    # Above critical
    excess = temp - crit
    return float(max(0.0, 10.0 - excess * 2.0))


def _pressure_score(pressure: float, thr: EquipmentThresholds) -> float:
    """Score hydraulic pressure: penalize both below-min and above-max."""
    p_min = thr.hydraulic_pressure_bar["min"]
    p_max = thr.hydraulic_pressure_bar["max"]
    p_crit_high = thr.hydraulic_pressure_bar["critical_high"]
    p_mid = (p_min + p_max) / 2.0

    if p_min <= pressure <= p_max:
        # Within operating range: penalty based on distance from midpoint
        t = abs(pressure - p_mid) / (p_max - p_min) * 2.0
        return float(100.0 - t * 10.0)
    if pressure < p_min:
        drop = (p_min - pressure) / p_min
        return float(max(0.0, 90.0 - drop * 150.0))
    if pressure <= p_crit_high:
        t = (pressure - p_max) / (p_crit_high - p_max)
        return float(90.0 - t * 60.0)
    # Above critical high
    return 0.0


def _power_score(power: float, thr: EquipmentThresholds) -> float:
    """Score power draw vs nominal operating range."""
    p_min = thr.power_kw["min"]
    p_nom = thr.power_kw["nominal"]
    p_max = thr.power_kw["max"]

    if power < p_min:
        # Underpowered
        t = (p_min - power) / p_min
        return float(max(0.0, 80.0 - t * 120.0))
    if power <= p_nom * 1.05:
        # Nominal zone
        return 100.0
    if power <= p_max:
        t = (power - p_nom * 1.05) / (p_max - p_nom * 1.05)
        return float(100.0 - t * 25.0)
    # Above max
    excess = (power - p_max) / p_max
    return float(max(0.0, 75.0 - excess * 150.0))


# ── Main API ──────────────────────────────────────────────────────────────────

WEIGHTS = {
    "vibration": 0.30,
    "thermal": 0.25,
    "pressure": 0.20,
    "power": 0.25,
}


def compute_health_summary(reading: SensorReading) -> HealthSummary:
    """Compute a HealthSummary from a single SensorReading."""
    thr = SAG_THRESHOLDS if reading.equipment_id == "SAG-01" else BALL_THRESHOLDS

    vib_s = _vibration_score(reading.vibration_mms, thr)
    temp_s = _thermal_score(reading.bearing_temp_c, thr)
    pres_s = _pressure_score(reading.hydraulic_pressure_bar, thr)
    pwr_s = _power_score(reading.power_kw, thr)

    hi = (
        WEIGHTS["vibration"] * vib_s
        + WEIGHTS["thermal"] * temp_s
        + WEIGHTS["pressure"] * pres_s
        + WEIGHTS["power"] * pwr_s
    )
    hi = float(np.clip(hi, 0.0, 100.0))

    return HealthSummary(
        equipment_id=reading.equipment_id,
        timestamp=reading.timestamp,
        health_index=round(hi, 2),
        vibration_score=round(vib_s, 2),
        thermal_score=round(temp_s, 2),
        pressure_score=round(pres_s, 2),
        power_score=round(pwr_s, 2),
        degradation_mode=reading.degradation_mode,
    )


def compute_rul(health_series: pd.Series, window_hours: int = 48) -> float | None:
    """
    Estimate Remaining Useful Life (days) using linear extrapolation.

    Uses the last `window_hours` of health index data to estimate
    the degradation rate, then projects to HI = 20 (critical threshold).

    Returns None if trend is stable or improving.
    """
    if len(health_series) < 4:
        return None

    recent = health_series.iloc[-min(window_hours, len(health_series)) :]
    x = np.arange(len(recent), dtype=float)
    y = recent.values.astype(float)

    # Fit linear trend
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]  # HI change per hour

    # Use a small epsilon to guard against floating-point noise on flat series.
    # np.polyfit on perfectly identical values returns a slope that is not
    # exactly 0.0 (e.g. ~-7e-13), which would bypass the >= 0 guard and
    # produce an astronomically large (and meaningless) RUL estimate.
    if slope >= -1e-6:
        # Stable or improving — no meaningful RUL projection
        return None

    current_hi = float(recent.iloc[-1])
    critical_threshold = 20.0

    if current_hi <= critical_threshold:
        return 0.0

    # Hours to reach critical_threshold
    hours_to_critical = (current_hi - critical_threshold) / abs(slope)
    return round(hours_to_critical / 24.0, 1)


def compute_fleet_health(summaries: list[HealthSummary]) -> float:
    """Fleet-level health index: minimum of individual equipment HI."""
    if not summaries:
        return 100.0
    return min(s.health_index for s in summaries)

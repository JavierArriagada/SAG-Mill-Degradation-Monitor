"""
src/data/degradation.py
───────────────────────
Physics-inspired degradation pattern models for SAG and Ball mill failures.

Modes implemented:
  bearing      — Progressive Weibull-like degradation (vibration + temperature)
  liner        — Liner wear: power increase + load fluctuation
  hydraulic    — Pressure drop + variance increase
  misalignment — Shaft misalignment: 2X vibration signature

ISO 13381: prognostics framework for condition-based maintenance.
"""
from __future__ import annotations

from enum import Enum

import numpy as np


class DegradationStage(str, Enum):
    HEALTHY = "healthy"
    INCIPIENT = "incipient"  # 0–20%
    MODERATE = "moderate"   # 20–50%
    SEVERE = "severe"       # 50–80%
    CRITICAL = "critical"   # 80–100%


# ── Bearing degradation ───────────────────────────────────────────────────────

def bearing_degradation(
    t: float,
    base_vib: float,
    base_temp: float,
    rng: np.random.Generator,
) -> tuple[float, float]:
    """
    Weibull-like bearing degradation model.

    Args:
        t: Normalized time in degradation event [0.0, 1.0]
        base_vib: Baseline vibration (mm/s)
        base_temp: Baseline temperature (°C)
        rng: Random generator for reproducible noise

    Returns:
        (vibration_mms, temp_c)
    """
    if t < 0.3:
        # Incipient: slight, barely detectable increase
        vib_f = 1.0 + 0.6 * (t / 0.3) ** 2
        temp_f = 1.0 + 0.06 * (t / 0.3)
    elif t < 0.65:
        # Moderate: clear upward trend
        tn = (t - 0.3) / 0.35
        vib_f = 1.6 + 1.8 * tn
        temp_f = 1.06 + 0.16 * tn
    else:
        # Severe → critical: exponential runaway
        tn = (t - 0.65) / 0.35
        vib_f = 3.4 + 6.0 * tn ** 1.8
        temp_f = 1.22 + 0.30 * tn ** 1.5

    noise_vib = rng.normal(0.0, 0.06 * vib_f)
    noise_temp = rng.normal(0.0, 0.4)

    return (
        float(np.clip(base_vib * vib_f + noise_vib, 0.0, 49.0)),
        float(np.clip(base_temp * temp_f + noise_temp, 20.0, 199.0)),
    )


# ── Liner wear degradation ────────────────────────────────────────────────────

def liner_degradation(
    t: float,
    base_power: float,
    base_load: float,
    rng: np.random.Generator,
) -> tuple[float, float]:
    """
    Liner wear model: reduced grinding efficiency raises power draw
    and load fluctuation.

    Returns:
        (power_kw, load_pct)
    """
    power_factor = 1.0 + 0.10 * t + 0.08 * t ** 2
    load_noise_scale = 1.0 + 3.0 * t

    power = base_power * power_factor + rng.normal(0.0, 200.0 * power_factor)
    load = base_load + rng.normal(0.0, 2.5 * load_noise_scale)

    return (
        float(np.clip(power, 0.0, 24_999.0)),
        float(np.clip(load, 0.0, 99.9)),
    )


# ── Hydraulic degradation ─────────────────────────────────────────────────────

def hydraulic_degradation(
    t: float,
    base_pressure: float,
    rng: np.random.Generator,
) -> float:
    """
    Hydraulic system degradation: gradual pressure drop with
    increasing variance (leaks, pump wear).

    Returns:
        pressure_bar
    """
    drop = base_pressure * (0.12 * t + 0.06 * t ** 2)
    noise_scale = 4.0 * (1.0 + 4.0 * t)
    pressure = base_pressure - drop + rng.normal(0.0, noise_scale)
    return float(np.clip(pressure, 0.0, 299.0))


# ── Misalignment degradation ──────────────────────────────────────────────────

def misalignment_degradation(
    t: float,
    base_vib: float,
    rng: np.random.Generator,
) -> float:
    """
    Shaft misalignment creates a 2× running-speed vibration component.
    Vibration grows non-linearly from the onset.

    Returns:
        vibration_mms
    """
    vib_f = 1.0 + 1.2 * t + 2.5 * t ** 2
    noise = rng.normal(0.0, 0.08 * vib_f)
    return float(np.clip(base_vib * vib_f + noise, 0.0, 49.0))


# ── Utility ───────────────────────────────────────────────────────────────────

def classify_stage(t: float) -> DegradationStage:
    """Map normalized degradation progress [0, 1] to a named stage."""
    if t < 0.2:
        return DegradationStage.HEALTHY
    if t < 0.4:
        return DegradationStage.INCIPIENT
    if t < 0.6:
        return DegradationStage.MODERATE
    if t < 0.8:
        return DegradationStage.SEVERE
    return DegradationStage.CRITICAL

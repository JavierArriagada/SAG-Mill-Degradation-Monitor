"""
src/data/simulator.py
─────────────────────
Synthetic sensor data generator for SAG and Ball mills.

Generates:
  - 90 days of historical hourly readings per equipment
  - Embedded degradation events (1–3 per equipment over the period)
  - Derived alerts from threshold crossings
  - New "real-time" readings on each call to generate_realtime_reading()

Design:
  - Reproducible with SIMULATION_SEED for consistent demos
  - Degradation events have random start/duration within the history window
  - Each event can be bearing, liner, hydraulic (SAG) or bearing, misalignment (Ball)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

from config.alerts import AlertSeverity
from config.equipment import BALL_THRESHOLDS, EQUIPMENT_CONFIG, SAG_THRESHOLDS
from config.settings import settings
from src.data.degradation import (
    bearing_degradation,
    hydraulic_degradation,
    liner_degradation,
    misalignment_degradation,
)
from src.data.models import Alert, DegradationMode, SensorReading

# ── Baseline operating points ─────────────────────────────────────────────────

BASELINES: dict[str, dict] = {
    "SAG-01": {
        "vibration_mms": 1.6,
        "bearing_temp_c": 58.0,
        "hydraulic_pressure_bar": 150.0,
        "power_kw": 12_800.0,
        "load_pct": 40.0,
        "liner_wear_pct": 15.0,     # starts at 15%, wears toward 80%
        "seal_condition_pct": 95.0,  # starts healthy
        "throughput_tph": 2_150.0,
    },
    "BALL-01": {
        "vibration_mms": 1.2,
        "bearing_temp_c": 52.0,
        "hydraulic_pressure_bar": 110.0,
        "power_kw": 6_200.0,
        "load_pct": 44.0,
        "throughput_tph": 1_780.0,
    },
}

# Noise scales for normal operation (σ)
NOISE: dict[str, dict] = {
    "SAG-01": {
        "vibration_mms": 0.15,
        "bearing_temp_c": 0.8,
        "hydraulic_pressure_bar": 3.0,
        "power_kw": 180.0,
        "load_pct": 1.5,
        "liner_wear_pct": 0.05,
        "seal_condition_pct": 0.1,
        "throughput_tph": 60.0,
    },
    "BALL-01": {
        "vibration_mms": 0.10,
        "bearing_temp_c": 0.6,
        "hydraulic_pressure_bar": 2.5,
        "power_kw": 120.0,
        "load_pct": 1.2,
        "throughput_tph": 45.0,
    },
}


@dataclass
class DegradationEvent:
    mode: str
    start_hour: int   # index into the hourly timeline
    duration_hours: int  # how long the event lasts
    severity: float   # peak degradation at end (0..1)


def _plan_events(equipment_id: str, total_hours: int, rng: np.random.Generator) -> list[DegradationEvent]:
    """Randomly plan 1–3 degradation events within the history window."""
    eq = EQUIPMENT_CONFIG[equipment_id]
    modes = eq["degradation_modes"]
    n_events = rng.integers(1, 4)
    events: list[DegradationEvent] = []

    for _ in range(n_events):
        mode = rng.choice(modes)
        # Events shouldn't overlap; use last 70% of history for realism
        start = int(rng.integers(total_hours // 4, total_hours * 3 // 4))
        duration = int(rng.integers(48, 240))   # 2–10 days
        duration = min(duration, total_hours - start)
        severity = float(rng.uniform(0.4, 0.95))
        events.append(DegradationEvent(mode=mode, start_hour=start, duration_hours=duration, severity=severity))

    # Sort chronologically
    events.sort(key=lambda e: e.start_hour)
    return events


def _degradation_progress(hour: int, event: DegradationEvent) -> float | None:
    """
    Returns normalized progress t ∈ [0, 1] if the hour falls within the event,
    else None.
    """
    if event.start_hour <= hour < event.start_hour + event.duration_hours:
        raw = (hour - event.start_hour) / event.duration_hours
        return float(raw * event.severity)
    return None


def _generate_sag_reading(
    hour: int,
    ts: datetime,
    events: list[DegradationEvent],
    rng: np.random.Generator,
) -> SensorReading:
    base = BASELINES["SAG-01"]
    noise = NOISE["SAG-01"]

    vib = base["vibration_mms"] + rng.normal(0, noise["vibration_mms"])
    temp = base["bearing_temp_c"] + rng.normal(0, noise["bearing_temp_c"])
    pres = base["hydraulic_pressure_bar"] + rng.normal(0, noise["hydraulic_pressure_bar"])
    pwr = base["power_kw"] + rng.normal(0, noise["power_kw"])
    load = base["load_pct"] + rng.normal(0, noise["load_pct"])
    liner_wear = min(100.0, base["liner_wear_pct"] + hour * 0.008 + rng.normal(0, noise["liner_wear_pct"]))
    seal = max(0.0, base["seal_condition_pct"] - hour * 0.003 + rng.normal(0, noise["seal_condition_pct"]))
    tph = base["throughput_tph"] + rng.normal(0, noise["throughput_tph"])

    mode = DegradationMode.NORMAL

    for event in events:
        t = _degradation_progress(hour, event)
        if t is None:
            continue
        mode = DegradationMode(event.mode)
        if event.mode == "bearing":
            vib, temp = bearing_degradation(t, base["vibration_mms"], base["bearing_temp_c"], rng)
        elif event.mode == "liner":
            pwr, load = liner_degradation(t, base["power_kw"], base["load_pct"], rng)
            liner_wear = min(100.0, base["liner_wear_pct"] + t * 60.0)
        elif event.mode == "hydraulic":
            pres = hydraulic_degradation(t, base["hydraulic_pressure_bar"], rng)
        break  # only one active event at a time

    return SensorReading(
        timestamp=ts,
        equipment_id="SAG-01",
        vibration_mms=round(float(np.clip(vib, 0.0, 49.0)), 3),
        bearing_temp_c=round(float(np.clip(temp, 20.0, 199.0)), 2),
        hydraulic_pressure_bar=round(float(np.clip(pres, 0.0, 299.0)), 2),
        power_kw=round(float(np.clip(pwr, 0.0, 24_999.0)), 1),
        load_pct=round(float(np.clip(load, 0.0, 99.9)), 2),
        liner_wear_pct=round(float(np.clip(liner_wear, 0.0, 99.9)), 2),
        seal_condition_pct=round(float(np.clip(seal, 0.0, 100.0)), 2),
        throughput_tph=round(float(np.clip(tph, 0.0, 5_999.0)), 1),
        degradation_mode=mode,
    )


def _generate_ball_reading(
    hour: int,
    ts: datetime,
    events: list[DegradationEvent],
    rng: np.random.Generator,
) -> SensorReading:
    base = BASELINES["BALL-01"]
    noise = NOISE["BALL-01"]

    vib = base["vibration_mms"] + rng.normal(0, noise["vibration_mms"])
    temp = base["bearing_temp_c"] + rng.normal(0, noise["bearing_temp_c"])
    pres = base["hydraulic_pressure_bar"] + rng.normal(0, noise["hydraulic_pressure_bar"])
    pwr = base["power_kw"] + rng.normal(0, noise["power_kw"])
    load = base["load_pct"] + rng.normal(0, noise["load_pct"])
    tph = base["throughput_tph"] + rng.normal(0, noise["throughput_tph"])

    mode = DegradationMode.NORMAL

    for event in events:
        t = _degradation_progress(hour, event)
        if t is None:
            continue
        mode = DegradationMode(event.mode)
        if event.mode == "bearing":
            vib, temp = bearing_degradation(t, base["vibration_mms"], base["bearing_temp_c"], rng)
        elif event.mode == "misalignment":
            vib = misalignment_degradation(t, base["vibration_mms"], rng)
        break

    return SensorReading(
        timestamp=ts,
        equipment_id="BALL-01",
        vibration_mms=round(float(np.clip(vib, 0.0, 49.0)), 3),
        bearing_temp_c=round(float(np.clip(temp, 20.0, 199.0)), 2),
        hydraulic_pressure_bar=round(float(np.clip(pres, 0.0, 299.0)), 2),
        power_kw=round(float(np.clip(pwr, 0.0, 24_999.0)), 1),
        load_pct=round(float(np.clip(load, 0.0, 99.9)), 2),
        throughput_tph=round(float(np.clip(tph, 0.0, 5_999.0)), 1),
        degradation_mode=mode,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def generate_history(seed: int = settings.SIMULATION_SEED, days: int = settings.HISTORY_DAYS) -> dict[str, list[SensorReading]]:
    """
    Generate `days` × 24 hourly readings for each equipment.
    Returns dict keyed by equipment_id.
    """
    rng = np.random.default_rng(seed)
    total_hours = days * 24
    end_ts = datetime.now(tz=UTC).replace(minute=0, second=0, microsecond=0)
    start_ts = end_ts - timedelta(hours=total_hours - 1)

    timestamps = [start_ts + timedelta(hours=h) for h in range(total_hours)]

    sag_events = _plan_events("SAG-01", total_hours, rng)
    ball_events = _plan_events("BALL-01", total_hours, rng)

    sag_readings = [_generate_sag_reading(h, timestamps[h], sag_events, rng) for h in range(total_hours)]
    ball_readings = [_generate_ball_reading(h, timestamps[h], ball_events, rng) for h in range(total_hours)]

    return {"SAG-01": sag_readings, "BALL-01": ball_readings}


def generate_realtime_reading(equipment_id: str) -> SensorReading:
    """
    Generate a single fresh reading that simulates a real-time sensor update.
    Uses a random seed based on current time for slight variation.
    """
    seed = int(datetime.now(tz=UTC).timestamp()) % 10_000
    rng = np.random.default_rng(seed)
    ts = datetime.now(tz=UTC).replace(second=0, microsecond=0)

    if equipment_id == "SAG-01":
        return _generate_sag_reading(0, ts, [], rng)
    return _generate_ball_reading(0, ts, [], rng)


def derive_alerts(readings: list[SensorReading], equipment_id: str) -> list[Alert]:
    """
    Scan a list of readings and emit alerts for threshold crossings.
    Returns a deduplicated list (one alert per crossing per variable).
    """
    thresholds = SAG_THRESHOLDS if equipment_id == "SAG-01" else BALL_THRESHOLDS
    alerts: list[Alert] = []
    in_alert: dict[str, bool] = {}  # variable → currently alerting

    for reading in readings:
        checks = [
            ("vibration_mms", reading.vibration_mms, thresholds.vibration.zone_b, thresholds.vibration.zone_c),
            ("bearing_temp_c", reading.bearing_temp_c,
             thresholds.bearing_temp_c["warning"], thresholds.bearing_temp_c["alert"]),
            ("hydraulic_pressure_bar", reading.hydraulic_pressure_bar,
             None, thresholds.hydraulic_pressure_bar["critical_high"]),
        ]

        for variable, value, warn_thresh, alert_thresh in checks:
            alert_key = f"{equipment_id}:{variable}"
            currently = in_alert.get(alert_key, False)

            if alert_thresh is not None and value > alert_thresh:
                severity = AlertSeverity.CRITICAL
            elif warn_thresh is not None and value > warn_thresh:
                severity = AlertSeverity.WARNING
            else:
                if currently:
                    in_alert[alert_key] = False
                continue

            if not currently:
                alerts.append(Alert(
                    id=str(uuid.uuid4()),
                    timestamp=reading.timestamp,
                    equipment_id=equipment_id,
                    severity=severity.value,
                    category=variable.split("_")[0] if "_" in variable else variable,
                    variable=variable,
                    value=round(value, 3),
                    threshold=alert_thresh if value > (alert_thresh or 0) else (warn_thresh or 0),
                    message=f"{equipment_id}: {variable} = {value:.2f} (umbral: {alert_thresh or warn_thresh:.2f})",
                ))
                in_alert[alert_key] = True

    return alerts


def to_dataframe(readings: list[SensorReading]) -> pd.DataFrame:
    """Convert a list of SensorReadings to a pandas DataFrame."""
    return pd.DataFrame([r.model_dump() for r in readings])

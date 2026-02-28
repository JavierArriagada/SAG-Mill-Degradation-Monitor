"""
config/equipment.py
───────────────────
Equipment definitions and ISO-compliant thresholds.

ISO 10816 vibration severity zones (mm/s RMS):
  Zone A: ≤ zone_a  → New/OK
  Zone B: ≤ zone_b  → Acceptable (long-term)
  Zone C: ≤ zone_c  → Unsatisfactory (short-term only)
  Zone D: > zone_c  → Danger / shutdown risk

ISO 13381: Condition monitoring prognostics framework.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class VibrationZones:
    """ISO 10816 vibration zone boundaries in mm/s RMS."""
    zone_a: float  # ≤ zone_a → OK
    zone_b: float  # ≤ zone_b → Warning
    zone_c: float  # ≤ zone_c → Alert
    # > zone_c → Critical (Zone D)


@dataclass(frozen=True)
class EquipmentThresholds:
    vibration: VibrationZones
    bearing_temp_c: dict[str, float]        # warning / alert / critical
    hydraulic_pressure_bar: dict[str, float]  # min / max / critical_high
    power_kw: dict[str, float]               # min / nominal / max
    load_pct: dict[str, float]               # min / opt_low / opt_high / max


# ── SAG Mill thresholds ───────────────────────────────────────────────────────
SAG_THRESHOLDS = EquipmentThresholds(
    vibration=VibrationZones(zone_a=2.3, zone_b=4.5, zone_c=7.1),
    bearing_temp_c={"warning": 72.0, "alert": 82.0, "critical": 92.0},
    hydraulic_pressure_bar={"min": 120.0, "max": 180.0, "critical_high": 195.0},
    power_kw={"min": 8_000.0, "nominal": 13_500.0, "max": 15_000.0},
    load_pct={"min": 20.0, "opt_low": 35.0, "opt_high": 45.0, "max": 55.0},
)

# ── Ball Mill thresholds ──────────────────────────────────────────────────────
BALL_THRESHOLDS = EquipmentThresholds(
    vibration=VibrationZones(zone_a=1.8, zone_b=3.5, zone_c=5.6),
    bearing_temp_c={"warning": 68.0, "alert": 78.0, "critical": 88.0},
    hydraulic_pressure_bar={"min": 80.0, "max": 140.0, "critical_high": 155.0},
    power_kw={"min": 3_000.0, "nominal": 6_500.0, "max": 7_500.0},
    load_pct={"min": 25.0, "opt_low": 40.0, "opt_high": 50.0, "max": 60.0},
)

# ── Equipment registry ────────────────────────────────────────────────────────
EQUIPMENT_CONFIG: dict[str, dict] = {
    "SAG-01": {
        "id": "SAG-01",
        "name": "Molino SAG",
        "type": "SAG",
        "color": "#58a6ff",
        "color_rgba": "rgba(88,166,255,0.15)",
        "thresholds": SAG_THRESHOLDS,
        "variables": [
            "vibration_mms",
            "bearing_temp_c",
            "hydraulic_pressure_bar",
            "power_kw",
            "load_pct",
            "liner_wear_pct",
            "seal_condition_pct",
        ],
        "degradation_modes": ["bearing", "liner", "hydraulic"],
        "nominal_throughput_tph": 2_200.0,
    },
    "BALL-01": {
        "id": "BALL-01",
        "name": "Molino de Bolas",
        "type": "BALL",
        "color": "#2ea44f",
        "color_rgba": "rgba(46,164,79,0.15)",
        "thresholds": BALL_THRESHOLDS,
        "variables": [
            "vibration_mms",
            "bearing_temp_c",
            "hydraulic_pressure_bar",
            "power_kw",
            "load_pct",
        ],
        "degradation_modes": ["bearing", "misalignment"],
        "nominal_throughput_tph": 1_800.0,
    },
}

EQUIPMENT_IDS = list(EQUIPMENT_CONFIG.keys())

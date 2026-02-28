"""
src/data/models.py
──────────────────
Pydantic v2 data models for sensor readings, alerts, and health summaries.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DegradationMode(str, Enum):
    NORMAL = "normal"
    BEARING = "bearing"
    LINER = "liner"
    HYDRAULIC = "hydraulic"
    MISALIGNMENT = "misalignment"


class SensorReading(BaseModel):
    timestamp: datetime
    equipment_id: str
    vibration_mms: float = Field(ge=0.0, le=50.0)
    bearing_temp_c: float = Field(ge=0.0, le=200.0)
    hydraulic_pressure_bar: float = Field(ge=0.0, le=300.0)
    power_kw: float = Field(ge=0.0, le=25_000.0)
    load_pct: float = Field(ge=0.0, le=100.0)
    liner_wear_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    seal_condition_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    throughput_tph: float = Field(ge=0.0, le=6_000.0)
    degradation_mode: DegradationMode = DegradationMode.NORMAL
    health_index: float = Field(default=100.0, ge=0.0, le=100.0)


class Alert(BaseModel):
    id: str
    timestamp: datetime
    equipment_id: str
    severity: str
    category: str
    variable: str
    value: float
    threshold: float
    message: str
    acknowledged: bool = False


class HealthSummary(BaseModel):
    equipment_id: str
    timestamp: datetime
    health_index: float = Field(ge=0.0, le=100.0)
    vibration_score: float = Field(ge=0.0, le=100.0)
    thermal_score: float = Field(ge=0.0, le=100.0)
    pressure_score: float = Field(ge=0.0, le=100.0)
    power_score: float = Field(ge=0.0, le=100.0)
    predicted_rul_days: float | None = None
    active_alerts: int = 0
    degradation_mode: DegradationMode = DegradationMode.NORMAL

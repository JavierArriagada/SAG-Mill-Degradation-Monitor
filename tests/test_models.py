"""
tests/test_models.py
─────────────────────
Tests for Pydantic v2 data models.
"""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.data.models import SensorReading, Alert, HealthSummary, DegradationMode


class TestSensorReading:
    def test_valid_sag_reading(self, sample_sag_reading):
        r = sample_sag_reading
        assert r.equipment_id == "SAG-01"
        assert 0.0 <= r.vibration_mms <= 50.0
        assert 0.0 <= r.health_index <= 100.0

    def test_valid_ball_reading(self, sample_ball_reading):
        r = sample_ball_reading
        assert r.equipment_id == "BALL-01"
        assert r.liner_wear_pct is None
        assert r.seal_condition_pct is None

    def test_degradation_mode_default(self, sample_sag_reading):
        assert sample_sag_reading.degradation_mode == DegradationMode.NORMAL

    def test_vibration_bounds(self, now):
        with pytest.raises(ValidationError):
            SensorReading(
                timestamp=now, equipment_id="SAG-01",
                vibration_mms=-1.0,  # invalid
                bearing_temp_c=60.0, hydraulic_pressure_bar=150.0,
                power_kw=12000.0, load_pct=40.0, throughput_tph=2000.0,
            )

    def test_health_index_bounds(self, now):
        with pytest.raises(ValidationError):
            SensorReading(
                timestamp=now, equipment_id="SAG-01",
                vibration_mms=1.5, bearing_temp_c=60.0,
                hydraulic_pressure_bar=150.0, power_kw=12000.0,
                load_pct=40.0, throughput_tph=2000.0,
                health_index=150.0,  # invalid (> 100)
            )

    def test_model_dump(self, sample_sag_reading):
        data = sample_sag_reading.model_dump()
        assert isinstance(data, dict)
        assert "timestamp" in data
        assert "vibration_mms" in data
        assert data["equipment_id"] == "SAG-01"


class TestAlert:
    def test_valid_alert(self, now):
        alert = Alert(
            id="test-001",
            timestamp=now,
            equipment_id="SAG-01",
            severity="warning",
            category="vibration",
            variable="vibration_mms",
            value=5.2,
            threshold=4.5,
            message="SAG-01: vibration_mms = 5.20 (umbral: 4.50)",
        )
        assert alert.acknowledged is False
        assert alert.severity == "warning"

    def test_acknowledged_default(self, now):
        alert = Alert(
            id="test-002",
            timestamp=now,
            equipment_id="BALL-01",
            severity="critical",
            category="temperature",
            variable="bearing_temp_c",
            value=92.0,
            threshold=88.0,
            message="Critical temperature",
        )
        assert not alert.acknowledged


class TestHealthSummary:
    def test_health_summary_valid(self, now):
        summary = HealthSummary(
            equipment_id="SAG-01",
            timestamp=now,
            health_index=85.0,
            vibration_score=90.0,
            thermal_score=88.0,
            pressure_score=80.0,
            power_score=82.0,
        )
        assert summary.predicted_rul_days is None
        assert summary.active_alerts == 0
        assert summary.degradation_mode == DegradationMode.NORMAL

    def test_health_index_bounds(self, now):
        with pytest.raises(ValidationError):
            HealthSummary(
                equipment_id="SAG-01",
                timestamp=now,
                health_index=110.0,  # invalid
                vibration_score=90.0,
                thermal_score=88.0,
                pressure_score=80.0,
                power_score=82.0,
            )

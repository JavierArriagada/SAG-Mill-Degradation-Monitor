"""
tests/conftest.py
─────────────────
Shared pytest fixtures for SAG Monitor test suite.
"""
import os
import pytest
import numpy as np
from datetime import datetime, timezone

# Use in-memory SQLite for tests
os.environ.setdefault("DATABASE_URL", ":memory:")
os.environ.setdefault("HISTORY_DAYS", "7")
os.environ.setdefault("SIMULATION_SEED", "42")


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(42)


@pytest.fixture
def now() -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_sag_reading(now):
    from src.data.models import SensorReading, DegradationMode
    return SensorReading(
        timestamp=now,
        equipment_id="SAG-01",
        vibration_mms=1.8,
        bearing_temp_c=60.0,
        hydraulic_pressure_bar=148.0,
        power_kw=12_500.0,
        load_pct=41.0,
        liner_wear_pct=18.0,
        seal_condition_pct=93.0,
        throughput_tph=2_100.0,
        degradation_mode=DegradationMode.NORMAL,
        health_index=90.0,
    )


@pytest.fixture
def sample_ball_reading(now):
    from src.data.models import SensorReading, DegradationMode
    return SensorReading(
        timestamp=now,
        equipment_id="BALL-01",
        vibration_mms=1.1,
        bearing_temp_c=53.0,
        hydraulic_pressure_bar=109.0,
        power_kw=6_100.0,
        load_pct=43.0,
        throughput_tph=1_760.0,
        degradation_mode=DegradationMode.NORMAL,
        health_index=95.0,
    )


@pytest.fixture
def degraded_sag_reading(now):
    """A SAG mill reading in bearing degradation (severe)."""
    from src.data.models import SensorReading, DegradationMode
    return SensorReading(
        timestamp=now,
        equipment_id="SAG-01",
        vibration_mms=8.5,    # Zone D — critical
        bearing_temp_c=88.0,  # Above alert threshold
        hydraulic_pressure_bar=145.0,
        power_kw=13_200.0,
        load_pct=42.0,
        liner_wear_pct=25.0,
        seal_condition_pct=80.0,
        throughput_tph=1_950.0,
        degradation_mode=DegradationMode.BEARING,
        health_index=30.0,
    )

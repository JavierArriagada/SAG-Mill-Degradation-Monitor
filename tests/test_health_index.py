"""
tests/test_health_index.py
───────────────────────────
Tests for the composite health index calculator.
"""

import numpy as np
import pandas as pd

from config.equipment import BALL_THRESHOLDS, SAG_THRESHOLDS
from src.analytics.health_index import (
    _power_score,
    _pressure_score,
    _thermal_score,
    _vibration_score,
    compute_fleet_health,
    compute_health_summary,
    compute_rul,
)
from src.data.models import HealthSummary


class TestVibrationScore:
    def test_perfect_vibration_returns_near_100(self):
        score = _vibration_score(0.5, SAG_THRESHOLDS)  # well in zone A
        assert score >= 90.0

    def test_zone_a_high_boundary(self):
        # At zone_a boundary
        score = _vibration_score(SAG_THRESHOLDS.vibration.zone_a, SAG_THRESHOLDS)
        assert 75.0 <= score <= 95.0

    def test_zone_b_gives_reduced_score(self):
        # Between zone_a and zone_b
        vib = (SAG_THRESHOLDS.vibration.zone_a + SAG_THRESHOLDS.vibration.zone_b) / 2
        score = _vibration_score(vib, SAG_THRESHOLDS)
        assert 50.0 <= score <= 85.0

    def test_zone_d_gives_low_score(self):
        # Way above zone_c
        score = _vibration_score(20.0, SAG_THRESHOLDS)
        assert score < 30.0

    def test_score_decreases_with_vibration(self):
        scores = [_vibration_score(v, SAG_THRESHOLDS) for v in [0.5, 2.0, 4.0, 7.0, 15.0]]
        assert scores == sorted(scores, reverse=True)

    def test_ball_mill_thresholds_tighter(self):
        # Ball mill has tighter zone_a (1.8 vs 2.3 for SAG)
        # Same vibration should score lower for ball mill
        vib = 1.9  # in SAG zone A, but in Ball zone B
        sag_score = _vibration_score(vib, SAG_THRESHOLDS)
        ball_score = _vibration_score(vib, BALL_THRESHOLDS)
        assert sag_score > ball_score


class TestThermalScore:
    def test_cool_temperature_returns_high_score(self):
        score = _thermal_score(40.0, SAG_THRESHOLDS)
        assert score >= 85.0

    def test_critical_temperature_returns_low_score(self):
        crit = SAG_THRESHOLDS.bearing_temp_c["critical"]
        score = _thermal_score(crit + 10.0, SAG_THRESHOLDS)
        assert score < 20.0

    def test_score_decreases_with_temperature(self):
        temps = [40.0, 65.0, 75.0, 85.0, 95.0]
        scores = [_thermal_score(t, SAG_THRESHOLDS) for t in temps]
        assert scores == sorted(scores, reverse=True)


class TestPressureScore:
    def test_mid_range_pressure_returns_high_score(self):
        p_mid = (
            SAG_THRESHOLDS.hydraulic_pressure_bar["min"]
            + SAG_THRESHOLDS.hydraulic_pressure_bar["max"]
        ) / 2
        score = _pressure_score(p_mid, SAG_THRESHOLDS)
        assert score >= 88.0

    def test_below_min_pressure_penalized(self):
        below_min = SAG_THRESHOLDS.hydraulic_pressure_bar["min"] - 20.0
        score = _pressure_score(below_min, SAG_THRESHOLDS)
        assert score < 80.0

    def test_above_critical_returns_zero(self):
        crit = SAG_THRESHOLDS.hydraulic_pressure_bar["critical_high"]
        score = _pressure_score(crit + 10.0, SAG_THRESHOLDS)
        assert score == 0.0


class TestPowerScore:
    def test_nominal_power_returns_high_score(self):
        nom = SAG_THRESHOLDS.power_kw["nominal"]
        score = _power_score(nom, SAG_THRESHOLDS)
        assert score >= 95.0

    def test_above_max_power_penalized(self):
        above_max = SAG_THRESHOLDS.power_kw["max"] + 1000.0
        score = _power_score(above_max, SAG_THRESHOLDS)
        assert score < 75.0

    def test_below_min_power_penalized(self):
        below_min = SAG_THRESHOLDS.power_kw["min"] - 2000.0
        score = _power_score(below_min, SAG_THRESHOLDS)
        assert score < 60.0


class TestComputeHealthSummary:
    def test_healthy_reading_high_hi(self, sample_sag_reading):
        summary = compute_health_summary(sample_sag_reading)
        assert summary.health_index >= 70.0
        assert 0.0 <= summary.health_index <= 100.0

    def test_degraded_reading_low_hi(self, degraded_sag_reading):
        summary = compute_health_summary(degraded_sag_reading)
        assert summary.health_index < 60.0

    def test_returns_health_summary_type(self, sample_sag_reading):
        summary = compute_health_summary(sample_sag_reading)
        assert isinstance(summary, HealthSummary)
        assert summary.equipment_id == "SAG-01"

    def test_subscores_in_range(self, sample_sag_reading):
        summary = compute_health_summary(sample_sag_reading)
        for score in [
            summary.vibration_score,
            summary.thermal_score,
            summary.pressure_score,
            summary.power_score,
        ]:
            assert 0.0 <= score <= 100.0

    def test_ball_mill_healthy(self, sample_ball_reading):
        summary = compute_health_summary(sample_ball_reading)
        assert summary.health_index >= 70.0
        assert summary.equipment_id == "BALL-01"

    def test_degraded_higher_vibration_lower_hi(self, sample_sag_reading, degraded_sag_reading):
        s1 = compute_health_summary(sample_sag_reading)
        s2 = compute_health_summary(degraded_sag_reading)
        assert s1.health_index > s2.health_index


class TestComputeRUL:
    def test_stable_trend_returns_none(self):
        hi_series = pd.Series([90.0] * 50)
        rul = compute_rul(hi_series)
        assert rul is None

    def test_improving_returns_none(self):
        hi_series = pd.Series(list(range(50, 100)))  # increasing
        rul = compute_rul(hi_series)
        assert rul is None

    def test_degrading_returns_positive_days(self):
        # Clearly degrading: from 80 to 25 over 48h
        hi_series = pd.Series(np.linspace(80, 25, 48))
        rul = compute_rul(hi_series, window_hours=48)
        assert rul is not None
        assert rul > 0.0

    def test_already_critical_returns_zero(self):
        hi_series = pd.Series(np.linspace(50, 15, 48))  # below 20 at end
        rul = compute_rul(hi_series, window_hours=48)
        assert rul == 0.0

    def test_too_few_points_returns_none(self):
        hi_series = pd.Series([80.0, 75.0])
        rul = compute_rul(hi_series)
        assert rul is None


class TestComputeFleetHealth:
    def test_fleet_health_is_minimum(self, now):
        summaries = [
            HealthSummary(
                equipment_id="SAG-01",
                timestamp=now,
                health_index=85.0,
                vibration_score=90.0,
                thermal_score=88.0,
                pressure_score=80.0,
                power_score=82.0,
            ),
            HealthSummary(
                equipment_id="BALL-01",
                timestamp=now,
                health_index=60.0,
                vibration_score=70.0,
                thermal_score=65.0,
                pressure_score=55.0,
                power_score=60.0,
            ),
        ]
        fleet = compute_fleet_health(summaries)
        assert fleet == 60.0

    def test_empty_list_returns_100(self):
        assert compute_fleet_health([]) == 100.0

"""
tests/test_thresholds.py
─────────────────────────
Tests for the threshold engine.
"""

import numpy as np
import pandas as pd

from src.analytics.thresholds import (
    ThresholdBand,
    compute_dynamic_thresholds,
    evaluate_current_value,
    get_static_thresholds,
    get_value_color,
)


class TestGetStaticThresholds:
    def test_vibration_thresholds_sag(self):
        band = get_static_thresholds("SAG-01", "vibration_mms")
        assert band.warning == 2.3  # ISO 10816 zone_a
        assert band.alert == 4.5  # zone_b
        assert band.critical == 7.1  # zone_c

    def test_vibration_thresholds_ball(self):
        band = get_static_thresholds("BALL-01", "vibration_mms")
        assert band.warning == 1.8
        assert band.alert == 3.5
        assert band.critical == 5.6

    def test_temperature_thresholds(self):
        band = get_static_thresholds("SAG-01", "bearing_temp_c")
        assert band.warning == 72.0
        assert band.alert == 82.0
        assert band.critical == 92.0

    def test_pressure_has_lower_bound(self):
        band = get_static_thresholds("SAG-01", "hydraulic_pressure_bar")
        assert band.lower_bound is not None
        assert band.lower_bound == 120.0

    def test_unknown_variable_returns_empty_band(self):
        band = get_static_thresholds("SAG-01", "unknown_variable")
        assert band.warning is None
        assert band.alert is None
        assert band.critical is None


class TestComputeDynamicThresholds:
    def test_returns_threshold_band(self):
        series = pd.Series(np.random.default_rng(42).normal(100.0, 5.0, 200))
        band = compute_dynamic_thresholds(series)
        assert isinstance(band, ThresholdBand)
        assert band.warning is not None
        assert band.alert is not None

    def test_warning_above_alert(self):
        series = pd.Series(np.random.default_rng(42).normal(50.0, 3.0, 200))
        band = compute_dynamic_thresholds(series)
        assert band.warning < band.alert  # type: ignore

    def test_consistent_series_small_band(self):
        """Very stable series should have tight thresholds."""
        series = pd.Series([100.0] * 200)
        band = compute_dynamic_thresholds(series)
        # Should use fallback sigma (5% of mean = 5.0)
        assert band.warning is not None

    def test_lower_bound_below_mean(self):
        series = pd.Series(np.random.default_rng(42).normal(100.0, 5.0, 200))
        band = compute_dynamic_thresholds(series)
        assert band.lower_bound is not None
        assert band.lower_bound < 100.0


class TestEvaluateCurrentValue:
    def test_ok_status(self):
        band = ThresholdBand("v", warning=4.5, alert=7.1, critical=10.0)
        assert evaluate_current_value(2.0, band) == "ok"

    def test_warning_status(self):
        band = ThresholdBand("v", warning=4.5, alert=7.1, critical=10.0)
        assert evaluate_current_value(5.0, band) == "warning"

    def test_alert_status(self):
        band = ThresholdBand("v", warning=4.5, alert=7.1, critical=10.0)
        assert evaluate_current_value(8.0, band) == "alert"

    def test_critical_status(self):
        band = ThresholdBand("v", warning=4.5, alert=7.1, critical=10.0)
        assert evaluate_current_value(11.0, band) == "critical"

    def test_below_lower_bound_triggers_alert(self):
        band = ThresholdBand("p", warning=None, alert=None, critical=None, lower_bound=100.0)
        assert evaluate_current_value(80.0, band) == "alert"

    def test_no_thresholds_always_ok(self):
        band = ThresholdBand("x", warning=None, alert=None, critical=None)
        assert evaluate_current_value(999.0, band) == "ok"


class TestGetValueColor:
    def test_ok_is_green(self):
        band = ThresholdBand("v", warning=4.5, alert=7.1, critical=10.0)
        assert get_value_color(1.0, band) == "#2ea44f"

    def test_critical_is_red(self):
        band = ThresholdBand("v", warning=4.5, alert=7.1, critical=10.0)
        assert get_value_color(15.0, band) == "#da3633"

    def test_warning_is_orange(self):
        band = ThresholdBand("v", warning=4.5, alert=7.1, critical=10.0)
        assert get_value_color(5.0, band) == "#e8a020"

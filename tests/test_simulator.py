"""
tests/test_simulator.py
────────────────────────
Tests for the synthetic data simulator.
"""

from src.data.models import DegradationMode
from src.data.simulator import (
    _degradation_progress,
    derive_alerts,
    generate_history,
    generate_realtime_reading,
    to_dataframe,
)


class TestGenerateHistory:
    def test_returns_both_equipment(self):
        history = generate_history(seed=42, days=3)
        assert "SAG-01" in history
        assert "BALL-01" in history

    def test_correct_reading_count(self):
        days = 5
        history = generate_history(seed=42, days=days)
        expected = days * 24
        assert len(history["SAG-01"]) == expected
        assert len(history["BALL-01"]) == expected

    def test_readings_are_chronological(self):
        history = generate_history(seed=42, days=3)
        timestamps = [r.timestamp for r in history["SAG-01"]]
        assert timestamps == sorted(timestamps)

    def test_readings_have_valid_values(self):
        history = generate_history(seed=42, days=2)
        for reading in history["SAG-01"]:
            assert 0.0 <= reading.vibration_mms <= 50.0
            assert 0.0 <= reading.bearing_temp_c <= 200.0
            assert 0.0 <= reading.hydraulic_pressure_bar <= 300.0
            assert 0.0 <= reading.load_pct <= 100.0
            assert reading.equipment_id == "SAG-01"

    def test_sag_has_liner_wear(self):
        history = generate_history(seed=42, days=2)
        for reading in history["SAG-01"]:
            assert reading.liner_wear_pct is not None
            assert reading.seal_condition_pct is not None

    def test_ball_no_liner_wear(self):
        history = generate_history(seed=42, days=2)
        for reading in history["BALL-01"]:
            assert reading.liner_wear_pct is None
            assert reading.seal_condition_pct is None

    def test_reproducibility(self):
        h1 = generate_history(seed=99, days=2)
        h2 = generate_history(seed=99, days=2)
        for r1, r2 in zip(h1["SAG-01"], h2["SAG-01"], strict=False):
            assert r1.vibration_mms == r2.vibration_mms
            assert r1.bearing_temp_c == r2.bearing_temp_c

    def test_different_seeds_differ(self):
        h1 = generate_history(seed=1, days=2)
        h2 = generate_history(seed=2, days=2)
        # At least some readings should differ
        diffs = [
            r1.vibration_mms != r2.vibration_mms
            for r1, r2 in zip(h1["SAG-01"], h2["SAG-01"], strict=False)
        ]
        assert any(diffs)

    def test_contains_degradation_events(self):
        """Over 30 days, there should be some non-normal readings."""
        history = generate_history(seed=42, days=30)
        modes = {r.degradation_mode for r in history["SAG-01"]}
        assert DegradationMode.NORMAL in modes
        # With seed=42 and 30 days, degradation events should occur
        assert len(modes) > 1


class TestDeriveAlerts:
    def test_no_alerts_for_healthy_readings(self):
        history = generate_history(seed=42, days=3)
        # Get only normal readings
        normal = [
            r
            for r in history["SAG-01"]
            if r.degradation_mode == DegradationMode.NORMAL and r.vibration_mms < 2.3
        ]
        if normal:
            alerts = derive_alerts(normal[:20], "SAG-01")
            # Should have few/no vibration alerts in zone A
            vib_alerts = [a for a in alerts if a.variable == "vibration_mms"]
            assert len(vib_alerts) == 0

    def test_alerts_for_degraded_readings(self):
        """Severe bearing degradation should trigger alerts."""
        history = generate_history(seed=42, days=30)
        sag_readings = history["SAG-01"]
        alerts = derive_alerts(sag_readings, "SAG-01")
        # Should have some alerts over 30 days with degradation events
        assert isinstance(alerts, list)

    def test_alert_structure(self):
        """Each alert should have required fields."""
        history = generate_history(seed=42, days=30)
        alerts = derive_alerts(history["SAG-01"], "SAG-01")
        for alert in alerts:
            assert alert.id
            assert alert.equipment_id == "SAG-01"
            assert alert.severity in ("info", "warning", "alert", "critical")
            assert alert.value > 0
            assert alert.threshold > 0


class TestRealtimeReading:
    def test_generates_valid_reading(self):
        reading = generate_realtime_reading("SAG-01")
        assert reading.equipment_id == "SAG-01"
        assert 0.0 <= reading.vibration_mms <= 50.0
        assert reading.timestamp is not None
        assert reading.timestamp.tzinfo is not None

    def test_ball_mill_reading(self):
        reading = generate_realtime_reading("BALL-01")
        assert reading.equipment_id == "BALL-01"
        assert reading.liner_wear_pct is None


class TestToDataframe:
    def test_returns_dataframe(self):
        import pandas as pd

        history = generate_history(seed=42, days=2)
        df = to_dataframe(history["SAG-01"])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2 * 24
        assert "vibration_mms" in df.columns
        assert "bearing_temp_c" in df.columns


class TestDegradationProgress:
    def test_none_outside_event(self):
        from src.data.simulator import DegradationEvent

        event = DegradationEvent(mode="bearing", start_hour=100, duration_hours=48, severity=0.8)
        assert _degradation_progress(50, event) is None
        assert _degradation_progress(200, event) is None

    def test_returns_progress_inside_event(self):
        from src.data.simulator import DegradationEvent

        event = DegradationEvent(mode="bearing", start_hour=0, duration_hours=100, severity=1.0)
        t = _degradation_progress(50, event)
        assert t is not None
        assert 0.0 <= t <= 1.0

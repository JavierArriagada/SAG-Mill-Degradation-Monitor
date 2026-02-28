"""
src/data/store.py
─────────────────
SQLite data store abstraction.

Provides:
  - initialize_db()    : Create tables + seed with historical data on first run
  - insert_readings()  : Bulk insert SensorReading rows
  - get_readings()     : Fetch readings for an equipment over a time range
  - insert_alerts()    : Bulk insert Alert rows
  - get_alerts()       : Fetch recent alerts
  - get_latest()       : Fetch the most recent reading per equipment

Thread safety: uses check_same_thread=False + a module-level lock.
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime, timedelta

import pandas as pd

from config.settings import settings
from src.data.models import Alert, SensorReading

_lock = threading.RLock()
_DB: sqlite3.Connection | None = None


# ── Connection ────────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    global _DB
    if _DB is None:
        _DB = sqlite3.connect(settings.DATABASE_URL, check_same_thread=False)
        _DB.row_factory = sqlite3.Row
    return _DB


# ── Schema ────────────────────────────────────────────────────────────────────

_CREATE_READINGS = """
CREATE TABLE IF NOT EXISTS readings (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp             TEXT NOT NULL,
    equipment_id          TEXT NOT NULL,
    vibration_mms         REAL NOT NULL,
    bearing_temp_c        REAL NOT NULL,
    hydraulic_pressure_bar REAL NOT NULL,
    power_kw              REAL NOT NULL,
    load_pct              REAL NOT NULL,
    liner_wear_pct        REAL,
    seal_condition_pct    REAL,
    throughput_tph        REAL NOT NULL,
    degradation_mode      TEXT NOT NULL DEFAULT 'normal',
    health_index          REAL NOT NULL DEFAULT 100.0
);
"""

_CREATE_ALERTS = """
CREATE TABLE IF NOT EXISTS alerts (
    id             TEXT PRIMARY KEY,
    timestamp      TEXT NOT NULL,
    equipment_id   TEXT NOT NULL,
    severity       TEXT NOT NULL,
    category       TEXT NOT NULL,
    variable       TEXT NOT NULL,
    value          REAL NOT NULL,
    threshold      REAL NOT NULL,
    message        TEXT NOT NULL,
    acknowledged   INTEGER NOT NULL DEFAULT 0
);
"""

_CREATE_IDX = """
CREATE INDEX IF NOT EXISTS idx_readings_eq_ts ON readings (equipment_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_eq_ts   ON alerts   (equipment_id, timestamp);
"""


def _create_tables(conn: sqlite3.Connection) -> None:
    with conn:
        conn.executescript(_CREATE_READINGS + _CREATE_ALERTS + _CREATE_IDX)


# ── Public API ────────────────────────────────────────────────────────────────

def initialize_db(force_reseed: bool = False) -> None:
    """
    Create tables and populate with simulated history if the DB is empty.
    Safe to call multiple times (idempotent).
    """
    # Import here to avoid circular deps
    from src.analytics.health_index import compute_health_summary
    from src.data.simulator import derive_alerts, generate_history

    conn = _get_conn()
    _create_tables(conn)

    with _lock:
        count = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        if count > 0 and not force_reseed:
            return  # Already seeded

        conn.execute("DELETE FROM readings")
        conn.execute("DELETE FROM alerts")

        history = generate_history()
        for equipment_id, reading_list in history.items():
            # Compute health index for each reading
            for reading in reading_list:
                summary = compute_health_summary(reading)
                reading.health_index = summary.health_index

            insert_readings(reading_list)
            alerts = derive_alerts(reading_list, equipment_id)
            insert_alerts(alerts)


def insert_readings(readings: list[SensorReading]) -> None:
    if not readings:
        return
    rows = [
        (
            r.timestamp.isoformat(),
            r.equipment_id,
            r.vibration_mms,
            r.bearing_temp_c,
            r.hydraulic_pressure_bar,
            r.power_kw,
            r.load_pct,
            r.liner_wear_pct,
            r.seal_condition_pct,
            r.throughput_tph,
            r.degradation_mode.value,
            r.health_index,
        )
        for r in readings
    ]
    conn = _get_conn()
    with _lock, conn:
        conn.executemany(
            """INSERT INTO readings
               (timestamp, equipment_id, vibration_mms, bearing_temp_c,
                hydraulic_pressure_bar, power_kw, load_pct,
                liner_wear_pct, seal_condition_pct, throughput_tph,
                degradation_mode, health_index)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )


def insert_alerts(alerts: list[Alert]) -> None:
    if not alerts:
        return
    rows = [
        (
            a.id,
            a.timestamp.isoformat(),
            a.equipment_id,
            a.severity,
            a.category,
            a.variable,
            a.value,
            a.threshold,
            a.message,
            int(a.acknowledged),
        )
        for a in alerts
    ]
    conn = _get_conn()
    with _lock, conn:
        conn.executemany(
            """INSERT OR IGNORE INTO alerts
               (id, timestamp, equipment_id, severity, category,
                variable, value, threshold, message, acknowledged)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )


def get_readings(
    equipment_id: str,
    hours: int = 90 * 24,
    limit: int = 10_000,
) -> pd.DataFrame:
    """Fetch readings for an equipment over the last `hours` hours."""
    since = (datetime.now(tz=UTC) - timedelta(hours=hours)).isoformat()
    conn = _get_conn()
    with _lock:
        df = pd.read_sql_query(
            """SELECT * FROM readings
               WHERE equipment_id = ? AND timestamp >= ?
               ORDER BY timestamp ASC
               LIMIT ?""",
            conn,
            params=(equipment_id, since, limit),
        )
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def get_latest(equipment_id: str) -> dict | None:
    """Return the most recent row for an equipment as a dict."""
    conn = _get_conn()
    with _lock:
        row = conn.execute(
            "SELECT * FROM readings WHERE equipment_id = ? ORDER BY timestamp DESC LIMIT 1",
            (equipment_id,),
        ).fetchone()
    return dict(row) if row else None


def get_alerts(
    equipment_id: str | None = None,
    severity: str | None = None,
    days: int = 30,
    limit: int = 500,
) -> pd.DataFrame:
    """Fetch alerts with optional filters."""
    since = (datetime.now(tz=UTC) - timedelta(days=days)).isoformat()
    where = ["timestamp >= ?"]
    params: list = [since]

    if equipment_id:
        where.append("equipment_id = ?")
        params.append(equipment_id)
    if severity:
        where.append("severity = ?")
        params.append(severity)

    sql = f"""SELECT * FROM alerts WHERE {' AND '.join(where)}
              ORDER BY timestamp DESC LIMIT ?"""
    params.append(limit)

    conn = _get_conn()
    with _lock:
        df = pd.read_sql_query(sql, conn, params=params)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def acknowledge_alert(alert_id: str) -> None:
    conn = _get_conn()
    with _lock, conn:
        conn.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))


def get_active_alert_count(equipment_id: str | None = None) -> int:
    """Count unacknowledged alerts."""
    conn = _get_conn()
    where = "acknowledged = 0"
    params: list = []
    if equipment_id:
        where += " AND equipment_id = ?"
        params.append(equipment_id)
    with _lock:
        return conn.execute(f"SELECT COUNT(*) FROM alerts WHERE {where}", params).fetchone()[0]

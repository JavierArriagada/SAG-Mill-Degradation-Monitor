"""
config/alerts.py
────────────────
Alert severity levels, categories, and display configuration.
"""

from enum import Enum


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"


class AlertCategory(str, Enum):
    VIBRATION = "vibration"
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    POWER = "power"
    DEGRADATION = "degradation"
    HEALTH = "health"


SEVERITY_COLORS: dict[str, str] = {
    AlertSeverity.INFO: "#58a6ff",
    AlertSeverity.WARNING: "#e8a020",
    AlertSeverity.ALERT: "#f0883e",
    AlertSeverity.CRITICAL: "#da3633",
}

SEVERITY_BG: dict[str, str] = {
    AlertSeverity.INFO: "rgba(88,166,255,0.12)",
    AlertSeverity.WARNING: "rgba(232,160,32,0.12)",
    AlertSeverity.ALERT: "rgba(240,136,62,0.12)",
    AlertSeverity.CRITICAL: "rgba(218,54,51,0.12)",
}

SEVERITY_LABELS_ES: dict[str, str] = {
    AlertSeverity.INFO: "Info",
    AlertSeverity.WARNING: "Advertencia",
    AlertSeverity.ALERT: "Alerta",
    AlertSeverity.CRITICAL: "Crítico",
}

SEVERITY_LABELS_EN: dict[str, str] = {
    AlertSeverity.INFO: "Info",
    AlertSeverity.WARNING: "Warning",
    AlertSeverity.ALERT: "Alert",
    AlertSeverity.CRITICAL: "Critical",
}

# Severity ordering for sorting (higher = more severe)
SEVERITY_ORDER: dict[str, int] = {
    AlertSeverity.CRITICAL: 4,
    AlertSeverity.ALERT: 3,
    AlertSeverity.WARNING: 2,
    AlertSeverity.INFO: 1,
}

MAX_ALERTS_DISPLAY = 100

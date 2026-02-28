"""
config/settings.py
──────────────────
Application configuration loaded from environment variables.
"""
import os
from dataclasses import dataclass


@dataclass
class Settings:
    # Server
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    PORT: int = int(os.getenv("PORT", "8050"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # Database (SQLite path or PostgreSQL URL for prod)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sag_monitor.db")

    # Live update interval in milliseconds
    UPDATE_INTERVAL_MS: int = int(os.getenv("UPDATE_INTERVAL_MS", "30000"))

    # Simulation
    SIMULATION_SEED: int = int(os.getenv("SIMULATION_SEED", "42"))
    HISTORY_DAYS: int = int(os.getenv("HISTORY_DAYS", "90"))

    # i18n
    DEFAULT_LANG: str = os.getenv("DEFAULT_LANG", "es")

    # Alerts
    ALERT_RETENTION_DAYS: int = int(os.getenv("ALERT_RETENTION_DAYS", "30"))


settings = Settings()

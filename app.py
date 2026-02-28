"""
app.py
──────
SAG Mill Degradation Monitor — Application Entry Point.

Startup sequence:
  1. Initialize SQLite DB and seed with 90-day simulated history
  2. Create Dash app with DARKLY bootstrap theme
  3. Register all callbacks
  4. Run dev server (or expose `server` for gunicorn in production)
"""
import dash
import dash_bootstrap_components as dbc

from config.settings import settings
from src.data.store import initialize_db
from src.layout.main import create_layout

# ── 1. Seed database on startup ───────────────────────────────────────────────
print("Initializing database and seeding simulation data...")
initialize_db()
print("Database ready.")

# ── 2. Dash app ───────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    title="SAG Monitor",
)

server = app.server  # gunicorn / Render entry point
app.layout = create_layout()

# ── 3. Register callbacks ─────────────────────────────────────────────────────
from src.callbacks import alerts, equipment, navigation, trends

navigation.register(app)
equipment.register(app)
alerts.register(app)
trends.register(app)

# ── 4. Run ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(
        debug=settings.DEBUG,
        host=settings.HOST,
        port=settings.PORT,
    )

"""
src/layout/main.py
───────────────────
Main application layout composition.

Contains:
  - dcc.Location for routing
  - dcc.Store for shared client-side state
  - dcc.Interval for live updates
  - Navbar + page content container
"""
from dash import html, dcc
import dash_bootstrap_components as dbc

from src.layout.navbar import create_navbar


def create_layout() -> html.Div:
    """Assemble the root application layout."""
    return html.Div(
        [
            # ── Client-side state stores ──────────────────────────────────────
            dcc.Store(id="store-equipment", data="SAG-01"),
            dcc.Store(id="store-lang", data="es"),
            dcc.Store(id="store-ack-alerts", data=[]),  # list of acknowledged alert IDs

            # ── Routing ───────────────────────────────────────────────────────
            dcc.Location(id="url", refresh=False),

            # ── Live update interval ──────────────────────────────────────────
            dcc.Interval(
                id="interval-live",
                interval=30_000,   # 30 seconds
                n_intervals=0,
            ),

            # ── Navigation bar ────────────────────────────────────────────────
            create_navbar(),

            # ── Page content ──────────────────────────────────────────────────
            html.Div(
                id="page-content",
                style={"minHeight": "calc(100vh - 60px)"},
            ),

            # ── Footer ────────────────────────────────────────────────────────
            html.Footer(
                [
                    html.Span("SAG Mill Degradation Monitor"),
                    html.Span(" · "),
                    html.Span("ISO 10816 / ISO 13381"),
                    html.Span(" · "),
                    html.Span("Datos simulados · Portfolio"),
                ],
                style={
                    "textAlign": "center",
                    "padding": ".7rem",
                    "fontSize": ".72rem",
                    "color": "#8b949e",
                    "borderTop": "1px solid #30363d",
                    "marginTop": "2rem",
                },
            ),
        ],
        style={"backgroundColor": "#0d1117", "minHeight": "100vh", "color": "#c9d1d9"},
    )

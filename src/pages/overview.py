"""
src/pages/overview.py
──────────────────────
Executive overview page.

Static structure; dynamic KPI data injected via callbacks.
"""

import dash_bootstrap_components as dbc
from dash import html

CARD_BG = "#161b22"
BORDER = "#30363d"
MUTED = "#8b949e"


def layout() -> html.Div:
    return html.Div(
        [
            # ── Page header ───────────────────────────────────────────────────
            html.Div(
                [
                    html.H2("Resumen Ejecutivo", className="page-title"),
                    html.P(
                        "Estado de la flota de molienda en tiempo real · ISO 10816 / ISO 13381",
                        className="page-subtitle",
                    ),
                ],
                className="page-header",
            ),
            # ── Fleet KPI banner (dynamic) ────────────────────────────────────
            html.Div(id="overview-kpi-banner", className="mb-4"),
            # ── Health gauges row (dynamic) ───────────────────────────────────
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("Molino SAG", className="chart-title"),
                                html.Div(id="overview-gauge-sag"),
                            ],
                            className="chart-card",
                        ),
                        md=6,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("Molino de Bolas", className="chart-title"),
                                html.Div(id="overview-gauge-ball"),
                            ],
                            className="chart-card",
                        ),
                        md=6,
                    ),
                ],
                className="g-3 mb-3",
            ),
            # ── Equipment status cards row (dynamic) ──────────────────────────
            html.Div(id="overview-status-cards", className="mb-3"),
            # ── Recent alerts summary ─────────────────────────────────────────
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("Alertas Recientes", className="chart-title"),
                                html.Div(id="overview-alerts-table"),
                            ],
                            className="chart-card",
                        ),
                        md=12,
                    ),
                ],
                className="g-3",
            ),
        ],
        style={"padding": "1.5rem"},
    )

"""
src/pages/alerts.py
────────────────────
Alert management page with filters and acknowledgement.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html

CARD_BG = "#161b22"
BORDER = "#30363d"
MUTED = "#8b949e"

_SEVERITY_OPTIONS = [
    {"label": "Todos", "value": "all"},
    {"label": "Crítico", "value": "critical"},
    {"label": "Alerta", "value": "alert"},
    {"label": "Advertencia", "value": "warning"},
    {"label": "Info", "value": "info"},
]

_EQUIPMENT_OPTIONS = [
    {"label": "Todos", "value": "all"},
    {"label": "Molino SAG (SAG-01)", "value": "SAG-01"},
    {"label": "Molino de Bolas (BALL-01)", "value": "BALL-01"},
]


def layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.H2("Gestión de Alertas", className="page-title"),
                    html.P(
                        "Historial y estado de alertas del sistema de monitoreo",
                        className="page-subtitle",
                    ),
                ],
                className="page-header",
            ),
            # ── Summary badges ─────────────────────────────────────────────────
            html.Div(id="alerts-summary-badges", className="mb-3"),
            # ── Filter row ─────────────────────────────────────────────────────
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label(
                                "Severidad",
                                style={
                                    "fontSize": ".72rem",
                                    "color": MUTED,
                                    "textTransform": "uppercase",
                                },
                            ),
                            dcc.Dropdown(
                                id="alerts-filter-severity",
                                options=_SEVERITY_OPTIONS,
                                value="all",
                                clearable=False,
                                style={"fontSize": ".85rem"},
                                className="dark-dropdown",
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label(
                                "Equipo",
                                style={
                                    "fontSize": ".72rem",
                                    "color": MUTED,
                                    "textTransform": "uppercase",
                                },
                            ),
                            dcc.Dropdown(
                                id="alerts-filter-equipment",
                                options=_EQUIPMENT_OPTIONS,
                                value="all",
                                clearable=False,
                                style={"fontSize": ".85rem"},
                                className="dark-dropdown",
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label(
                                "Estado",
                                style={
                                    "fontSize": ".72rem",
                                    "color": MUTED,
                                    "textTransform": "uppercase",
                                },
                            ),
                            dcc.Dropdown(
                                id="alerts-filter-status",
                                options=[
                                    {"label": "Todos", "value": "all"},
                                    {"label": "Sin reconocer", "value": "unacked"},
                                    {"label": "Reconocidas", "value": "acked"},
                                ],
                                value="all",
                                clearable=False,
                                style={"fontSize": ".85rem"},
                                className="dark-dropdown",
                            ),
                        ],
                        md=3,
                    ),
                ],
                className="g-3 mb-3",
            ),
            # ── Alert table ────────────────────────────────────────────────────
            html.Div(
                html.Div(id="alerts-table"),
                className="chart-card",
            ),
        ],
        style={"padding": "1.5rem"},
    )

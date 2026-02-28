"""
src/pages/trends.py
────────────────────
Historical trend analysis page with anomaly detection overlay.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc

CARD_BG = "#161b22"
BORDER = "#30363d"
MUTED = "#8b949e"

_VARIABLE_OPTIONS = [
    {"label": "Vibración (mm/s)", "value": "vibration_mms"},
    {"label": "Temperatura Cojinete (°C)", "value": "bearing_temp_c"},
    {"label": "Presión Hidráulica (bar)", "value": "hydraulic_pressure_bar"},
    {"label": "Potencia (kW)", "value": "power_kw"},
    {"label": "Carga (%)", "value": "load_pct"},
    {"label": "Índice de Salud (%)", "value": "health_index"},
    {"label": "Throughput (t/h)", "value": "throughput_tph"},
]

_WINDOW_OPTIONS = [
    {"label": "7 días", "value": 7 * 24},
    {"label": "30 días", "value": 30 * 24},
    {"label": "60 días", "value": 60 * 24},
    {"label": "90 días", "value": 90 * 24},
]


def layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.H2("Tendencias Históricas", className="page-title"),
                    html.P("Análisis de patrones de degradación · Últimos 90 días", className="page-subtitle"),
                ],
                className="page-header",
            ),

            # ── Controls ───────────────────────────────────────────────────────
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Equipo", style={"fontSize": ".72rem", "color": MUTED, "textTransform": "uppercase"}),
                            dcc.Dropdown(
                                id="trends-equipment",
                                options=[
                                    {"label": "Molino SAG (SAG-01)", "value": "SAG-01"},
                                    {"label": "Molino de Bolas (BALL-01)", "value": "BALL-01"},
                                ],
                                value="SAG-01",
                                clearable=False,
                                className="dark-dropdown",
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Variable", style={"fontSize": ".72rem", "color": MUTED, "textTransform": "uppercase"}),
                            dcc.Dropdown(
                                id="trends-variable",
                                options=_VARIABLE_OPTIONS,
                                value="vibration_mms",
                                clearable=False,
                                className="dark-dropdown",
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Ventana", style={"fontSize": ".72rem", "color": MUTED, "textTransform": "uppercase"}),
                            dcc.Dropdown(
                                id="trends-window",
                                options=_WINDOW_OPTIONS,
                                value=30 * 24,
                                clearable=False,
                                className="dark-dropdown",
                            ),
                        ],
                        md=2,
                    ),
                    dbc.Col(
                        [
                            html.Label("Opciones", style={"fontSize": ".72rem", "color": MUTED, "textTransform": "uppercase"}),
                            dbc.Checklist(
                                id="trends-options",
                                options=[
                                    {"label": " Anomalías", "value": "anomalies"},
                                    {"label": " Umbrales", "value": "thresholds"},
                                    {"label": " Media móvil", "value": "rolling"},
                                ],
                                value=["thresholds"],
                                inline=True,
                                style={"fontSize": ".82rem", "color": "#c9d1d9", "paddingTop": "8px"},
                                inputStyle={"marginRight": "4px"},
                            ),
                        ],
                        md=4,
                    ),
                ],
                className="g-3 mb-3",
            ),

            # ── Main trend chart ───────────────────────────────────────────────
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(id="trends-chart-title", className="chart-title"),
                                dcc.Graph(id="trends-main-chart", config={"displayModeBar": True}),
                            ],
                            className="chart-card",
                        ),
                        md=12,
                    ),
                ],
                className="g-3 mb-3",
            ),

            # ── Anomaly summary + Z-score chart ────────────────────────────────
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("Z-Score (detección de anomalías)", className="chart-title"),
                                dcc.Graph(id="trends-zscore-chart", config={"displayModeBar": False}),
                            ],
                            className="chart-card",
                        ),
                        md=8,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("Resumen de Anomalías", className="chart-title"),
                                html.Div(id="trends-anomaly-summary"),
                            ],
                            className="chart-card",
                        ),
                        md=4,
                    ),
                ],
                className="g-3",
            ),
        ],
        style={"padding": "1.5rem"},
    )

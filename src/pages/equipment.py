"""
src/pages/equipment.py
───────────────────────
Equipment detail page.

Layout: sidebar selector + detail panel with dynamic charts.
"""
import dash_bootstrap_components as dbc
from dash import dcc, html

from src.layout.sidebar import create_sidebar

CARD_BG = "#161b22"
BORDER = "#30363d"
MUTED = "#8b949e"


def layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.H2("Detalle de Equipo", className="page-title"),
                    html.P("Monitoreo en tiempo real de variables de proceso y condición", className="page-subtitle"),
                ],
                className="page-header",
            ),

            dbc.Row(
                [
                    # ── Sidebar ───────────────────────────────────────────────
                    dbc.Col(
                        html.Div(
                            [
                                create_sidebar(),
                                # Degradation mode indicator
                                html.Div(
                                    [
                                        html.Div("Modo de Degradación", style={"fontSize": ".68rem", "color": MUTED, "textTransform": "uppercase", "marginBottom": "6px", "marginTop": "16px"}),
                                        html.Div(id="eq-degradation-badge"),
                                    ]
                                ),
                                # RUL display
                                html.Div(
                                    [
                                        html.Div("Vida Útil Restante", style={"fontSize": ".68rem", "color": MUTED, "textTransform": "uppercase", "marginBottom": "6px", "marginTop": "16px"}),
                                        html.Div(id="eq-rul-display"),
                                    ]
                                ),
                            ]
                        ),
                        md=2,
                    ),

                    # ── Main detail panel ─────────────────────────────────────
                    dbc.Col(
                        [
                            # Health gauge + KPI strip
                            dbc.Row(
                                [
                                    dbc.Col(html.Div([html.Div(id="eq-health-gauge")], className="chart-card"), md=3),
                                    dbc.Col(html.Div([html.Div(id="eq-kpi-strip")], className="chart-card"), md=9),
                                ],
                                className="g-3 mb-3",
                            ),

                            # Vibration + Temperature charts
                            dbc.Row(
                                [
                                    dbc.Col(html.Div([html.Div("Vibración (mm/s)", className="chart-title"), dcc.Graph(id="eq-chart-vibration", config={"displayModeBar": False})], className="chart-card"), md=6),
                                    dbc.Col(html.Div([html.Div("Temperatura Cojinete (°C)", className="chart-title"), dcc.Graph(id="eq-chart-temperature", config={"displayModeBar": False})], className="chart-card"), md=6),
                                ],
                                className="g-3 mb-3",
                            ),

                            # Pressure + Power charts
                            dbc.Row(
                                [
                                    dbc.Col(html.Div([html.Div("Presión Hidráulica (bar)", className="chart-title"), dcc.Graph(id="eq-chart-pressure", config={"displayModeBar": False})], className="chart-card"), md=6),
                                    dbc.Col(html.Div([html.Div("Potencia (kW)", className="chart-title"), dcc.Graph(id="eq-chart-power", config={"displayModeBar": False})], className="chart-card"), md=6),
                                ],
                                className="g-3 mb-3",
                            ),

                            # Health index trend
                            dbc.Row(
                                [
                                    dbc.Col(html.Div([html.Div("Índice de Salud — Últimas 72h", className="chart-title"), dcc.Graph(id="eq-chart-health", config={"displayModeBar": False})], className="chart-card"), md=12),
                                ],
                                className="g-3",
                            ),
                        ],
                        md=10,
                    ),
                ],
                className="g-3",
            ),
        ],
        style={"padding": "1.5rem"},
    )

"""
src/callbacks/navigation.py — Overview page dynamic content callback.
"""
from __future__ import annotations

from datetime import UTC, datetime

import dash_bootstrap_components as dbc
from dash import Input, Output, html

from config.alerts import SEVERITY_COLORS, SEVERITY_LABELS_ES
from config.equipment import EQUIPMENT_CONFIG
from src.analytics.health_index import compute_health_summary
from src.data import store
from src.data.models import DegradationMode, SensorReading
from src.layout.components.health_gauge import health_gauge
from src.layout.components.kpi_card import kpi_card

CARD_BG = "#161b22"
BORDER = "#30363d"
MUTED = "#8b949e"


def _latest_to_reading(latest: dict, equipment_id: str) -> SensorReading:
    return SensorReading(
        timestamp=datetime.now(tz=UTC),
        equipment_id=equipment_id,
        vibration_mms=float(latest["vibration_mms"]),
        bearing_temp_c=float(latest["bearing_temp_c"]),
        hydraulic_pressure_bar=float(latest["hydraulic_pressure_bar"]),
        power_kw=float(latest["power_kw"]),
        load_pct=float(latest["load_pct"]),
        liner_wear_pct=float(latest["liner_wear_pct"]) if latest.get("liner_wear_pct") else None,
        seal_condition_pct=float(latest["seal_condition_pct"]) if latest.get("seal_condition_pct") else None,
        throughput_tph=float(latest["throughput_tph"]),
        degradation_mode=DegradationMode(latest.get("degradation_mode", "normal")),
        health_index=float(latest.get("health_index", 100.0)),
    )


def register(app) -> None:
    """Register navigation + overview page callbacks."""

    # ── Page routing ──────────────────────────────────────────────────────────
    from src.pages import alerts, equipment, overview, trends

    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname"),
    )
    def display_page(pathname: str):
        routes = {
            "/": overview.layout,
            "/equipment": equipment.layout,
            "/alerts": alerts.layout,
            "/trends": trends.layout,
        }
        return routes.get(pathname, overview.layout)()

    # ── Navbar collapse ───────────────────────────────────────────────────────
    from dash import State

    @app.callback(
        Output("navbar-collapse", "is_open"),
        Input("navbar-toggler", "n_clicks"),
        State("navbar-collapse", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_navbar(n_clicks: int, is_open: bool) -> bool:
        return not is_open

    # ── Language toggle ───────────────────────────────────────────────────────
    @app.callback(
        Output("store-lang", "data"),
        Input("lang-es-btn", "n_clicks"),
        Input("lang-en-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def update_lang(n_es: int, n_en: int) -> str:
        from dash import ctx
        return "en" if ctx.triggered_id == "lang-en-btn" else "es"

    # ── Overview: KPI banner ──────────────────────────────────────────────────
    @app.callback(
        [
            Output("overview-kpi-banner", "children"),
            Output("overview-gauge-sag", "children"),
            Output("overview-gauge-ball", "children"),
            Output("overview-status-cards", "children"),
            Output("overview-alerts-table", "children"),
        ],
        Input("interval-live", "n_intervals"),
    )
    def update_overview(n_intervals: int):
        summaries = []
        status_cards = []

        for eq_id, eq in EQUIPMENT_CONFIG.items():
            latest = store.get_latest(eq_id)
            if latest is None:
                continue
            reading = _latest_to_reading(latest, eq_id)
            summary = compute_health_summary(reading)
            summaries.append(summary)

            hi = summary.health_index
            hi_color = "#2ea44f" if hi >= 80 else "#58a6ff" if hi >= 60 else "#e8a020" if hi >= 40 else "#da3633"
            mode = latest.get("degradation_mode", "normal")
            mode_labels = {"normal": "Normal", "bearing": "Rodamiento", "liner": "Revestimiento",
                           "hydraulic": "Hidráulico", "misalignment": "Desalineamiento"}
            active_count = store.get_active_alert_count(eq_id)
            alert_color = "#da3633" if active_count > 5 else "#e8a020" if active_count > 0 else "#2ea44f"

            status_cards.append(
                dbc.Col(
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(eq["name"], style={"fontWeight": "700", "color": eq["color"], "fontSize": ".95rem"}),
                                    html.Span(eq_id, style={"fontSize": ".68rem", "color": MUTED, "marginLeft": "8px"}),
                                ],
                                style={"marginBottom": "10px"},
                            ),
                            html.Div(
                                [
                                    html.Div([html.Div("Health Index", style={"fontSize": ".65rem", "color": MUTED}),
                                              html.Div(f"{hi:.1f}%", style={"fontSize": "1.2rem", "fontWeight": "700", "color": hi_color})]),
                                    html.Div([html.Div("Alertas Activas", style={"fontSize": ".65rem", "color": MUTED}),
                                              html.Div(str(active_count), style={"fontSize": "1.2rem", "fontWeight": "700", "color": alert_color})]),
                                    html.Div([html.Div("Modo", style={"fontSize": ".65rem", "color": MUTED}),
                                              html.Div(mode_labels.get(mode, mode), style={"fontSize": ".82rem", "fontWeight": "600", "color": "#c9d1d9"})]),
                                    html.Div([html.Div("Throughput", style={"fontSize": ".65rem", "color": MUTED}),
                                              html.Div(f"{latest['throughput_tph']:.0f} t/h", style={"fontSize": ".82rem", "fontWeight": "600", "color": "#c9d1d9"})]),
                                ],
                                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "8px"},
                            ),
                        ],
                        style={
                            "backgroundColor": CARD_BG,
                            "border": f"1px solid {eq['color'] if active_count > 0 else BORDER}",
                            "borderRadius": "8px",
                            "padding": "14px",
                        },
                    ),
                    md=6,
                )
            )

        # Fleet metrics
        if summaries:
            fleet_hi = min(s.health_index for s in summaries)
            fleet_color = "#2ea44f" if fleet_hi >= 80 else "#58a6ff" if fleet_hi >= 60 else "#e8a020" if fleet_hi >= 40 else "#da3633"
        else:
            fleet_hi = 0.0
            fleet_color = MUTED

        total_alerts = store.get_active_alert_count()
        total_critical = len(store.get_alerts(days=1).query("severity == 'critical'")) if not store.get_alerts(days=1).empty else 0

        kpi_banner = dbc.Row(
            [
                dbc.Col(kpi_card("Salud de Flota", f"{fleet_hi:.1f}%", fleet_color, border_color=fleet_color), xs=6, md=3),
                dbc.Col(kpi_card("Equipos Monitoreados", str(len(EQUIPMENT_CONFIG)), "#58a6ff"), xs=6, md=3),
                dbc.Col(kpi_card("Alertas Activas", str(total_alerts), "#e8a020" if total_alerts > 0 else "#2ea44f"), xs=6, md=3),
                dbc.Col(kpi_card("Alertas Críticas (24h)", str(total_critical), "#da3633" if total_critical > 0 else "#2ea44f"), xs=6, md=3),
            ],
            className="g-3",
        )

        # Health gauges
        sag_latest = store.get_latest("SAG-01")
        ball_latest = store.get_latest("BALL-01")

        sag_hi = float(sag_latest.get("health_index", 0)) if sag_latest else 0.0
        ball_hi = float(ball_latest.get("health_index", 0)) if ball_latest else 0.0

        sag_gauge = health_gauge(sag_hi, "SAG-01", height=180)
        ball_gauge = health_gauge(ball_hi, "BALL-01", height=180)

        # Recent alerts mini table
        alerts_df = store.get_alerts(days=7, limit=10)
        if alerts_df.empty:
            alerts_table = html.Div("Sin alertas recientes.", style={"color": MUTED, "padding": "12px"})
        else:
            rows = []
            for _, row in alerts_df.head(8).iterrows():
                sev_color = SEVERITY_COLORS.get(row["severity"], MUTED)
                rows.append(html.Tr([
                    html.Td(str(row["timestamp"])[:16], style={"fontSize": ".72rem", "color": MUTED}),
                    html.Td(html.Span(row["equipment_id"], style={"color": "#58a6ff", "fontSize": ".78rem"})),
                    html.Td(html.Span(SEVERITY_LABELS_ES.get(row["severity"], row["severity"]),
                                       style={"color": sev_color, "fontSize": ".72rem", "fontWeight": "700"})),
                    html.Td(row["variable"], style={"fontSize": ".72rem"}),
                    html.Td(row["message"][:60] + "…" if len(row["message"]) > 60 else row["message"],
                             style={"fontSize": ".70rem", "color": MUTED}),
                ]))
            alerts_table = html.Table(
                [html.Thead(html.Tr([html.Th(h) for h in ["Hora", "Equipo", "Severidad", "Variable", "Mensaje"]],
                                     style={"color": MUTED, "fontSize": ".65rem", "textTransform": "uppercase"})),
                 html.Tbody(rows)],
                style={"width": "100%", "borderCollapse": "collapse", "fontSize": ".8rem"},
            )

        return (
            kpi_banner,
            sag_gauge,
            ball_gauge,
            dbc.Row(status_cards, className="g-3"),
            alerts_table,
        )

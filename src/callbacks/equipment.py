"""
src/callbacks/equipment.py
───────────────────────────
Equipment detail page callbacks.
Updates charts and KPIs based on selected equipment and live interval.
"""
from __future__ import annotations

from datetime import UTC

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, html

from config.equipment import EQUIPMENT_CONFIG
from src.analytics.health_index import compute_health_summary, compute_rul
from src.analytics.thresholds import get_static_thresholds, get_value_color
from src.data import store
from src.layout.components.health_gauge import health_gauge
from src.layout.components.kpi_card import mini_kpi

CARD_BG = "#161b22"
GRID_CLR = "#30363d"
MUTED = "#8b949e"
PLOTLY_TMPL = "plotly_dark"

_DEGRAD_COLORS = {
    "normal": "#2ea44f",
    "bearing": "#e8a020",
    "liner": "#f0883e",
    "hydraulic": "#58a6ff",
    "misalignment": "#da3633",
}
_DEGRAD_LABELS = {
    "normal": "Normal",
    "bearing": "Rodamiento",
    "liner": "Revestimiento",
    "hydraulic": "Hidráulico",
    "misalignment": "Desalineamiento",
}


def _base_layout(title: str = "") -> dict:
    return {
        "template": PLOTLY_TMPL,
        "paper_bgcolor": CARD_BG,
        "plot_bgcolor": CARD_BG,
        "margin": {"l": 10, "r": 10, "t": 30, "b": 10},
        "font": {"color": "#c9d1d9", "size": 11},
        "title": {"text": title, "font": {"size": 12, "color": MUTED}},
        "xaxis": {"gridcolor": GRID_CLR, "showgrid": True},
        "yaxis": {"gridcolor": GRID_CLR, "showgrid": True},
        "legend": {"bgcolor": "rgba(0,0,0,0)", "font": {"size": 10}},
        "height": 220,
    }


def _trend_fig(df, col: str, equipment_id: str, last_hours: int = 72) -> go.Figure:
    """Build a single-variable trend chart with threshold lines."""
    eq = EQUIPMENT_CONFIG[equipment_id]
    color = eq["color"]
    df_recent = df.tail(last_hours)

    fig = go.Figure()
    fig.add_scatter(
        x=df_recent["timestamp"], y=df_recent[col],
        line={"color": color, "width": 1.5},
        name=col,
        mode="lines",
        hovertemplate="%{x|%d/%m %H:%M}<br>%{y:.2f}<extra></extra>",
    )

    band = get_static_thresholds(equipment_id, col)
    if band.warning:
        fig.add_hline(y=band.warning, line_dash="dot", line_color="#e8a020", line_width=1,
                      annotation_text="Warn", annotation_font_color="#e8a020", annotation_font_size=9)
    if band.alert:
        fig.add_hline(y=band.alert, line_dash="dash", line_color="#f0883e", line_width=1,
                      annotation_text="Alert", annotation_font_color="#f0883e", annotation_font_size=9)
    if band.critical:
        fig.add_hline(y=band.critical, line_dash="solid", line_color="#da3633", line_width=1,
                      annotation_text="Crit", annotation_font_color="#da3633", annotation_font_size=9)

    fig.update_layout(**_base_layout())
    return fig


def register(app) -> None:

    @app.callback(
        Output("store-equipment", "data"),
        Input("equipment-selector", "value"),
        prevent_initial_call=True,
    )
    def update_selected_equipment(value: str) -> str:
        return value or "SAG-01"

    @app.callback(
        [
            Output("eq-health-gauge", "children"),
            Output("eq-kpi-strip", "children"),
            Output("eq-degradation-badge", "children"),
            Output("eq-rul-display", "children"),
            Output("eq-chart-vibration", "figure"),
            Output("eq-chart-temperature", "figure"),
            Output("eq-chart-pressure", "figure"),
            Output("eq-chart-power", "figure"),
            Output("eq-chart-health", "figure"),
        ],
        [
            Input("interval-live", "n_intervals"),
            Input("store-equipment", "data"),
        ],
    )
    def update_equipment_panel(n_intervals: int, equipment_id: str):
        if not equipment_id:
            equipment_id = "SAG-01"

        df = store.get_readings(equipment_id, hours=72)
        if df.empty:
            empty_fig = go.Figure()
            empty_fig.update_layout(**_base_layout("Sin datos"))
            no_data = html.Div("Sin datos", style={"color": MUTED, "padding": "20px"})
            return no_data, no_data, no_data, no_data, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig

        latest = df.iloc[-1]
        eq = EQUIPMENT_CONFIG[equipment_id]

        # Build a SensorReading from the latest row for health computation
        from datetime import datetime

        from src.data.models import DegradationMode, SensorReading

        reading = SensorReading(
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

        summary = compute_health_summary(reading)
        hi = summary.health_index

        # RUL
        rul = compute_rul(df["health_index"])

        # ── Health gauge ──────────────────────────────────────────────────────
        gauge = health_gauge(hi, eq["name"], height=180)

        # ── KPI strip ─────────────────────────────────────────────────────────
        def _color(val, col_name):
            band = get_static_thresholds(equipment_id, col_name)
            return get_value_color(val, band)

        kpi_strip = dbc.Row(
            [
                dbc.Col(mini_kpi("Vibración", f"{latest['vibration_mms']:.2f} mm/s",
                                  _color(latest['vibration_mms'], 'vibration_mms')), xs=6, md=2),
                dbc.Col(mini_kpi("Temperatura", f"{latest['bearing_temp_c']:.1f} °C",
                                  _color(latest['bearing_temp_c'], 'bearing_temp_c')), xs=6, md=2),
                dbc.Col(mini_kpi("Presión", f"{latest['hydraulic_pressure_bar']:.1f} bar",
                                  _color(latest['hydraulic_pressure_bar'], 'hydraulic_pressure_bar')), xs=6, md=2),
                dbc.Col(mini_kpi("Potencia", f"{latest['power_kw']:,.0f} kW",
                                  _color(latest['power_kw'], 'power_kw')), xs=6, md=2),
                dbc.Col(mini_kpi("Carga", f"{latest['load_pct']:.1f}%",
                                  _color(latest['load_pct'], 'load_pct')), xs=6, md=2),
                dbc.Col(mini_kpi("Throughput", f"{latest['throughput_tph']:.0f} t/h", "#58a6ff"), xs=6, md=2),
            ],
            className="g-2",
            style={"padding": "8px 0"},
        )

        # ── Degradation badge ─────────────────────────────────────────────────
        mode = latest.get("degradation_mode", "normal")
        mode_color = _DEGRAD_COLORS.get(mode, "#8b949e")
        mode_label = _DEGRAD_LABELS.get(mode, mode.capitalize())
        degrad_badge = html.Span(
            mode_label,
            style={
                "fontSize": ".72rem", "fontWeight": "700",
                "color": mode_color,
                "border": f"1px solid {mode_color}",
                "borderRadius": "4px",
                "padding": "2px 8px",
            },
        )

        # ── RUL ───────────────────────────────────────────────────────────────
        if rul is not None:
            rul_color = "#da3633" if rul < 7 else "#e8a020" if rul < 30 else "#2ea44f"
            rul_display = html.Div([
                html.Span(f"{rul:.1f}", style={"fontSize": "1.4rem", "fontWeight": "700", "color": rul_color}),
                html.Span(" días", style={"fontSize": ".8rem", "color": MUTED}),
            ])
        else:
            rul_display = html.Span("Estable", style={"color": "#2ea44f", "fontSize": ".85rem"})

        # ── Trend charts ──────────────────────────────────────────────────────
        fig_vib = _trend_fig(df, "vibration_mms", equipment_id)
        fig_temp = _trend_fig(df, "bearing_temp_c", equipment_id)
        fig_pres = _trend_fig(df, "hydraulic_pressure_bar", equipment_id)
        fig_pwr = _trend_fig(df, "power_kw", equipment_id)

        # Health index chart (longer window)
        df_full = store.get_readings(equipment_id, hours=72)
        fig_health = go.Figure()
        fig_health.add_scatter(
            x=df_full["timestamp"], y=df_full["health_index"],
            line={"color": eq["color"], "width": 1.8},
            fill="tozeroy",
            fillcolor=eq["color_rgba"],
            name="Health Index",
            hovertemplate="%{x|%d/%m %H:%M}<br>HI: %{y:.1f}%<extra></extra>",
        )
        fig_health.add_hline(y=20, line_dash="solid", line_color="#da3633", line_width=1,
                              annotation_text="Crítico (20%)", annotation_font_color="#da3633", annotation_font_size=9)
        fig_health.add_hline(y=60, line_dash="dot", line_color="#e8a020", line_width=1,
                              annotation_text="Alerta (60%)", annotation_font_color="#e8a020", annotation_font_size=9)
        fig_health.update_layout(**{**_base_layout(), "height": 180, "yaxis": {"range": [0, 105], "gridcolor": GRID_CLR}})

        return gauge, kpi_strip, degrad_badge, rul_display, fig_vib, fig_temp, fig_pres, fig_pwr, fig_health

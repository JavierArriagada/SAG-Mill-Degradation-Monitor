"""
src/callbacks/trends.py
────────────────────────
Historical trends page callbacks.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, html

from config.equipment import EQUIPMENT_CONFIG
from src.analytics.anomaly import detect_anomalies, get_anomaly_periods
from src.analytics.thresholds import get_static_thresholds
from src.data import store

CARD_BG = "#161b22"
GRID_CLR = "#30363d"
MUTED = "#8b949e"
PLOTLY_TMPL = "plotly_dark"

_VARIABLE_LABELS = {
    "vibration_mms": "Vibración (mm/s)",
    "bearing_temp_c": "Temperatura Cojinete (°C)",
    "hydraulic_pressure_bar": "Presión Hidráulica (bar)",
    "power_kw": "Potencia (kW)",
    "load_pct": "Carga (%)",
    "health_index": "Índice de Salud (%)",
    "throughput_tph": "Throughput (t/h)",
}


def _layout(height: int = 300) -> dict:
    return {
        "template": PLOTLY_TMPL,
        "paper_bgcolor": CARD_BG,
        "plot_bgcolor": CARD_BG,
        "margin": {"l": 10, "r": 10, "t": 10, "b": 10},
        "font": {"color": "#c9d1d9", "size": 11},
        "xaxis": {"gridcolor": GRID_CLR},
        "yaxis": {"gridcolor": GRID_CLR},
        "legend": {"bgcolor": "rgba(0,0,0,0)", "font": {"size": 10}},
        "height": height,
        "showlegend": True,
    }


def register(app) -> None:

    @app.callback(
        [
            Output("trends-main-chart", "figure"),
            Output("trends-zscore-chart", "figure"),
            Output("trends-anomaly-summary", "children"),
            Output("trends-chart-title", "children"),
        ],
        [
            Input("trends-equipment", "value"),
            Input("trends-variable", "value"),
            Input("trends-window", "value"),
            Input("trends-options", "value"),
            Input("interval-live", "n_intervals"),
        ],
    )
    def update_trends(equipment_id: str, variable: str, window_hours: int, options: list, n_intervals: int):
        options = options or []
        df = store.get_readings(equipment_id, hours=int(window_hours))

        eq = EQUIPMENT_CONFIG.get(equipment_id, EQUIPMENT_CONFIG["SAG-01"])
        color = eq["color"]
        eq["color_rgba"]
        var_label = _VARIABLE_LABELS.get(variable, variable)
        chart_title = f"{eq['name']} — {var_label}"

        if df.empty or variable not in df.columns:
            empty = go.Figure()
            empty.update_layout(**_layout())
            return empty, empty, html.Div("Sin datos", style={"color": MUTED}), chart_title

        # ── Main trend chart ──────────────────────────────────────────────────
        fig = go.Figure()

        # Raw data trace
        fig.add_scatter(
            x=df["timestamp"],
            y=df[variable],
            mode="lines",
            line={"color": color, "width": 1.3},
            name=var_label,
            hovertemplate="%{x|%d/%m %H:%M}<br>%{y:.3f}<extra></extra>",
        )

        # Rolling mean (24h)
        if "rolling" in options:
            roll_mean = df[variable].rolling(24, min_periods=2).mean()
            fig.add_scatter(
                x=df["timestamp"],
                y=roll_mean,
                mode="lines",
                line={"color": "#c9d1d9", "width": 1, "dash": "dash"},
                name="Media 24h",
                opacity=0.7,
            )

        # Threshold bands
        if "thresholds" in options:
            band = get_static_thresholds(equipment_id, variable)
            if band.warning:
                fig.add_hline(y=band.warning, line_dash="dot", line_color="#e8a020", line_width=1,
                              annotation_text="Warn", annotation_font_color="#e8a020", annotation_font_size=9)
            if band.alert:
                fig.add_hline(y=band.alert, line_dash="dash", line_color="#f0883e", line_width=1,
                              annotation_text="Alert", annotation_font_color="#f0883e", annotation_font_size=9)
            if band.critical:
                fig.add_hline(y=band.critical, line_dash="solid", line_color="#da3633", line_width=1,
                              annotation_text="Crit", annotation_font_color="#da3633", annotation_font_size=9)
            if band.lower_bound:
                fig.add_hline(y=band.lower_bound, line_dash="dot", line_color="#e8a020", line_width=1,
                              annotation_text="Min", annotation_font_color="#e8a020", annotation_font_size=9)

        # Anomaly markers
        anomaly_periods = []
        if "anomalies" in options:
            zscores, mask = detect_anomalies(df[variable])
            anomaly_df = df[mask]
            if not anomaly_df.empty:
                fig.add_scatter(
                    x=anomaly_df["timestamp"],
                    y=anomaly_df[variable],
                    mode="markers",
                    marker={"color": "#da3633", "size": 6, "symbol": "x"},
                    name="Anomalía",
                )
            anomaly_periods = get_anomaly_periods(df, variable)

        fig.update_layout(**_layout(300))

        # ── Z-score chart ─────────────────────────────────────────────────────
        zscores, mask = detect_anomalies(df[variable])
        z_df = pd.DataFrame({"timestamp": df["timestamp"], "zscore": zscores, "anomaly": mask})

        z_fig = go.Figure()
        z_fig.add_scatter(
            x=z_df["timestamp"],
            y=z_df["zscore"],
            mode="lines",
            line={"color": "#58a6ff", "width": 1.2},
            name="Z-score",
            hovertemplate="%{x|%d/%m %H:%M}<br>z=%{y:.2f}<extra></extra>",
        )

        # Threshold lines at ±2.5
        z_fig.add_hline(y=2.5, line_dash="dash", line_color="#da3633", line_width=1,
                         annotation_text="+2.5σ", annotation_font_color="#da3633", annotation_font_size=9)
        z_fig.add_hline(y=-2.5, line_dash="dash", line_color="#da3633", line_width=1,
                         annotation_text="-2.5σ", annotation_font_color="#da3633", annotation_font_size=9)
        z_fig.add_hline(y=0, line_dash="dot", line_color="#8b949e", line_width=0.8)

        # Shade anomaly regions
        anomaly_scatter_x = z_df.loc[z_df["anomaly"], "timestamp"]
        anomaly_scatter_y = z_df.loc[z_df["anomaly"], "zscore"]
        if not anomaly_scatter_x.empty:
            z_fig.add_scatter(
                x=anomaly_scatter_x,
                y=anomaly_scatter_y,
                mode="markers",
                marker={"color": "#da3633", "size": 5, "symbol": "circle"},
                name="Anomalía",
            )

        z_fig.update_layout(**_layout(200))

        # ── Anomaly summary ───────────────────────────────────────────────────
        n_anomaly_pts = int(mask.sum())
        total_pts = len(df)
        anomaly_pct = 100.0 * n_anomaly_pts / total_pts if total_pts > 0 else 0.0

        summary_items = [
            html.Div([
                html.Div(f"{n_anomaly_pts}", style={"fontSize": "1.8rem", "fontWeight": "700", "color": "#da3633" if n_anomaly_pts > 0 else "#2ea44f"}),
                html.Div("Puntos anómalos", style={"fontSize": ".7rem", "color": MUTED}),
            ], style={"marginBottom": "10px"}),
            html.Div([
                html.Div(f"{anomaly_pct:.1f}%", style={"fontSize": "1.2rem", "fontWeight": "700", "color": MUTED}),
                html.Div("del período", style={"fontSize": ".7rem", "color": MUTED}),
            ], style={"marginBottom": "10px"}),
            html.Div([
                html.Div(f"{len(anomaly_periods)}", style={"fontSize": "1.2rem", "fontWeight": "700", "color": "#e8a020"}),
                html.Div("Eventos anómalos", style={"fontSize": ".7rem", "color": MUTED}),
            ], style={"marginBottom": "14px"}),
        ]

        if anomaly_periods:
            summary_items.append(html.Div("Eventos detectados:", style={"fontSize": ".7rem", "color": MUTED, "textTransform": "uppercase", "marginBottom": "6px"}))
            for p in anomaly_periods[:5]:
                start = pd.to_datetime(p["start"]).strftime("%d/%m %H:%M")
                summary_items.append(
                    html.Div(
                        f"• {start} (z={p['peak_zscore']:.1f})",
                        style={"fontSize": ".72rem", "color": "#f0883e", "marginBottom": "3px"},
                    )
                )

        return fig, z_fig, html.Div(summary_items), chart_title

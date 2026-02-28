"""
src/layout/components/health_gauge.py
──────────────────────────────────────
Health Index gauge using Plotly indicator chart.
"""
from __future__ import annotations

import plotly.graph_objects as go
from dash import dcc

CARD_BG = "#161b22"


def _gauge_color(hi: float) -> str:
    if hi >= 80:
        return "#2ea44f"
    if hi >= 60:
        return "#58a6ff"
    if hi >= 40:
        return "#e8a020"
    if hi >= 20:
        return "#f0883e"
    return "#da3633"


def health_gauge(
    health_index: float,
    equipment_name: str,
    height: int = 200,
) -> dcc.Graph:
    """
    Plotly gauge indicator for health index.

    Args:
        health_index: 0–100 value
        equipment_name: Label shown below gauge
        height: Figure height in px
    """
    color = _gauge_color(health_index)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=health_index,
        number={"suffix": "%", "font": {"color": color, "size": 28}},
        title={"text": equipment_name, "font": {"color": "#8b949e", "size": 12}},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickwidth": 1,
                "tickcolor": "#30363d",
                "tickfont": {"color": "#8b949e", "size": 9},
            },
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 20],  "color": "rgba(218,54,51,0.15)"},
                {"range": [20, 40], "color": "rgba(240,136,62,0.12)"},
                {"range": [40, 60], "color": "rgba(232,160,32,0.10)"},
                {"range": [60, 80], "color": "rgba(88,166,255,0.10)"},
                {"range": [80, 100],"color": "rgba(46,164,79,0.10)"},
            ],
            "threshold": {
                "line": {"color": "#da3633", "width": 2},
                "thickness": 0.75,
                "value": 20,
            },
        },
    ))

    fig.update_layout(
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        margin=dict(l=20, r=20, t=40, b=20),
        height=height,
        font=dict(color="#c9d1d9"),
    )

    return dcc.Graph(
        figure=fig,
        config={"displayModeBar": False},
        style={"height": f"{height}px"},
    )

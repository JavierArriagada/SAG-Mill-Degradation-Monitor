"""
src/callbacks/alerts.py
────────────────────────
Alert management page callbacks.
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import Input, Output, State, html, ctx, ALL
import pandas as pd

from config.alerts import SEVERITY_COLORS, SEVERITY_LABELS_ES
from src.data import store

CARD_BG = "#161b22"
BORDER = "#30363d"
MUTED = "#8b949e"

_SEVERITY_ORDER = {"critical": 4, "alert": 3, "warning": 2, "info": 1}


def _severity_badge(severity: str) -> html.Span:
    color = SEVERITY_COLORS.get(severity, MUTED)
    label = SEVERITY_LABELS_ES.get(severity, severity.capitalize())
    return html.Span(
        label,
        style={
            "fontSize": ".65rem",
            "fontWeight": "700",
            "color": color,
            "border": f"1px solid {color}",
            "borderRadius": "4px",
            "padding": "1px 6px",
        },
    )


def _build_table(df: pd.DataFrame, acked_ids: list[str]) -> html.Div:
    if df.empty:
        return html.Div(
            "Sin alertas para los filtros seleccionados.",
            style={"color": MUTED, "padding": "20px", "textAlign": "center"},
        )

    rows = []
    for _, row in df.iterrows():
        is_acked = row["id"] in acked_ids or bool(row.get("acknowledged", False))
        rows.append(
            html.Tr(
                [
                    html.Td(
                        str(pd.to_datetime(row["timestamp"]).strftime("%d/%m %H:%M")),
                        style={"color": MUTED, "fontSize": ".78rem"},
                    ),
                    html.Td(
                        html.Span(row["equipment_id"], style={"color": "#58a6ff", "fontSize": ".82rem", "fontWeight": "600"}),
                    ),
                    html.Td(_severity_badge(row["severity"])),
                    html.Td(row["variable"], style={"fontSize": ".78rem", "color": "#c9d1d9"}),
                    html.Td(f"{row['value']:.3f}", style={"fontSize": ".78rem"}),
                    html.Td(f"{row['threshold']:.3f}", style={"fontSize": ".78rem", "color": MUTED}),
                    html.Td(
                        row["message"],
                        style={"fontSize": ".72rem", "color": MUTED, "maxWidth": "260px", "overflow": "hidden", "textOverflow": "ellipsis"},
                    ),
                    html.Td(
                        html.Button(
                            "✓ Reconocida" if is_acked else "Reconocer",
                            id={"type": "ack-btn", "index": row["id"]},
                            n_clicks=0,
                            disabled=is_acked,
                            style={
                                "fontSize": ".68rem",
                                "fontWeight": "600",
                                "color": "#2ea44f" if is_acked else "#58a6ff",
                                "background": "transparent",
                                "border": f"1px solid {'#2ea44f' if is_acked else '#58a6ff'}",
                                "borderRadius": "4px",
                                "padding": "2px 8px",
                                "cursor": "default" if is_acked else "pointer",
                                "opacity": "0.6" if is_acked else "1",
                            },
                        )
                    ),
                ],
                style={"borderBottom": f"1px solid {BORDER}"},
            )
        )

    return html.Div(
        html.Table(
            [
                html.Thead(
                    html.Tr(
                        [html.Th(h) for h in ["Fecha/Hora", "Equipo", "Severidad", "Variable", "Valor", "Umbral", "Mensaje", "Estado"]],
                        style={"color": MUTED, "fontSize": ".68rem", "textTransform": "uppercase"},
                    )
                ),
                html.Tbody(rows),
            ],
            style={"width": "100%", "borderCollapse": "collapse", "fontSize": ".82rem"},
        ),
        style={"overflowX": "auto"},
    )


def register(app) -> None:

    @app.callback(
        [
            Output("alerts-table", "children"),
            Output("alerts-summary-badges", "children"),
        ],
        [
            Input("interval-live", "n_intervals"),
            Input("alerts-filter-severity", "value"),
            Input("alerts-filter-equipment", "value"),
            Input("alerts-filter-status", "value"),
            Input("store-ack-alerts", "data"),
        ],
    )
    def update_alerts_table(
        n_intervals: int,
        severity_filter: str,
        equipment_filter: str,
        status_filter: str,
        acked_ids: list[str],
    ):
        df = store.get_alerts(days=30, limit=500)

        if df.empty:
            table = html.Div("Sin alertas en los últimos 30 días.", style={"color": MUTED, "padding": "20px", "textAlign": "center"})
            badges = html.Div()
            return table, badges

        # Apply filters
        if severity_filter != "all":
            df = df[df["severity"] == severity_filter]
        if equipment_filter != "all":
            df = df[df["equipment_id"] == equipment_filter]
        if status_filter == "unacked":
            df = df[(df["acknowledged"] == 0) & (~df["id"].isin(acked_ids))]
        elif status_filter == "acked":
            df = df[(df["acknowledged"] == 1) | (df["id"].isin(acked_ids))]

        # Sort by severity then timestamp
        df["_sev_order"] = df["severity"].map(_SEVERITY_ORDER).fillna(0)
        df = df.sort_values(["_sev_order", "timestamp"], ascending=[False, False]).head(100)

        # Summary badges
        full_df = store.get_alerts(days=30, limit=500)
        counts = full_df.groupby("severity").size()
        badges = dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            html.Div(str(counts.get(sev, 0)), style={"fontSize": "1.4rem", "fontWeight": "700", "color": SEVERITY_COLORS.get(sev, MUTED)}),
                            html.Div(SEVERITY_LABELS_ES.get(sev, sev), style={"fontSize": ".65rem", "color": MUTED, "textTransform": "uppercase"}),
                        ],
                        style={"backgroundColor": CARD_BG, "border": f"1px solid {BORDER}", "borderRadius": "8px", "padding": "10px 16px"},
                    ),
                    xs=6, md=3,
                )
                for sev in ["critical", "alert", "warning", "info"]
            ],
            className="g-2",
        )

        return _build_table(df, acked_ids or []), badges

    @app.callback(
        Output("store-ack-alerts", "data"),
        Input({"type": "ack-btn", "index": ALL}, "n_clicks"),
        State("store-ack-alerts", "data"),
        prevent_initial_call=True,
    )
    def acknowledge_alert(n_clicks_list: list, acked_ids: list[str]) -> list[str]:
        if not ctx.triggered_id:
            return acked_ids or []
        alert_id = ctx.triggered_id["index"]
        acked = list(acked_ids or [])
        if alert_id not in acked:
            acked.append(alert_id)
            store.acknowledge_alert(alert_id)
        return acked

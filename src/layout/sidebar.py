"""
src/layout/sidebar.py
──────────────────────
Equipment selector sidebar (shown on /equipment page).
"""
import dash_bootstrap_components as dbc
from dash import html

from config.equipment import EQUIPMENT_CONFIG

SIDEBAR_BG = "#0d1117"
CARD_BG = "#161b22"
BORDER = "#30363d"
MUTED = "#8b949e"


def create_sidebar() -> html.Div:
    """Equipment selector sidebar with health status indicators."""
    options = [
        {
            "label": html.Div(
                [
                    html.Span(
                        eq["name"],
                        style={"color": eq["color"], "fontWeight": "600", "fontSize": ".9rem"},
                    ),
                    html.Div(
                        eq["id"],
                        style={"fontSize": ".68rem", "color": MUTED},
                    ),
                ]
            ),
            "value": eq_id,
        }
        for eq_id, eq in EQUIPMENT_CONFIG.items()
    ]

    return html.Div(
        [
            html.Div(
                "Equipo",
                style={
                    "fontSize": ".68rem",
                    "color": MUTED,
                    "textTransform": "uppercase",
                    "letterSpacing": ".08em",
                    "marginBottom": "8px",
                },
            ),
            dbc.RadioItems(
                id="equipment-selector",
                options=options,
                value="SAG-01",
                inputStyle={"marginRight": "8px"},
                labelStyle={"cursor": "pointer", "marginBottom": "8px"},
                style={"display": "flex", "flexDirection": "column", "gap": "4px"},
            ),
        ],
        style={
            "backgroundColor": CARD_BG,
            "border": f"1px solid {BORDER}",
            "borderRadius": "8px",
            "padding": "14px",
            "minWidth": "160px",
        },
    )

"""
src/layout/components/kpi_card.py
──────────────────────────────────
Reusable KPI indicator card component.
"""
from dash import html

CARD_BG = "#161b22"
MUTED = "#8b949e"


def kpi_card(
    label: str,
    value: str,
    color: str = "#c9d1d9",
    icon: str = "",
    sub_label: str = "",
    border_color: str = "#30363d",
) -> html.Div:
    """
    Compact KPI metric card.

    Args:
        label: Metric name (shown above value)
        value: Formatted value string
        color: Value text color (reflects status)
        icon: Optional single-char/emoji icon
        sub_label: Small secondary label below value
        border_color: Card border color (can reflect severity)
    """
    children = []
    if icon:
        children.append(html.Div(icon, style={"fontSize": "1.4rem", "marginBottom": "4px"}))
    children.append(
        html.Div(label, style={"fontSize": ".68rem", "color": MUTED, "textTransform": "uppercase", "letterSpacing": ".06em"})
    )
    children.append(
        html.Div(value, style={"fontSize": "1.4rem", "fontWeight": "700", "color": color, "lineHeight": "1.2", "marginTop": "2px"})
    )
    if sub_label:
        children.append(
            html.Div(sub_label, style={"fontSize": ".68rem", "color": MUTED, "marginTop": "2px"})
        )

    return html.Div(
        children,
        style={
            "backgroundColor": CARD_BG,
            "border": f"1px solid {border_color}",
            "borderRadius": "8px",
            "padding": "14px 16px",
            "minWidth": "120px",
        },
    )


def mini_kpi(label: str, value: str, color: str = "#c9d1d9") -> html.Div:
    """Compact inline KPI for status cards."""
    return html.Div([
        html.Div(label, style={"fontSize": ".62rem", "color": MUTED, "textTransform": "uppercase"}),
        html.Div(value, style={"fontSize": ".85rem", "fontWeight": "700", "color": color}),
    ])

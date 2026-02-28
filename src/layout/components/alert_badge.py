"""
src/layout/components/alert_badge.py
──────────────────────────────────────
Alert severity badge component.
"""

from dash import html

from config.alerts import SEVERITY_COLORS, SEVERITY_LABELS_ES


def alert_badge(severity: str, lang: str = "es") -> html.Span:
    """Inline severity badge with color-coded border."""
    color = SEVERITY_COLORS.get(severity, "#8b949e")
    labels = (
        SEVERITY_LABELS_ES
        if lang == "es"
        else {"info": "Info", "warning": "Warning", "alert": "Alert", "critical": "Critical"}
    )
    label = labels.get(severity, severity.capitalize())

    return html.Span(
        label,
        style={
            "fontSize": ".65rem",
            "fontWeight": "700",
            "color": color,
            "border": f"1px solid {color}",
            "borderRadius": "4px",
            "padding": "1px 7px",
            "whiteSpace": "nowrap",
        },
    )

"""
src/layout/navbar.py
─────────────────────
Navigation bar with page links and language toggle.
"""

import dash_bootstrap_components as dbc
from dash import html

NAV_BG = "#0d1117"
BORDER = "#30363d"
ACCENT = "#58a6ff"


def create_navbar() -> dbc.Navbar:
    return dbc.Navbar(
        dbc.Container(
            [
                # Brand
                dbc.NavbarBrand(
                    [
                        html.Span("⚙", style={"marginRight": "8px", "fontSize": "1.1rem"}),
                        html.Span(
                            "SAG Monitor", style={"fontWeight": "700", "letterSpacing": ".04em"}
                        ),
                    ],
                    href="/",
                    style={"color": ACCENT, "textDecoration": "none"},
                ),
                dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
                dbc.Collapse(
                    dbc.Nav(
                        [
                            dbc.NavItem(
                                dbc.NavLink("Resumen", href="/", id="nav-overview", active="exact")
                            ),
                            dbc.NavItem(
                                dbc.NavLink(
                                    "Equipos", href="/equipment", id="nav-equipment", active="exact"
                                )
                            ),
                            dbc.NavItem(
                                dbc.NavLink(
                                    "Alertas", href="/alerts", id="nav-alerts", active="exact"
                                )
                            ),
                            dbc.NavItem(
                                dbc.NavLink(
                                    "Tendencias", href="/trends", id="nav-trends", active="exact"
                                )
                            ),
                            # Language toggle
                            dbc.NavItem(
                                html.Div(
                                    [
                                        html.Button(
                                            "ES",
                                            id="lang-es-btn",
                                            n_clicks=0,
                                            style=_lang_btn_style(True),
                                        ),
                                        html.Button(
                                            "EN",
                                            id="lang-en-btn",
                                            n_clicks=0,
                                            style=_lang_btn_style(False),
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "gap": "4px",
                                        "alignItems": "center",
                                        "marginLeft": "12px",
                                    },
                                )
                            ),
                        ],
                        className="ms-auto",
                        navbar=True,
                    ),
                    id="navbar-collapse",
                    navbar=True,
                    is_open=False,
                ),
            ],
            fluid=True,
        ),
        color=NAV_BG,
        dark=True,
        sticky="top",
        style={"borderBottom": f"1px solid {BORDER}", "padding": ".5rem 1rem"},
    )


def _lang_btn_style(active: bool) -> dict:
    return {
        "background": "rgba(88,166,255,0.15)" if active else "transparent",
        "border": "1px solid #30363d",
        "color": "#58a6ff" if active else "#8b949e",
        "borderRadius": "4px",
        "fontSize": ".72rem",
        "fontWeight": "700",
        "padding": "2px 8px",
        "cursor": "pointer",
    }

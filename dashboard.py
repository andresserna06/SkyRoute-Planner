# dashboard.py — R1: interactive web visualization of the air route network
# Run:  python dashboard.py   then open  http://localhost:8050  in your browser

import base64
import json
import os
import sys

# Add project root to path so models/services can be imported from any directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dash
from dash import dcc, html, Input, Output, State
import dash_cytoscape as cyto

from services.graphService import build_graph_from_dict
from services.itineraryService import (
    propose_max_coverage_by_budget,
    propose_max_coverage_by_time,
    find_best_routes,
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _load_default_data():
    try:
        with open("data/air_network.json", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _build_graph_from_store(data):
    if data is None:
        return None
    return build_graph_from_dict(data)


# ── Tab styling ──────────────────────────────────────────────────────────────
TAB_STYLE = {
    "padding": "6px 10px",
    "fontSize": "11px",
    "fontWeight": "600",
    "color": "#5d6b80",
    "backgroundColor": "#f6f8fb",
    "border": "none",
    "borderBottom": "2px solid transparent",
}
TAB_SELECTED_STYLE = {
    "padding": "6px 10px",
    "fontSize": "11px",
    "fontWeight": "700",
    "color": "#1e293b",
    "backgroundColor": "#f6f8fb",
    "border": "none",
    "borderBottom": f"2px solid #7c3aed",
}


# ── Color palette (single source of truth for the whole UI) ───────────────────
# Balanced light theme: soft gray-blue canvas with saturated accent nodes.
COLORS = {
    "bg_canvas":    "#e8ecf2",   # graph canvas — soft gray-blue (not stark white)
    "bg_panel":     "#f6f8fb",   # sidebar / header panels
    "bg_panel_2":   "#eceff4",   # raised cards inside the panel
    "border":       "#d4dbe5",   # subtle separators
    "text":         "#1e293b",   # main dark text
    "text_dim":     "#5d6b80",   # secondary muted text
    "hub":          "#ea580c",   # hub airports — orange
    "hub_border":   "#c2410c",   # darker orange border
    "secondary":    "#2563eb",   # secondary airports — blue
    "sec_border":   "#1d4ed8",   # darker blue border
    "route":        "#8a98ab",   # regular route line
    "subsidized":   "#16a34a",   # subsidised route line — green
    "highlight":    "#7c3aed",   # selected node's outgoing routes — violet
    "node_outline": "#1e293b",   # thin outline around node labels
    "ok":           "#16a34a",
    "error":        "#dc2626",
}


# ── Convert a Graph object into the element list Cytoscape expects ────────────
def build_elements(g):
    elements = []

    # One node per airport — position is set by the layout algorithm, not here
    for v in g.vertices:
        elements.append({
            "data": {
                "id":        v.id,
                "label":     v.id,
                "full_name": v.name,
                "city":      v.city,
                "country":   v.country,
                "timezone":  v.timezone,
                "airlines":  ", ".join(v.airlines) if v.airlines else "N/A",
                "node_type": "hub" if v.is_hub else "secondary",
            },
            "classes": "hub" if v.is_hub else "secondary",
        })

    # One directed edge per route
    for v in g.vertices:
        for edge in v.adjacencies:
            # Abbreviate each aircraft type to a single letter: C / R / H
            abbrevs = []
            for a in edge.aircraft:
                if "Comercial" in a or "Commercial" in a:
                    abbrevs.append("C")
                elif "Regional" in a:
                    abbrevs.append("R")
                else:
                    abbrevs.append("H")  # Hélice / Propeller

            label         = f"{int(edge.distance_km)} km · {','.join(abbrevs)}"
            is_subsidized = (edge.base_cost == 0)

            elements.append({
                "data": {
                    "source":      v.id,
                    "target":      edge.destination_vertex.id,
                    "label":       label,
                    "distance_km": edge.distance_km,
                    "aircraft":    ", ".join(edge.aircraft),
                },
                "classes": "subsidiada" if is_subsidized else "ruta",
            })

    return elements


# ── Cytoscape visual stylesheet ───────────────────────────────────────────────
# Returns the base list of style rules. Built by a function so the highlight
# callback can reuse it and append a few extra rules on top.
def base_stylesheet():
    return [
        # Base node style — label centred, smooth transitions on hover/select
        {
            "selector": "node",
            "style": {
                "label":               "data(label)",
                "text-valign":         "center",
                "text-halign":         "center",
                "font-family":         "Inter, Segoe UI, sans-serif",
                "font-size":           "10px",
                "font-weight":         "700",
                "color":               "#ffffff",
                "text-outline-width":  1.6,
                "text-outline-color":  COLORS["node_outline"],
                "transition-property": "width, height, underlay-opacity, border-color",
                "transition-duration": "0.18s",
            },
        },
        # Hub airports — solid orange, larger
        {
            "selector": ".hub",
            "style": {
                "background-color": COLORS["hub"],
                "width":            56,
                "height":           56,
                "font-size":        "12px",
                "border-width":     2,
                "border-color":     COLORS["hub_border"],
            },
        },
        # Secondary airports — solid blue, smaller
        {
            "selector": ".secondary",
            "style": {
                "background-color": COLORS["secondary"],
                "width":            38,
                "height":           38,
                "border-width":     2,
                "border-color":     COLORS["sec_border"],
            },
        },
        # Standard route edges
        {
            "selector": "edge.ruta",
            "style": {
                "label":                   "data(label)",
                "curve-style":             "bezier",
                "target-arrow-shape":      "triangle",
                "target-arrow-color":      COLORS["route"],
                "line-color":              COLORS["route"],
                "arrow-scale":             1.0,
                "width":                   1.3,
                "opacity":                 0.65,
                "font-family":             "Inter, Segoe UI, sans-serif",
                "font-size":               "9px",
                "font-weight":             "600",
                "color":                   COLORS["text"],
                "text-background-color":   "#ffffff",
                "text-background-opacity": 0.95,
                "text-background-padding": "3px",
                "text-background-shape":   "roundrectangle",
                "text-border-width":       1,
                "text-border-color":       COLORS["border"],
                "text-border-opacity":     1,
            },
        },
        # Subsidised routes — green dashed line, always a bit brighter
        {
            "selector": "edge.subsidiada",
            "style": {
                "label":                   "data(label)",
                "curve-style":             "bezier",
                "target-arrow-shape":      "triangle",
                "target-arrow-color":      COLORS["subsidized"],
                "line-color":              COLORS["subsidized"],
                "line-style":              "dashed",
                "arrow-scale":             1.0,
                "width":                   1.8,
                "opacity":                 0.9,
                "font-family":             "Inter, Segoe UI, sans-serif",
                "font-size":               "9px",
                "font-weight":             "600",
                "color":                   COLORS["subsidized"],
                "text-background-color":   "#ffffff",
                "text-background-opacity": 0.95,
                "text-background-padding": "3px",
                "text-background-shape":   "roundrectangle",
                "text-border-width":       1,
                "text-border-color":       COLORS["border"],
                "text-border-opacity":     1,
            },
        },
    ]


# ── Available graph layouts (the user picks one from a dropdown) ───────────────
# Each value is a plain dict passed straight to Cytoscape — no JS functions.
LAYOUTS = {
    # Force-directed: pushes nodes apart, pulls connected ones together
    "cose": {
        "name":            "cose",
        "animate":         False,
        "randomize":       False,
        "idealEdgeLength": 180,
        "nodeRepulsion":   9000,
        "gravity":         0.2,
        "nodeOverlap":     24,
        "fit":             True,
        "padding":         60,
    },
    # Concentric: most-connected airports (hubs) are placed in the centre rings
    "concentric": {
        "name":           "concentric",
        "animate":        False,
        "minNodeSpacing": 45,
        "fit":            True,
        "padding":        60,
    },
    # Circle: all airports evenly spaced around a ring
    "circle": {
        "name":    "circle",
        "animate": False,
        "fit":     True,
        "padding": 60,
    },
}


# ── Reusable style snippets ───────────────────────────────────────────────────
SECTION_TITLE = {
    "margin":        "0 0 12px 0",
    "color":         COLORS["text"],
    "fontSize":      "12px",
    "textTransform": "uppercase",
    "letterSpacing": "1.2px",
    "fontWeight":    "700",
}

STAT_CHIP = {
    "display":         "flex",
    "alignItems":      "center",
    "gap":             "7px",
    "backgroundColor": COLORS["bg_panel_2"],
    "border":          f"1px solid {COLORS['border']}",
    "color":           COLORS["text"],
    "padding":         "5px 14px",
    "borderRadius":    "20px",
    "fontSize":        "13px",
    "fontWeight":      "600",
}


# Helper: a header stat chip = coloured dot + a number span (updated by callback) + a label
def stat_chip(dot_color, span_id, label):
    return html.Div(
        style=STAT_CHIP,
        children=[
            html.Span(style={"width": "8px", "height": "8px", "borderRadius": "50%",
                             "backgroundColor": dot_color, "flexShrink": 0}),
            html.Span("—", id=span_id, style={"fontWeight": "700"}),
            html.Span(label, style={"color": COLORS["text_dim"], "fontWeight": "500"}),
        ],
    )


# Helper: placeholder shown in the detail card before any node is clicked
def _placeholder():
    return html.P(
        "Haz clic en un aeropuerto para ver su información.",
        style={"fontSize": "12px", "color": COLORS["text_dim"], "margin": 0, "lineHeight": "1.6"},
    )


# Small helper: one row in the legend (a coloured swatch + a label)
def legend_row(swatch_style, text):
    return html.Div(
        style={"display": "flex", "alignItems": "center", "gap": "10px", "marginBottom": "9px"},
        children=[
            html.Div(style={**swatch_style, "flexShrink": 0}),
            html.Span(text, style={"fontSize": "13px", "color": COLORS["text_dim"]}),
        ],
    )


# ── Dash app ──────────────────────────────────────────────────────────────────
# Load the Inter font from Google Fonts for a cleaner, more modern look.
EXTERNAL_STYLES = [
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
]

app = dash.Dash(__name__, title="SkyRoute Planner", external_stylesheets=EXTERNAL_STYLES)

app.layout = html.Div(
    style={
        "fontFamily":      "Inter, Segoe UI, Arial, sans-serif",
        "backgroundColor": COLORS["bg_canvas"],
        "height":          "100vh",
        "display":         "flex",
        "flexDirection":   "column",
        "overflow":        "hidden",
    },
    children=[

        # ── Header bar ────────────────────────────────────────────────────────
        html.Div(
            style={"flexShrink": 0},
            children=[
                # Main header row
                html.Div(
                    style={
                        "backgroundColor": COLORS["bg_panel"],
                        "padding":     "0 26px",
                        "height":      "68px",
                        "display":     "flex",
                        "alignItems":  "center",
                        "gap":         "14px",
                        "boxShadow":   "0 2px 8px rgba(0,0,0,0.05)",
                    },
                    children=[
                        # Circular gradient badge holding the plane glyph
                        html.Div(
                            "✈",
                            style={
                                "width":          "40px",
                                "height":         "40px",
                                "borderRadius":   "50%",
                                "background":     f"linear-gradient(135deg, {COLORS['hub']}, #f97316)",
                                "color":          "#ffffff",
                                "display":        "flex",
                                "alignItems":     "center",
                                "justifyContent": "center",
                                "fontSize":       "18px",
                                "transform":      "rotate(-45deg)",
                                "boxShadow":      f"0 3px 8px rgba(234,88,12,0.35)",
                                "flexShrink":     0,
                            },
                        ),
                        # Title + subtitle stacked
                        html.Div([
                            html.H1(
                                "SkyRoute Planner",
                                style={"color": COLORS["text"], "margin": 0, "fontSize": "21px",
                                       "fontWeight": "800", "letterSpacing": "0.3px", "lineHeight": "1.1"},
                            ),
                            html.Span(
                                "Red Aérea Latinoamericana",
                                style={"color": COLORS["text_dim"], "fontSize": "12px", "fontWeight": "500"},
                            ),
                        ]),
                        # Dynamic stats — the number spans are updated by the upload callback
                        html.Div(
                            style={"marginLeft": "auto", "display": "flex", "gap": "10px"},
                            children=[
                                stat_chip(COLORS["secondary"], "stat-airports", "aeropuertos"),
                                stat_chip(COLORS["route"],     "stat-routes",   "rutas"),
                                stat_chip(COLORS["hub"],       "stat-hubs",     "hubs"),
                            ],
                        ),
                    ],
                ),
                # Thin gradient accent line under the header
                html.Div(style={
                    "height": "3px",
                    "background": f"linear-gradient(90deg, {COLORS['hub']}, {COLORS['highlight']}, {COLORS['secondary']})",
                }),
                # Hidden stores for cross-callback state
                dcc.Store(id="graph-data",     data=None),
                dcc.Store(id="dynamic-state",  data=None),
                dcc.Store(id="dynamic-step",   data=0),
            ],
        ),

        # ── Body: sidebar + graph ─────────────────────────────────────────────
        html.Div(
            style={"display": "flex", "flex": 1, "overflow": "hidden"},
            children=[

                # Left sidebar — tabbed interface (R1 visualisation + R2.2 / R2.3)
                html.Div(
                    style={
                        "width":           "320px",
                        "minWidth":        "320px",
                        "backgroundColor": COLORS["bg_panel"],
                        "borderRight":     f"1px solid {COLORS['border']}",
                        "padding":         "0",
                        "display":         "flex",
                        "flexDirection":   "column",
                        "overflowY":       "auto",
                    },
                    children=[
                        dcc.Tabs(
                            id="sidebar-tabs",
                            value="vis",
                            style={"flexShrink": 0},
                            children=[

                                # ── TAB: Visualización ─────────────────────────
                                dcc.Tab(label="Vis", value="vis",
                                        style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE,
                                        children=[html.Div(
                                style={"padding": "14px 16px", "display": "flex",
                                       "flexDirection": "column", "gap": "14px"},
                                children=[
                                    html.Div([
                                        html.H4("Cargar red a\u00e9rea", style=SECTION_TITLE),
                                        dcc.Upload(
                                            id="upload-json",
                                            children=html.Div([
                                                html.Div("\u2913", style={"fontSize": "22px",
                                                    "color": COLORS["secondary"], "marginBottom": "4px"}),
                                                "Arrastra el archivo JSON aqu\u00ed",
                                                html.Br(),
                                                html.A("o haz clic para seleccionarlo",
                                                    style={"color": COLORS["secondary"],
                                                           "textDecoration": "underline", "cursor": "pointer"}),
                                            ]),
                                            style={"width": "100%", "padding": "14px 10px",
                                                "borderWidth": "1.5px", "borderStyle": "dashed",
                                                "borderRadius": "10px", "borderColor": COLORS["border"],
                                                "textAlign": "center", "fontSize": "12px",
                                                "color": COLORS["text_dim"],
                                                "backgroundColor": COLORS["bg_panel_2"],
                                                "cursor": "pointer", "boxSizing": "border-box",
                                                "lineHeight": "1.6"},
                                            accept=".json"),
                                        html.Div(id="upload-status",
                                                 style={"marginTop": "6px", "minHeight": "16px"}),
                                    ]),
                                    html.Div([
                                        html.H4("Disposici\u00f3n del grafo", style=SECTION_TITLE),
                                        dcc.Dropdown(id="layout-dropdown",
                                            options=[
                                                {"label": "Org\u00e1nica (fuerzas)", "value": "cose"},
                                                {"label": "Conc\u00e9ntrica (hubs al centro)", "value": "concentric"},
                                                {"label": "Circular", "value": "circle"}],
                                            value="cose", clearable=False,
                                            style={"fontSize": "13px", "color": "#1a2440"}),
                                    ]),
                                    html.Hr(style={"margin": "0", "border": "none",
                                                   "borderTop": f"1px solid {COLORS['border']}"}),
                                    html.Div([
                                        html.H4("Leyenda", style=SECTION_TITLE),
                                        legend_row({"width": "20px", "height": "20px", "borderRadius": "50%",
                                                     "backgroundColor": COLORS["hub"],
                                                     "border": f"2px solid {COLORS['hub_border']}"},
                                                    "Aeropuerto hub"),
                                        legend_row({"width": "14px", "height": "14px", "borderRadius": "50%",
                                                     "backgroundColor": COLORS["secondary"],
                                                     "border": f"2px solid {COLORS['sec_border']}"},
                                                    "Aeropuerto secundario"),
                                        legend_row({"width": "28px", "height": "2px",
                                                     "backgroundColor": COLORS["route"]}, "Ruta regular"),
                                        legend_row({"width": "28px", "height": "0",
                                                     "borderTop": f"2px dashed {COLORS['subsidized']}"},
                                                    "Ruta subsidiada"),
                                    ]),
                                    html.Hr(style={"margin": "0", "border": "none",
                                                   "borderTop": f"1px solid {COLORS['border']}"}),
                                    html.Div([
                                        html.H4("Tipos de aeronave", style=SECTION_TITLE),
                                        html.Div("C  \u00b7  Avi\u00f3n Comercial",
                                                 style={"fontSize": "12px", "color": COLORS["text_dim"], "marginBottom": "4px"}),
                                        html.Div("R  \u00b7  Jet Regional",
                                                 style={"fontSize": "12px", "color": COLORS["text_dim"], "marginBottom": "4px"}),
                                        html.Div("H  \u00b7  Avi\u00f3n de H\u00e9lice",
                                                 style={"fontSize": "12px", "color": COLORS["text_dim"]}),
                                    ]),
                                    html.Hr(style={"margin": "0", "border": "none",
                                                   "borderTop": f"1px solid {COLORS['border']}"}),
                                    html.Button("\u21ba  Ver todo el grafo",
                                        id="clear-selection", n_clicks=0,
                                        style={"width": "100%", "padding": "8px 12px",
                                            "backgroundColor": COLORS["bg_panel_2"],
                                            "color": COLORS["text"],
                                            "border": f"1px solid {COLORS['border']}",
                                            "borderRadius": "8px", "fontSize": "12px",
                                            "fontWeight": "600",
                                            "fontFamily": "Inter, Segoe UI, sans-serif",
                                            "cursor": "pointer"}),
                                    html.Div(id="airport-info", children=_placeholder()),
                                ])]),

                                # ── TAB: Presupuesto (Propuesta A) ─────────────
                                dcc.Tab(label="$", value="budget",
                                        style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE,
                                        children=[html.Div(
                                style={"padding": "14px 16px", "display": "flex",
                                       "flexDirection": "column", "gap": "10px"},
                                children=[
                                    html.H4("M\u00e1x. destinos por presupuesto", style=SECTION_TITLE),
                                    html.Div("Origen:", style={"fontSize": "12px", "fontWeight": "600",
                                                               "color": COLORS["text"]}),
                                    dcc.Input(id="budget-origin", type="text", placeholder="Ej: BOG",
                                        style={"width": "100%", "padding": "8px", "borderRadius": "6px",
                                               "border": f"1px solid {COLORS['border']}", "fontSize": "13px",
                                               "boxSizing": "border-box"}),
                                    html.Div("Presupuesto m\u00e1ximo (USD):", style={"fontSize": "12px",
                                        "fontWeight": "600", "color": COLORS["text"]}),
                                    dcc.Input(id="budget-amount", type="number", placeholder="Ej: 500",
                                        style={"width": "100%", "padding": "8px", "borderRadius": "6px",
                                               "border": f"1px solid {COLORS['border']}", "fontSize": "13px",
                                               "boxSizing": "border-box"}),
                                    html.Div("L\u00edmite de tiempo (horas, opcional):",
                                             style={"fontSize": "12px", "fontWeight": "600",
                                                    "color": COLORS["text"]}),
                                    dcc.Input(id="budget-time", type="number", placeholder="Ej: 24",
                                        style={"width": "100%", "padding": "8px", "borderRadius": "6px",
                                               "border": f"1px solid {COLORS['border']}", "fontSize": "13px",
                                               "boxSizing": "border-box"}),
                                    html.Div("Aeronaves preferidas:", style={"fontSize": "12px",
                                        "fontWeight": "600", "color": COLORS["text"]}),
                                    dcc.Checklist(id="budget-aircraft",
                                        options=[
                                            {"label": " Avi\u00f3n Comercial", "value": "Avión Comercial"},
                                            {"label": " Jet Regional",       "value": "Jet Regional"},
                                            {"label": " Avi\u00f3n de H\u00e9lice", "value": "Avión de Hélice"}],
                                        style={"fontSize": "12px", "color": COLORS["text"]}),
                                    html.Button("Calcular ruta", id="budget-btn", n_clicks=0,
                                        style={"width": "100%", "padding": "9px", "marginTop": "4px",
                                               "backgroundColor": COLORS["hub"], "color": "#fff",
                                               "border": "none", "borderRadius": "8px",
                                               "fontSize": "13px", "fontWeight": "700",
                                               "fontFamily": "Inter, Segoe UI, sans-serif",
                                               "cursor": "pointer"}),
                                    html.Div(id="budget-result",
                                             style={"fontSize": "12px", "color": COLORS["text"]}),
                                ])]),

                                # ── TAB: Tiempo (Propuesta B) ───────────────────
                                dcc.Tab(label="\u23f1", value="time",
                                        style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE,
                                        children=[html.Div(
                                style={"padding": "14px 16px", "display": "flex",
                                       "flexDirection": "column", "gap": "10px"},
                                children=[
                                    html.H4("M\u00e1x. destinos por tiempo", style=SECTION_TITLE),
                                    html.Div("Origen:", style={"fontSize": "12px", "fontWeight": "600",
                                                               "color": COLORS["text"]}),
                                    dcc.Input(id="time-origin", type="text", placeholder="Ej: LIM",
                                        style={"width": "100%", "padding": "8px", "borderRadius": "6px",
                                               "border": f"1px solid {COLORS['border']}", "fontSize": "13px",
                                               "boxSizing": "border-box"}),
                                    html.Div("Tiempo disponible (horas):", style={"fontSize": "12px",
                                        "fontWeight": "600", "color": COLORS["text"]}),
                                    dcc.Input(id="time-limit", type="number", placeholder="Ej: 8",
                                        style={"width": "100%", "padding": "8px", "borderRadius": "6px",
                                               "border": f"1px solid {COLORS['border']}", "fontSize": "13px",
                                               "boxSizing": "border-box"}),
                                    html.Div("Presupuesto m\u00e1ximo (USD, opcional):",
                                             style={"fontSize": "12px", "fontWeight": "600",
                                                    "color": COLORS["text"]}),
                                    dcc.Input(id="time-budget", type="number", placeholder="Ej: 1000",
                                        style={"width": "100%", "padding": "8px", "borderRadius": "6px",
                                               "border": f"1px solid {COLORS['border']}", "fontSize": "13px",
                                               "boxSizing": "border-box"}),
                                    html.Div("Aeronaves preferidas:", style={"fontSize": "12px",
                                        "fontWeight": "600", "color": COLORS["text"]}),
                                    dcc.Checklist(id="time-aircraft",
                                        options=[
                                            {"label": " Avi\u00f3n Comercial", "value": "Avión Comercial"},
                                            {"label": " Jet Regional",       "value": "Jet Regional"},
                                            {"label": " Avi\u00f3n de H\u00e9lice", "value": "Avión de Hélice"}],
                                        style={"fontSize": "12px", "color": COLORS["text"]}),
                                    html.Button("Calcular ruta", id="time-btn", n_clicks=0,
                                        style={"width": "100%", "padding": "9px", "marginTop": "4px",
                                               "backgroundColor": COLORS["secondary"], "color": "#fff",
                                               "border": "none", "borderRadius": "8px",
                                               "fontSize": "13px", "fontWeight": "700",
                                               "fontFamily": "Inter, Segoe UI, sans-serif",
                                               "cursor": "pointer"}),
                                    html.Div(id="time-result",
                                             style={"fontSize": "12px", "color": COLORS["text"]}),
                                ])]),

                                # ── TAB: B\u00fasqueda Manual ────────────────────
                                dcc.Tab(label="Ruta", value="search",
                                        style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE,
                                        children=[html.Div(
                                style={"padding": "14px 16px", "display": "flex",
                                       "flexDirection": "column", "gap": "10px"},
                                children=[
                                    html.H4("B\u00fasqueda manual de ruta", style=SECTION_TITLE),
                                    html.Div("Origen:", style={"fontSize": "12px", "fontWeight": "600",
                                                               "color": COLORS["text"]}),
                                    dcc.Input(id="search-origin", type="text", placeholder="Ej: BOG",
                                        style={"width": "100%", "padding": "8px", "borderRadius": "6px",
                                               "border": f"1px solid {COLORS['border']}", "fontSize": "13px",
                                               "boxSizing": "border-box"}),
                                    html.Div("Destino:", style={"fontSize": "12px", "fontWeight": "600",
                                                                "color": COLORS["text"]}),
                                    dcc.Input(id="search-dest", type="text", placeholder="Ej: LIM",
                                        style={"width": "100%", "padding": "8px", "borderRadius": "6px",
                                               "border": f"1px solid {COLORS['border']}", "fontSize": "13px",
                                               "boxSizing": "border-box"}),
                                    html.Div("Criterio(s) de optimizaci\u00f3n:",
                                             style={"fontSize": "12px", "fontWeight": "600",
                                                    "color": COLORS["text"]}),
                                    dcc.Checklist(id="search-criteria",
                                        options=[
                                            {"label": " Distancia", "value": "distance"},
                                            {"label": " Tiempo",    "value": "time"},
                                            {"label": " Costo",     "value": "cost"}],
                                        value=["distance"],
                                        style={"fontSize": "12px", "color": COLORS["text"]}),
                                    html.Div("Incluir aeropuertos secundarios:",
                                             style={"fontSize": "12px", "fontWeight": "600",
                                                    "color": COLORS["text"]}),
                                    dcc.RadioItems(id="search-secondary",
                                        options=[
                                            {"label": " S\u00ed", "value": True},
                                            {"label": " No",  "value": False}],
                                        value=True,
                                        style={"fontSize": "12px", "color": COLORS["text"]}),
                                    html.Div("Aeronaves preferidas:", style={"fontSize": "12px",
                                        "fontWeight": "600", "color": COLORS["text"]}),
                                    dcc.Checklist(id="search-aircraft",
                                        options=[
                                            {"label": " Avi\u00f3n Comercial", "value": "Avión Comercial"},
                                            {"label": " Jet Regional",       "value": "Jet Regional"},
                                            {"label": " Avi\u00f3n de H\u00e9lice", "value": "Avión de Hélice"}],
                                        style={"fontSize": "12px", "color": COLORS["text"]}),
                                    html.Button("Buscar ruta", id="search-btn", n_clicks=0,
                                        style={"width": "100%", "padding": "9px", "marginTop": "4px",
                                               "backgroundColor": COLORS["highlight"], "color": "#fff",
                                               "border": "none", "borderRadius": "8px",
                                               "fontSize": "13px", "fontWeight": "700",
                                               "fontFamily": "Inter, Segoe UI, sans-serif",
                                               "cursor": "pointer"}),
                                    html.Div(id="search-result",
                                             style={"fontSize": "12px", "color": COLORS["text"]}),
                                ])]),

                                # ── TAB: Planificaci\u00f3n Din\u00e1mica ──────────
                                dcc.Tab(label="Din", value="dynamic",
                                        style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE,
                                        children=[html.Div(
                                style={"padding": "14px 16px", "display": "flex",
                                       "flexDirection": "column", "gap": "10px"},
                                children=[
                                    html.H4("Planificaci\u00f3n din\u00e1mica",
                                            style=SECTION_TITLE),
                                    html.Div("Origen:", style={"fontSize": "12px", "fontWeight": "600",
                                                               "color": COLORS["text"]}),
                                    dcc.Input(id="dynamic-origin", type="text", placeholder="Ej: BOG",
                                        style={"width": "100%", "padding": "8px", "borderRadius": "6px",
                                               "border": f"1px solid {COLORS['border']}", "fontSize": "13px",
                                               "boxSizing": "border-box"}),
                                    html.Div("Presupuesto inicial (USD):", style={"fontSize": "12px",
                                        "fontWeight": "600", "color": COLORS["text"]}),
                                    dcc.Input(id="dynamic-budget", type="number", placeholder="Ej: 500",
                                        style={"width": "100%", "padding": "8px", "borderRadius": "6px",
                                               "border": f"1px solid {COLORS['border']}", "fontSize": "13px",
                                               "boxSizing": "border-box"}),
                                    html.Button("Iniciar viaje", id="dynamic-btn", n_clicks=0,
                                        style={"width": "100%", "padding": "9px", "marginTop": "4px",
                                               "backgroundColor": COLORS["ok"], "color": "#fff",
                                               "border": "none", "borderRadius": "8px",
                                               "fontSize": "13px", "fontWeight": "700",
                                               "fontFamily": "Inter, Segoe UI, sans-serif",
                                               "cursor": "pointer"}),
                                    # Flight and job selectors (hidden until journey starts)
                                    html.Div(id="dynamic-controls",
                                             style={"display": "none"},
                                             children=[
                                        html.Div(id="dynamic-flight-section", children=[
                                            html.Div(id="dynamic-origin-label",
                                                     style={"fontSize": "12px", "fontWeight": "600",
                                                            "color": COLORS["text"], "marginTop": "4px"}),
                                            dcc.Dropdown(id="dynamic-flight-choice",
                                                         options=[], placeholder="Vuelos disponibles...",
                                                         style={"fontSize": "12px"}),
                                            html.Button("Volar", id="dynamic-fly-btn", n_clicks=0,
                                                style={"width": "100%", "padding": "7px", "marginTop": "4px",
                                                       "backgroundColor": COLORS["hub"], "color": "#fff",
                                                       "border": "none", "borderRadius": "6px",
                                                       "fontSize": "12px", "fontWeight": "700",
                                                       "fontFamily": "Inter, Segoe UI, sans-serif",
                                                       "cursor": "pointer"}),
                                        ]),
                                        html.Div(id="dynamic-job-section",
                                                 style={"display": "none"}, children=[
                                            html.Hr(style={"margin": "8px 0", "border": "none",
                                                           "borderTop": f"1px solid {COLORS['border']}"}),
                                            html.Div("Trabajo en destino (opcional):",
                                                     style={"fontSize": "12px", "fontWeight": "600",
                                                            "color": COLORS["text"]}),
                                            dcc.Dropdown(id="dynamic-job-choice",
                                                         options=[], placeholder="Selecciona trabajo...",
                                                         style={"fontSize": "12px"}),
                                            dcc.Input(id="dynamic-hours", type="number",
                                                      placeholder="Horas", min=0, max=24,
                                                      style={"width": "100%", "padding": "6px",
                                                             "borderRadius": "6px",
                                                             "border": f"1px solid {COLORS['border']}",
                                                             "fontSize": "12px",
                                                             "boxSizing": "border-box",
                                                             "marginTop": "4px"}),
                                            html.Button("Trabajar", id="dynamic-work-btn", n_clicks=0,
                                                style={"width": "100%", "padding": "7px", "marginTop": "4px",
                                                       "backgroundColor": COLORS["secondary"], "color": "#fff",
                                                       "border": "none", "borderRadius": "6px",
                                                       "fontSize": "12px", "fontWeight": "700",
                                                       "fontFamily": "Inter, Segoe UI, sans-serif",
                                                       "cursor": "pointer"}),
                                            html.Button("Continuar sin trabajar",
                                                        id="dynamic-skip-btn", n_clicks=0,
                                                style={"width": "100%", "padding": "7px", "marginTop": "4px",
                                                       "backgroundColor": COLORS["bg_panel_2"],
                                                       "color": COLORS["text"],
                                                       "border": f"1px solid {COLORS['border']}",
                                                       "borderRadius": "6px", "fontSize": "12px",
                                                       "fontWeight": "600",
                                                       "fontFamily": "Inter, Segoe UI, sans-serif",
                                                       "cursor": "pointer"}),
                                            html.Div(id="dynamic-status",
                                                     style={"marginTop": "6px", "fontSize": "11px",
                                                            "color": COLORS["text_dim"]}),
                                        ]),
                                    ]),
                                    html.Div(id="dynamic-display",
                                             style={"fontSize": "12px", "color": COLORS["text"],
                                                    "marginTop": "4px"}),
                                ])]),

                            ],
                        ),
                    ],
                ),

                # ── Cytoscape graph ───────────────────────────────────────────
                cyto.Cytoscape(
                    id="network-graph",
                    elements=[],   # empty until the user uploads a JSON
                    layout=LAYOUTS["cose"],
                    stylesheet=base_stylesheet(),
                    style={
                        "flex":            1,
                        "height":          "100%",
                        "backgroundColor": COLORS["bg_canvas"],
                    },
                    minZoom=0.15,
                    maxZoom=4.0,
                    userZoomingEnabled=True,
                    userPanningEnabled=True,
                ),
            ],
        ),
    ],
)


# ── Callback: parse uploaded JSON and populate the graph ──────────────────────
@app.callback(
    Output("network-graph", "elements"),
    Output("stat-airports",  "children"),
    Output("stat-routes",    "children"),
    Output("stat-hubs",      "children"),
    Output("upload-status",  "children"),
    Output("graph-data",     "data"),
    Input("upload-json",     "contents"),
    State("upload-json",     "filename"),
)
def load_uploaded_json(contents, filename):
    # No file uploaded yet — keep everything empty
    if contents is None:
        raise dash.exceptions.PreventUpdate

    # The upload content arrives as  "data:<mime>;base64,<data>"
    _, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)

    try:
        data  = json.loads(decoded.decode("utf-8"))
        g     = build_graph_from_dict(data)
        elems = build_elements(g)

        n_airports = len(g.vertices)
        n_routes   = sum(len(v.adjacencies) for v in g.vertices)
        n_hubs     = sum(1 for v in g.vertices if v.is_hub)

        status = html.Span(
            f"✓  {filename}",
            style={"color": COLORS["ok"], "fontSize": "11px", "fontWeight": "600"},
        )
        return (elems, str(n_airports), str(n_routes), str(n_hubs), status, data)

    except Exception as e:
        status = html.Span(
            f"Error al cargar el archivo: {e}",
            style={"color": COLORS["error"], "fontSize": "11px"},
        )
        return [], "—", "—", "—", status, dash.no_update


# ── Callback: switch the graph layout from the dropdown ───────────────────────
@app.callback(
    Output("network-graph", "layout"),
    Input("layout-dropdown", "value"),
)
def update_layout(layout_name):
    return LAYOUTS.get(layout_name, LAYOUTS["cose"])


# ── Callback: highlight the selected airport's outgoing routes ────────────────
@app.callback(
    Output("network-graph",  "stylesheet"),
    Input("network-graph",   "tapNodeData"),
    Input("clear-selection", "n_clicks"),
)
def highlight_routes(node_data, clear_clicks):
    # If the reset button was the trigger, or nothing is selected, show base style
    triggered = dash.callback_context.triggered_id
    if triggered == "clear-selection" or not node_data:
        return base_stylesheet()

    nid = node_data["id"]

    # Start from the base style, then layer highlight rules on top:
    #  1. fade every edge into the background
    #  2. light up only the routes leaving the selected airport
    #  3. give the selected node a bold violet border
    return base_stylesheet() + [
        {"selector": "edge", "style": {"opacity": 0.08}},
        {
            "selector": f'edge[source = "{nid}"]',
            "style": {
                "opacity":            1,
                "line-color":         COLORS["highlight"],
                "target-arrow-color": COLORS["highlight"],
                "width":              2.6,
                "color":              COLORS["highlight"],
                "z-index":            99,
            },
        },
        {
            "selector": f'node[id = "{nid}"]',
            "style": {
                "border-color": COLORS["highlight"],
                "border-width": 4,
            },
        },
    ]


# ── Callback: show airport details when a node is clicked ─────────────────────
@app.callback(
    Output("airport-info",   "children"),
    Input("network-graph",   "tapNodeData"),
    Input("clear-selection", "n_clicks"),
)
def show_airport_info(node_data, clear_clicks):
    # Reset button trigger, or nothing selected — show the placeholder
    triggered = dash.callback_context.triggered_id
    if triggered == "clear-selection" or not node_data:
        return _placeholder()

    is_hub     = node_data["node_type"] == "hub"
    type_label = "Aeropuerto Hub" if is_hub else "Aeropuerto Secundario"
    accent     = COLORS["hub"] if is_hub else COLORS["secondary"]

    # Card showing the selected airport's full details
    return html.Div(
        style={
            "backgroundColor": COLORS["bg_panel_2"],
            "border":          f"1px solid {COLORS['border']}",
            "borderLeft":      f"3px solid {accent}",
            "borderRadius":    "10px",
            "padding":         "14px 16px",
        },
        children=[
            html.Div(
                node_data["id"],
                style={"fontSize": "32px", "fontWeight": "800", "color": accent, "lineHeight": "1"},
            ),
            html.Div(
                type_label,
                style={"fontSize": "10px", "color": accent, "fontWeight": "700",
                       "textTransform": "uppercase", "letterSpacing": "1.2px", "marginBottom": "10px"},
            ),
            html.Div(
                node_data["full_name"],
                style={"fontSize": "12px", "color": COLORS["text"], "fontStyle": "italic",
                       "marginBottom": "14px", "lineHeight": "1.4"},
            ),
            html.Div(_info_row("Ciudad",       node_data["city"]),     style={"marginBottom": "6px"}),
            html.Div(_info_row("País",         node_data["country"]),  style={"marginBottom": "6px"}),
            html.Div(_info_row("Zona horaria", node_data["timezone"]), style={"marginBottom": "10px"}),
            html.Div(
                html.Span("Aerolíneas", style={"fontWeight": "700", "fontSize": "12px", "color": COLORS["text"]}),
                style={"marginBottom": "4px"},
            ),
            html.Div(
                node_data["airlines"],
                style={"fontSize": "11px", "color": COLORS["text_dim"], "lineHeight": "1.6"},
            ),
        ],
    )


def _info_row(label, value):
    # Returns a label + value pair as inline spans
    return [
        html.Span(f"{label}: ", style={"fontWeight": "700", "fontSize": "12px", "color": COLORS["text"]}),
        html.Span(value,        style={"fontSize": "12px", "color": COLORS["text_dim"]}),
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  R2.2 / R2.3 — Itinerary planning callbacks
# ══════════════════════════════════════════════════════════════════════════════

# ── Helper: renders a service result (proposal-style) as HTML ────────────────
def _result_card(result, accent_color):
    if not result.get("success"):
        return html.Div(
            html.Span(f"⚠ {result.get('error', 'Unknown error')}"),
            style={"color": COLORS["error"], "fontSize": "12px", "padding": "8px 0"},
        )
    if "note" in result:
        return html.Div(
            html.Span(result["note"]),
            style={"color": COLORS["text_dim"], "fontSize": "12px", "padding": "8px 0",
                    "fontStyle": "italic"},
        )

    path_str = " \u2192 ".join(result["path"])
    seg_rows = []
    for s in result["segments"]:
        seg_rows.append(html.Tr([
            html.Td(f"{s['origin']} \u2192 {s['destination']}",
                    style={"padding": "2px 6px", "fontSize": "11px"}),
            html.Td(s["aircraft"], style={"padding": "2px 6px", "fontSize": "11px"}),
            html.Td(f"${s['cost']}", style={"padding": "2px 6px", "fontSize": "11px",
                                             "textAlign": "right"}),
            html.Td(f"{s['time_min']} min", style={"padding": "2px 6px", "fontSize": "11px",
                                                    "textAlign": "right"}),
        ]))

    return html.Div([
        html.Div(f"Destinos visitados: {result['destinations_visited']}",
                 style={"fontWeight": "700", "fontSize": "13px", "color": accent_color,
                        "marginBottom": "4px"}),
        html.Div([
            html.Span(f"Costo total: ${result['total_cost']}",
                      style={"marginRight": "16px", "fontSize": "12px"}),
            html.Span(f"Tiempo total: {result['total_time_hours']} h",
                      style={"fontSize": "12px"}),
        ], style={"marginBottom": "6px"}),
        html.Div(f"Aeronaves: {', '.join(result['aircraft_used'])}",
                 style={"fontSize": "11px", "color": COLORS["text_dim"],
                        "marginBottom": "8px"}),
        html.Div(f"Ruta: {path_str}",
                 style={"fontSize": "11px", "color": COLORS["text_dim"],
                        "marginBottom": "8px", "wordBreak": "break-all"}),
        html.Table([
            html.Thead(html.Tr([
                html.Th("Segmento", style={"padding": "2px 6px", "fontSize": "11px",
                                           "textAlign": "left", "color": COLORS["text_dim"]}),
                html.Th("Aeronave", style={"padding": "2px 6px", "fontSize": "11px",
                                           "textAlign": "left", "color": COLORS["text_dim"]}),
                html.Th("Costo", style={"padding": "2px 6px", "fontSize": "11px",
                                        "textAlign": "right", "color": COLORS["text_dim"]}),
                html.Th("Tiempo", style={"padding": "2px 6px", "fontSize": "11px",
                                         "textAlign": "right", "color": COLORS["text_dim"]}),
            ])), html.Tbody(seg_rows)],
            style={"width": "100%", "borderCollapse": "collapse",
                   "border": f"1px solid {COLORS['border']}",
                   "borderRadius": "6px", "overflow": "hidden"},
        ),
    ])


# ── Helper: renders manual search results as HTML ──────────────────────────
def _search_results_card(results):
    cards = []
    for r in results:
        if not r["success"]:
            cards.append(html.Div([
                html.Div(r["criterion"].upper(),
                         style={"fontWeight": "700", "fontSize": "12px", "color": COLORS["error"],
                                "marginBottom": "4px"}),
                html.Div(r.get("error", ""), style={"fontSize": "11px", "color": COLORS["text_dim"]}),
            ], style={"marginBottom": "12px", "padding": "8px",
                       "borderLeft": f"3px solid {COLORS['error']}",
                       "backgroundColor": COLORS["bg_panel_2"],
                       "borderRadius": "6px"}))
            continue
        path_str = " \u2192 ".join(r["path"])
        seg_rows = []
        for s in r["segments"]:
            seg_rows.append(html.Tr([
                html.Td(f"{s['origin']} \u2192 {s['destination']}",
                        style={"padding": "2px 6px", "fontSize": "11px"}),
                html.Td(s["aircraft"], style={"padding": "2px 6px", "fontSize": "11px"}),
                html.Td(f"{s['distance_km']} km",
                        style={"padding": "2px 6px", "fontSize": "11px", "textAlign": "right"}),
                html.Td(str(s["weight"]),
                        style={"padding": "2px 6px", "fontSize": "11px", "textAlign": "right"}),
            ]))
        cards.append(html.Div([
            html.Div(r["criterion"].upper(),
                     style={"fontWeight": "700", "fontSize": "12px", "color": COLORS["highlight"],
                            "marginBottom": "4px"}),
            html.Div(f"Ruta: {path_str}",
                     style={"fontSize": "11px", "color": COLORS["text_dim"],
                            "marginBottom": "6px", "wordBreak": "break-all"}),
            html.Div(f"Peso total: {r['total_weight']}",
                     style={"fontSize": "12px", "fontWeight": "600", "marginBottom": "6px"}),
            html.Table(
                [html.Thead(html.Tr([
                    html.Th("Segmento", style={"padding": "2px 6px", "fontSize": "11px",
                                               "textAlign": "left", "color": COLORS["text_dim"]}),
                    html.Th("Aeronave", style={"padding": "2px 6px", "fontSize": "11px",
                                               "textAlign": "left", "color": COLORS["text_dim"]}),
                    html.Th("Dist.", style={"padding": "2px 6px", "fontSize": "11px",
                                            "textAlign": "right", "color": COLORS["text_dim"]}),
                    html.Th("Peso", style={"padding": "2px 6px", "fontSize": "11px",
                                           "textAlign": "right", "color": COLORS["text_dim"]}),
                ])), html.Tbody(seg_rows)],
                style={"width": "100%", "borderCollapse": "collapse",
                       "border": f"1px solid {COLORS['border']}",
                       "borderRadius": "6px", "overflow": "hidden"},
            ),
        ], style={"marginBottom": "12px", "padding": "8px",
                   "borderLeft": f"3px solid {COLORS['highlight']}",
                   "backgroundColor": COLORS["bg_panel_2"],
                   "borderRadius": "6px"}))
    return html.Div(cards)





# ──────────────────────────────────────────────────────────────────────────────
#  Callback: Proposal A — Max destinations by budget
# ──────────────────────────────────────────────────────────────────────────────
@app.callback(
    Output("budget-result",   "children"),
    Input("budget-btn",       "n_clicks"),
    State("budget-origin",    "value"),
    State("budget-amount",    "value"),
    State("budget-time",      "value"),
    State("budget-aircraft",  "value"),
    State("graph-data",       "data"),
)
def calc_budget_route(n, origin, amount, time_limit, aircraft, graph_data):
    if not n or not origin or not amount:
        raise dash.exceptions.PreventUpdate
    g = _build_graph_from_store(graph_data)
    if g is None:
        return html.Span("No hay datos de red.", style={"color": COLORS["error"]})
    pref = set(aircraft) if aircraft else set()
    t = float(time_limit) if time_limit else float("inf")
    result = propose_max_coverage_by_budget(g, origin.upper(), float(amount), t, pref)
    return _result_card(result, COLORS["hub"])


# ──────────────────────────────────────────────────────────────────────────────
#  Callback: Proposal B — Max destinations by time
# ──────────────────────────────────────────────────────────────────────────────
@app.callback(
    Output("time-result",     "children"),
    Input("time-btn",         "n_clicks"),
    State("time-origin",      "value"),
    State("time-limit",       "value"),
    State("time-budget",      "value"),
    State("time-aircraft",    "value"),
    State("graph-data",       "data"),
)
def calc_time_route(n, origin, limit, budget, aircraft, graph_data):
    if not n or not origin or not limit:
        raise dash.exceptions.PreventUpdate
    g = _build_graph_from_store(graph_data)
    if g is None:
        return html.Span("No hay datos de red.", style={"color": COLORS["error"]})
    pref = set(aircraft) if aircraft else set()
    b = float(budget) if budget else float("inf")
    result = propose_max_coverage_by_time(g, origin.upper(), float(limit), b, pref)
    return _result_card(result, COLORS["secondary"])


# ──────────────────────────────────────────────────────────────────────────────
#  Callback: Manual route search (Dijkstra multi-criteria)
# ──────────────────────────────────────────────────────────────────────────────
@app.callback(
    Output("search-result",     "children"),
    Input("search-btn",         "n_clicks"),
    State("search-origin",      "value"),
    State("search-dest",        "value"),
    State("search-criteria",    "value"),
    State("search-secondary",   "value"),
    State("search-aircraft",    "value"),
    State("graph-data",         "data"),
)
def calc_manual_search(n, origin, dest, criteria, include_sec, aircraft, graph_data):
    if not n or not origin or not dest or not criteria:
        raise dash.exceptions.PreventUpdate
    g = _build_graph_from_store(graph_data)
    if g is None:
        return html.Span("No hay datos de red.", style={"color": COLORS["error"]})
    pref = set(aircraft) if aircraft else set()
    sec = include_sec if include_sec is not None else True
    results = find_best_routes(g, origin.upper(), dest.upper(), criteria, sec, pref)
    return _search_results_card(results)


# ──────────────────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
#  Dynamic Itinerary (R2.3) — multi-callback state machine
# ──────────────────────────────────────────────────────────────────────────────

def _get_available_flights_for(vertex, visited, aircraft_config, budget, free_km=0.0, total_km=0.0):
    from services.dynamicService import _edge_cost, _edge_time
    options = []
    for edge in vertex.adjacencies:
        dest_id = edge.destination_vertex.id
        if dest_id in visited:
            continue

        new_total = total_km + edge.distance_km
        new_free = free_km + (edge.distance_km if edge.base_cost == 0 else 0)
        if edge.base_cost == 0 and total_km > 0 and new_free > 0.20 * new_total:
            continue

        for aircraft in edge.aircraft:
            cost = _edge_cost(edge, aircraft, aircraft_config)
            if cost <= budget:
                options.append({
                    "label": f"{dest_id}  |  {aircraft}  |  ${cost:.2f}  |  {_edge_time(edge, aircraft, aircraft_config):.0f} min",
                    "value": json.dumps({
                        "dest": dest_id,
                        "aircraft": aircraft,
                        "cost": round(cost, 2),
                        "time_min": round(_edge_time(edge, aircraft, aircraft_config), 2),
                        "distance_km": edge.distance_km,
                        "origin": vertex.id,
                        "base_cost": edge.base_cost,
                    }),
                })
    return options


def _get_jobs_for(vertex):
    if not vertex or not vertex.jobs:
        return []
    return [
        {"label": f"{j['name']}  (${j['hourlyRate']}/h, max {j['maxHours']}h)",
         "value": json.dumps(j)}
        for j in vertex.jobs
    ]


def _dynamic_display_state(state):
    if state is None:
        return html.P("Presiona 'Iniciar viaje' para comenzar.",
                      style={"color": COLORS["text_dim"], "fontSize": "12px"})
    segs = state.get("segments", [])
    parts = []
    if segs:
        path = [s["origin"] for s in segs] + [segs[-1]["destination"]]
        parts.append(html.Div(f"Ruta: {' → '.join(path)}",
                     style={"fontSize": "11px", "color": COLORS["text_dim"],
                            "marginBottom": "4px", "wordBreak": "break-all"}))
    parts.append(html.Div(f"Presupuesto restante: ${state['budget']:.2f}",
                 style={"fontSize": "12px", "fontWeight": "600", "marginBottom": "2px"}))
    parts.append(html.Div(f"Tiempo transcurrido: {state['time_min']:.0f} min",
                 style={"fontSize": "11px", "color": COLORS["text_dim"], "marginBottom": "2px"}))
    if state.get("money_earned", 0) > 0:
        parts.append(html.Div(f"Ganado en trabajos: ${state['money_earned']:.2f}",
                     style={"fontSize": "11px", "color": COLORS["ok"]}))
    return html.Div(parts)


def _dynamic_summary(state):
    segs = state.get("segments", [])
    path = [s["origin"] for s in segs] + [segs[-1]["destination"]] if segs else [state["current_id"]]
    return html.Div([
        html.Div("✈ Viaje completo", style={"fontWeight": "700", "fontSize": "14px",
                                            "color": COLORS["ok"], "marginBottom": "8px"}),
        html.Div(f"Destinos visitados: {len(segs)}",
                 style={"fontSize": "12px", "marginBottom": "4px"}),
        html.Div(f"Costo total: ${sum(s['cost'] for s in segs):.2f}",
                 style={"fontSize": "12px", "marginBottom": "4px"}),
        html.Div(f"Tiempo total: {state['time_min']:.0f} min",
                 style={"fontSize": "12px", "marginBottom": "4px"}),
        html.Div(f"Ganado en trabajos: ${state.get('money_earned', 0):.2f}",
                 style={"fontSize": "12px", "marginBottom": "4px", "color": COLORS["ok"]}),
        html.Div(f"Aeronaves usadas: {', '.join(state.get('aircraft_used', []))}",
                 style={"fontSize": "11px", "color": COLORS["text_dim"], "marginBottom": "4px"}),
        html.Div(f"Ruta: {' → '.join(path)}",
                 style={"fontSize": "11px", "color": COLORS["text_dim"], "wordBreak": "break-all"}),
    ])


# ── Callback 1: Start journey ──────────────────────────────────────────────
@app.callback(
    Output("dynamic-state",      "data"),
    Output("dynamic-display",    "children"),
    Output("dynamic-controls",   "style"),
    Output("dynamic-flight-choice", "options"),
    Output("dynamic-flight-choice", "value"),
    Output("dynamic-origin-label", "children"),
    Input("dynamic-btn",         "n_clicks"),
    State("dynamic-origin",      "value"),
    State("dynamic-budget",      "value"),
    State("graph-data",          "data"),
)
def dynamic_start(btn, origin, budget, graph_data):
    if not origin or not budget:
        return (None,
                html.Span("Completa origen y presupuesto.", style={"color": COLORS["error"]}),
                {"display": "none"}, [], None, "Selecciona vuelo:")

    state = {
        "current_id": origin.strip().upper(),
        "budget": float(budget),
        "time_min": 0.0,
        "visited": [origin.strip().upper()],
        "segments": [],
        "aircraft_used": [],
        "money_earned": 0.0,
        "free_km": 0.0,
        "total_km": 0.0,
    }

    g = _build_graph_from_store(graph_data)
    if g is None:
        return None, html.Span("No hay datos de red.", style={"color": COLORS["error"]}), {"display": "none"}, [], None, "Selecciona vuelo:"

    vertex = g.get_vertex(state["current_id"])
    if vertex is None:
        return None, html.Span(f"Aeropuerto desconocido: {state['current_id']}",
                               style={"color": COLORS["error"]}), {"display": "none"}, [], None, "Selecciona vuelo:"

    options = _get_available_flights_for(vertex, set(state["visited"]), g.aircraft_config, state["budget"],
                                         state["free_km"], state["total_km"])
    if not options:
        return (None,
                html.Div([_dynamic_display_state(state),
                         html.Div("No hay vuelos disponibles desde el origen.",
                                  style={"color": COLORS["text_dim"], "fontSize": "12px", "marginTop": "8px"})]),
                {"display": "none"}, [], None,
                f"Vuelos desde {vertex.city} ({vertex.id}):")

    return (state, _dynamic_display_state(state),
            {"display": "block", "padding": "0"}, options, None,
            f"Vuelos desde {vertex.city} ({vertex.id}):")


# ── Callback 2: Fly ────────────────────────────────────────────────────────
@app.callback(
    Output("dynamic-state",       "data",  allow_duplicate=True),
    Output("dynamic-display",     "children", allow_duplicate=True),
    Output("dynamic-flight-choice", "options", allow_duplicate=True),
    Output("dynamic-flight-choice", "value",  allow_duplicate=True),
    Output("dynamic-job-choice",  "options"),
    Output("dynamic-job-choice",  "value"),
    Output("dynamic-job-section", "style", allow_duplicate=True),
    Output("dynamic-status",      "children"),
    Input("dynamic-fly-btn",      "n_clicks"),
    State("dynamic-flight-choice", "value"),
    State("dynamic-state",        "data"),
    State("graph-data",           "data"),
    prevent_initial_call=True,
)
def dynamic_fly(btn, flight_json, state, graph_data):
    if not flight_json or state is None:
        raise dash.exceptions.PreventUpdate

    opt = json.loads(flight_json)
    g = _build_graph_from_store(graph_data)
    if g is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, [], None, dash.no_update, html.Span("Error: no hay datos de red.", style={"color": COLORS["error"]})

    # Process flight
    state["budget"] -= opt["cost"]
    state["time_min"] += opt["time_min"]
    state["visited"].append(opt["dest"])
    state["current_id"] = opt["dest"]
    state["aircraft_used"].append(opt["aircraft"])
    state["total_km"] += opt["distance_km"]
    if opt.get("base_cost", 1) == 0:
        state["free_km"] += opt["distance_km"]
    state["segments"].append({
        "origin": opt["origin"],
        "destination": opt["dest"],
        "aircraft": opt["aircraft"],
        "distance_km": opt["distance_km"],
        "cost": opt["cost"],
        "time_min": opt["time_min"],
    })

    # Get jobs at destination
    dest_v = g.get_vertex(opt["dest"])
    jobs = _get_jobs_for(dest_v)

    status = html.Div([
        html.Div(f"✅ {opt['origin']} → {opt['dest']} completado",
                 style={"fontWeight": "600", "fontSize": "12px", "color": COLORS["ok"],
                        "marginBottom": "4px"}),
        html.Div(f"Aeronave: {opt['aircraft']}  |  Costo: ${opt['cost']}  |  Tiempo: {opt['time_min']} min",
                 style={"fontSize": "11px", "marginBottom": "2px"}),
        html.Div(f"Presupuesto restante: ${state['budget']:.2f}",
                 style={"fontSize": "11px", "color": COLORS["text_dim"]}),
    ])

    return state, _dynamic_display_state(state), [], None, jobs, None, {"display": "block"}, status


# ── Callback 3: Work ───────────────────────────────────────────────────────
@app.callback(
    Output("dynamic-state",      "data",  allow_duplicate=True),
    Output("dynamic-status",     "children", allow_duplicate=True),
    Input("dynamic-work-btn",    "n_clicks"),
    State("dynamic-job-choice",  "value"),
    State("dynamic-hours",       "value"),
    State("dynamic-state",       "data"),
    prevent_initial_call=True,
)
def dynamic_work(btn, job_json, hours, state):
    if not job_json or not hours or state is None:
        raise dash.exceptions.PreventUpdate

    job = json.loads(job_json)
    hours = float(hours)
    max_h = job.get("maxHours", 0)
    if hours > max_h:
        return state, html.Span(f"Máximo {max_h} horas. No se trabajó.",
                                style={"color": COLORS["error"], "fontSize": "11px"})

    earned = hours * job["hourlyRate"]
    state["budget"] += earned
    state["money_earned"] = state.get("money_earned", 0) + earned

    return state, html.Div([
        html.Div(f"💰 Trabajaste {hours}h como {job['name']} y ganaste ${earned:.2f}",
                 style={"fontWeight": "600", "fontSize": "12px", "color": COLORS["ok"],
                        "marginBottom": "2px"}),
        html.Div(f"Nuevo presupuesto: ${state['budget']:.2f}",
                 style={"fontSize": "11px", "color": COLORS["text_dim"]}),
    ])


# ── Callback 4: Skip / advance ────────────────────────────────────────────
@app.callback(
    Output("dynamic-display",       "children", allow_duplicate=True),
    Output("dynamic-flight-choice", "options",  allow_duplicate=True),
    Output("dynamic-flight-choice", "value",    allow_duplicate=True),
    Output("dynamic-job-choice",    "options",  allow_duplicate=True),
    Output("dynamic-job-choice",    "value",    allow_duplicate=True),
    Output("dynamic-hours",         "value"),
    Output("dynamic-job-section",   "style", allow_duplicate=True),
    Output("dynamic-origin-label",  "children", allow_duplicate=True),
    Output("dynamic-status",        "children", allow_duplicate=True),
    Input("dynamic-skip-btn",       "n_clicks"),
    State("dynamic-state",          "data"),
    State("graph-data",             "data"),
    prevent_initial_call=True,
)
def dynamic_skip(btn, state, graph_data):
    if state is None:
        raise dash.exceptions.PreventUpdate

    g = _build_graph_from_store(graph_data)
    if g is None:
        return (html.Span("No hay datos de red.", style={"color": COLORS["error"]}),
                [], None, [], None, None, {"display": "none"}, "")

    vertex = g.get_vertex(state["current_id"])
    if vertex is None:
        return (html.Span(f"Aeropuerto desconocido: {state['current_id']}",
                          style={"color": COLORS["error"]}), [], None, [], None, None, {"display": "none"}, "")

    options = _get_available_flights_for(vertex, set(state["visited"]), g.aircraft_config, state["budget"],
                                         state.get("free_km", 0.0), state.get("total_km", 0.0))
    if not options:
        return (_dynamic_summary(state), [], None, [], None, None, {"display": "none"}, "")

    # Show "Nuevo origen" banner with next routes
    nuevo_origen = html.Div([
        html.Div(f"Ubicación Actual: {state['current_id']}",
                 style={"fontWeight": "700", "fontSize": "13px", "color": COLORS["hub"],
                        "marginTop": "8px", "marginBottom": "4px"}),
        html.Div("Selecciona tu siguiente vuelo:",
                 style={"fontSize": "11px", "color": COLORS["text_dim"], "marginBottom": "4px"}),
    ])
    display = html.Div([_dynamic_display_state(state), nuevo_origen])

    return (display, options, None, [], None, None, {"display": "none"},
            html.Span("Vuelos disponibles.", style={"color": COLORS["text_dim"], "fontSize": "11px"}))


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("SkyRoute Planner iniciando - http://localhost:8050 ")
    app.run(debug=True)

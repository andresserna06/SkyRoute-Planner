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
            ],
        ),

        # ── Body: sidebar + graph ─────────────────────────────────────────────
        html.Div(
            style={"display": "flex", "flex": 1, "overflow": "hidden"},
            children=[

                # Left sidebar
                html.Div(
                    style={
                        "width":           "270px",
                        "minWidth":        "270px",
                        "backgroundColor": COLORS["bg_panel"],
                        "borderRight":     f"1px solid {COLORS['border']}",
                        "padding":         "22px 18px",
                        "display":         "flex",
                        "flexDirection":   "column",
                        "gap":             "20px",
                        "overflowY":       "auto",
                    },
                    children=[

                        # ── File upload ───────────────────────────────────────
                        html.Div([
                            html.H4("Cargar red aérea", style=SECTION_TITLE),
                            dcc.Upload(
                                id="upload-json",
                                children=html.Div([
                                    html.Div("⤓", style={"fontSize": "22px",
                                                          "color": COLORS["secondary"],
                                                          "marginBottom": "4px"}),
                                    "Arrastra el archivo JSON aquí",
                                    html.Br(),
                                    html.A(
                                        "o haz clic para seleccionarlo",
                                        style={"color": COLORS["secondary"],
                                               "textDecoration": "underline", "cursor": "pointer"},
                                    ),
                                ]),
                                style={
                                    "width":           "100%",
                                    "padding":         "18px 10px",
                                    "borderWidth":     "1.5px",
                                    "borderStyle":     "dashed",
                                    "borderRadius":    "10px",
                                    "borderColor":     COLORS["border"],
                                    "textAlign":       "center",
                                    "fontSize":        "12px",
                                    "color":           COLORS["text_dim"],
                                    "backgroundColor": COLORS["bg_panel_2"],
                                    "cursor":          "pointer",
                                    "boxSizing":       "border-box",
                                    "lineHeight":      "1.6",
                                },
                                accept=".json",
                            ),
                            html.Div(id="upload-status", style={"marginTop": "8px", "minHeight": "16px"}),
                        ]),

                        # ── Layout selector ───────────────────────────────────
                        html.Div([
                            html.H4("Disposición del grafo", style=SECTION_TITLE),
                            dcc.Dropdown(
                                id="layout-dropdown",
                                options=[
                                    {"label": "Orgánica (fuerzas)",   "value": "cose"},
                                    {"label": "Concéntrica (hubs al centro)", "value": "concentric"},
                                    {"label": "Circular",             "value": "circle"},
                                ],
                                value="cose",
                                clearable=False,
                                style={"fontSize": "13px", "color": "#1a2440"},
                            ),
                        ]),

                        html.Hr(style={"margin": "0", "border": "none",
                                       "borderTop": f"1px solid {COLORS['border']}"}),

                        # ── Legend ────────────────────────────────────────────
                        html.Div([
                            html.H4("Leyenda", style=SECTION_TITLE),
                            legend_row(
                                {"width": "20px", "height": "20px", "borderRadius": "50%",
                                 "backgroundColor": COLORS["hub"],
                                 "border": f"2px solid {COLORS['hub_border']}"},
                                "Aeropuerto hub",
                            ),
                            legend_row(
                                {"width": "14px", "height": "14px", "borderRadius": "50%",
                                 "backgroundColor": COLORS["secondary"],
                                 "border": f"2px solid {COLORS['sec_border']}"},
                                "Aeropuerto secundario",
                            ),
                            legend_row(
                                {"width": "28px", "height": "2px", "backgroundColor": COLORS["route"]},
                                "Ruta regular",
                            ),
                            legend_row(
                                {"width": "28px", "height": "0", "borderTop": f"2px dashed {COLORS['subsidized']}"},
                                "Ruta subsidiada",
                            ),
                        ]),

                        html.Hr(style={"margin": "0", "border": "none",
                                       "borderTop": f"1px solid {COLORS['border']}"}),

                        # ── Aircraft key ──────────────────────────────────────
                        html.Div([
                            html.H4("Tipos de aeronave", style=SECTION_TITLE),
                            html.Div("C  ·  Avión Comercial", style={"fontSize": "12px", "color": COLORS["text_dim"], "marginBottom": "6px"}),
                            html.Div("R  ·  Jet Regional",    style={"fontSize": "12px", "color": COLORS["text_dim"], "marginBottom": "6px"}),
                            html.Div("H  ·  Avión de Hélice", style={"fontSize": "12px", "color": COLORS["text_dim"]}),
                        ]),

                        html.Hr(style={"margin": "0", "border": "none",
                                       "borderTop": f"1px solid {COLORS['border']}"}),

                        # ── Reset button: clears selection, shows the full graph ──
                        html.Button(
                            "↺  Ver todo el grafo",
                            id="clear-selection",
                            n_clicks=0,
                            style={
                                "width":           "100%",
                                "padding":         "9px 12px",
                                "backgroundColor": COLORS["bg_panel_2"],
                                "color":           COLORS["text"],
                                "border":          f"1px solid {COLORS['border']}",
                                "borderRadius":    "8px",
                                "fontSize":        "12px",
                                "fontWeight":      "600",
                                "fontFamily":      "Inter, Segoe UI, sans-serif",
                                "cursor":          "pointer",
                            },
                        ),

                        # ── Airport detail card (filled on node click) ────────
                        html.Div(id="airport-info", children=_placeholder()),
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
        return (elems, str(n_airports), str(n_routes), str(n_hubs), status)

    except Exception as e:
        status = html.Span(
            f"Error al cargar el archivo: {e}",
            style={"color": COLORS["error"], "fontSize": "11px"},
        )
        return [], "—", "—", "—", status


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


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("SkyRoute Planner iniciando - http://localhost:8050 ")
    app.run(debug=True)

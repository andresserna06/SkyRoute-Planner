# ── ITEM 2.1 — Full Dash layout: header, upload, legend, Cytoscape graph, sidebar tabs ──

from dash import dcc, html
import dash_cytoscape as cyto

from frontend.config import (
    COLORS, LAYOUTS, SECTION_TITLE, CARD, BTN_PRIMARY, BTN_SUCCESS,
    BTN_DANGER, BTN_NEUTRAL, LABEL, INPUT_STYLE, DROPDOWN_STYLE,
    SHOW, HIDE, stat_chip, _placeholder, legend_row,
)
from frontend.graph_helpers import base_stylesheet


def build_layout():
    return html.Div(
        style={"fontFamily": "Inter, Segoe UI, Arial, sans-serif", "backgroundColor": COLORS["bg_canvas"],
               "height": "100vh", "display": "flex", "flexDirection": "column", "overflow": "hidden"},
        children=[

            dcc.Store(id="graph-store"),
            dcc.Store(id="journey-store"),
            dcc.Store(id="route-highlight-store"),
            dcc.Store(id="original-graph-store"),

            html.Div(style={"flexShrink": 0}, children=[
                html.Div(style={
                    "backgroundColor": COLORS["bg_panel"], "padding": "0 26px", "height": "68px",
                    "display": "flex", "alignItems": "center", "gap": "14px",
                    "boxShadow": "0 2px 8px rgba(0,0,0,0.05)",
                }, children=[
                    html.Div("✈", style={
                        "width": "40px", "height": "40px", "borderRadius": "50%",
                        "background": f"linear-gradient(135deg, {COLORS['hub']}, #f97316)",
                        "color": "#ffffff", "display": "flex", "alignItems": "center",
                        "justifyContent": "center", "fontSize": "18px", "transform": "rotate(-45deg)",
                        "boxShadow": "0 3px 8px rgba(234,88,12,0.35)", "flexShrink": 0,
                    }),
                    html.Div([
                        html.H1("SkyRoute Planner", style={"color": COLORS["text"], "margin": 0,
                                "fontSize": "21px", "fontWeight": "800", "letterSpacing": "0.3px", "lineHeight": "1.1"}),
                        html.Span("Red Aérea Latinoamericana", style={"color": COLORS["text_dim"], "fontSize": "12px", "fontWeight": "500"}),
                    ]),
                    html.Div(style={"marginLeft": "auto", "display": "flex", "gap": "10px"}, children=[
                        stat_chip(COLORS["secondary"], "stat-airports", "aeropuertos"),
                        stat_chip(COLORS["route"],     "stat-routes",   "rutas"),
                        stat_chip(COLORS["hub"],        "stat-hubs",     "hubs"),
                    ]),
                ]),
                html.Div(style={"height": "3px", "background": f"linear-gradient(90deg, {COLORS['hub']}, {COLORS['highlight']}, {COLORS['secondary']})"}),
            ]),

            html.Div(style={"display": "flex", "flex": 1, "overflow": "hidden"}, children=[

                html.Div(style={
                    "width": "250px", "minWidth": "250px", "backgroundColor": COLORS["bg_panel"],
                    "borderRight": f"1px solid {COLORS['border']}", "padding": "20px 16px",
                    "display": "flex", "flexDirection": "column", "gap": "18px", "overflowY": "auto",
                }, children=[
                    html.Div([
                        html.H4("Cargar red aérea", style=SECTION_TITLE),
                        dcc.Upload(id="upload-json", accept=".json",
                            children=html.Div([
                                html.Div("⤓", style={"fontSize": "22px", "color": COLORS["secondary"], "marginBottom": "4px"}),
                                "Arrastra el JSON aquí", html.Br(),
                                html.A("o haz clic para seleccionarlo",
                                       style={"color": COLORS["secondary"], "textDecoration": "underline", "cursor": "pointer"}),
                            ]),
                            style={
                                "width": "100%", "padding": "16px 10px", "borderWidth": "1.5px",
                                "borderStyle": "dashed", "borderRadius": "10px", "borderColor": COLORS["border"],
                                "textAlign": "center", "fontSize": "12px", "color": COLORS["text_dim"],
                                "backgroundColor": COLORS["bg_panel_2"], "cursor": "pointer",
                                "boxSizing": "border-box", "lineHeight": "1.6",
                            }),
                        html.Div(id="upload-status", style={"marginTop": "8px", "minHeight": "16px"}),
                    ]),
                    html.Div([
                        html.H4("Disposición del grafo", style=SECTION_TITLE),
                        dcc.Dropdown(id="layout-dropdown",
                            options=[{"label": "Orgánica (fuerzas)", "value": "cose"},
                                     {"label": "Concéntrica", "value": "concentric"},
                                     {"label": "Circular", "value": "circle"}],
                            value="cose", clearable=False, style={"fontSize": "13px", "color": "#1a2440"}),
                    ]),
                    html.Hr(style={"margin": "0", "border": "none", "borderTop": f"1px solid {COLORS['border']}"}),
                    html.Div([
                        html.H4("Leyenda", style=SECTION_TITLE),
                        legend_row({"width": "20px", "height": "20px", "borderRadius": "50%",
                                    "backgroundColor": COLORS["hub"], "border": f"2px solid {COLORS['hub_border']}"}, "Aeropuerto hub"),
                        legend_row({"width": "14px", "height": "14px", "borderRadius": "50%",
                                    "backgroundColor": COLORS["secondary"], "border": f"2px solid {COLORS['sec_border']}"}, "Aeropuerto secundario"),
                        legend_row({"width": "28px", "height": "2px", "backgroundColor": COLORS["route"]}, "Ruta regular"),
                        legend_row({"width": "28px", "height": "0", "borderTop": f"2px dashed {COLORS['subsidized']}"}, "Ruta subsidiada"),
                        legend_row({"width": "28px", "height": "2px", "backgroundColor": COLORS["highlight"]}, "Ruta resaltada"),
                    ]),
                    html.Hr(style={"margin": "0", "border": "none", "borderTop": f"1px solid {COLORS['border']}"}),
                    html.Div(style={"display": "flex", "flexDirection": "column", "gap": "6px"}, children=[
                        html.H4("Config. de aeronaves", style=SECTION_TITLE),
                        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 55px 55px",
                                        "gap": "3px", "fontSize": "10px", "fontWeight": "700",
                                        "color": COLORS["text_dim"], "marginBottom": "2px"}, children=[
                            html.Span("Aeronave"),
                            html.Span("$/km", style={"textAlign": "right"}),
                            html.Span("min/km", style={"textAlign": "right"}),
                        ]),
                        html.Div(id="aircraft-config-editor", children=[
                            *[
                                html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 55px 55px",
                                                "gap": "3px", "alignItems": "center"}, children=[
                                    html.Span(name, style={"fontSize": "11px", "color": COLORS["text"],
                                                           "fontWeight": "500", "whiteSpace": "nowrap"}),
                                    dcc.Input(id={"type": "aircraft-cost", "index": key},
                                              type="number", step="0.01", min=0,
                                              style={**INPUT_STYLE, "padding": "2px 4px", "fontSize": "11px",
                                                     "textAlign": "right", "width": "55px"}),
                                    dcc.Input(id={"type": "aircraft-time", "index": key},
                                              type="number", step="0.01", min=0,
                                              style={**INPUT_STYLE, "padding": "2px 4px", "fontSize": "11px",
                                                     "textAlign": "right", "width": "55px"}),
                                ]) for key, name in [
                                    ("comercial", "Comercial"),
                                    ("regional", "Regional"),
                                    ("helice", "Hélice"),
                                ]
                            ],
                        ]),
                        html.Div(style={"display": "flex", "gap": "6px", "marginTop": "4px"}, children=[
                            html.Button("Aplicar", id="aircraft-apply-btn", n_clicks=0,
                                        style={**BTN_PRIMARY, "flex": 1, "padding": "5px 8px", "fontSize": "11px"}),
                            html.Button("Restaurar", id="aircraft-restore-btn", n_clicks=0,
                                        style={**BTN_NEUTRAL, "flex": 1, "padding": "5px 8px", "fontSize": "11px"}),
                        ]),
                        html.Div(id="aircraft-editor-msg", style={"fontSize": "10px", "color": COLORS["text_dim"],
                                                                   "minHeight": "14px"}),
                    ]),
                    html.Hr(style={"margin": "0", "border": "none", "borderTop": f"1px solid {COLORS['border']}"}),
                    html.Button("↺  Ver todo el grafo", id="clear-selection", n_clicks=0, style={
                        "width": "100%", "padding": "9px 12px", "backgroundColor": COLORS["bg_panel_2"],
                        "color": COLORS["text"], "border": f"1px solid {COLORS['border']}",
                        "borderRadius": "8px", "fontSize": "12px", "fontWeight": "600",
                        "fontFamily": "Inter, Segoe UI, sans-serif", "cursor": "pointer",
                    }),
                    html.Div(id="airport-info", children=_placeholder()),
                ]),

                cyto.Cytoscape(
                    id="network-graph", elements=[], layout=LAYOUTS["cose"],
                    stylesheet=base_stylesheet(),
                    style={"flex": 1, "height": "100%", "backgroundColor": COLORS["bg_canvas"]},
                    minZoom=0.15, maxZoom=4.0, userZoomingEnabled=True, userPanningEnabled=True,
                ),

                html.Div(style={
                    "width": "330px", "minWidth": "330px", "backgroundColor": COLORS["bg_panel"],
                    "borderLeft": f"1px solid {COLORS['border']}", "overflow": "hidden",
                    "display": "flex", "flexDirection": "column", "height": "100%",
                }, children=[
                    dcc.Tabs(id="right-tabs", value="route",
                        style={"borderBottom": f"1px solid {COLORS['border']}", "flexShrink": 0},
                        colors={"border": COLORS["border"], "primary": COLORS["secondary"], "background": COLORS["bg_panel"]},
                        children=[

                            dcc.Tab(label="Buscar Ruta", value="route",
                                style={"fontSize": "12px", "fontWeight": "600", "padding": "8px 8px"},
                                selected_style={"fontSize": "12px", "fontWeight": "700", "padding": "8px 8px",
                                                "borderTop": f"2px solid {COLORS['secondary']}", "color": COLORS["secondary"]},
                                children=[
                                    html.Div(style={"padding": "16px", "overflowY": "auto", "maxHeight": "calc(100vh - 120px)"}, children=[
                                        html.Span("Origen", style=LABEL),
                                        dcc.Dropdown(id="route-origin", placeholder="Selecciona origen...",
                                                     style=DROPDOWN_STYLE, clearable=False),
                                        html.Span("Destino", style=LABEL),
                                        dcc.Dropdown(id="route-dest", placeholder="Selecciona destino...",
                                                     style=DROPDOWN_STYLE, clearable=False),
                                        html.Span("Criterio(s) de búsqueda", style=LABEL),
                                        dcc.Checklist(id="route-criteria", value=[],
                                            options=[{"label": "  Menor costo", "value": "cost"},
                                                     {"label": "  Menor tiempo", "value": "time"},
                                                     {"label": "  Menor distancia", "value": "distance"}],
                                            style={"fontSize": "13px", "color": COLORS["text"], "marginBottom": "14px"},
                                            labelStyle={"display": "flex", "alignItems": "center",
                                                        "gap": "6px", "marginBottom": "6px", "cursor": "pointer"}),
                                        html.Span("Aeropuertos secundarios", style=LABEL),
                                        dcc.RadioItems(id="route-include-secondary", value="yes",
                                            options=[{"label": "  Incluir", "value": "yes"},
                                                     {"label": "  Excluir", "value": "no"}],
                                            style={"fontSize": "13px", "color": COLORS["text"], "marginBottom": "14px"},
                                            labelStyle={"display": "flex", "alignItems": "center",
                                                        "gap": "6px", "marginBottom": "6px", "cursor": "pointer"}),
                                        html.Span("Tipos de transporte", style=LABEL),
                                        dcc.Checklist(id="route-aircraft", value=["Avión Comercial", "Jet Regional", "Avión de Hélice"],
                                            options=[{"label": "  Avión Comercial", "value": "Avión Comercial"},
                                                     {"label": "  Jet Regional",    "value": "Jet Regional"},
                                                     {"label": "  Avión de Hélice", "value": "Avión de Hélice"}],
                                            style={"fontSize": "13px", "color": COLORS["text"], "marginBottom": "14px"},
                                            labelStyle={"display": "flex", "alignItems": "center",
                                                        "gap": "6px", "marginBottom": "6px", "cursor": "pointer"}),
                                        html.Button("Buscar ruta", id="route-search-btn", n_clicks=0,
                                                    style={**BTN_PRIMARY, "width": "100%", "marginBottom": "16px"}),
                                        html.Div(id="route-results"),
                                    ]),
                                ]),

                            dcc.Tab(label="$", value="propuesta-a",
                                style={"fontSize": "11px", "fontWeight": "600", "padding": "8px 8px"},
                                selected_style={"fontSize": "11px", "fontWeight": "700", "padding": "8px 8px",
                                                "borderTop": f"2px solid {COLORS['ok']}", "color": COLORS["ok"]},
                                children=[
                                    html.Div(style={"padding": "16px", "overflowY": "auto", "maxHeight": "calc(100vh - 120px)"}, children=[
                                        html.Span("Origen", style=LABEL),
                                        dcc.Dropdown(id="prop-a-origin", placeholder="Selecciona origen...",
                                                     style=DROPDOWN_STYLE, clearable=False),
                                        html.Span("Presupuesto (USD)", style=LABEL),
                                        dcc.Input(id="prop-a-budget", type="number", placeholder="Ej: 500",
                                                  style=INPUT_STYLE),
                                        html.Span("Tiempo límite (horas, opcional)", style=LABEL),
                                        dcc.Input(id="prop-a-time", type="number", placeholder="Ej: 24",
                                                  style=INPUT_STYLE),
                                        html.Button("Calcular Propuesta A", id="prop-a-btn", n_clicks=0,
                                                    style={**BTN_PRIMARY, "width": "100%", "marginBottom": "12px"}),
                                        html.Div(id="prop-a-results"),
                                    ]),
                                ]),

                            dcc.Tab(label="🕐", value="propuesta-b",
                                style={"fontSize": "11px", "fontWeight": "600", "padding": "8px 8px"},
                                selected_style={"fontSize": "11px", "fontWeight": "700", "padding": "8px 8px",
                                                "borderTop": f"2px solid {COLORS['secondary']}", "color": COLORS["secondary"]},
                                children=[
                                    html.Div(style={"padding": "16px", "overflowY": "auto", "maxHeight": "calc(100vh - 120px)"}, children=[
                                        html.Span("Origen", style=LABEL),
                                        dcc.Dropdown(id="prop-b-origin", placeholder="Selecciona origen...",
                                                     style=DROPDOWN_STYLE, clearable=False),
                                        html.Span("Tiempo disponible (horas)", style=LABEL),
                                        dcc.Input(id="prop-b-time", type="number", placeholder="Ej: 12",
                                                  style=INPUT_STYLE),
                                        html.Span("Presupuesto límite (USD, opcional)", style=LABEL),
                                        dcc.Input(id="prop-b-budget", type="number", placeholder="Ej: 1000",
                                                  style=INPUT_STYLE),
                                        html.Button("Calcular Propuesta B", id="prop-b-btn", n_clicks=0,
                                                    style={**BTN_SUCCESS, "width": "100%", "marginBottom": "12px"}),
                                        html.Div(id="prop-b-results"),
                                    ]),
                                ]),

                            dcc.Tab(label="Planificador", value="planner",
                                style={"fontSize": "12px", "fontWeight": "600", "padding": "8px 8px"},
                                selected_style={"fontSize": "12px", "fontWeight": "700", "padding": "8px 8px",
                                                "borderTop": f"2px solid {COLORS['hub']}", "color": COLORS["hub"]},
                                children=[
                                    html.Div(style={
                                        "padding": "16px",
                                        "paddingBottom": "120px",
                                        "overflowY": "auto",
                                        "overflowX": "hidden",
                                        "maxHeight": "calc(100vh - 120px)",
                                    }, children=[

                                        html.Div(id="journey-status"),

                                        html.Div(id="setup-section", children=[
                                            html.Span("Aeropuerto de origen", style=LABEL),
                                            dcc.Dropdown(id="planner-origin", placeholder="Selecciona origen...",
                                                         style=DROPDOWN_STYLE, clearable=False),
                                            html.Span("Presupuesto inicial (USD)", style=LABEL),
                                            dcc.Input(id="planner-budget", type="number", placeholder="1000",
                                                      min=1, step=1, value=1000, style=INPUT_STYLE),
                                            html.Button("✈  Iniciar viaje", id="start-btn", n_clicks=0,
                                                        style={**BTN_SUCCESS, "width": "100%"}),
                                        ]),

                                        html.Div(id="flying-section", style=HIDE, children=[
                                            html.Div(id="job-section", style=HIDE, children=[
                                                html.Div(style={**CARD, "borderLeft": f"3px solid {COLORS['warning']}"}, children=[
                                                    html.Div("💼 Trabajos disponibles",
                                                             style={"fontSize": "12px", "fontWeight": "700",
                                                                    "color": COLORS["warning"], "marginBottom": "8px"}),
                                                    dcc.Dropdown(id="job-dropdown", placeholder="Selecciona trabajo...",
                                                                 style={"fontSize": "12px", "marginBottom": "8px"}),
                                                    dcc.Input(id="hours-input", type="number", placeholder="Horas a trabajar",
                                                              min=0.5, step=0.5, style={**INPUT_STYLE, "marginBottom": "8px"}),
                                                    html.Button("Trabajar", id="work-btn", n_clicks=0,
                                                                style={**BTN_NEUTRAL, "width": "100%"}),
                                                    html.Div(id="job-result", style={"fontSize": "11px", "marginTop": "6px", "color": COLORS["text_dim"]}),
                                                ]),
                                            ]),

                                            html.Div(style={**CARD}, children=[
                                                html.Div("Vuelos disponibles",
                                                         style={"fontSize": "12px", "fontWeight": "700",
                                                                "color": COLORS["text"], "marginBottom": "6px"}),
                                                dcc.RadioItems(id="flight-radio", options=[], value=None,
                                                    style={"fontSize": "12px"},
                                                    labelStyle={"display": "flex", "alignItems": "flex-start",
                                                                "gap": "4px", "marginBottom": "4px",
                                                                "padding": "4px 6px", "borderRadius": "4px",
                                                                "backgroundColor": "#fff",
                                                                "border": f"1px solid {COLORS['border']}",
                                                                "cursor": "pointer", "lineHeight": "1.4"}),
                                                html.Div(id="no-flights-msg", style=HIDE,
                                                         children=html.P("Sin vuelos disponibles.",
                                                                          style={"fontSize": "12px", "color": COLORS["text_dim"], "margin": 0})),
                                            ]),

                                            html.Div(style={
                                                "display": "flex",
                                                "gap": "8px",
                                                "flexWrap": "wrap",
                                                "position": "sticky",
                                                "bottom": "0",
                                                "zIndex": "10",
                                                "backgroundColor": COLORS["bg_panel"],
                                                "borderTop": f"1px solid {COLORS['border']}",
                                                "paddingTop": "10px",
                                                "paddingBottom": "10px",
                                                "marginTop": "8px",
                                            }, children=[
                                                html.Button("Tomar vuelo", id="fly-btn", n_clicks=0,
                                                            style={**BTN_PRIMARY, "flex": "1", "minWidth": "100px"}),
                                                html.Button("Terminar viaje", id="end-btn", n_clicks=0,
                                                            style={**BTN_DANGER, "flex": "1", "minWidth": "100px"}),
                                            ]),
                                        ]),

                                        html.Div(id="arrival-section", style=HIDE, children=[
                                            html.Div(id="arrival-info"),
                                            html.Div(id="activity-panel", style=HIDE, children=[
                                                html.Div("Actividades opcionales",
                                                         style={"fontSize": "12px", "fontWeight": "700",
                                                                "color": COLORS["text"], "marginBottom": "8px"}),
                                                dcc.Checklist(id="activity-checklist", options=[], value=[],
                                                    style={"fontSize": "12px"},
                                                    labelStyle={"display": "flex", "alignItems": "flex-start",
                                                                "gap": "6px", "marginBottom": "6px",
                                                                "cursor": "pointer", "lineHeight": "1.5"}),
                                            ]),
                                            html.Button("Continuar →", id="confirm-activities-btn", n_clicks=0,
                                                        style={**BTN_PRIMARY, "width": "100%", "marginTop": "10px"}),
                                        ]),

                                        html.Div(id="complete-section", style=HIDE, children=[
                                            html.Div(id="journey-report"),
                                            html.Button("↺  Nuevo viaje", id="new-journey-btn", n_clicks=0,
                                                        style={**BTN_NEUTRAL, "width": "100%", "marginTop": "12px"}),
                                        ]),
                                    ]),
                                ]),
                        ]),
                ]),
            ]),
        ],
    )

# ── END ITEM 2.1 ──

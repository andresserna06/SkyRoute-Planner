# ── ITEM 2.1 — Web callbacks: JSON upload → build graph, layout switch, node info, route highlight ──

import base64
import json

from dash import html, Input, Output, State
import dash

from backend.services.graphService import build_graph_from_dict
from frontend.config import COLORS, LAYOUTS, _placeholder
from frontend.graph_helpers import build_elements, base_stylesheet


def register(app):

    @app.callback(
        Output("network-graph",         "elements"),
        Output("stat-airports",         "children"),
        Output("stat-routes",           "children"),
        Output("stat-hubs",             "children"),
        Output("upload-status",         "children"),
        Output("graph-store",           "data"),
        Output("original-graph-store",  "data"),
        Output("route-origin",          "options"),
        Output("route-dest",            "options"),
        Output("planner-origin",        "options"),
        Input("upload-json",            "contents"),
        State("upload-json",            "filename"),
    )
    def load_uploaded_json(contents, filename):
        if contents is None:
            raise dash.exceptions.PreventUpdate
        _, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)
        try:
            data  = json.loads(decoded.decode("utf-8"))
            g     = build_graph_from_dict(data)
            elems = build_elements(g)
            airport_opts = [{"label": f"{v.id} — {v.city}", "value": v.id}
                            for v in sorted(g.vertices, key=lambda x: x.id)]
            n_airports = len(g.vertices)
            n_routes   = sum(len(v.adjacencies) for v in g.vertices)
            n_hubs     = sum(1 for v in g.vertices if v.is_hub)
            status = html.Span(f"✓  {filename}",
                               style={"color": COLORS["ok"], "fontSize": "11px", "fontWeight": "600"})
            return (elems, str(n_airports), str(n_routes), str(n_hubs),
                    status, data, data,
                    airport_opts, airport_opts, airport_opts)
        except Exception as e:
            status = html.Span(f"Error: {e}", style={"color": COLORS["error"], "fontSize": "11px"})
            return [], "—", "—", "—", status, None, None, [], [], []

    @app.callback(
        Output("network-graph", "layout"),
        Input("layout-dropdown", "value"),
    )
    def update_layout(layout_name):
        return LAYOUTS.get(layout_name, LAYOUTS["cose"])

    @app.callback(
        Output("network-graph",        "stylesheet"),
        Input("network-graph",         "tapNodeData"),
        Input("clear-selection",       "n_clicks"),
        Input("route-highlight-store", "data"),
        Input("journey-store",         "data"),
        Input("right-tabs",            "value"),
    )
    def update_stylesheet(node_data, clear_clicks, route_hl, journey_data, active_tab):
        triggered = dash.callback_context.triggered_id

        if triggered == "clear-selection":
            return base_stylesheet()

        if active_tab == "planner" and journey_data and journey_data.get("segments"):
            visited = journey_data.get("visited", [])
            segs    = journey_data.get("segments", [])
            rules = base_stylesheet() + [{"selector": "edge", "style": {"opacity": 0.07}}]
            for seg in segs:
                rules.append({
                    "selector": f'edge[source="{seg["origin"]}"][target="{seg["destination"]}"]',
                    "style": {"opacity": 1, "line-color": COLORS["hub"],
                              "target-arrow-color": COLORS["hub"], "width": 2.8},
                })
            for nid in visited:
                rules.append({
                    "selector": f'node[id="{nid}"]',
                    "style": {"border-color": COLORS["hub"], "border-width": 4},
                })
            return rules

        if active_tab == "route" and route_hl and route_hl.get("path"):
            path  = route_hl["path"]
            rules = base_stylesheet() + [{"selector": "edge", "style": {"opacity": 0.07}}]
            for i in range(len(path) - 1):
                rules.append({
                    "selector": f'edge[source="{path[i]}"][target="{path[i+1]}"]',
                    "style": {"opacity": 1, "line-color": COLORS["highlight"],
                              "target-arrow-color": COLORS["highlight"], "width": 2.8, "z-index": 99},
                })
            for nid in path:
                rules.append({
                    "selector": f'node[id="{nid}"]',
                    "style": {"border-color": COLORS["highlight"], "border-width": 4},
                })
            return rules

        if triggered not in (None, "right-tabs") and node_data:
            nid = node_data["id"]
            return base_stylesheet() + [
                {"selector": "edge", "style": {"opacity": 0.08}},
                {"selector": f'edge[source="{nid}"]', "style": {
                    "opacity": 1, "line-color": COLORS["highlight"],
                    "target-arrow-color": COLORS["highlight"], "width": 2.6, "z-index": 99}},
                {"selector": f'node[id="{nid}"]',
                 "style": {"border-color": COLORS["highlight"], "border-width": 4}},
            ]

        return base_stylesheet()

    @app.callback(
        Output("airport-info",   "children"),
        Input("network-graph",   "tapNodeData"),
        Input("clear-selection", "n_clicks"),
    )
    def show_airport_info(node_data, clear_clicks):
        if dash.callback_context.triggered_id == "clear-selection" or not node_data:
            return _placeholder()
        is_hub = node_data["node_type"] == "hub"
        accent = COLORS["hub"] if is_hub else COLORS["secondary"]
        return html.Div(style={
            "backgroundColor": COLORS["bg_panel_2"], "border": f"1px solid {COLORS['border']}",
            "borderLeft": f"3px solid {accent}", "borderRadius": "10px", "padding": "14px 16px",
        }, children=[
            html.Div(node_data["id"],
                     style={"fontSize": "32px", "fontWeight": "800", "color": accent, "lineHeight": "1"}),
            html.Div("Aeropuerto Hub" if is_hub else "Aeropuerto Secundario",
                     style={"fontSize": "10px", "color": accent, "fontWeight": "700",
                            "textTransform": "uppercase", "letterSpacing": "1.2px", "marginBottom": "10px"}),
            html.Div(node_data["full_name"],
                     style={"fontSize": "12px", "color": COLORS["text"],
                            "fontStyle": "italic", "marginBottom": "14px", "lineHeight": "1.4"}),
            html.Div([html.Span("Ciudad: ", style={"fontWeight": "700", "fontSize": "12px"}),
                      html.Span(node_data["city"], style={"fontSize": "12px", "color": COLORS["text_dim"]})],
                     style={"marginBottom": "6px"}),
            html.Div([html.Span("País: ", style={"fontWeight": "700", "fontSize": "12px"}),
                      html.Span(node_data["country"], style={"fontSize": "12px", "color": COLORS["text_dim"]})],
                     style={"marginBottom": "6px"}),
            html.Div([html.Span("Zona horaria: ", style={"fontWeight": "700", "fontSize": "12px"}),
                      html.Span(node_data["timezone"], style={"fontSize": "12px", "color": COLORS["text_dim"]})],
                     style={"marginBottom": "10px"}),
            html.Div(html.Span("Aerolíneas", style={"fontWeight": "700", "fontSize": "12px"}),
                     style={"marginBottom": "4px"}),
            html.Div(node_data["airlines"],
                     style={"fontSize": "11px", "color": COLORS["text_dim"], "lineHeight": "1.6"}),
        ])

# ── END ITEM 2.1 ──
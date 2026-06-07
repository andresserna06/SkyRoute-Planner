# ── ITEM 2.2.c — Web callback: Dijkstra route search (origin, dest, criteria, highlight path on graph) ──

from dash import html, Input, Output, State
import dash

from backend.services.graphService import build_graph_from_dict
from backend.services.itineraryService import find_best_routes
from frontend.config import COLORS, CARD


def register(app):

    @app.callback(
        Output("route-results",        "children"),
        Output("route-highlight-store","data"),
        Input("route-search-btn",      "n_clicks"),
        State("route-origin",          "value"),
        State("route-dest",            "value"),
        State("route-criteria",        "value"),
        State("graph-store",           "data"),
    )
    def search_route(n_clicks, origin, dest, criteria, graph_data):
        if not n_clicks or not origin or not dest or not graph_data:
            raise dash.exceptions.PreventUpdate
        if origin == dest:
            return html.P("Origen y destino deben ser distintos.",
                          style={"color": COLORS["error"], "fontSize": "12px"}), None
        g       = build_graph_from_dict(graph_data)
        results = find_best_routes(g, origin, dest, [criteria])
        r       = results[0]
        if not r["success"]:
            return html.P(f"Sin ruta: {r.get('error', '')}",
                          style={"color": COLORS["error"], "fontSize": "12px"}), None

        path = r["path"]
        segs = r["segments"]

        crit_label = {"cost": "Costo", "time": "Tiempo", "distance": "Distancia"}[criteria]
        unit_label  = {"cost": "USD", "time": "min", "distance": "km"}[criteria]

        rows = []
        for seg in segs:
            rows.append(html.Tr([
                html.Td(f"{seg['origin']} → {seg['destination']}",
                        style={"padding": "5px 8px", "fontSize": "12px", "fontWeight": "600"}),
                html.Td(seg["aircraft"],
                        style={"padding": "5px 8px", "fontSize": "11px", "color": COLORS["text_dim"]}),
                html.Td(f"{seg['distance_km']:.0f} km",
                        style={"padding": "5px 8px", "fontSize": "11px"}),
                html.Td(f"{seg['weight']:.1f} {unit_label}",
                        style={"padding": "5px 8px", "fontSize": "11px", "fontWeight": "600",
                               "color": COLORS["secondary"]}),
            ]))

        card = html.Div(style={**CARD, "borderLeft": f"3px solid {COLORS['highlight']}"}, children=[
            html.Div(f"Ruta óptima — {crit_label}",
                     style={"fontSize": "12px", "fontWeight": "700", "color": COLORS["highlight"], "marginBottom": "8px"}),
            html.Div(" → ".join(path),
                     style={"fontSize": "13px", "fontWeight": "600", "color": COLORS["text"], "marginBottom": "10px"}),
            html.Table(style={"width": "100%", "borderCollapse": "collapse"}, children=[
                html.Thead(html.Tr([
                    html.Th("Tramo",     style={"padding": "4px 8px", "fontSize": "10px", "textAlign": "left",
                                                "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
                    html.Th("Aeronave", style={"padding": "4px 8px", "fontSize": "10px", "textAlign": "left",
                                                "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
                    html.Th("Dist.",    style={"padding": "4px 8px", "fontSize": "10px",
                                                "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
                    html.Th(crit_label, style={"padding": "4px 8px", "fontSize": "10px",
                                                "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
                ])),
                html.Tbody(rows),
            ]),
            html.Div(f"Total: {r['total_weight']:.1f} {unit_label}",
                     style={"fontSize": "13px", "fontWeight": "700", "color": COLORS["secondary"],
                            "marginTop": "10px", "textAlign": "right"}),
        ])
        return card, {"path": path}

# ── END ITEM 2.2.c ──

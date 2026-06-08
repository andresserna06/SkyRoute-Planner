# ── ITEM 2.2.c — Web callback: Dijkstra route search (origin, dest, criteria, highlight path on graph) ──

from dash import html, Input, Output, State
import dash

from backend.services.graphService import build_graph_from_dict
from backend.services.itineraryService import find_best_routes
from frontend.config import COLORS, CARD

CRIT_META = {
    "cost":     {"label": "Costo",     "unit": "USD", "color": "#16a34a", "key": "cost_metric_usd"},
    "time":     {"label": "Tiempo",    "unit": "min",  "color": "#2563eb", "key": "time_metric_min"},
    "distance": {"label": "Distancia", "unit": "km",   "color": "#d97706", "key": "distance_metric_km"},
}

TOTAL_KEY = {
    "cost":     "total_cost_usd",
    "time":     "total_time_min",
    "distance": "total_distance_km",
}


def _build_route_card(r, criteria):
    meta = CRIT_META[criteria]
    rows = []
    for seg in r["segments"]:
        metric_value = seg.get(meta["key"], 0)
        if seg.get("subsidized"):
            row_style = {"backgroundColor": "#fef2f2", "color": "#dc2626"}
            label_suffix = " (Subsidiada)"
        elif not seg.get("destination_is_hub"):
            row_style = {"backgroundColor": "#dbeafe", "color": "#1d4ed8"}
            label_suffix = " (Secundario)"
        else:
            row_style = {}
            label_suffix = ""
        rows.append(html.Tr([
            html.Td(f"{seg['origin']} → {seg['destination']}",
                    style={"padding": "5px 8px", "fontSize": "12px", "fontWeight": "600", **row_style}),
            html.Td(f"{seg['aircraft']}{label_suffix}",
                    style={"padding": "5px 8px", "fontSize": "11px", "color": COLORS["text_dim"], **row_style}),
            html.Td(f"{seg['distance_km']:.0f} km",
                    style={"padding": "5px 8px", "fontSize": "11px", **row_style}),
            html.Td(f"{metric_value:.1f} {meta['unit']}",
                    style={"padding": "5px 8px", "fontSize": "11px", "fontWeight": "600",
                           "color": meta["color"], **row_style}),
        ]))

    total_metric = r.get(TOTAL_KEY[criteria], 0)

    if criteria == "time":
        total_label = f"{total_metric / 60:.2f} h"
    else:
        total_label = f"{total_metric:.1f} {meta['unit']}"

    return html.Div(style={**CARD, "borderLeft": f"3px solid {meta['color']}"}, children=[
        html.Div(f"Ruta óptima — {meta['label']}",
                 style={"fontSize": "12px", "fontWeight": "700", "color": meta["color"], "marginBottom": "8px"}),
        html.Div(" → ".join(r["path"]),
                 style={"fontSize": "13px", "fontWeight": "600", "color": COLORS["text"], "marginBottom": "10px"}),
        html.Table(style={"width": "100%", "borderCollapse": "collapse"}, children=[
            html.Thead(html.Tr([
                html.Th("Tramo",     style={"padding": "4px 8px", "fontSize": "10px", "textAlign": "left",
                                            "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
                html.Th("Aeronave", style={"padding": "4px 8px", "fontSize": "10px", "textAlign": "left",
                                            "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
                html.Th("Dist.",    style={"padding": "4px 8px", "fontSize": "10px",
                                            "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
                html.Th(meta["label"], style={"padding": "4px 8px", "fontSize": "10px",
                                              "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
            ])),
            html.Tbody(rows),
        ]),
        html.Div(f"Total: {total_label}",
                 style={"fontSize": "13px", "fontWeight": "700", "color": meta["color"],
                        "marginTop": "10px", "textAlign": "right"}),
    ])


def register(app):

    @app.callback(
        Output("route-results",         "children"),
        Output("route-highlight-store", "data"),
        Input("route-search-btn",       "n_clicks"),
        State("route-origin",           "value"),
        State("route-dest",             "value"),
        State("route-criteria",         "value"),
        State("route-include-secondary","value"),
        State("route-aircraft",         "value"),
        State("graph-store",            "data"),
    )
    def search_route(n_clicks, origin, dest, criteria, include_secondary, aircraft_types, graph_data):
        if not n_clicks or not origin or not dest or not graph_data:
            raise dash.exceptions.PreventUpdate
        if origin == dest:
            return html.P("Origen y destino deben ser distintos.",
                          style={"color": COLORS["error"], "fontSize": "12px"}), None
        if not criteria:
            return html.P("Selecciona al menos un criterio de búsqueda.",
                          style={"color": COLORS["error"], "fontSize": "12px"}), None
        if not aircraft_types:
            return html.P("Selecciona al menos un tipo de transporte.",
                          style={"color": COLORS["error"], "fontSize": "12px"}), None

        g = build_graph_from_dict(graph_data)
        results = find_best_routes(
            g, origin, dest, criteria,
            include_secondary=(include_secondary == "yes"),
            preferred_aircraft=set(aircraft_types),
        )

        cards = []
        highlight_path = None

        for r in results:
            if r["success"]:
                crit = r["criterion"]
                cards.append(_build_route_card(r, crit))
                if highlight_path is None:
                    highlight_path = r["path"]
            else:
                cards.append(html.P(
                    f"Sin ruta {r['criterion']}: no existe conexión entre {origin} y {dest} "
                    f"con los tipos de transporte y filtros seleccionados.",
                    style={"color": COLORS["error"], "fontSize": "12px", "marginTop": "6px"}
                ))

        if not cards:
            return html.P("No se encontraron rutas.",
                          style={"color": COLORS["error"], "fontSize": "12px"}), None

        container = html.Div(children=cards, style={"display": "flex", "flexDirection": "column", "gap": "12px"})
        return container, {"path": highlight_path} if highlight_path else None

# ── END ITEM 2.2.c ──
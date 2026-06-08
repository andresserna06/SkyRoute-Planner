# ── 2.4 — Route interruptions: block/unblock edges, reroute, visual update ──

from dash import html, Input, Output, State
import dash
import math

from backend.services.graphService import build_graph_from_dict
from frontend.config import COLORS, CARD, SHOW, HIDE


def register(app):

    @app.callback(
        Output("edge-info",          "style"),
        Output("edge-info-content",  "children"),
        Output("block-edge-btn",     "children"),
        Input("network-graph",       "tapEdgeData"),
        Input("clear-selection",     "n_clicks"),
        State("blocked-edges-store", "data"),
    )
    def show_edge_info(edge_data, clear_clicks, blocked_list):
        if dash.callback_context.triggered_id == "clear-selection" or not edge_data:
            return HIDE, "", "Bloquear ruta"

        blocked_list = blocked_list or []
        edge_key  = f"{edge_data['source']}->{edge_data['target']}"
        is_blocked = edge_key in blocked_list

        content = html.Div([
            html.Div(f"{edge_data['source']} -> {edge_data['target']}",
                     style={"fontWeight": "700", "fontSize": "14px",
                            "color": COLORS["error"] if is_blocked else COLORS["text"],
                            "marginBottom": "4px"}),
            html.Div(f"{edge_data['distance_km']:.0f} km  ·  {edge_data['aircraft']}",
                     style={"fontSize": "11px", "color": COLORS["text_dim"]}),
            html.Div("Ruta bloqueada" if is_blocked else "",
                     style={"fontSize": "11px", "color": COLORS["error"],
                            "marginTop": "4px", "fontWeight": "600"}),
        ])

        btn_text = "Desbloquear ruta" if is_blocked else "Bloquear ruta"
        return SHOW, content, btn_text

    @app.callback(
        Output("blocked-edges-store", "data"),
        Output("journey-store",       "data", allow_duplicate=True),
        Input("block-edge-btn",       "n_clicks"),
        State("network-graph",        "tapEdgeData"),
        State("blocked-edges-store",  "data"),
        State("journey-store",        "data"),
        State("graph-store",          "data"),
        prevent_initial_call=True,
    )
    def toggle_edge(n_clicks, edge_data, blocked_list, journey_data, graph_data):
        if not n_clicks or not edge_data or not graph_data:
            raise dash.exceptions.PreventUpdate

        blocked_list = list(blocked_list or [])
        origin      = edge_data["source"]
        destination = edge_data["target"]
        edge_key    = f"{origin}->{destination}"

        # Unblock if already blocked
        if edge_key in blocked_list:
            blocked_list.remove(edge_key)
            if journey_data:
                journey_data["blocked_edges"] = blocked_list
            return blocked_list, journey_data if journey_data else dash.no_update

        # Block
        blocked_list.append(edge_key)

        if not journey_data or journey_data.get("finished", False):
            return blocked_list, dash.no_update

        journey_data["blocked_edges"] = blocked_list

        # Check if blocked edge affects the current planned path
        segments   = journey_data.get("segments", [])
        current_id = journey_data.get("current_id")

        edge_in_plan = any(
            s["origin"] == origin and s["destination"] == destination
            for s in segments
        )

        if edge_in_plan:
            graph = build_graph_from_dict(graph_data)

            def edge_filter(edge):
                key = f"{edge.origin_vertex.id}->{edge.destination_vertex.id}"
                return key not in blocked_list

            if segments:
                last_dest = segments[-1]["destination"]
                distances, predecessors, path = graph.dijkstra(
                    current_id,
                    last_dest,
                    edge_filter=edge_filter,
                )
                if distances.get(last_dest, math.inf) < math.inf:
                    journey_data["reroute_notice"] = (
                        f"Route {origin}->{destination} blocked. "
                        f"Rerouted: {' -> '.join(path)}"
                    )
                else:
                    journey_data["reroute_notice"] = (
                        f"Route {origin}->{destination} blocked. "
                        f"No alternative found."
                    )

        return blocked_list, journey_data

    @app.callback(
        Output("network-graph", "elements", allow_duplicate=True),
        Input("blocked-edges-store", "data"),
        State("graph-store",         "data"),
        prevent_initial_call=True,
    )
    def update_blocked_visuals(blocked_list, graph_data):
        if not graph_data:
            raise dash.exceptions.PreventUpdate
        # Allow empty list to reset all blocked visuals
        blocked_list = blocked_list or []
        graph = build_graph_from_dict(graph_data)
        from frontend.graph_helpers import build_elements
        elements = build_elements(graph)
        for element in elements:
            if "source" in element.get("data", {}):
                key = f"{element['data']['source']}->{element['data']['target']}"
                if key in blocked_list:
                    element["classes"] = "bloqueada"
        return elements
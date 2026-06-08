# ── ITEM 2.4 — Route interruptions: block edges, reroute, visual update ──

from dash import html, Input, Output, State
import dash

from backend.services.graphService import build_graph_from_dict
from backend.services.itineraryService import find_best_routes
from frontend.config import COLORS, CARD, SHOW, HIDE


def register(app):

    @app.callback(
        Output("edge-info",         "style"),
        Output("edge-info-content", "children"),
        Input("network-graph",      "tapEdgeData"),
        Input("clear-selection",    "n_clicks"),
    )
    def show_edge_info(edge_data, clear_clicks):
        if dash.callback_context.triggered_id == "clear-selection" or not edge_data:
            return HIDE, ""

        is_blocked = edge_data.get("classes") == "bloqueada"
        content = html.Div([
            html.Div(f"{edge_data['source']} → {edge_data['target']}",
                     style={"fontWeight": "700", "fontSize": "14px",
                            "color": COLORS["error"] if is_blocked else COLORS["text"],
                            "marginBottom": "4px"}),
            html.Div(f"{edge_data['distance_km']:.0f} km  ·  {edge_data['aircraft']}",
                     style={"fontSize": "11px", "color": COLORS["text_dim"]}),
            html.Div("⛔ Ruta bloqueada" if is_blocked else "",
                     style={"fontSize": "11px", "color": COLORS["error"],
                            "marginTop": "4px", "fontWeight": "600"}),
        ])
        return SHOW, content

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
    def block_edge(n_clicks, edge_data, blocked_list, journey_data, graph_data):
        if not n_clicks or not edge_data or not graph_data:
            raise dash.exceptions.PreventUpdate

        origin = edge_data["source"]
        destination = edge_data["target"]
        edge_key = f"{origin}->{destination}"

        if edge_key in blocked_list:
            raise dash.exceptions.PreventUpdate

        blocked_list = list(blocked_list) + [edge_key]

        # Recalculate route if journey is active and edge is in planned path
        if journey_data and not journey_data.get("finished", False):
            g = build_graph_from_dict(graph_data)

            # Mark edge as blocked in graph
            current_id = journey_data.get("current_id")
            segments = journey_data.get("segments", [])

            # Check if blocked edge is in the remaining planned path
            remaining_origins = [s["origin"] for s in segments
                                  if s["origin"] == current_id or
                                  any(s2["destination"] == s["origin"]
                                      for s2 in segments)]

            edge_in_plan = any(
                s["origin"] == origin and s["destination"] == destination
                for s in segments
            )

            if edge_in_plan:
                # Find alternative route from current position
                # excluding the blocked edge
                blocked_set = set(blocked_list)

                def edge_filter(e):
                    key = f"{e.origin_vertex.id}->{e.destination_vertex.id}"
                    return key not in blocked_set

                # Try to find reroute to last planned destination
                if segments:
                    last_dest = segments[-1]["destination"]
                    dist, pred, path = g.dijkstra(
                        current_id,
                        last_dest,
                        edge_filter=edge_filter
                    )

                    import math
                    if dist.get(last_dest, math.inf) < math.inf:
                        journey_data["reroute_notice"] = (
                            f"Route {origin}→{destination} blocked. "
                            f"Rerouted: {' → '.join(path)}"
                        )
                    else:
                        journey_data["reroute_notice"] = (
                            f"Route {origin}→{destination} blocked. "
                            f"No alternative found."
                        )

            journey_data["blocked_edges"] = blocked_list
            return blocked_list, journey_data

        return blocked_list, dash.no_update
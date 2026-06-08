# ── 2.4 — Flight transit animation and interruption handling ──

import math
from dash import Input, Output, State
import dash

from backend.services.graphService import build_graph_from_dict
from backend.services.dynamicService import choose_flight, get_available_flights
from frontend.config import COLORS, SHOW, HIDE

# Total simulated transit steps
TRANSIT_STEPS = 10


def register(app):

    @app.callback(
        Output("flight-interval",       "disabled"),
        Output("flight-progress-store", "data"),
        Output("journey-store",         "data",     allow_duplicate=True),
        Output("transit-title",         "children"),
        Output("transit-bar",           "style"),
        Output("transit-status",        "children"),
        Input("flight-interval",        "n_intervals"),
        Input("journey-store",          "data"),
        State("flight-progress-store",  "data"),
        State("graph-store",            "data"),
        State("blocked-edges-store",    "data"),
        prevent_initial_call=True,
    )
    def manage_transit(n_intervals, journey_data, progress_data, graph_data, blocked_edges):
        tid = dash.callback_context.triggered_id

        bar_style = {
            "height": "100%", "width": "0%",
            "backgroundColor": COLORS["hub"],
            "borderRadius": "3px",
            "transition": "width 1s linear",
        }

        # journey-store changed — start or stop interval
        if tid == "journey-store":
            if not journey_data or not journey_data.get("in_transit", False):
                return True, None, dash.no_update, "", bar_style, ""
            return False, {"tick": 0, "total": TRANSIT_STEPS}, dash.no_update, "", bar_style, "Preparing flight..."

        # interval tick
        if not journey_data or not journey_data.get("in_transit", False):
            return True, None, dash.no_update, "", bar_style, ""
        if not progress_data or not graph_data:
            return True, None, dash.no_update, "", bar_style, ""

        tick  = progress_data.get("tick", 0) + 1
        total = progress_data.get("total", TRANSIT_STEPS)
        pct   = min(int(tick / total * 100), 100)

        g           = build_graph_from_dict(graph_data)
        origin      = journey_data["current_id"]
        flight_id   = journey_data.get("pending_flight", 0)
        blocked     = blocked_edges or []
        journey_data["blocked_edges"] = blocked

        # Use the destination and aircraft locked at flight selection time.
        # Never re-derive from options list — blocked edges change the list order,
        # which would silently reroute to a different airport.
        destination = journey_data.get("pending_destination", "?")
        aircraft    = journey_data.get("pending_aircraft",    "?")
        title       = f"{origin} -> {destination}  ·  {aircraft}"

        bar_style["width"] = f"{pct}%"

        # Check if edge was blocked mid-flight — return traveler to origin
        edge_key = f"{origin}->{destination}"
        if edge_key in blocked:
            journey_data["in_transit"]        = False
            journey_data["pending_flight"]    = None
            journey_data["pending_destination"] = None
            journey_data["pending_aircraft"]  = None
            journey_data["current_id"]        = origin   # guarantee stay at origin
            journey_data["show_activities"]   = False
            journey_data["reroute_notice"] = (
                f"Ruta {origin}→{destination} interrumpida. "
                f"El viajero permanece en {origin}."
            )
            return True, None, journey_data, title, bar_style, "Vuelo interrumpido."

        # Transit complete
        if tick >= total:
            choose_flight(g, journey_data, flight_id)
            journey_data["in_transit"]        = False
            journey_data["pending_flight"]    = None
            journey_data["pending_destination"] = None
            journey_data["pending_aircraft"]  = None
            journey_data["show_activities"]   = True
            return True, None, journey_data, title, bar_style, "¡Llegaste!"

        progress_data["tick"] = tick
        return False, progress_data, dash.no_update, title, bar_style, f"In transit... {pct}%"
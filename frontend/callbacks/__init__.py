def register_all(app):
    # Each module owns one feature area; register() wires its callbacks to the app.
    from . import (
        network_view,      # R1 — JSON upload, network view, node info, route highlight
        route_search,      # R2.c — Dijkstra route search
        proposals,         # R2.a/b — Proposal A (budget) and B (time)
        journey_planner,   # R3 — dynamic itinerary planner
        trip_report,       # R5 — final trip report (helper module, no callbacks)
        interruptions,     # R4 — block/unblock edges + reroute
        aircraft_editor,   # aircraft cost/time config editor
        flight_animation,  # R4 — flight transit animation
    )
    network_view.register(app)
    route_search.register(app)
    proposals.register(app)
    journey_planner.register(app)
    interruptions.register(app)
    aircraft_editor.register(app)
    flight_animation.register(app)
    # trip_report has no register() — it only exposes render_report() to journey_planner

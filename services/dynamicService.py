# dynamicService.py — ITEM 2.3.3 C
# Frontend/API-friendly dynamic itinerary service

from services.itineraryService import (
    _edge_cost,
    _edge_time,
    _exceeds_subsidized_limit
)


def _list_available_flights(
    vertex,
    visited,
    aircraft_config,
    free_km,
    total_km,
    budget
):
    # Return list of affordable flights from current airport

    options = []

    for edge in vertex.adjacencies:
        dest_id = edge.destination_vertex.id

        if dest_id in visited:
            continue

        # Enforce 20% subsidized route rule
        if _exceeds_subsidized_limit(edge, free_km, total_km):
            continue

        for aircraft in edge.aircraft:

            cost = _edge_cost(edge, aircraft, aircraft_config)

            # _edge_time already returns minutes
            time_min = _edge_time(edge, aircraft, aircraft_config)

            if cost <= budget:

                options.append({
                    "_edge": edge,  # internal only
                    "destination": dest_id,
                    "aircraft": aircraft,
                    "distance_km": edge.distance_km,
                    "cost": round(cost, 2),
                    "time_min": round(time_min, 2)
                })

    return options


def create_dynamic_state(origin_id, initial_budget):

    return {
        "origin_id": origin_id,
        "current_id": origin_id,
        "budget": initial_budget,
        "time_min": 0.0,

        # JSON-safe lists
        "visited": [origin_id],
        "segments": [],
        "aircraft_used": [],

        "free_km": 0.0,
        "total_km": 0.0,

        "finished": False
    }


def get_available_flights(graph, state):

    vertex = graph.get_vertex(state["current_id"])

    if vertex is None:
        return {
            "success": False,
            "error": f"Unknown airport: {state['current_id']}"
        }

    options = _list_available_flights(
        vertex,
        state["visited"],
        graph.aircraft_config,
        state["free_km"],
        state["total_km"],
        state["budget"]
    )

    flights = []

    for idx, option in enumerate(options):

        flights.append({
            "id": idx,
            "destination": option["destination"],
            "aircraft": option["aircraft"],
            "distance_km": option["distance_km"],
            "cost": option["cost"],
            "time_min": option["time_min"]
        })

    return {
        "success": True,
        "current_airport": state["current_id"],
        "remaining_budget": round(state["budget"], 2),
        "total_time_min": round(state["time_min"], 2),
        "available_flights": flights
    }


def choose_flight(graph, state, flight_id):

    vertex = graph.get_vertex(state["current_id"])

    if vertex is None:
        return {
            "success": False,
            "error": f"Unknown airport: {state['current_id']}"
        }

    options = _list_available_flights(
        vertex,
        state["visited"],
        graph.aircraft_config,
        state["free_km"],
        state["total_km"],
        state["budget"]
    )

    if flight_id < 0 or flight_id >= len(options):

        return {
            "success": False,
            "error": "Invalid flight selection"
        }

    selected = options[flight_id]

    edge = selected["_edge"]
    aircraft = selected["aircraft"]
    cost = selected["cost"]
    time_min = selected["time_min"]
    destination = selected["destination"]

    # Update budget/time
    state["budget"] -= cost
    state["time_min"] += time_min

    # Update visited airports
    if destination not in state["visited"]:
        state["visited"].append(destination)

    # Update aircraft used
    if aircraft not in state["aircraft_used"]:
        state["aircraft_used"].append(aircraft)

    # Update km tracking
    state["total_km"] += edge.distance_km

    if edge.base_cost == 0:
        state["free_km"] += edge.distance_km

    # Add segment
    state["segments"].append({
        "origin": state["current_id"],
        "destination": destination,
        "aircraft": aircraft,
        "distance_km": edge.distance_km,
        "cost": round(cost, 2),
        "time_min": round(time_min, 2)
    })

    # Move traveller
    state["current_id"] = destination

    # Check if more flights exist
    next_vertex = graph.get_vertex(destination)

    remaining = _list_available_flights(
        next_vertex,
        state["visited"],
        graph.aircraft_config,
        state["free_km"],
        state["total_km"],
        state["budget"]
    )

    if not remaining:
        state["finished"] = True

    return {
        "success": True,
        "message": "Flight added successfully",
        "state": build_summary(state)
    }


def finish_itinerary(state):

    state["finished"] = True

    return {
        "success": True,
        "summary": build_summary(state)
    }


def build_summary(state):

    path = [state["origin_id"]]

    for segment in state["segments"]:
        path.append(segment["destination"])

    return {
        "origin": state["origin_id"],
        "current_airport": state["current_id"],

        "destinations_visited": len(state["visited"]) - 1,

        "segments": state["segments"],

        "total_cost": round(
            sum(s["cost"] for s in state["segments"]),
            2
        ),

        "total_time_min": round(state["time_min"], 2),

        "total_time_hours": round(
            state["time_min"] / 60.0,
            2
        ),

        "aircraft_used": state["aircraft_used"],

        "path": path,

        "remaining_budget": round(state["budget"], 2),

        "finished": state["finished"]
    }
    
# END ITEM 2.3.3 C
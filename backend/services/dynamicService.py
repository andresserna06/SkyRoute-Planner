# ── ITEM 2.3 — Advanced planning with dynamic budget
#   2.3.a: Activities (mandatory lodging/meals + optional tours)
#   2.3.b: Jobs at airports (earn additional budget when budget < 35%)
#   2.3.c: Transport costs (aircraft selection, flight cost/time, subsidised 20% rule) ──

from backend.services.itineraryService import (
    _edge_cost,
    _edge_time,
    _exceeds_subsidized_limit
)


# ── ITEM 2.3.c — List affordable flights from current airport (aircraft types, cost/km, time/km) ──

def _list_available_flights(
    vertex,
    visited,
    aircraft_config,
    free_km,
    total_km,
    budget
):
    # List flights within budget from current airport (respects subsidised 20% rule)

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


# ── ITEM 2.3 (shared) — Create initial journey state ──

def create_dynamic_state(origin_id, initial_budget):

    return {
        "origin_id": origin_id,
        "current_id": origin_id,
        "budget": initial_budget,
        "initial_budget": initial_budget,
        "time_min": 0.0,

        # JSON-safe lists
        "visited": [origin_id],
        "segments": [],
        "aircraft_used": [],

        "free_km": 0.0,
        "total_km": 0.0,

        "jobs_done": [],
        "total_earned": 0.0,

        "finished": False
    }


# ── ITEM 2.3.c — API: get list of reachable flights from current airport within remaining budget ──

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


# ── ITEM 2.3 (shared) — Take a flight: update budget, time, visited airports, segments ──

def choose_flight(graph, state, flight_id, traveler=None):

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
        
    # 2.3.a — Traveler obligatory activities
    if traveler is not None:
        time_per_km = graph.aircraft_config[aircraft]["timePerKm"]
        traveler.check_flight(edge, time_per_km)
        traveler.current_location = graph.get_vertex(destination)
        traveler.check_obligatory(graph.get_vertex(destination))

    return {
        "success": True,
        "message": "Flight added successfully",
        "state": build_summary(state)
    }


# ── ITEM 2.3.b — Jobs at airports: earn budget by working ──

def get_available_jobs(graph, state):
    # Returns list of jobs at the current airport when budget < 35% of initial
    threshold = state["initial_budget"] * 0.35
    if state["budget"] > threshold:
        return {"success": True, "show_jobs": False, "jobs": [],
                "reason": f"Presupuesto ${state['budget']:.2f} > 35% (${threshold:.2f})"}

    vertex = graph.get_vertex(state["current_id"])
    if vertex is None:
        return {"success": False, "show_jobs": False, "jobs": [],
                "error": f"Unknown airport: {state['current_id']}"}

    raw = getattr(vertex, "jobs", [])
    if not raw:
        return {"success": True, "show_jobs": True, "jobs": [],
                "reason": "No hay trabajos disponibles en este aeropuerto."}

    jobs_out = []
    for idx, j in enumerate(raw):
        jobs_out.append({
            "id": idx,
            "name": j.get("name", "Trabajo"),
            "hourly_rate": j.get("hourlyRate", 0),
            "max_hours": j.get("maxHours", 8),
        })

    return {"success": True, "show_jobs": True, "jobs": jobs_out}


def work_at_job(graph, state, job_index, hours):
    # Execute work: earnings = hourly_rate * hours, consume time, record job
    threshold = state["initial_budget"] * 0.35
    if state["budget"] > threshold:
        return {"success": False,
                "error": f"Presupuesto ${state['budget']:.2f} > 35% — no necesitas trabajar."}

    vertex = graph.get_vertex(state["current_id"])
    if vertex is None:
        return {"success": False, "error": f"Unknown airport: {state['current_id']}"}

    raw = getattr(vertex, "jobs", [])
    if job_index < 0 or job_index >= len(raw):
        return {"success": False, "error": "Trabajo inválido."}

    job = raw[job_index]
    max_hours = job.get("maxHours", 8)
    if hours <= 0 or hours > max_hours:
        return {"success": False,
                "error": f"Las horas deben estar entre 0.5 y {max_hours}."}

    rate = job.get("hourlyRate", 0)
    earnings = round(rate * hours, 2)

    # Update state
    state["budget"] += earnings
    state["time_min"] += hours * 60
    state["jobs_done"].append({
        "airport": state["current_id"],
        "job_name": job.get("name", "Trabajo"),
        "hours": hours,
        "earnings": earnings,
        "hourly_rate": rate,
    })
    state["total_earned"] += earnings

    return {"success": True, "earnings": earnings, "job_name": job.get("name", "Trabajo"),
            "hours": hours, "remaining_budget": round(state["budget"], 2)}

# ── ITEM 2.3 (shared) — Finish journey and return summary ──

def finish_itinerary(state):

    state["finished"] = True

    return {
        "success": True,
        "summary": build_summary(state)
    }


# ── ITEM 2.3 (shared) — Build journey summary (path, cost, time, destinations, jobs) ──

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

        "jobs_done": state["jobs_done"],

        "total_earned": round(state["total_earned"], 2),

        "path": path,

        "remaining_budget": round(state["budget"], 2),

        "finished": state["finished"]
    }
    
# ── END ITEM 2.3 ──

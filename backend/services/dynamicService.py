# Dynamic itinerary service
# 2.3.a: Obligatory (food + accommodation) and optional activities
# 2.3.b: Jobs at airports (available when budget < 35% of initial)
# 2.3.c: Transport costs with aircraft selection and subsidised-route rule

from backend.services.itineraryService import (
    _edge_cost,
    _edge_time,
    _exceeds_subsidized_limit,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _list_available_flights(vertex, visited, aircraft_config, free_km, total_km, budget):
    """Return all affordable, unvisited flights from vertex respecting the 20% subsidised rule."""
    options = []

    for edge in vertex.adjacencies:
        dest_id = edge.destination_vertex.id

        if dest_id in visited:
            continue

        if _exceeds_subsidized_limit(edge, free_km, total_km):
            continue

        for aircraft in edge.aircraft:
            cost = _edge_cost(edge, aircraft, aircraft_config)
            time_min = _edge_time(edge, aircraft, aircraft_config)

            if cost <= budget:
                options.append({
                    "_edge": edge,
                    "destination": dest_id,
                    "aircraft": aircraft,
                    "distance_km": edge.distance_km,
                    "cost": round(cost, 2),
                    "time_min": round(time_min, 2),
                })

    return options


# ── State management ───────────────────────────────────────────────────────────

def create_dynamic_state(origin_id, initial_budget):
    """Create the initial journey state dict stored in the Dash journey-store."""
    return {
        "origin_id": origin_id,
        "current_id": origin_id,
        "budget": initial_budget,
        "initial_budget": initial_budget,
        "time_min": 0.0,

        "visited": [origin_id],
        "segments": [],
        "aircraft_used": [],

        "free_km": 0.0,
        "total_km": 0.0,

        "jobs_done": [],
        "total_earned": 0.0,

        # 2.3.a — obligatory cost tracking
        "obligatory_cost_total": 0.0,   # cumulative food + accommodation charged
        "last_food_h": 0.0,             # hours at which the last meal was charged
        "last_accommodation_h": 0.0,    # hours at which the last stay was charged

        # 2.3.a — arrival info for the current airport (used by activity panel)
        "arrival_time_h": 0.0,          # arrival time at current airport (hours)
        "minimum_stay_h": 0.0,          # minimum stay required at current airport (hours)

        "finished": False,
    }


# ── Flight actions ─────────────────────────────────────────────────────────────

def get_available_flights(graph, state):
    """Return flights reachable from the current airport within remaining budget."""
    vertex = graph.get_vertex(state["current_id"])
    if vertex is None:
        return {"success": False, "error": f"Unknown airport: {state['current_id']}"}

    options = _list_available_flights(
        vertex,
        state["visited"],
        graph.aircraft_config,
        state["free_km"],
        state["total_km"],
        state["budget"],
    )

    flights = [
        {
            "id": idx,
            "destination": o["destination"],
            "aircraft": o["aircraft"],
            "distance_km": o["distance_km"],
            "cost": o["cost"],
            "time_min": o["time_min"],
        }
        for idx, o in enumerate(options)
    ]

    return {
        "success": True,
        "current_airport": state["current_id"],
        "remaining_budget": round(state["budget"], 2),
        "total_time_min": round(state["time_min"], 2),
        "available_flights": flights,
    }


def choose_flight(graph, state, flight_id):
    """
    Execute a flight choice:
      - Deduct flight cost from budget.
      - Advance time (including mid-flight meal charges via Traveler).
      - Update visited airports, segments, km counters, and arrival metadata.

    Obligatory costs (food incurred during flight) are calculated here and
    immediately synced into state so the callback never needs to adjust budget manually.
    """
    vertex = graph.get_vertex(state["current_id"])
    if vertex is None:
        return {"success": False, "error": f"Unknown airport: {state['current_id']}"}

    options = _list_available_flights(
        vertex,
        state["visited"],
        graph.aircraft_config,
        state["free_km"],
        state["total_km"],
        state["budget"],
    )

    if flight_id < 0 or flight_id >= len(options):
        return {"success": False, "error": "Invalid flight selection"}

    selected = options[flight_id]
    edge = selected["_edge"]
    aircraft = selected["aircraft"]
    cost = selected["cost"]
    time_min = selected["time_min"]
    destination = selected["destination"]

    # Reconstruct a Traveler seeded from current state to compute obligatory costs
    from backend.models.traveler import Traveler

    traveler = Traveler(budget=state["budget"])
    traveler.current_time = state["time_min"] / 60.0
    traveler.last_food = state["last_food_h"]
    traveler.last_accommodation = state["last_accommodation_h"]
    traveler.current_location = vertex

    # Deduct flight cost
    state["budget"] = round(state["budget"] - cost, 2)
    traveler.budget = state["budget"]

    # Advance time and charge mid-flight meals
    time_per_km = graph.aircraft_config[aircraft]["timePerKm"]
    traveler.check_flight(edge, time_per_km)

    # Sync obligatory costs incurred during flight back into state
    # (traveler.total_cost holds ONLY the delta from this call since it started at 0)
    obligatory_delta = round(traveler.total_cost, 2)
    state["budget"] = round(traveler.budget, 2)               # already deducted inside traveler
    state["obligatory_cost_total"] = round(
        state.get("obligatory_cost_total", 0.0) + obligatory_delta, 2
    )
    state["last_food_h"] = traveler.last_food
    state["last_accommodation_h"] = traveler.last_accommodation

    # Advance total journey time
    state["time_min"] = round(traveler.current_time * 60.0, 2)

    # Record the edge minimum stay for the activity panel
    state["arrival_time_h"] = round(traveler.arrival_time, 4)
    state["minimum_stay_h"] = round(edge.minimum_stay / 60.0, 4)

    # Update route tracking
    state["total_km"] += edge.distance_km
    if edge.base_cost == 0:
        state["free_km"] += edge.distance_km

    if destination not in state["visited"]:
        state["visited"].append(destination)

    if aircraft not in state["aircraft_used"]:
        state["aircraft_used"].append(aircraft)

    state["segments"].append({
        "origin": state["current_id"],
        "destination": destination,
        "aircraft": aircraft,
        "distance_km": edge.distance_km,
        "cost": round(cost, 2),
        "time_min": round(time_min, 2),
    })

    state["current_id"] = destination

    # Check whether any further flights remain
    next_vertex = graph.get_vertex(destination)
    remaining = _list_available_flights(
        next_vertex,
        state["visited"],
        graph.aircraft_config,
        state["free_km"],
        state["total_km"],
        state["budget"],
    )
    if not remaining:
        state["finished"] = True

    return {"success": True, "message": "Flight added successfully", "state": build_summary(state)}


# ── 2.3.a — Optional activities ───────────────────────────────────────────────

def get_optional_activities(graph, state):
    """
    Return the list of optional activities at the current airport together with
    the time window still available (minimum_stay minus time already spent there).
    """
    vertex = graph.get_vertex(state["current_id"])
    if vertex is None:
        return {"success": False, "error": f"Unknown airport: {state['current_id']}"}

    activities = getattr(vertex, "activities", []) or []

    current_time_h = state["time_min"] / 60.0
    arrival_time_h = state.get("arrival_time_h", current_time_h)
    minimum_stay_h = state.get("minimum_stay_h", 0.0)
    available_until_h = arrival_time_h + minimum_stay_h
    remaining_window_h = max(0.0, available_until_h - current_time_h)

    enriched = []
    for idx, act in enumerate(activities):
        duration_h = act.get("durationMin", 0) / 60.0
        fits = duration_h <= remaining_window_h
        enriched.append({
            "id": idx,
            "name": act.get("name", "Activity"),
            "duration_min": act.get("durationMin", 0),
            "cost_usd": act.get("costUSD", 0),
            "fits_in_window": fits,
        })

    return {
        "success": True,
        "airport": state["current_id"],
        "activities": enriched,
        "remaining_window_h": round(remaining_window_h, 2),
        "minimum_stay_h": round(minimum_stay_h, 2),
    }


def do_optional_activity(graph, state, activity_index):
    """
    Perform an optional activity at the current airport:
      - Deduct cost from budget.
      - Advance current time by activity duration.
      - Charge any obligatory costs triggered by the time advance.

    Returns updated cost/time info or an error if the activity does not fit.
    """
    vertex = graph.get_vertex(state["current_id"])
    if vertex is None:
        return {"success": False, "error": f"Unknown airport: {state['current_id']}"}

    activities = getattr(vertex, "activities", []) or []
    if activity_index < 0 or activity_index >= len(activities):
        return {"success": False, "error": "Invalid activity index"}

    activity = activities[activity_index]
    duration_h = activity.get("durationMin", 0) / 60.0
    cost_usd = activity.get("costUSD", 0)

    current_time_h = state["time_min"] / 60.0
    arrival_time_h = state.get("arrival_time_h", current_time_h)
    minimum_stay_h = state.get("minimum_stay_h", 0.0)
    available_until_h = arrival_time_h + minimum_stay_h

    if current_time_h + duration_h > available_until_h:
        return {
            "success": False,
            "error": (
                f"Not enough time for '{activity.get('name')}'. "
                f"Activity needs {activity.get('durationMin')} min but only "
                f"{round((available_until_h - current_time_h) * 60)} min remain in the stay window."
            ),
        }

    if cost_usd > state["budget"]:
        return {"success": False, "error": f"Insufficient budget for '{activity.get('name')}'"}

    # Deduct activity cost
    state["budget"] = round(state["budget"] - cost_usd, 2)

    # Advance time
    new_time_h = current_time_h + duration_h
    state["time_min"] = round(new_time_h * 60.0, 2)

    # Charge any obligatory costs triggered by the time advance
    from backend.models.traveler import Traveler

    traveler = Traveler(budget=state["budget"])
    traveler.current_time = new_time_h
    traveler.last_food = state["last_food_h"]
    traveler.last_accommodation = state["last_accommodation_h"]
    traveler.current_location = vertex

    traveler.check_obligatory(vertex)

    obligatory_delta = round(traveler.total_cost, 2)
    state["budget"] = round(traveler.budget, 2)
    state["obligatory_cost_total"] = round(
        state.get("obligatory_cost_total", 0.0) + obligatory_delta, 2
    )
    state["last_food_h"] = traveler.last_food
    state["last_accommodation_h"] = traveler.last_accommodation

    return {
        "success": True,
        "activity_name": activity.get("name"),
        "cost_usd": cost_usd,
        "duration_min": activity.get("durationMin"),
        "obligatory_delta": obligatory_delta,
        "remaining_budget": round(state["budget"], 2),
    }


def compute_free_time(state):
    """
    Calculate free time remaining in the current airport's minimum stay window.
    Free time = time left in the stay window after all activities and work.
    """
    current_time_h = state["time_min"] / 60.0
    arrival_time_h = state.get("arrival_time_h", current_time_h)
    minimum_stay_h = state.get("minimum_stay_h", 0.0)
    available_until_h = arrival_time_h + minimum_stay_h
    free_time_h = max(0.0, available_until_h - current_time_h)
    return round(free_time_h, 2)


# ── 2.3.b — Jobs ──────────────────────────────────────────────────────────────

def get_available_jobs(graph, state):
    """Return jobs at the current airport if budget has fallen below 35% of initial."""
    threshold = state["initial_budget"] * 0.35
    if state["budget"] > threshold:
        return {
            "success": True,
            "show_jobs": False,
            "jobs": [],
            "reason": f"Budget ${state['budget']:.2f} is above 35% threshold (${threshold:.2f})",
        }

    vertex = graph.get_vertex(state["current_id"])
    if vertex is None:
        return {"success": False, "show_jobs": False, "jobs": [], "error": f"Unknown airport: {state['current_id']}"}

    raw = getattr(vertex, "jobs", []) or []
    if not raw:
        return {"success": True, "show_jobs": True, "jobs": [], "reason": "No jobs available at this airport."}

    jobs_out = [
        {
            "id": idx,
            "name": j.get("name", "Job"),
            "hourly_rate": j.get("hourlyRate", 0),
            "max_hours": j.get("maxHours", 8),
        }
        for idx, j in enumerate(raw)
    ]

    return {"success": True, "show_jobs": True, "jobs": jobs_out}


def work_at_job(graph, state, job_index, hours):
    """Execute a work shift: earn income, consume time, record the job."""
    threshold = state["initial_budget"] * 0.35
    if state["budget"] > threshold:
        return {"success": False, "error": f"Budget ${state['budget']:.2f} is above 35% — no need to work."}

    vertex = graph.get_vertex(state["current_id"])
    if vertex is None:
        return {"success": False, "error": f"Unknown airport: {state['current_id']}"}

    raw = getattr(vertex, "jobs", []) or []
    if job_index < 0 or job_index >= len(raw):
        return {"success": False, "error": "Invalid job selection."}

    job = raw[job_index]
    max_hours = job.get("maxHours", 8)
    if hours <= 0 or hours > max_hours:
        return {"success": False, "error": f"Hours must be between 0.5 and {max_hours}."}

    earnings = round(job.get("hourlyRate", 0) * hours, 2)

    state["budget"] = round(state["budget"] + earnings, 2)
    state["time_min"] = round(state["time_min"] + hours * 60.0, 2)
    state["jobs_done"].append({
        "airport": state["current_id"],
        "job_name": job.get("name", "Job"),
        "hours": hours,
        "earnings": earnings,
        "hourly_rate": job.get("hourlyRate", 0),
    })
    state["total_earned"] = round(state.get("total_earned", 0.0) + earnings, 2)

    return {
        "success": True,
        "earnings": earnings,
        "job_name": job.get("name", "Job"),
        "hours": hours,
        "remaining_budget": round(state["budget"], 2),
    }


# ── Summary ────────────────────────────────────────────────────────────────────

def finish_itinerary(state):
    """Mark the journey as finished and return the final summary."""
    state["finished"] = True
    return {"success": True, "summary": build_summary(state)}


def build_summary(state):
    """Build a JSON-safe journey summary from current state."""
    path = [state["origin_id"]] + [s["destination"] for s in state["segments"]]

    return {
        "origin": state["origin_id"],
        "current_airport": state["current_id"],
        "destinations_visited": len(state["visited"]) - 1,
        "segments": state["segments"],
        "total_cost": round(sum(s["cost"] for s in state["segments"]), 2),
        "total_time_min": round(state["time_min"], 2),
        "total_time_hours": round(state["time_min"] / 60.0, 2),
        "aircraft_used": state["aircraft_used"],
        "jobs_done": state.get("jobs_done", []),
        "total_earned": round(state.get("total_earned", 0.0), 2),
        "obligatory_cost_total": round(state.get("obligatory_cost_total", 0.0), 2),
        "path": path,
        "remaining_budget": round(state["budget"], 2),
        "finished": state["finished"],
    }
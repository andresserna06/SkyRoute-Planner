# dynamicService.py — R3: pure-function step-by-step planner (no I/O).
# All state transitions take a state dict and return a new state dict.
# The web dashboard calls these functions from its callbacks.

from services.itineraryService import _edge_cost, _edge_time


# ── Journey state initializer ─────────────────────────────────────────────────

def init_journey_state(origin_id, initial_budget, threshold_pct=35):
    return {
        "current_id":          origin_id,
        "budget":              float(initial_budget),
        "initial_budget":      float(initial_budget),
        "threshold_pct":       threshold_pct,
        "time_min":            0.0,
        "visited":             [origin_id],
        "segments":            [],
        "aircraft_used":       [],
        "jobs_taken":          [],
        "money_earned":        0.0,
        "subsidized_km":       0.0,
        "total_km":            0.0,
        "destination_details": [],
        "activities_done":     [],
        "phase":               "flying",   # flying | arrival | complete
        "arrival_data":        None,
    }


# ── Read-only queries (do not mutate state) ───────────────────────────────────

def get_flight_options(graph, state):
    vertex = graph.get_vertex(state["current_id"])
    if vertex is None:
        return []
    visited_set = set(state["visited"])
    options = []
    for edge in vertex.adjacencies:
        dest_id = edge.destination_vertex.id
        if dest_id in visited_set:
            continue
        for aircraft in edge.aircraft:
            cost     = _edge_cost(edge, aircraft, graph.aircraft_config,
                                  state["subsidized_km"], state["total_km"])
            time_min = _edge_time(edge, aircraft, graph.aircraft_config)
            if cost <= state["budget"]:
                options.append({
                    "destination":   dest_id,
                    "dest_name":     edge.destination_vertex.name,
                    "aircraft":      aircraft,
                    "cost":          round(cost, 2),
                    "time_min":      round(time_min, 2),
                    "distance_km":   edge.distance_km,
                    "is_subsidized": edge.base_cost == 0,
                    "is_free":       edge.base_cost == 0 and cost == 0.0,
                })
    return options


def get_available_jobs(graph, state):
    budget_pct = (state["budget"] / state["initial_budget"]) * 100
    if budget_pct >= state["threshold_pct"]:
        return []
    vertex = graph.get_vertex(state["current_id"])
    return vertex.jobs if vertex and vertex.jobs else []


# ── State transitions ─────────────────────────────────────────────────────────

def apply_flight(graph, state, dest_id, aircraft):
    # Find the matching edge
    vertex = graph.get_vertex(state["current_id"])
    edge = next(
        (e for e in vertex.adjacencies
         if e.destination_vertex.id == dest_id and aircraft in e.aircraft),
        None,
    )
    if edge is None:
        return state

    cost     = _edge_cost(edge, aircraft, graph.aircraft_config,
                          state["subsidized_km"], state["total_km"])
    time_min = _edge_time(edge, aircraft, graph.aircraft_config)

    new_aircraft = list(state["aircraft_used"])
    if aircraft not in new_aircraft:
        new_aircraft.append(aircraft)

    new_state = {
        **state,
        "budget":        round(state["budget"] - cost, 2),
        "time_min":      state["time_min"] + time_min,
        "total_km":      state["total_km"] + edge.distance_km,
        "subsidized_km": state["subsidized_km"] + (edge.distance_km if edge.base_cost == 0 and cost == 0.0 else 0),
        "visited":       state["visited"] + [dest_id],
        "aircraft_used": new_aircraft,
        "segments":      state["segments"] + [{
            "origin":      state["current_id"],
            "destination": dest_id,
            "aircraft":    aircraft,
            "distance_km": edge.distance_km,
            "cost":        round(cost, 2),
            "time_min":    round(time_min, 2),
        }],
        "current_id":    dest_id,
        "phase":         "arrival",
        "arrival_data":  _build_arrival_data(edge, edge.destination_vertex),
    }
    return new_state


def apply_arrival(state):
    # Charge stay costs + mandatory activities, transition to flying phase.
    arrival = state["arrival_data"]
    if not arrival:
        return {**state, "phase": "flying"}

    stay_days     = arrival["stay_days"]
    accommodation = arrival["accommodation"]
    food          = arrival["food"]
    stay_cost     = accommodation + food

    new_budget   = round(state["budget"] - stay_cost, 2)
    new_time_min = state["time_min"] + stay_days * 24 * 60

    dest_record = {
        "id":                arrival["id"],
        "name":              arrival["name"],
        "city":              arrival["city"],
        "country":           arrival["country"],
        "stay_days":         stay_days,
        "accommodation":     accommodation,
        "food":              food,
        "activity_cost":     0.0,
        "activity_time_min": 0,
        "activities_done":   [],
        "total_cost":        stay_cost,
    }

    new_activities = list(state["activities_done"])
    for act in arrival.get("mandatory_activities", []):
        cost    = act.get("costUSD", 0)
        dur_min = act.get("durationMin", 0)
        new_budget   -= cost
        new_time_min += dur_min
        record = {"airport": arrival["id"], "name": act["name"], "type": "obligatoria",
                  "duration_min": dur_min, "cost": cost}
        dest_record["activity_cost"]     += cost
        dest_record["activity_time_min"] += dur_min
        dest_record["total_cost"]        += cost
        dest_record["activities_done"].append(record)
        new_activities.append(record)

    dest_record["activity_cost"] = round(dest_record["activity_cost"], 2)
    dest_record["total_cost"]    = round(dest_record["total_cost"], 2)

    return {
        **state,
        "budget":              round(new_budget, 2),
        "time_min":            new_time_min,
        "destination_details": state["destination_details"] + [dest_record],
        "activities_done":     new_activities,
        "phase":               "flying",
    }


def apply_optional_activities(state, selected_indices):
    # selected_indices: list of ints (0-based) into arrival_data["optional_activities"]
    arrival  = state["arrival_data"]
    optional = arrival.get("optional_activities", []) if arrival else []

    new_budget   = state["budget"]
    new_time_min = state["time_min"]
    new_activities = list(state["activities_done"])
    new_details    = list(state["destination_details"])
    last = dict(new_details[-1]) if new_details else None

    for idx in selected_indices:
        if idx < 0 or idx >= len(optional):
            continue
        act  = optional[idx]
        cost = act.get("costUSD", 0)
        dur  = act.get("durationMin", 0)
        if cost > new_budget:
            continue
        new_budget   -= cost
        new_time_min += dur
        record = {"airport": arrival["id"], "name": act["name"], "type": "opcional",
                  "duration_min": dur, "cost": cost}
        new_activities.append(record)
        if last is not None:
            last = {**last,
                    "activity_cost":     round(last["activity_cost"] + cost, 2),
                    "activity_time_min": last["activity_time_min"] + dur,
                    "total_cost":        round(last["total_cost"] + cost, 2),
                    "activities_done":   last["activities_done"] + [record]}

    if last is not None:
        new_details[-1] = last

    return {
        **state,
        "budget":              round(new_budget, 2),
        "time_min":            new_time_min,
        "activities_done":     new_activities,
        "destination_details": new_details,
        "phase":               "flying",
    }


def apply_job(graph, state, job_idx, hours):
    jobs = get_available_jobs(graph, state)
    if not jobs or job_idx < 0 or job_idx >= len(jobs):
        return state
    job = jobs[job_idx]
    hours = float(hours)
    if hours <= 0 or hours > job["maxHours"]:
        return state
    earned = round(hours * job["hourlyRate"], 2)
    return {
        **state,
        "budget":       round(state["budget"] + earned, 2),
        "time_min":     state["time_min"] + hours * 60,
        "money_earned": round(state["money_earned"] + earned, 2),
        "jobs_taken":   state["jobs_taken"] + [{
            "airport": state["current_id"],
            "job":     job["name"],
            "hours":   hours,
            "earned":  earned,
        }],
    }


def finish_journey(state):
    return {**state, "phase": "complete"}


def build_summary(state):
    initial = state["initial_budget"]
    return {
        "success":              True,
        "origin":               state["visited"][0] if state["visited"] else "",
        "initial_budget":       initial,
        "destinations_visited": len(state["visited"]) - 1,
        "destination_details":  state["destination_details"],
        "segments":             state["segments"],
        "activities_done":      state["activities_done"],
        "total_cost":           round(initial - state["budget"], 2),
        "total_time_hours":     round(state["time_min"] / 60.0, 2),
        "aircraft_used":        state["aircraft_used"],
        "path":                 state["visited"],
        "jobs_taken":           state["jobs_taken"],
        "money_earned":         state["money_earned"],
        "budget_remaining":     state["budget"],
        "subsidized_km":        round(state["subsidized_km"], 2),
        "total_km":             round(state["total_km"], 2),
    }


# ── Internal helper ───────────────────────────────────────────────────────────

def _build_arrival_data(edge, dest_vertex):
    stay_days = edge.minimum_stay
    return {
        "id":                   dest_vertex.id,
        "name":                 dest_vertex.name,
        "city":                 dest_vertex.city,
        "country":              dest_vertex.country,
        "stay_days":            stay_days,
        "accommodation":        round(dest_vertex.accommodation_cost * stay_days, 2),
        "food":                 round(dest_vertex.food_cost * stay_days, 2),
        "mandatory_activities": [a for a in (dest_vertex.activities or [])
                                 if a.get("type") == "obligatoria"],
        "optional_activities":  [a for a in (dest_vertex.activities or [])
                                 if a.get("type") != "obligatoria"],
    }

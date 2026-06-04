"""
itineraryService.py — Basic Itinerary Planning (Requirement 2.2)

Provides three core functions for the SkyRoute Planner:

    1. propose_max_coverage_by_budget (Proposal A)
       Maximises the number of visited airports without exceeding a given
       budget in USD.  Internally uses DFS with pruning.

    2. propose_max_coverage_by_time (Proposal B)
       Maximises the number of visited airports without exceeding a given
       time limit in hours.  Internally uses DFS with pruning.

    3. find_best_routes (Manual search)
       Computes the optimal route between a user-provided origin and
       destination for each selected optimisation criterion (distance,
       time, cost) using Dijkstra's algorithm.

Algorithm selection rationale
-----------------------------
*Max-coverage under constraints (Proposals A & B)*
  The problem of visiting as many distinct vertices as possible while
  staying within a resource budget is a variant of the Orienteering
  Problem, which is NP-hard.  For the small-to-medium graphs in this
  project (≈30 nodes), a DFS with aggressive pruning explores the
  entire feasible space efficiently.  Greedy approaches would sacrifice
  optimality, while dynamic programming is impractical because the
  resource constraints are continuous.

*Point-to-point shortest path (Manual search)*
  Dijkstra's algorithm is the natural choice for finding a minimum-weight
  path in a directed graph with non-negative edge weights.  All criteria
  (distance, time, fuel cost) produce non-negative weights.
"""

import math

from models.graph import Graph


# ──────────────────────────────────────────────────────────────────────
# Helper: pick the best aircraft for an edge given a criterion
# ──────────────────────────────────────────────────────────────────────

def _pick_aircraft(edge, criterion, aircraft_config, preferred_set):
    """
    Selects the best aircraft available on *edge* for the given criterion.

    Parameters
    ----------
    edge : Edge
        The route whose available aircraft list is inspected.
    criterion : str
        ``"budget"`` → cheapest cost per km;
        ``"time"``   → fastest time per km;
        ``"cost"``   → same as budget;
        ``"distance"`` → any aircraft (first valid).
    aircraft_config : dict
        Mapping of aircraft name → {"costPerKm": float, "timePerKm": float}.
    preferred_set : set of str
        Aircraft types the user is willing to use (empty = all allowed).

    Returns
    -------
    str
        The chosen aircraft name, or ``None`` if no valid aircraft exists.
    """
    valid = [a for a in edge.aircraft if not preferred_set or a in preferred_set]
    if not valid:
        return None

    if criterion in ("budget", "cost"):
        key = lambda a: aircraft_config[a]["costPerKm"]
    elif criterion == "time":
        key = lambda a: aircraft_config[a]["timePerKm"]
    else:  # distance — first valid
        return valid[0]

    return min(valid, key=key)


def _edge_cost(edge, aircraft, aircraft_config):
    """
    Calculates the cost in USD of traversing *edge* with the given *aircraft*.

    Subsidised routes (base_cost == 0):
      Only 20% of the route distance is free, the remaining 80% is
      charged at the normal rate.

    Formula (normal):     cost = distance_km * cost_per_km(aircraft)
    Formula (subsidised): cost = distance_km * 0.80 * cost_per_km(aircraft)

    Example:  Avion Comercial on BOG->LIM (1900 km)
              cost = 1900 * 0.18 = 342.0 USD

    Example:  Subsidised route BOG->MDE (230 km, Helice)
              cost = 230 * 0.80 * 0.12 = 22.08 USD
    """
    cost_per_km = aircraft_config[aircraft]["costPerKm"]

    if edge.base_cost == 0:
        return edge.distance_km * 0.80 * cost_per_km

    return edge.distance_km * cost_per_km


def _edge_time(edge, aircraft, aircraft_config):
    """
    Calculates the flight time in minutes of traversing *edge* with the
    given *aircraft*.

    Formula:  time = distance_km * time_per_km(aircraft)

    Example:  Avion Comercial on BOG->LIM (1900 km)
              time = 1900 * 0.7 = 1330.0 minutes
    """
    time_per_km = aircraft_config[aircraft]["timePerKm"]
    return edge.distance_km * time_per_km


# ──────────────────────────────────────────────────────────────────────
# DFS with pruning — maximum destination coverage
# ──────────────────────────────────────────────────────────────────────

def _dfs_max_coverage(graph, current_id, visited, budget_spent, time_spent,
                      budget_limit, time_limit_mins, aircraft_used, segments,
                      criterion, aircraft_config, preferred_set,
                      all_aircraft_types=None):
    """
    Explores the graph recursively, pruning branches that violate resource
    constraints, and returns the best result found from this state onward.

    Parameters mirror the public proposals below.

    all_aircraft_types : set of str, optional
        The complete set of aircraft types available in the graph.
        When provided, solutions that use every aircraft type are
        preferred over solutions with more destinations but incomplete
        coverage (Requirement 2.2 — transport diversity).

    Returns
    -------
    tuple (destinations_count, segments_list, budget_spent, time_spent,
           aircraft_used_set)
    """
    if all_aircraft_types is None:
        all_aircraft_types = set()

    current = graph.get_vertex(current_id)
    if current is None:
        return (len(visited), list(segments), budget_spent, time_spent,
                set(aircraft_used))

    best = (len(visited), list(segments), budget_spent, time_spent,
            set(aircraft_used))

    for edge in current.adjacencies:
        dest_id = edge.destination_vertex.id
        if dest_id in visited:
            continue

        chosen = _pick_aircraft(edge, criterion, aircraft_config, preferred_set)
        if chosen is None:
            continue

        ec = _edge_cost(edge, chosen, aircraft_config)
        et = _edge_time(edge, chosen, aircraft_config)

        new_budget = budget_spent + ec
        new_time = time_spent + et

        if new_budget > budget_limit or new_time > time_limit_mins:
            continue

        new_aircraft = set(aircraft_used)
        new_aircraft.add(chosen)

        new_visited = set(visited)
        new_visited.add(dest_id)

        new_segments = list(segments)
        new_segments.append({
            "origin": current_id,
            "destination": dest_id,
            "aircraft": chosen,
            "distance_km": edge.distance_km,
            "cost": round(ec, 2),
            "time_min": round(et, 2),
        })

        result = _dfs_max_coverage(
            graph, dest_id, new_visited,
            new_budget, new_time,
            budget_limit, time_limit_mins,
            new_aircraft, new_segments,
            criterion, aircraft_config, preferred_set,
            all_aircraft_types,
        )

        # Priority: aircraft diversity > destinations > resource consumption
        result_all = all_aircraft_types.issubset(result[4])
        best_all = all_aircraft_types.issubset(best[4])

        if result_all and not best_all:
            best = result
        elif best_all and not result_all:
            pass
        elif result[0] > best[0]:
            best = result
        elif result[0] == best[0]:
            if criterion == "budget" and result[2] < best[2]:
                best = result
            elif criterion == "time" and result[3] < best[3]:
                best = result

    return best


# ──────────────────────────────────────────────────────────────────────
# Public API — Proposal A
# ──────────────────────────────────────────────────────────────────────

def propose_max_coverage_by_budget(graph, origin_id, budget_usd,
                                   time_hours=float("inf"),
                                   preferred_aircraft=None):
    """
    Proposal A — Ruta de Máxima Cobertura por Presupuesto.

    Finds the itinerary that visits the most distinct airports without
    exceeding *budget_usd* (USD).  Among equal-coverage itineraries, the
    one with the smallest total cost is returned.

    Parameters
    ----------
    graph : Graph
        The air route network.
    origin_id : str
        IATA code of the departure airport.
    budget_usd : float
        Maximum allowed spending (hard constraint).
    time_hours : float, optional
        Maximum allowed travel time in hours (default: no limit).
    preferred_aircraft : set of str, optional
        Aircraft types the user is willing to use (default: all).

    Returns
    -------
    dict with keys:
        "success" : bool
        "error"   : str  (only when success is False)
        "origin"  : str
        "destinations_visited" : int
        "segments" : list[dict]
        "total_cost" : float
        "total_time_hours" : float
        "aircraft_used" : list[str]
        "path" : list[str]   (sequence of IATA codes)
    """
    if graph.get_vertex(origin_id) is None:
        return {"success": False, "error": f"Unknown origin airport: {origin_id}"}
    if preferred_aircraft is None:
        preferred_aircraft = set()

    pref_set = set(preferred_aircraft) if preferred_aircraft else set()
    time_limit_mins = time_hours * 60.0
    all_types = set(graph.aircraft_config.keys())

    _, segments, total_cost, total_time, aircraft_used = _dfs_max_coverage(
        graph, origin_id, {origin_id},
        0.0, 0.0,
        budget_usd, time_limit_mins,
        set(), [],
        "budget", graph.aircraft_config, pref_set,
        all_types,
    )

    if not segments:
        return {
            "success": True,
            "origin": origin_id,
            "destinations_visited": 0,
            "segments": [],
            "total_cost": 0.0,
            "total_time_hours": 0.0,
            "aircraft_used": [],
            "path": [origin_id],
            "note": "No additional destinations reachable within the given budget and time.",
        }

    path = [origin_id]
    for s in segments:
        path.append(s["destination"])

    return {
        "success": True,
        "origin": origin_id,
        "destinations_visited": len(segments),
        "segments": segments,
        "total_cost": round(total_cost, 2),
        "total_time_hours": round(total_time / 60.0, 2),
        "aircraft_used": list(aircraft_used),
        "path": path,
    }


# ──────────────────────────────────────────────────────────────────────
# Public API — Proposal B
# ──────────────────────────────────────────────────────────────────────

def propose_max_coverage_by_time(graph, origin_id, time_hours,
                                 budget_usd=float("inf"),
                                 preferred_aircraft=None):
    """
    Proposal B — Ruta de Máxima Cobertura por Tiempo.

    Finds the itinerary that visits the most distinct airports without
    exceeding *time_hours*.  Among equal-coverage itineraries, the one
    with the smallest total time is returned.

    Parameters
    ----------
    graph : Graph
        The air route network.
    origin_id : str
        IATA code of the departure airport.
    time_hours : float
        Maximum allowed travel time in hours (hard constraint).
    budget_usd : float, optional
        Maximum allowed spending in USD (default: no limit).
    preferred_aircraft : set of str, optional
        Aircraft types the user is willing to use (default: all).

    Returns
    -------
    dict (same structure as propose_max_coverage_by_budget).
    """
    if graph.get_vertex(origin_id) is None:
        return {"success": False, "error": f"Unknown origin airport: {origin_id}"}
    if preferred_aircraft is None:
        preferred_aircraft = set()

    pref_set = set(preferred_aircraft) if preferred_aircraft else set()
    time_limit_mins = time_hours * 60.0
    all_types = set(graph.aircraft_config.keys())

    _, segments, total_cost, total_time, aircraft_used = _dfs_max_coverage(
        graph, origin_id, {origin_id},
        0.0, 0.0,
        budget_usd, time_limit_mins,
        set(), [],
        "time", graph.aircraft_config, pref_set,
        all_types,
    )

    if not segments:
        return {
            "success": True,
            "origin": origin_id,
            "destinations_visited": 0,
            "segments": [],
            "total_cost": 0.0,
            "total_time_hours": 0.0,
            "aircraft_used": [],
            "path": [origin_id],
            "note": "No additional destinations reachable within the given time and budget.",
        }

    path = [origin_id]
    for s in segments:
        path.append(s["destination"])

    return {
        "success": True,
        "origin": origin_id,
        "destinations_visited": len(segments),
        "segments": segments,
        "total_cost": round(total_cost, 2),
        "total_time_hours": round(total_time / 60.0, 2),
        "aircraft_used": list(aircraft_used),
        "path": path,
    }


# ──────────────────────────────────────────────────────────────────────
# Public API — Manual Route Search (multiple criteria)
# ──────────────────────────────────────────────────────────────────────

def _criterion_weight_fn(criterion, aircraft_config, preferred_set):
    """
    Returns a weight function for Dijkstra based on the optimisation
    criterion.

    The returned callable accepts an Edge and returns the numeric weight
    (always non-negative).

    Parameters
    ----------
    criterion : str
        ``"distance"``, ``"time"``, or ``"cost"``.
    aircraft_config : dict
    preferred_set : set of str

    Returns
    -------
    callable  (edge → float)
    """
    def weight_fn(edge):
        chosen = _pick_aircraft(edge, criterion, aircraft_config, preferred_set)
        if chosen is None:
            return float("inf")
        if criterion == "distance":
            return edge.distance_km
        if criterion == "time":
            return _edge_time(edge, chosen, aircraft_config)
        if criterion == "cost":
            return _edge_cost(edge, chosen, aircraft_config)
        return edge.distance_km
    return weight_fn


def _criterion_edge_filter(include_secondary, origin_id=None):
    """
    Returns an edge filter that optionally excludes edges whose
    destination is a secondary (non-hub) airport.

    Parameters
    ----------
    include_secondary : bool
        If False, edges leading to non-hub airports are blocked.

    Returns
    -------
    callable  (edge → bool)
    """
    def edge_filter(edge):
        if not include_secondary and not edge.destination_vertex.is_hub:
            return False
        return True
    return edge_filter


def find_best_routes(graph, origin_id, destination_id, criteria,
                     include_secondary=True, preferred_aircraft=None):
    """
    Computes the optimal route between *origin_id* and *destination_id*
    for each selected criterion using Dijkstra's algorithm.

    Parameters
    ----------
    graph : Graph
    origin_id : str
    destination_id : str
    criteria : list of str
        Any subset of ``"distance"``, ``"time"``, ``"cost"``.
    include_secondary : bool
        If False, secondary airports are excluded from routing.
    preferred_aircraft : set of str, optional
        Aircraft types the user is willing to use (default: all).

    Returns
    -------
    list of dict:
        One result per criterion, each with keys:
        "criterion", "success", "error",
        "path" (list of IATA codes),
        "segments" (with aircraft details),
        "total_weight".
        If a criterion cannot produce a valid route, success is False.
    """
    if graph.get_vertex(origin_id) is None:
        return [{"criterion": c, "success": False,
                 "error": f"Unknown origin: {origin_id}"} for c in criteria]
    if graph.get_vertex(destination_id) is None:
        return [{"criterion": c, "success": False,
                 "error": f"Unknown destination: {destination_id}"} for c in criteria]

    if preferred_aircraft is None:
        preferred_aircraft = set()
    pref_set = set(preferred_aircraft) if preferred_aircraft else set()
    edge_filter = _criterion_edge_filter(include_secondary)

    results = []

    for criterion in criteria:
        c = criterion.lower().strip()
        if c not in ("distance", "time", "cost"):
            results.append({"criterion": criterion, "success": False,
                            "error": f"Unknown criterion: {criterion}"})
            continue

        weight_fn = _criterion_weight_fn(c, graph.aircraft_config, pref_set)
        d, p, path = graph.dijkstra(origin_id, destination_id, weight_fn, edge_filter, criterion=c)

        if path is None or len(path) == 0 or d.get(destination_id, math.inf) == math.inf:
            results.append({"criterion": c, "success": False,
                            "error": "No valid route found."})
            continue

        # Build segment details from the path
        built_segments = []
        for i in range(len(path) - 1):
            o = path[i]
            dst = path[i + 1]
            origin_v = graph.get_vertex(o)
            edge_obj = None
            for e in origin_v.adjacencies:
                if e.destination_vertex.id == dst:
                    edge_obj = e
                    break
            chosen = _pick_aircraft(edge_obj, c, graph.aircraft_config, pref_set) \
                if edge_obj else "Unknown"
            built_segments.append({
                "origin": o,
                "destination": dst,
                "aircraft": chosen or "Unknown",
                "distance_km": edge_obj.distance_km if edge_obj else 0,
                "weight": round(d[dst] - d[o], 2),
            })

        results.append({
            "criterion": c,
            "success": True,
            "path": path,
            "segments": built_segments,
            "total_weight": round(d[destination_id], 2),
        })

    return results

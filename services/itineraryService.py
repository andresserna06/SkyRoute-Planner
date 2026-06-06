# itineraryService.py — R2.2: DFS max-coverage proposals + Dijkstra manual search
#
# Proposal A/B use DFS with pruning (orienteering problem, NP-hard,
# feasible for ~30 nodes).  Manual search uses Dijkstra on non-negative
# edge weights (distance, time, cost).

import math

from models.graph import Graph


# ──────────────────────────────────────────────────────────────────────
# Helper: pick the best aircraft for an edge given a criterion
# ──────────────────────────────────────────────────────────────────────

def _pick_aircraft(edge, criterion, aircraft_config, preferred_set):
    # Pick the best aircraft on an edge for a given criterion
    # Returns aircraft name or None if none available
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


def _edge_cost(edge, aircraft, aircraft_config, subsidized_km=0.0, total_km=0.0):
    # Cost = distance_km * cost_per_km.
    # Subsidised routes (base_cost == 0) are free unless the traveler has already
    # used subsidised routes for more than 20 % of total distance traveled —
    # in that case the segment is charged at full price.
    cost_per_km = aircraft_config[aircraft]["costPerKm"]

    if edge.base_cost == 0:
        projected_sub   = subsidized_km + edge.distance_km
        projected_total = total_km + edge.distance_km
        if projected_total > 0 and projected_sub / projected_total > 0.20:
            return edge.distance_km * cost_per_km  # limit exceeded — full price
        return 0.0  # within the 20 % allowance — free

    return edge.distance_km * cost_per_km


def _edge_time(edge, aircraft, aircraft_config):
    # Time = distance_km * time_per_km (in minutes)
    time_per_km = aircraft_config[aircraft]["timePerKm"]
    return edge.distance_km * time_per_km


# ──────────────────────────────────────────────────────────────────────
# DFS with pruning — maximum destination coverage
# ──────────────────────────────────────────────────────────────────────

def _dfs_max_coverage(graph, current_id, visited, budget_spent, time_spent,
                      budget_limit, time_limit_mins, aircraft_used, segments,
                      criterion, aircraft_config, preferred_set,
                      all_aircraft_types=None):
    # DFS with pruning: returns (destinations_count, segments, budget, time, aircraft_set)
    # Prioritises solutions that use all aircraft types (R2.2 transport diversity)
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
    # Proposal A: max destinations under a budget constraint using DFS
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
    # Proposal B: max destinations under a time constraint using DFS
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
    # Returns a weight function (edge -> float) for Dijkstra based on criterion
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
    # Returns an edge filter that optionally excludes secondary airports
    def edge_filter(edge):
        if not include_secondary and not edge.destination_vertex.is_hub:
            return False
        return True
    return edge_filter


def find_best_routes(graph, origin_id, destination_id, criteria,
                     include_secondary=True, preferred_aircraft=None):
    # Dijkstra-based manual search: one result per criterion (distance, time, cost)
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

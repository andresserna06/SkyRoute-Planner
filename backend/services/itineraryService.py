# ── ITEM 2.2 — DFS proposals A/B (max destinations by budget or time)
#               + Dijkstra route search by distance/time/cost (2.2.c) ──

import math


# ──────────────────────────────────────────────────────────────────────
# ITEM 2.2 (shared) — Aircraft selection: picks optimal aircraft per criterion
#                     Edge cost/time with subsidized route 20% rule
# ──────────────────────────────────────────────────────────────────────

def _pick_aircraft(edge, criterion, aircraft_config, preferred_set):

    # Filter preferred aircraft if provided
    valid = [
        a for a in edge.aircraft
        if not preferred_set or a in preferred_set
    ]

    if not valid:
        return None

    # Distance does not optimize aircraft
    if criterion == "distance":
        return valid[0]

    # Cost optimization
    if criterion in ("budget", "cost"):
        key = lambda a: aircraft_config[a]["costPerKm"]

    # Time optimization
    elif criterion == "time":
        key = lambda a: aircraft_config[a]["timePerKm"]

    else:
        return valid[0]

    return min(valid, key=key)


def _edge_cost(edge, aircraft, aircraft_config):
    # Cost = distance * cost_per_km
    # Subsidized routes (base_cost == 0) are free
    cost_per_km = aircraft_config[aircraft]["costPerKm"]
    if edge.base_cost == 0:
        return 0.0
    return edge.distance_km * cost_per_km


def _edge_time(edge, aircraft, aircraft_config):

    # Time returned in MINUTES
    time_per_km = aircraft_config[aircraft]["timePerKm"]

    return edge.distance_km * time_per_km


def _exceeds_subsidized_limit(edge, subsidized_km, total_km):

    # Rule only applies to subsidized routes
    if edge.base_cost != 0:
        return False

    # First segment always allowed
    if total_km == 0:
        return False

    new_total = total_km + edge.distance_km
    new_subsidized = subsidized_km + edge.distance_km

    return new_subsidized > 0.20 * new_total


# ──────────────────────────────────────────────────────────────────────
# ITEM 2.2.a / 2.2.b — DFS with pruning (orienteering, ~30 nodes feasible)
#   Maximises destinations while respecting budget (2.2.a) or time (2.2.b)
#   Enforces aircraft diversity (all types used at least once)
# ──────────────────────────────────────────────────────────────────────

def _dfs_max_coverage(
    graph,
    current_id,
    visited,
    budget_spent,
    time_spent_min,
    budget_limit,
    time_limit_min,
    aircraft_used,
    segments,
    criterion,
    aircraft_config,
    preferred_set,
    all_aircraft_types=None,
    subsidized_km=0.0,
    total_km=0.0
):

    if all_aircraft_types is None:
        all_aircraft_types = set()

    current = graph.get_vertex(current_id)

    if current is None:
        return (
            len(visited),
            list(segments),
            budget_spent,
            time_spent_min,
            set(aircraft_used)
        )

    best = (
        len(visited),
        list(segments),
        budget_spent,
        time_spent_min,
        set(aircraft_used)
    )

    for edge in current.adjacencies:

        destination_id = edge.destination_vertex.id

        if destination_id in visited:
            continue

        chosen_aircraft = _pick_aircraft(
            edge,
            criterion,
            aircraft_config,
            preferred_set
        )

        if chosen_aircraft is None:
            continue

        edge_cost = _edge_cost(
            edge,
            chosen_aircraft,
            aircraft_config
        )

        edge_time_min = _edge_time(
            edge,
            chosen_aircraft,
            aircraft_config
        )

        # Enforce subsidized route limit
        if _exceeds_subsidized_limit(
            edge,
            subsidized_km,
            total_km
        ):
            continue

        new_total_km = total_km + edge.distance_km

        new_subsidized_km = subsidized_km + (
            edge.distance_km
            if edge.base_cost == 0 else 0
        )

        new_budget = budget_spent + edge_cost
        new_time_min = time_spent_min + edge_time_min

        # Resource constraints
        if (
            new_budget > budget_limit or
            new_time_min > time_limit_min
        ):
            continue

        # Track aircraft diversity
        new_aircraft_used = set(aircraft_used)
        new_aircraft_used.add(chosen_aircraft)

        # Track visited airports
        new_visited = set(visited)
        new_visited.add(destination_id)

        # Build segment
        new_segments = list(segments)

        new_segments.append({
            "origin": current_id,
            "destination": destination_id,
            "aircraft": chosen_aircraft,

            "distance_km": edge.distance_km,

            "cost": round(edge_cost, 2),

            "time_min": round(edge_time_min, 2),

            "time_hours": round(
                edge_time_min / 60.0,
                2
            )
        })

        # Recursive DFS
        result = _dfs_max_coverage(
            graph,
            destination_id,
            new_visited,
            new_budget,
            new_time_min,
            budget_limit,
            time_limit_min,
            new_aircraft_used,
            new_segments,
            criterion,
            aircraft_config,
            preferred_set,
            all_aircraft_types,
            new_subsidized_km,
            new_total_km
        )

        # Priorities:
        # 1. Aircraft diversity
        # 2. Destination count
        # 3. Lower resource usage

        result_uses_all = all_aircraft_types.issubset(result[4])
        best_uses_all = all_aircraft_types.issubset(best[4])

        if result_uses_all and not best_uses_all:
            best = result

        elif best_uses_all and not result_uses_all:
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
# ITEM 2.2.a — Proposal A: route visiting max destinations without exceeding budget
#   Input: origin, budget_usd, time_hours, preferred_aircraft
#   Output: flight sequence, costs per segment, cumulative total
# ──────────────────────────────────────────────────────────────────────

def propose_max_coverage_by_budget(
    graph,
    origin_id,
    budget_usd,
    time_hours=float("inf"),
    preferred_aircraft=None
):

    if graph.get_vertex(origin_id) is None:
        return {
            "success": False,
            "error": f"Unknown origin airport: {origin_id}"
        }

    if preferred_aircraft is None:
        preferred_aircraft = set()

    preferred_set = (
        set(preferred_aircraft)
        if preferred_aircraft else set()
    )

    time_limit_min = time_hours * 60.0

    all_aircraft_types = set(
        graph.aircraft_config.keys()
    )

    (
        _,
        segments,
        total_cost,
        total_time_min,
        aircraft_used
    ) = _dfs_max_coverage(
        graph,
        origin_id,
        {origin_id},
        0.0,
        0.0,
        budget_usd,
        time_limit_min,
        set(),
        [],
        "budget",
        graph.aircraft_config,
        preferred_set,
        all_aircraft_types
    )

    if not segments:
        return {
            "success": True,
            "origin": origin_id,
            "destinations_visited": 0,
            "segments": [],
            "total_cost": 0.0,
            "total_time_min": 0.0,
            "total_time_hours": 0.0,
            "aircraft_used": [],
            "path": [origin_id],
            "note": (
                "No additional destinations reachable "
                "within the given budget and time."
            )
        }

    path = [origin_id]

    for segment in segments:
        path.append(segment["destination"])

    return {
        "success": True,
        "origin": origin_id,

        "destinations_visited": len(segments),

        "segments": segments,

        "total_cost": round(total_cost, 2),

        "total_time_min": round(total_time_min, 2),

        "total_time_hours": round(
            total_time_min / 60.0,
            2
        ),

        "aircraft_used": list(aircraft_used),

        "path": path
    }


# ──────────────────────────────────────────────────────────────────────
# ITEM 2.2.b — Proposal B: route visiting max destinations within available time
#   Input: origin, time_hours, budget_usd, preferred_aircraft
#   Output: flight sequence, duration per segment, cumulative time
# ──────────────────────────────────────────────────────────────────────

def propose_max_coverage_by_time(
    graph,
    origin_id,
    time_hours,
    budget_usd=float("inf"),
    preferred_aircraft=None
):

    if graph.get_vertex(origin_id) is None:
        return {
            "success": False,
            "error": f"Unknown origin airport: {origin_id}"
        }

    if preferred_aircraft is None:
        preferred_aircraft = set()

    preferred_set = (
        set(preferred_aircraft)
        if preferred_aircraft else set()
    )

    time_limit_min = time_hours * 60.0

    all_aircraft_types = set(
        graph.aircraft_config.keys()
    )

    (
        _,
        segments,
        total_cost,
        total_time_min,
        aircraft_used
    ) = _dfs_max_coverage(
        graph,
        origin_id,
        {origin_id},
        0.0,
        0.0,
        budget_usd,
        time_limit_min,
        set(),
        [],
        "time",
        graph.aircraft_config,
        preferred_set,
        all_aircraft_types
    )

    if not segments:
        return {
            "success": True,
            "origin": origin_id,
            "destinations_visited": 0,
            "segments": [],
            "total_cost": 0.0,
            "total_time_min": 0.0,
            "total_time_hours": 0.0,
            "aircraft_used": [],
            "path": [origin_id],
            "note": (
                "No additional destinations reachable "
                "within the given time and budget."
            )
        }

    path = [origin_id]

    for segment in segments:
        path.append(segment["destination"])

    return {
        "success": True,
        "origin": origin_id,

        "destinations_visited": len(segments),

        "segments": segments,

        "total_cost": round(total_cost, 2),

        "total_time_min": round(total_time_min, 2),

        "total_time_hours": round(
            total_time_min / 60.0,
            2
        ),

        "aircraft_used": list(aircraft_used),

        "path": path
    }


# ──────────────────────────────────────────────────────────────────────
# ITEM 2.2.c — Dijkstra helpers: weight function (cost/time/distance) + edge filter (secondary toggle)
# ──────────────────────────────────────────────────────────────────────

def _criterion_weight_fn(
    criterion,
    aircraft_config,
    preferred_set
):

    def weight_fn(edge):

        chosen_aircraft = _pick_aircraft(
            edge,
            criterion,
            aircraft_config,
            preferred_set
        )

        if chosen_aircraft is None:
            return float("inf")

        if criterion == "distance":
            return edge.distance_km

        if criterion == "time":
            return _edge_time(
                edge,
                chosen_aircraft,
                aircraft_config
            )

        if criterion == "cost":
            return _edge_cost(
                edge,
                chosen_aircraft,
                aircraft_config
            )

        return edge.distance_km

    return weight_fn


def _criterion_edge_filter(include_secondary):

    def edge_filter(edge):

        if (
            not include_secondary and
            not edge.destination_vertex.is_hub
        ):
            return False

        return True

    return edge_filter


# ──────────────────────────────────────────────────────────────────────
# ITEM 2.2.c — Manual route search: Dijkstra by distance, time, or cost
#   Supports: origin/destination, multiple criteria, secondary airport toggle,
#             preferred aircraft filter. Returns one result per criterion.
# ──────────────────────────────────────────────────────────────────────

def find_best_routes(
    graph,
    origin_id,
    destination_id,
    criteria,
    include_secondary=True,
    preferred_aircraft=None
):

    if graph.get_vertex(origin_id) is None:
        return [{
            "criterion": c,
            "success": False,
            "error": f"Unknown origin: {origin_id}"
        } for c in criteria]

    if graph.get_vertex(destination_id) is None:
        return [{
            "criterion": c,
            "success": False,
            "error": f"Unknown destination: {destination_id}"
        } for c in criteria]

    if preferred_aircraft is None:
        preferred_aircraft = set()

    preferred_set = (
        set(preferred_aircraft)
        if preferred_aircraft else set()
    )

    edge_filter = _criterion_edge_filter(
        include_secondary
    )

    results = []

    for criterion in criteria:

        normalized = criterion.lower().strip()

        if normalized not in (
            "distance",
            "time",
            "cost"
        ):

            results.append({
                "criterion": criterion,
                "success": False,
                "error": (
                    f"Unknown criterion: {criterion}"
                )
            })

            continue

        weight_fn = _criterion_weight_fn(
            normalized,
            graph.aircraft_config,
            preferred_set
        )

        distances, previous, path = graph.dijkstra(
            origin_id,
            destination_id,
            weight_fn,
            edge_filter,
            criterion=normalized
        )

        if (
            path is None or
            len(path) == 0 or
            distances.get(destination_id, math.inf) == math.inf
        ):

            results.append({
                "criterion": normalized,
                "success": False,
                "error": "No valid route found."
            })

            continue

        built_segments = []

        for i in range(len(path) - 1):

            origin = path[i]
            destination = path[i + 1]

            origin_vertex = graph.get_vertex(origin)

            edge_obj = None

            for edge in origin_vertex.adjacencies:

                if edge.destination_vertex.id == destination:
                    edge_obj = edge
                    break

            chosen_aircraft = (
                _pick_aircraft(
                    edge_obj,
                    normalized,
                    graph.aircraft_config,
                    preferred_set
                )
                if edge_obj else "Unknown"
            )

            segment = {
                "origin": origin,
                "destination": destination,
                "aircraft": chosen_aircraft or "Unknown",
                "distance_km": (
                    edge_obj.distance_km
                    if edge_obj else 0
                )
            }

            metric_value = round(
                distances[destination] - distances[origin],
                2
            )

            if normalized == "distance":
                segment["distance_metric_km"] = metric_value

            elif normalized == "time":
                segment["time_metric_min"] = metric_value
                segment["time_metric_hours"] = round(
                    metric_value / 60.0,
                    2
                )

            elif normalized == "cost":
                segment["cost_metric_usd"] = metric_value

            built_segments.append(segment)

        total_metric = round(
            distances[destination_id],
            2
        )

        result = {
            "criterion": normalized,
            "success": True,
            "path": path,
            "segments": built_segments
        }

        if normalized == "distance":
            result["total_distance_km"] = total_metric

        elif normalized == "time":
            result["total_time_min"] = total_metric
            result["total_time_hours"] = round(
                total_metric / 60.0,
                2
            )

        elif normalized == "cost":
            result["total_cost_usd"] = total_metric

        results.append(result)

    return results

# ── END ITEM 2.2 ──

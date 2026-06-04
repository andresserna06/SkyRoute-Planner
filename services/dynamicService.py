# dynamicService.py — R2.3: interactive step-by-step planner where the traveler
# chooses aircraft per segment and can work at airports to earn more budget

from services.itineraryService import _edge_cost, _edge_time


def _list_available_flights(vertex, visited, aircraft_config, free_km, total_km, budget):
    # Return list of (edge, aircraft, cost, time) for affordable flights from vertex
    options = []
    for edge in vertex.adjacencies:
        dest_id = edge.destination_vertex.id
        if dest_id in visited:
            continue
        for aircraft in edge.aircraft:
            cost = _edge_cost(edge, aircraft, aircraft_config)
            time_min = _edge_time(edge, aircraft, aircraft_config)
            if cost <= budget:
                options.append((edge, aircraft, cost, time_min))
    return options


def _display_flights(origin_id, options):
    # Print available flights with aircraft, cost and time
    print(f"\n  Flights from {origin_id}:")
    print(f"  {'#':<3} {'Destination':<12} {'Aircraft':<22} {'Cost (USD)':<12} {'Time (min)':<10}")
    print(f"  {'-'*3} {'-'*12} {'-'*22} {'-'*12} {'-'*10}")
    for i, (edge, aircraft, cost, time_min) in enumerate(options):
        dest = edge.destination_vertex.id
        print(f"  {i+1:<3} {dest:<12} {aircraft:<22} {cost:<12.2f} {time_min:<10.0f}")


def _display_jobs(vertex):
    # Print available jobs at the current airport
    if not vertex.jobs:
        return []
    print(f"\n  Available jobs at {vertex.id}:")
    print(f"  {'#':<3} {'Job':<28} {'Hourly Rate':<14} {'Max Hours':<10}")
    print(f"  {'-'*3} {'-'*28} {'-'*14} {'-'*10}")
    for i, job in enumerate(vertex.jobs):
        print(f"  {i+1:<3} {job['name']:<28} ${job['hourlyRate']:<11.2f} {job['maxHours']:<10}")
    return vertex.jobs


def run_dynamic_itinerary(graph, origin_id, initial_budget):
    # Interactive loop: show flights -> traveller picks -> work at destination -> repeat
    current = graph.get_vertex(origin_id)
    if current is None:
        return {"success": False, "error": f"Unknown origin: {origin_id}"}

    state = {
        "current_id": origin_id,
        "budget": initial_budget,
        "time_min": 0.0,
        "visited": {origin_id},
        "segments": [],
        "aircraft_used": set(),
        "free_km": 0.0,
        "total_km": 0.0,
        "jobs_taken": [],
        "money_earned": 0.0,
    }

    print(f"\n{'='*60}")
    print(f"  DYNAMIC ITINERARY PLANNER (R2.3)")
    print(f"  Origin: {origin_id}  |  Initial budget: ${initial_budget:.2f}")
    print(f"{'='*60}")

    while True:
        vertex = graph.get_vertex(state["current_id"])
        options = _list_available_flights(
            vertex, state["visited"],
            graph.aircraft_config,
            state["free_km"], state["total_km"],
            state["budget"],
        )

        if not options:
            print(f"\n  No affordable flights from {state['current_id']}. Journey complete.")
            break

        _display_flights(state["current_id"], options)

        # Traveller picks a flight
        try:
            choice = input(f"\n  Choose flight (1-{len(options)}) or 0 to stop: ").strip()
            if choice == "0":
                print("  Journey ended by choice.")
                break
            idx = int(choice) - 1
            if idx < 0 or idx >= len(options):
                print("  Invalid choice.")
                continue
        except (ValueError, EOFError, KeyboardInterrupt):
            print("  Invalid input.")
            continue

        edge, chosen_aircraft, cost, time_min = options[idx]
        dest_id = edge.destination_vertex.id

        # Update state
        state["budget"] -= cost
        state["time_min"] += time_min
        state["visited"].add(dest_id)
        state["aircraft_used"].add(chosen_aircraft)
        state["total_km"] += edge.distance_km
        if edge.base_cost == 0:
            state["free_km"] += edge.distance_km

        state["segments"].append({
            "origin": state["current_id"],
            "destination": dest_id,
            "aircraft": chosen_aircraft,
            "distance_km": edge.distance_km,
            "cost": round(cost, 2),
            "time_min": round(time_min, 2),
        })
        state["current_id"] = dest_id

        # Show updated status
        print(f"\n  >>> {state['segments'][-1]['origin']} → {dest_id}")
        print(f"      Aircraft: {chosen_aircraft}")
        print(f"      Cost: ${cost:.2f}  |  Time: {time_min:.0f} min")
        print(f"      Remaining budget: ${state['budget']:.2f}")

        # Offer jobs at destination
        dest_vertex = graph.get_vertex(dest_id)
        jobs = _display_jobs(dest_vertex)

        if jobs:
            try:
                work = input(f"\n  Work at {dest_id}? (y/n): ").strip().lower()
                if work == "y":
                    print(f"  Choose a job (1-{len(jobs)}):")
                    job_choice = int(input("  Choose job: ")) - 1
                    if 0 <= job_choice < len(jobs):
                        hours = float(input("  Hours to work: "))
                        max_h = jobs[job_choice]["maxHours"]
                        if hours <= max_h:
                            earned = hours * jobs[job_choice]["hourlyRate"]
                            state["budget"] += earned
                            state["money_earned"] += earned
                            state["jobs_taken"].append({
                                "airport": dest_id,
                                "job": jobs[job_choice]["name"],
                                "hours": hours,
                                "earned": earned,
                            })
                            print(f"  Earned ${earned:.2f}. New budget: ${state['budget']:.2f}")
                        else:
                            print(f"  Max {max_h} hours. No work taken.")
            except (ValueError, EOFError, KeyboardInterrupt):
                print("  Invalid input. Continuing without work.")

    # Build summary
    summary = {
        "success": True,
        "origin": origin_id,
        "destinations_visited": len(state["visited"]) - 1,
        "segments": state["segments"],
        "total_cost": round(initial_budget - state["budget"], 2),
        "total_time_hours": round(state["time_min"] / 60.0, 2),
        "aircraft_used": list(state["aircraft_used"]),
        "path": [origin_id] + [s["destination"] for s in state["segments"]],
        "jobs_taken": state["jobs_taken"],
        "money_earned": round(state["money_earned"], 2),
    }

    print(f"\n{'='*60}")
    print(f"  ITINERARY COMPLETE")
    print(f"{'='*60}")
    print(f"  Destinations visited : {summary['destinations_visited']}")
    print(f"  Total cost (USD)    : {summary['total_cost']}")
    print(f"  Total time (hours)  : {summary['total_time_hours']}")
    print(f"  Money earned (jobs) : {summary['money_earned']}")
    print(f"  Aircraft used       : {', '.join(summary['aircraft_used']) if summary['aircraft_used'] else 'None'}")
    print(f"  Path                : {' → '.join(summary['path'])}")
    if summary["segments"]:
        print(f"\n  {'Segment':<35} {'Aircraft':<20} {'Cost':<10} {'Time(min)':<10}")
        print(f"  {'-'*35} {'-'*20} {'-'*10} {'-'*10}")
        for s in summary["segments"]:
            seg_str = f"{s['origin']} → {s['destination']}"
            print(f"  {seg_str:<35} {s['aircraft']:<20} {s['cost']:<10} {s['time_min']:<10}")
    print()

    return summary

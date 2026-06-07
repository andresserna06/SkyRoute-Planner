# SkyRoute Planner — Main entry point
# Usage: python app.py (interactive) or python app.py --test

import sys
from services.graphService import load_from_json
from services.itineraryService import (
    propose_max_coverage_by_budget,
    propose_max_coverage_by_time,
    find_best_routes,
)
from services.dynamicService import run_dynamic_itinerary


def list_airports(graph):
    # Print all airports with IATA code, city and country
    print(f"\n{'Code':<6} {'Type':<11} {'City, Country':<30}")
    print("-" * 50)
    for v in graph.vertices:
        label = "HUB" if v.is_hub else "secondary"
        print(f"{v.id:<6} {label:<11} {v.city}, {v.country:<25}")
    print()


def print_proposal_result(title, result):
    # Pretty-print a DFS proposal result
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    if not result["success"]:
        print(f"  ERROR: {result['error']}\n")
        return
    if "note" in result:
        print(f"  NOTE: {result['note']}\n")
        return
    print(f"  Destinations visited : {result['destinations_visited']}")
    print(f"  Total cost (USD)    : {result['total_cost']}")
    print(f"  Total time (hours)  : {result['total_time_hours']}")
    print(f"  Path                : {' → '.join(result['path'])}")
    print(f"  Aircraft used       : {', '.join(result['aircraft_used'])}")
    print(f"\n  {'Segment':<35} {'Aircraft':<20} {'Cost':<10} {'Time(min)':<10}")
    print(f"  {'-'*35} {'-'*20} {'-'*10} {'-'*10}")
    for s in result["segments"]:
        seg_str = f"{s['origin']} → {s['destination']}"
        print(f"  {seg_str:<35} {s['aircraft']:<20} {s['cost']:<10} {s['time_min']:<10}")
    print()


def print_route_results(results):
    # Pretty-print manual route search results
    for r in results:
        print(f"\n  Criterion: {r['criterion'].upper()}")
        if not r["success"]:
            print(f"    ERROR: {r['error']}")
            continue
        print(f"    Path    : {' → '.join(r['path'])}")
        print(f"    Total   : {r['total_weight']}")
        print(f"    Segments:")
        for s in r["segments"]:
            print(f"      {s['origin']} → {s['destination']} "
                  f"[{s['aircraft']}] {s['distance_km']} km  w={s['weight']}")
    print()


def run_interactive(graph):
    # Interactive CLI menu for R2.2 / R2.3
    while True:
        print("\n" + "=" * 60)
        print("   SKYROUTE PLANNER — Basic Itinerary Planning (R2.2)")
        print("=" * 60)
        print("  1. Show available airports")
        print("  2. Proposal A — Max coverage by budget")
        print("  3. Proposal B — Max coverage by time")
        print("  4. Manual route search (Dijkstra)")
        print("  5. Dynamic itinerary (R2.3)")
        print("  6. Visualise network (matplotlib)")
        print("  0. Exit")
        print("-" * 60)

        choice = input("  Select an option: ").strip()

        if choice == "1":
            list_airports(graph)

        elif choice == "2":
            origin = input("  Origin IATA code: ").strip().upper()
            try:
                budget = float(input("  Budget (USD): "))
                time_h = input("  Time limit in hours (optional, press Enter to skip): ").strip()
                time_h = float(time_h) if time_h else float("inf")
            except ValueError:
                print("  Invalid number.\n")
                continue
            pref = input("  Preferred aircraft (comma-separated, or Enter for all): ").strip()
            pref_set = set(a.strip() for a in pref.split(",")) if pref else set()
            result = propose_max_coverage_by_budget(graph, origin, budget, time_h, pref_set)
            print_proposal_result("PROPOSAL A — Max Coverage by Budget", result)

        elif choice == "3":
            origin = input("  Origin IATA code: ").strip().upper()
            try:
                time_h = float(input("  Time limit (hours): "))
                budget = input("  Budget limit in USD (optional, press Enter to skip): ").strip()
                budget = float(budget) if budget else float("inf")
            except ValueError:
                print("  Invalid number.\n")
                continue
            pref = input("  Preferred aircraft (comma-separated, or Enter for all): ").strip()
            pref_set = set(a.strip() for a in pref.split(",")) if pref else set()
            result = propose_max_coverage_by_time(graph, origin, time_h, budget, pref_set)
            print_proposal_result("PROPOSAL B — Max Coverage by Time", result)

        elif choice == "4":
            origin = input("  Origin IATA code: ").strip().upper()
            destination = input("  Destination IATA code: ").strip().upper()
            criteria_input = input("  Criteria (comma-separated: distance, time, cost): ").strip()
            criteria = [c.strip() for c in criteria_input.split(",")] if criteria_input else ["distance"]
            incl_sec = input("  Include secondary airports? (y/n, default y): ").strip().lower()
            include_secondary = incl_sec != "n"
            pref = input("  Preferred aircraft (comma-separated, or Enter for all): ").strip()
            pref_set = set(a.strip() for a in pref.split(",")) if pref else set()
            results = find_best_routes(graph, origin, destination, criteria,
                                       include_secondary, pref_set)
            print_route_results(results)

        elif choice == "5":
            origin = input("  Origin IATA code: ").strip().upper()
            try:
                budget = float(input("  Initial budget (USD): "))
            except ValueError:
                print("  Invalid number.\n")
                continue
            run_dynamic_itinerary(graph, origin, budget)

        elif choice == "6":
            graph.visualize()

        elif choice == "0":
            print("  Goodbye!\n")
            break

        else:
            print("  Invalid option.\n")


def run_tests():
    # Run pre-defined test cases for R2.2 validation
    print("Loading graph from data/air_network.json ...")
    graph = load_from_json("data/air_network.json")
    print(f"Loaded {len(graph.vertices)} airports.\n")

    # ── Test 1: Proposal A — Budget from BOG ──
    print("─" * 60)
    print("TEST 1: Proposal A — BOG, budget=300 USD")
    r = propose_max_coverage_by_budget(graph, "BOG", 300)
    print_proposal_result("Result", r)

    # ── Test 2: Proposal A — insufficient budget (edge case) ──
    print("─" * 60)
    print("TEST 2: Proposal A — BOG, budget=5 USD (expect no viable edges)")
    r = propose_max_coverage_by_budget(graph, "BOG", 5)
    print_proposal_result("Result", r)

    # ── Test 3: Proposal B — Time from LIM ──
    print("─" * 60)
    print("TEST 3: Proposal B — LIM, time=8 hours")
    r = propose_max_coverage_by_time(graph, "LIM", 8)
    print_proposal_result("Result", r)

    # ── Test 4: Manual search BOG → LIM, all criteria ──
    print("─" * 60)
    print("TEST 4: Manual search  BOG → LIM  [distance, time, cost]")
    results = find_best_routes(graph, "BOG", "LIM", ["distance", "time", "cost"])
    print_route_results(results)

    # ── Test 5: Unknown airport (edge case) ──
    print("─" * 60)
    print("TEST 5: Unknown origin (should report error)")
    r = propose_max_coverage_by_budget(graph, "XYZ", 500)
    print_proposal_result("Result", r)

    # ── Test 6: Unreachable destination (edge case) ──
    print("─" * 60)
    print("TEST 6: Unreachable destination (should report error)")
    results = find_best_routes(graph, "BOG", "CUN", ["cost"])
    print_route_results(results)

    print("─" * 60)
    print("All tests completed.\n")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_tests()
        return

    graph = load_from_json("data/air_network.json")
    print(f"SkyRoute Planner loaded: {len(graph.vertices)} airports, "
          f"{sum(len(v.adjacencies) for v in graph.vertices)} routes.\n")

    if len(sys.argv) > 1 and sys.argv[1] == "--visualize":
        graph.visualize()
        return

    run_interactive(graph)


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\n  Goodbye!\n")

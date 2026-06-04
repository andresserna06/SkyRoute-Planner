import json
from models.vertex import Vertex
from models.edge import Edge
from models.graph import Graph


DEFAULT_AIRCRAFT_CONFIG = {
    "Avión Comercial": {"costPerKm": 0.18, "timePerKm": 0.7},
    "Jet Regional": {"costPerKm": 0.25, "timePerKm": 1.1},
    "Avión de Hélice": {"costPerKm": 0.12, "timePerKm": 2.5},
}


def load_from_json(file_path):
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    graph = Graph()

    # First pass: create one Vertex per airport
    for node in data["nodes"]:
        v = Vertex(
            id=node["id"],
            name=node["name"],
            city=node["city"],
            country=node["country"],
            timezone=node.get("timezone", ""),
            is_hub=node.get("isHub", False),
            airlines=node.get("airlines", []),
            accommodation_cost=node.get("accommodationCost", 0),
            food_cost=node.get("foodCost", 0),
            activities=node.get("activities", []),
            jobs=node.get("jobs", [])
        )
        graph.add_vertex(v)

    # Second pass: create one Edge per route
    for item in data["edges"]:
        origin_id = item["origin"]
        destination_id = item["destination"]

        origin = graph.get_vertex(origin_id)
        destination = graph.get_vertex(destination_id)

        if origin is None:
            raise ValueError(f"Route references unknown origin airport: '{origin_id}'")
        if destination is None:
            raise ValueError(f"Route references unknown destination airport: '{destination_id}'")

        edge = Edge(
            destination_vertex=destination,
            distance_km=item["distanceKm"],
            aircraft=item.get("aircraft", []),
            base_cost=item.get("baseCost", 1),
            minimum_stay=item.get("minimumStay", 0)
        )
        origin.add_adjacency(edge)

    # Load aircraft config from JSON or fall back to defaults
    config = data.get("aircraftConfig") or data.get("configuracionGlobal", {}).get("aeronaves")
    if config:
        for name, values in config.items():
            graph.aircraft_config[name] = {
                "costPerKm": values.get("costPerKm") or values.get("costoKm", 0.18),
                "timePerKm": values.get("timePerKm") or values.get("tiempoKm", 0.7),
            }
    else:
        graph.aircraft_config = dict(DEFAULT_AIRCRAFT_CONFIG)

    # Store full global config for R2.3
    graph.global_config = data.get("aircraftConfig") or data.get("configuracionGlobal", {})

    return graph

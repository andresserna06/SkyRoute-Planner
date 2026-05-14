import json
from models.vertex import Vertex
from models.edge import Edge
from models.graph import Graph


# Reads the JSON file and builds the Graph with all airports and routes
def load_from_json(file_path):

    # Open and parse the JSON file
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    # Create an empty graph
    graph = Graph()

    # --- First pass: create one Vertex per airport ---
    # We do this first so all nodes exist before we start linking them with edges
    for node in data["nodes"]:
        v = Vertex(
            id=node["id"],
            name=node["name"],
            city=node["city"],
            country=node["country"],
            timezone=node["timezone"],
            is_hub=node.get("isHub", False),
            airlines=node.get("airlines", [])
        )
        graph.add_vertex(v)

    # --- Second pass: create one Edge per route and link it to its origin airport ---
    for item in data["edges"]:
        origin_id  = item["origin"]
        destination_id = item["destination"]

        # Look up both airports by their IATA code
        origin  = graph.get_vertex(origin_id)
        destination = graph.get_vertex(destination_id)

        # Stop loading if the JSON references an airport that was not declared in "nodes"
        if origin is None:
            raise ValueError(f"Route references unknown origin airport: '{origin_id}'")
        if destination is None:
            raise ValueError(f"Route references unknown destination airport: '{destination_id}'")

        edge = Edge(
            destination_vertex=destination,
            distance_km=item["distanceKm"],
            aircraft=item["aircraft"]
        )

        # Attach the route to the origin airport's adjacency list
        origin.add_adjacency(edge)

    return graph
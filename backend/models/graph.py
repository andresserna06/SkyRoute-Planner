# ── ITEM 2.1 — Graph structure (adjacency list + vertex map) ──

import math


class Graph:
    # Directed weighted graph built from scratch

    def __init__(self):
        self.vertices = []          # List of all Vertex objects
        self._map = {}              # Fast lookup: IATA code -> Vertex
        self.aircraft_config = {}   # Aircraft speed/cost configuration
        self.global_config = {}     # Global configuration from JSON

    def add_vertex(self, vertex):
        # Add an airport node to the graph
        self.vertices.append(vertex)
        self._map[vertex.id] = vertex

    def get_vertex(self, id):
        # Look up an airport by its IATA code
        return self._map.get(id)

    # ── ITEM 2.2.c — Dijkstra's algorithm (weighted shortest path, custom weight_fn + edge_filter) ──

    def dijkstra(self, origin_id, destination_id, weight_func=None, edge_filter=None, criterion="distance"):
        # Dijkstra's algorithm: finds min-weight path in a directed graph
        # with non-negative edges
        if weight_func is None:
            weight_func = lambda edge: edge.get_weight()
        if edge_filter is None:
            edge_filter = lambda e: True

        # Get all vertex identifiers
        all_ids = [vertex.id for vertex in self.vertices]

        # Distance and predecessor tables (keyed by airport id)
        distances = {airport_id: math.inf for airport_id in all_ids}
        predecessors = {airport_id: None for airport_id in all_ids}
        distances[origin_id] = 0

        unvisited = set(all_ids)

        # Quick lookup: id -> Vertex object
        vertex_map = {vertex.id: vertex for vertex in self.vertices}

        # print("=== Initial iteration ===")
        # for airport_id in all_ids:
        #     print(f"{airport_id}: ({'∞' if distances[airport_id] == math.inf else distances[airport_id]}, {predecessors[airport_id]})")
        # print()

        while unvisited:
            # Select the unvisited vertex with the smallest distance
            closest_id = min(unvisited, key=lambda airport_id: distances[airport_id])
            if distances[closest_id] == math.inf:
                break

            # print(f"Processing vertex {closest_id} with distance {distances[closest_id]}")
            unvisited.remove(closest_id)

            if closest_id == destination_id:
                # print(f"\nDestination {destination_id} reached. Search complete.\n")
                break

            # Relax edges using the Edge structure
            current_vertex = vertex_map[closest_id]
            for edge in current_vertex.adjacencies:
                if not edge_filter(edge):
                    continue
                neighbor_id = edge.destination_vertex.id
                if neighbor_id in unvisited:
                    new_distance = distances[closest_id] + weight_func(edge)
                    if new_distance < distances[neighbor_id]:
                        distances[neighbor_id] = new_distance
                        predecessors[neighbor_id] = closest_id
                        # print(f"  Updated {neighbor_id}: comes from {closest_id}, new cost = {new_distance}")

            # print("\nCurrent labels:")
            # for airport_id in all_ids:
                # cost = "∞" if distances[airport_id] == math.inf else distances[airport_id]
                # print(f"{airport_id}: ({cost}, {predecessors[airport_id]})")
            # print()

        # Reconstruct the shortest path by walking predecessors backwards
        path = []
        current = destination_id
        while current is not None:
            path.insert(0, current)
            current = predecessors[current]

        # print(f"Shortest path from {origin_id} to {destination_id}: {' → '.join(str(n) for n in path)}")
        # print(f"Total {criterion}: {distances[destination_id]}")
        return distances, predecessors, path

    # ── END ITEM 2.2.c ──

    def __repr__(self):
        total_routes = sum(len(vertex.adjacencies) for vertex in self.vertices)
        return f"Graph({len(self.vertices)} airports, {total_routes} routes)"

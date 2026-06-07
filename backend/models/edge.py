# ── ITEM 2.1 — Directed route: destination, distance, aircraft types, subsidized flag ──

class Edge:
    # Directed route connecting two airports

    def __init__(self, destination_vertex, distance_km, aircraft,
                 base_cost=1, minimum_stay=0):
        self.destination_vertex = destination_vertex  # Where this route goes
        self.distance_km = distance_km                # Route length in km
        self.aircraft = aircraft                      # Aircraft types available on this route
        self.base_cost = base_cost                    # 0 = subsidized route, 1 = normal
        self.minimum_stay = minimum_stay              # Minimum stay in minutes at destination

    def get_weight(self):
        # Returns edge weight (distance in km)
        return self.distance_km

    def getPeso(self):
        # Alias for get_weight, matches Dijkstra naming from class
        return self.distance_km

    def __repr__(self):
        return f"Edge(-> {self.destination_vertex.id}, {self.distance_km} km)"

# ── END ITEM 2.1 ──

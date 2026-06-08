class Edge:

    def __init__(self, origin_vertex, destination_vertex, distance_km, aircraft,
                 base_cost=1, minimum_stay=0):
        self.origin_vertex = origin_vertex
        self.destination_vertex = destination_vertex
        self.distance_km = distance_km
        self.aircraft = aircraft
        self.base_cost = base_cost
        self.minimum_stay = minimum_stay
        self.is_blocked = False

    def get_weight(self):
        # Default edge weight = distance in km (used by Dijkstra when no weight_func is given)
        return self.distance_km

    def __repr__(self):
        return f"Edge(-> {self.destination_vertex.id}, {self.distance_km} km)"
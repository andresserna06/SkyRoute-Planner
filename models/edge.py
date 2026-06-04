class Edge:

    def __init__(self, destination_vertex, distance_km, aircraft,
                 base_cost=1, minimum_stay=0):
        self.destination_vertex = destination_vertex
        self.distance_km = distance_km
        self.aircraft = aircraft
        self.base_cost = base_cost
        self.minimum_stay = minimum_stay

    def get_weight(self):
        return self.distance_km

    def getPeso(self):
        """getPeso: returns the edge weight (distance in km).
        Matches the getPeso method used in Dijkstra's algorithm as taught in class."""
        return self.distance_km

    def __repr__(self):
        return f"Edge(-> {self.destination_vertex.id}, {self.distance_km} km)"

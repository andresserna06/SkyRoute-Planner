class Edge:

    # Each edge represents a directed route between two airports
    def __init__(self, destination_vertex, distance_km, aircraft):
        self.destination_vertex = destination_vertex  # destination Vertex object
        self.distance_km = distance_km                # route distance in kilometres
        self.aircraft = aircraft                      # list of aircraft types on this route
        self.minimum_stay

    # Returns the distance in km — used as the default edge weight
    def get_weight(self):
        return self.distance_km

    def __repr__(self):
        return f"Edge(-> {self.destination_vertex.id}, {self.distance_km} km)"
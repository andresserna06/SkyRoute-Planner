class Vertex:

    def __init__(self, id, name, city, country, timezone, is_hub, airlines,
                 accommodation_cost=0, food_cost=0, activities=None, jobs=None):
        self.id = id
        self.name = name
        self.city = city
        self.country = country
        self.timezone = timezone
        self.is_hub = is_hub
        self.airlines = airlines
        self.accommodation_cost = accommodation_cost
        self.food_cost = food_cost
        self.activities = activities if activities is not None else []
        self.jobs = jobs if jobs is not None else []
        self.adjacencies = []

    def add_adjacency(self, edge):
        self.adjacencies.append(edge)

    def __repr__(self):
        type_str = "HUB" if self.is_hub else "secondary"
        return f"Vertex({self.id} - {self.city}, {self.country} [{type_str}])"

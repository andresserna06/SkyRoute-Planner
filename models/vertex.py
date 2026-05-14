class Vertex:

    # Each vertex represents one airport in the network
    def __init__(self, id, name, city, country, timezone, is_hub, airlines):
        self.id = id                    # IATA code, e.g. "BOG"
        self.name = name                # full airport name
        self.city = city                # city
        self.country = country          # country
        self.timezone = timezone        # timezone string
        self.is_hub = is_hub            # True if this is a major hub airport
        self.airlines = airlines        # list of airlines operating from here
        self.adjacencies = []           # list of Edge objects (outgoing routes)

    # Adds an outgoing route from this airport to another
    def add_adjacency(self, edge):
        self.adjacencies.append(edge)

    def __repr__(self):
        type_str = "HUB" if self.is_hub else "secondary"
        return f"Vertex({self.id} - {self.city}, {self.country} [{type_str}])"
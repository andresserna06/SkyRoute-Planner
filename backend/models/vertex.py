# ── ITEM 2.1 — Airport node: IATA code, city, country, hub/secondary flag, airlines, costs ──

class Vertex:
    # Airport node in the route network

    def __init__(self, id, name, city, country, timezone, is_hub, airlines,
                 accommodation_cost=0, food_cost=0, activities=None, jobs=None):
        self.id = id                    # IATA code, e.g. BOG, LIM
        self.name = name                # Full airport name
        self.city = city                # City where the airport is located
        self.country = country          # Country
        self.timezone = timezone        # Timezone string
        self.is_hub = is_hub            # True = hub, False = secondary
        self.airlines = airlines        # List of airlines at this airport
        self.accommodation_cost = accommodation_cost  # Cost per night stay
        self.food_cost = food_cost      # Daily food cost
        self.activities = activities if activities is not None else []  # Optional/mandatory activities
        self.jobs = jobs if jobs is not None else []  # Available jobs for earning budget (R3)
        self.adjacencies = []           # Outgoing directed routes (Edge objects)

    def add_adjacency(self, edge):
        # Add a directed route from this airport
        self.adjacencies.append(edge)

    def __repr__(self):
        type_str = "HUB" if self.is_hub else "secondary"
        return f"Vertex({self.id} - {self.city}, {self.country} [{type_str}])"

# ── END ITEM 2.1 ──

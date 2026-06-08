# Traveler model — tracks budget, time, food/accommodation obligations, and flight state

class Traveler:

    def __init__(self, budget, food_interval=8, accommodation_interval=20):
        self.last_food = 0               # Hours since last meal was charged
        self.last_accommodation = 0      # Hours since last accommodation was charged
        self.total_cost = 0              # Total obligatory costs incurred THIS instance
        self.budget = budget             # Current remaining budget (local copy — sync to state after use)
        self.current_location = None     # Current Vertex object
        self.current_time = 0            # Current time in hours
        self.arrival_time = 0            # Arrival time at current airport (hours)
        self.food_interval = food_interval               # Hours between required meals (default 8)
        self.accommodation_interval = accommodation_interval  # Hours between required stays (default 20)
        self.is_flying = False
        self.current_flight = None
        self.destination = None
        self.planned_route = None

    def check_obligatory(self, node):
        """Charge food and accommodation costs based on elapsed time at a node.

        Returns a dict with 'success' (bool) and 'error' (str) if funds are insufficient
        for obligatory charges. Obligatory costs are always charged even if budget goes
        negative — but the error is reported so the UI can inform the traveler.
        """
        errors = []

        # Meals — every food_interval hours
        meals = int((self.current_time - self.last_food) // self.food_interval)
        if meals > 0:
            cost = meals * node.food_cost
            if self.budget < cost:
                errors.append(
                    f"Imposible realizar el pago de alimentación (${cost:.2f}): "
                    f"fondos insuficientes (disponible: ${self.budget:.2f})."
                )
            self.last_food += meals * self.food_interval
            self.budget -= cost
            self.total_cost += cost

        # Accommodation — every accommodation_interval hours
        stays = int((self.current_time - self.last_accommodation) // self.accommodation_interval)
        if stays > 0:
            cost = stays * node.accommodation_cost
            if self.budget < cost:
                errors.append(
                    f"Imposible realizar el pago de alojamiento (${cost:.2f}): "
                    f"fondos insuficientes (disponible: ${self.budget:.2f})."
                )
            self.last_accommodation += stays * self.accommodation_interval
            self.budget -= cost
            self.total_cost += cost

        if errors:
            self.obligatory_errors = errors
            return {"success": False, "error": " | ".join(errors)}
        self.obligatory_errors = []
        return {"success": True}

    def check_flight(self, edge, time_per_km):
        """Simulate a flight: advance time and charge any meals incurred mid-flight."""
        self.is_flying = True
        self.current_flight = edge

        flight_duration_h = (edge.distance_km * time_per_km) / 60.0
        arrival_time = self.current_time + flight_duration_h

        # Meals consumed during the flight are billed from the departure airport
        meals = int((arrival_time - self.last_food) // self.food_interval)
        if meals > 0:
            cost = meals * self.current_location.food_cost
            if self.budget < cost:
                self.flight_food_error = (
                    f"Imposible realizar el pago de alimentación durante el vuelo (${cost:.2f}): "
                    f"fondos insuficientes (disponible: ${self.budget:.2f})."
                )
            else:
                self.flight_food_error = None
            self.last_food += meals * self.food_interval
            self.budget -= cost
            self.total_cost += cost
        else:
            self.flight_food_error = None

        self.current_time = arrival_time
        self.arrival_time = arrival_time
        self.is_flying = False
        self.current_flight = None

    def do_activity(self, activity, edge):
        """Attempt to perform an optional activity within the minimum stay window."""
        duration_h = activity["durationMin"] / 60.0
        finish_time = self.current_time + duration_h
        available_until = self.arrival_time + (edge.minimum_stay / 60.0)

        if finish_time <= available_until:
            cost = activity["costUSD"]
            if self.budget < cost:
                return False  # Insufficient funds — caller should report the error
            self.current_time = finish_time
            self.total_cost += cost
            self.budget -= cost
            self.check_obligatory(self.current_location)
            return True
        return False
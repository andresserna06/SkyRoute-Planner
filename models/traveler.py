class Traveler:

    def __init__(self, budget, food_interval=8, accommodation_interval=20):
        self.last_food = 0
        self.last_accommodation = 0
        self.total_cost = 0
        self.budget = budget
        self.current_location = None
        self.current_time = 0
        self.food_interval = food_interval
        self.accommodation_interval = accommodation_interval
        self.arrival_time = 0 


    # El viajero ya aterrizó
    def check_obligatory(self, node):
        # Alimentacion
        meals = (self.current_time - self.last_food) // self.food_interval
        if meals > 0:
            cost = meals * node.food_cost
            self.last_food = self.current_time
            self.budget -= cost
            self.total_cost += cost

        # Alojamiento
        accommodations = (self.current_time - self.last_accommodation) // self.accommodation_interval
        if accommodations > 0:
            cost = accommodations * node.accommodation_cost
            self.last_accommodation = self.current_time
            self.budget -= cost
            self.total_cost += cost
            
    def check_flight(self, edge, time_per_km):
        # Calcular duracion del vuelo y hora de llegada
        flight_duration = edge.distance_km * time_per_km
        arrival_time = self.current_time + flight_duration
        
        # Comidas durante el vuelo — costo del nodo actual (origen)
        meals = (self.  arrival_time - self.last_food) // self.food_interval
        if meals > 0:
            cost = meals * self.current_location.food_cost
            self.last_food += meals * self.food_interval
            self.budget -= cost
            self.total_cost += cost
        
        # Actualizar tiempo actual a hora de llegada
        self.arrival_time = arrival_time     
        
        
    def do_activity(self, activity, edge):
        duration_activity = activity["durationMin"] / 60
        finish_time = self.current_time + duration_activity
        available_until = self.arrival_time + (edge.minimum_stay / 60)
        
        if finish_time <= available_until:
            self.current_time = finish_time
            self.total_cost += activity["costUSD"]
            self.budget -= activity["costUSD"]
            self.check_obligatory(self.current_location)
        else:
            print(f"No hay tiempo suficiente para realizar {activity['name']}")
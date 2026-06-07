from services.graphService import load_from_json

from services.itineraryService import (
    propose_max_coverage_by_budget,
    propose_max_coverage_by_time,
    find_best_routes
)

from services.dynamicService import (
    create_dynamic_state,
    get_available_flights,
    choose_flight,
    finish_itinerary
)


# =========================================================
# CARGAR GRAFO DESDE JSON
# =========================================================

graph = load_from_json("data/skyroute_network.json")

print("\n========== GRAFO CARGADO ==========")
print("Aeropuertos cargados:", len(graph.vertices))


# =========================================================
# VERIFICAR AEROPUERTO
# =========================================================

print("\n========== AEROPUERTO BOG ==========")

bog = graph.get_vertex("BOG")

print("Nombre:", bog.name)
print("Ciudad:", bog.city)
print("País:", bog.country)

print("\nRutas desde BOG:")

for edge in bog.adjacencies:
    print(
        f"-> {edge.destination_vertex.id} "
        f"({edge.distance_km} km)"
    )


# =========================================================
# PRUEBA 1 — Proposal A
# Máximo destinos por presupuesto
# =========================================================

print("\n========== PROPOSAL A ==========")

proposal_a = propose_max_coverage_by_budget(
    graph=graph,
    origin_id="BOG",
    budget_usd=50,
    time_hours=20
)

print(proposal_a)


# =========================================================
# PRUEBA 2 — Proposal B
# Máximo destinos por tiempo
# =========================================================

print("\n========== PROPOSAL B ==========")

proposal_b = propose_max_coverage_by_time(
    graph=graph,
    origin_id="BOG",
    time_hours=15,
    budget_usd=1500
)

print(proposal_b)


# =========================================================
# PRUEBA 3 — BEST ROUTES
# Buscar mejores rutas
# =========================================================

print("\n========== BEST ROUTES ==========")

routes = find_best_routes(
    graph=graph,
    origin_id="BOG",
    destination_id="GRU",
    criteria=["distance", "time", "cost"]
)

for route in routes:
    print("\nCRITERIO:", route["criterion"])
    print(route)


# =========================================================
# PRUEBA 4 — DYNAMIC SERVICE
# Planificador interactivo
# =========================================================

print("\n========== DYNAMIC SERVICE ==========")

# Crear estado inicial
state = create_dynamic_state(
    origin_id="BOG",
    initial_budget=1200
)

print("\nEstado inicial:")
print(state)


# =========================================================
# Mostrar vuelos disponibles
# =========================================================

available = get_available_flights(graph, state)

print("\nVuelos disponibles:")

for flight in available["available_flights"]:
    print(
        f'ID: {flight["id"]} | '
        f'Destino: {flight["destination"]} | '
        f'Aeronave: {flight["aircraft"]} | '
        f'Costo: {flight["cost"]} USD | '
        f'Tiempo: {flight["time_min"]} min'
    )


# =========================================================
# Elegir primer vuelo
# =========================================================

if available["available_flights"]:

    print("\n========== ELIGIENDO VUELO 0 ==========")

    response = choose_flight(
        graph,
        state,
        0
    )

    print(response)


# =========================================================
# Mostrar nuevos vuelos disponibles
# =========================================================

available = get_available_flights(graph, state)

print("\nNuevos vuelos disponibles:")

for flight in available["available_flights"]:
    print(
        f'ID: {flight["id"]} | '
        f'Destino: {flight["destination"]} | '
        f'Aeronave: {flight["aircraft"]} | '
        f'Costo: {flight["cost"]} USD | '
        f'Tiempo: {flight["time_min"]} min'
    )


# =========================================================
# Elegir segundo vuelo si existe
# =========================================================

if available["available_flights"]:

    print("\n========== ELIGIENDO SEGUNDO VUELO ==========")

    response = choose_flight(
        graph,
        state,
        0
    )

    print(response)


# =========================================================
# Finalizar itinerario
# =========================================================

print("\n========== FINALIZAR ITINERARIO ==========")

summary = finish_itinerary(state)

print(summary)
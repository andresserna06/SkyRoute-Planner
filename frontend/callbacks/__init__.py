def register_all(app):
    from . import r1_graph, r2_route, r3_journey, r4_interruptions, r5_flight_animation
    r1_graph.register(app)
    r2_route.register(app)
    r3_journey.register(app)
    r4_interruptions.register(app)
    r5_flight_animation.register(app)

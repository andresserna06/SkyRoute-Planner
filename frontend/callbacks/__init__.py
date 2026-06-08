def register_all(app):
    from . import r1_graph, r2_route, r3_journey, r4_proposals, r5_editor
    r1_graph.register(app)
    r2_route.register(app)
    r3_journey.register(app)
    r4_proposals.register(app)
    r5_editor.register(app)

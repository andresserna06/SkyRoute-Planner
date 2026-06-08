# ── ITEM 2.1 — Cytoscape node/edge builder + base stylesheet (hub orange, secondary blue) ──

from frontend.config import COLORS


def build_elements(graph):
    # Convert Graph object into Cytoscape elements (nodes + edges)
    elements = []

    # Create Cytoscape nodes for each airport
    for vertex in graph.vertices:
        elements.append({
            "data": {
                "id": vertex.id,
                "label": vertex.id,
                "full_name": vertex.name,
                "city": vertex.city,
                "country": vertex.country,
                "timezone": vertex.timezone,
                "airlines": ", ".join(vertex.airlines) if vertex.airlines else "N/A",
                "node_type": "hub" if vertex.is_hub else "secondary",
            },
            "classes": "hub" if vertex.is_hub else "secondary",
        })

    # Create Cytoscape edges for each route
    for vertex in graph.vertices:
        for edge in vertex.adjacencies:
            aircraft_codes = []
            for aircraft in edge.aircraft:
                if "Comercial" in aircraft or "Commercial" in aircraft:
                    aircraft_codes.append("C")
                elif "Regional" in aircraft:
                    aircraft_codes.append("R")
                else:
                    aircraft_codes.append("H")

            if edge.is_blocked:
                classes = "bloqueada"
            elif edge.base_cost == 0:
                classes = "subsidiada"
            else:
                classes = "ruta"

            elements.append({
                "data": {
                    "source": vertex.id,
                    "target": edge.destination_vertex.id,
                    "label": f"{int(edge.distance_km)} km · {','.join(aircraft_codes)}",
                    "distance_km": edge.distance_km,
                    "aircraft": ", ".join(edge.aircraft),
                },
                "classes": classes,
            })

    return elements


def base_stylesheet():
    return [
        {
            "selector": "node",
            "style": {
                "label": "data(label)",
                "text-valign": "center",
                "text-halign": "center",
                "font-family": "Inter, Segoe UI, sans-serif",
                "font-size": "10px",
                "font-weight": "bold",
                "color": "#ffffff",
                "text-outline-width": 1.6,
                "text-outline-color": COLORS["node_outline"],
            },
        },
        {
            "selector": ".hub",
            "style": {
                "background-color": COLORS["hub"],
                "width": 56,
                "height": 56,
                "font-size": "12px",
                "border-width": 2,
                "border-color": COLORS["hub_border"],
            },
        },
        {
            "selector": ".secondary",
            "style": {
                "background-color": COLORS["secondary"],
                "width": 38,
                "height": 38,
                "border-width": 2,
                "border-color": COLORS["sec_border"],
            },
        },
        {
            "selector": "edge.ruta",
            "style": {
                "label": "data(label)",
                "curve-style": "bezier",
                "target-arrow-shape": "triangle",
                "target-arrow-color": COLORS["route"],
                "line-color": COLORS["route"],
                "arrow-scale": 1.0,
                "width": 1.3,
                "opacity": 0.65,
                "font-family": "Inter, Segoe UI, sans-serif",
                "font-size": "9px",
                "font-weight": "bold",
                "color": COLORS["text"],
                "text-background-color": "#ffffff",
                "text-background-opacity": 0.95,
                "text-background-padding": "3px",
                "text-background-shape": "roundrectangle",
                "text-border-width": 1,
                "text-border-color": COLORS["border"],
                "text-border-opacity": 1,
            },
        },
        {
            "selector": "edge.subsidiada",
            "style": {
                "label": "data(label)",
                "curve-style": "bezier",
                "target-arrow-shape": "triangle",
                "target-arrow-color": COLORS["subsidized"],
                "line-color": COLORS["subsidized"],
                "line-style": "dashed",
                "arrow-scale": 1.0,
                "width": 1.8,
                "opacity": 0.9,
                "font-family": "Inter, Segoe UI, sans-serif",
                "font-size": "9px",
                "font-weight": "bold",
                "color": COLORS["subsidized"],
                "text-background-color": "#ffffff",
                "text-background-opacity": 0.95,
                "text-background-padding": "3px",
                "text-background-shape": "roundrectangle",
                "text-border-width": 1,
                "text-border-color": COLORS["border"],
                "text-border-opacity": 1,
            },
        },
        {
            "selector": "edge.bloqueada",
            "style": {
                "label": "data(label)",
                "curve-style": "bezier",
                "target-arrow-shape": "triangle",
                "target-arrow-color": COLORS["error"],
                "line-color": COLORS["error"],
                "line-style": "dashed",
                "width": 2.5,
                "opacity": 1,
                "font-family": "Inter, Segoe UI, sans-serif",
                "font-size": "9px",
                "font-weight": "bold",
                "color": COLORS["error"],
                "text-background-color": "#ffffff",
                "text-background-opacity": 0.95,
                "text-background-padding": "3px",
                "text-background-shape": "roundrectangle",
                "text-border-width": 1,
                "text-border-color": COLORS["border"],
                "text-border-opacity": 1,
            },
        },
    ]

# ── END ITEM 2.1 ──
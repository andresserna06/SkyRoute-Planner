from frontend.config import COLORS


def build_elements(g):
    elements = []
    for v in g.vertices:
        elements.append({
            "data": {
                "id": v.id, "label": v.id, "full_name": v.name,
                "city": v.city, "country": v.country, "timezone": v.timezone,
                "airlines": ", ".join(v.airlines) if v.airlines else "N/A",
                "node_type": "hub" if v.is_hub else "secondary",
            },
            "classes": "hub" if v.is_hub else "secondary",
        })
    for v in g.vertices:
        for edge in v.adjacencies:
            abbrevs = []
            for a in edge.aircraft:
                if "Comercial" in a or "Commercial" in a: abbrevs.append("C")
                elif "Regional" in a: abbrevs.append("R")
                else: abbrevs.append("H")
            elements.append({
                "data": {
                    "source": v.id, "target": edge.destination_vertex.id,
                    "label": f"{int(edge.distance_km)} km · {','.join(abbrevs)}",
                    "distance_km": edge.distance_km,
                    "aircraft": ", ".join(edge.aircraft),
                },
                "classes": "subsidiada" if edge.base_cost == 0 else "ruta",
            })
    return elements


def base_stylesheet():
    return [
        {"selector": "node", "style": {
            "label": "data(label)", "text-valign": "center", "text-halign": "center",
            "font-family": "Inter, Segoe UI, sans-serif", "font-size": "10px",
            "font-weight": "700", "color": "#ffffff", "text-outline-width": 1.6,
            "text-outline-color": COLORS["node_outline"],
        }},
        {"selector": ".hub", "style": {
            "background-color": COLORS["hub"], "width": 56, "height": 56,
            "font-size": "12px", "border-width": 2, "border-color": COLORS["hub_border"],
        }},
        {"selector": ".secondary", "style": {
            "background-color": COLORS["secondary"], "width": 38, "height": 38,
            "border-width": 2, "border-color": COLORS["sec_border"],
        }},
        {"selector": "edge.ruta", "style": {
            "label": "data(label)", "curve-style": "bezier",
            "target-arrow-shape": "triangle", "target-arrow-color": COLORS["route"],
            "line-color": COLORS["route"], "arrow-scale": 1.0, "width": 1.3,
            "opacity": 0.65, "font-family": "Inter, Segoe UI, sans-serif",
            "font-size": "9px", "font-weight": "600", "color": COLORS["text"],
            "text-background-color": "#ffffff", "text-background-opacity": 0.95,
            "text-background-padding": "3px", "text-background-shape": "roundrectangle",
            "text-border-width": 1, "text-border-color": COLORS["border"],
            "text-border-opacity": 1,
        }},
        {"selector": "edge.subsidiada", "style": {
            "label": "data(label)", "curve-style": "bezier",
            "target-arrow-shape": "triangle", "target-arrow-color": COLORS["subsidized"],
            "line-color": COLORS["subsidized"], "line-style": "dashed",
            "arrow-scale": 1.0, "width": 1.8, "opacity": 0.9,
            "font-family": "Inter, Segoe UI, sans-serif", "font-size": "9px",
            "font-weight": "600", "color": COLORS["subsidized"],
            "text-background-color": "#ffffff", "text-background-opacity": 0.95,
            "text-background-padding": "3px", "text-background-shape": "roundrectangle",
            "text-border-width": 1, "text-border-color": COLORS["border"],
            "text-border-opacity": 1,
        }},
    ]

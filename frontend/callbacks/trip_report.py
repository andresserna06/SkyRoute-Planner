# ── ITEM 2.5 — Reporte final del viaje (R5) ──
# Builds the final trip summary shown in the modal when the journey finishes.
# Used by journey_planner.render_planner once the itinerary is marked finished.

from dash import html

from frontend.config import COLORS, CARD, SECTION_TITLE


def render_report(summary, graph=None):
    # Builds the complete trip report with 5 sections: destinations, segments,
    # activities, jobs, and totals. Accepts the graph to look up airport metadata.

    def _vertex_info(airport_id):
        # Returns (name, city, country) from graph if available
        if graph:
            vertex = graph.get_vertex(airport_id)
            if vertex:
                return vertex.name, vertex.city, vertex.country
        return airport_id, "", ""

    sections      = []
    dest_log      = summary.get("destination_log", [])
    acts_done     = summary.get("activities_done", [])
    jobs_done     = summary.get("jobs_done", [])
    segments      = summary.get("segments", [])
    total_time_h  = summary.get("total_time_hours", 0)

    # ── Sección 1: Destinos visitados ──
    if dest_log:
        dest_cards = []
        for entry in dest_log:
            airport_id  = entry["airport_id"]
            arrival_h   = entry.get("arrival_h")    # None for origin
            departure_h = entry.get("departure_h")  # None for final destination
            name, city, country = _vertex_info(airport_id)

            if arrival_h is None:
                # Origin airport — no incoming flight
                accent     = COLORS["hub"]
                time_label = f"Origen  ·  Salida: {departure_h or 0.0:.2f} h"
                stay_h     = 0.0
            elif departure_h is None:
                # Final destination — no outgoing flight
                stay_h     = max(0.0, total_time_h - arrival_h)
                accent     = COLORS["ok"]
                time_label = f"Llegada: {arrival_h:.2f} h  ·  Estadía: {stay_h:.2f} h"
            else:
                # Transit airport
                stay_h     = max(0.0, departure_h - arrival_h)
                accent     = COLORS["secondary"]
                time_label = f"Llegada: {arrival_h:.2f} h  ·  Estadía: {stay_h:.2f} h"

            # Flight cost to arrive at this airport
            seg_cost = next(
                (seg["cost"] for seg in segments if seg["destination"] == airport_id),
                None,
            )
            # Optional activities at this airport
            airport_acts = [activity for activity in acts_done if activity.get("airport") == airport_id]
            act_cost = sum(activity["cost"] for activity in airport_acts)

            card_children = [
                html.Div(style={"display": "flex", "justifyContent": "space-between",
                                "alignItems": "baseline", "marginBottom": "2px"}, children=[
                    html.Span(airport_id, style={"fontSize": "16px", "fontWeight": "800", "color": accent}),
                    html.Span(time_label, style={"fontSize": "10px", "color": COLORS["text_dim"]}),
                ]),
            ]
            if name != airport_id:
                card_children.append(html.Div(
                    name, style={"fontSize": "11px", "fontStyle": "italic",
                                 "color": COLORS["text_dim"], "marginBottom": "2px"}))
            if city:
                card_children.append(html.Div(
                    f"{city}, {country}",
                    style={"fontSize": "11px", "color": COLORS["text_dim"], "marginBottom": "6px"}))

            # Cost breakdown for this destination
            cost_parts = []
            if seg_cost is not None and seg_cost > 0:
                cost_parts.append(f"Vuelo: ${seg_cost:.2f}")
            if act_cost > 0:
                act_names = " / ".join(activity["name"] for activity in airport_acts)
                cost_parts.append(f"Actividades ({act_names}): ${act_cost:.2f}")
            if cost_parts:
                card_children.append(html.Div(
                    "  ·  ".join(cost_parts),
                    style={"fontSize": "11px", "fontWeight": "600", "color": COLORS["error"]},
                ))

            dest_cards.append(html.Div(
                style={**CARD, "borderLeft": f"3px solid {accent}", "marginBottom": "6px"},
                children=card_children,
            ))

        sections.append(html.Div([
            html.Div(f"Destinos visitados: {summary.get('destinations_visited', 0)}",
                     style={**SECTION_TITLE, "marginBottom": "8px"}),
            *dest_cards,
        ]))

    # ── Sección 2: Tramos volados ──
    if segments:
        seg_cards = [
            html.Div(style={**CARD, "marginBottom": "6px", "padding": "8px 12px"}, children=[
                html.Div(style={"display": "flex", "justifyContent": "space-between"}, children=[
                    html.Span(f"{seg['origin']} → {seg['destination']}",
                              style={"fontWeight": "700", "fontSize": "12px"}),
                    html.Span(f"${seg['cost']:.2f}",
                              style={"fontWeight": "700", "fontSize": "12px", "color": COLORS["error"]}),
                ]),
                html.Div(
                    f"{seg['aircraft']}  ·  {seg['distance_km']:.0f} km  ·  {seg['time_min']:.0f} min",
                    style={"fontSize": "11px", "color": COLORS["text_dim"], "marginTop": "3px"},
                ),
            ])
            for seg in segments
        ]
        sections.append(html.Div([
            html.Div("Tramos volados", style={**SECTION_TITLE, "marginBottom": "8px", "marginTop": "12px"}),
            *seg_cards,
        ]))

    # ── Sección 3: Actividades realizadas ──
    act_items = []
    obligatory_total = summary.get("obligatory_cost_total", 0.0)

    # Mandatory activities (food + accommodation) — shown as a single total
    if obligatory_total > 0:
        act_items.append(html.Div(
            style={"display": "flex", "justifyContent": "space-between",
                   "marginBottom": "6px", "alignItems": "flex-start"},
            children=[
                html.Div([
                    html.Span("Comida + Alojamiento",
                              style={"fontWeight": "600", "fontSize": "11px"}),
                    html.Div("Obligatoria  ·  cargos acumulados durante el viaje",
                             style={"fontSize": "10px", "color": COLORS["text_dim"]}),
                ]),
                html.Span(f"-${obligatory_total:.2f}",
                          style={"fontWeight": "700", "fontSize": "12px",
                                 "color": COLORS["error"], "whiteSpace": "nowrap"}),
            ],
        ))

    # Optional activities — one row each
    for activity in acts_done:
        act_items.append(html.Div(
            style={"display": "flex", "justifyContent": "space-between",
                   "marginBottom": "6px", "alignItems": "flex-start"},
            children=[
                html.Div([
                    html.Span(activity["name"], style={"fontWeight": "600", "fontSize": "11px"}),
                    html.Div(
                        f"Opcional  ·  {activity['airport']}  ·  {activity['duration_min']} min",
                        style={"fontSize": "10px", "color": COLORS["text_dim"]},
                    ),
                ]),
                html.Span(f"-${activity['cost']:.2f}",
                          style={"fontWeight": "700", "fontSize": "12px",
                                 "color": COLORS["error"], "whiteSpace": "nowrap"}),
            ],
        ))

    if act_items:
        sections.append(html.Div([
            html.Div("Actividades realizadas",
                     style={**SECTION_TITLE, "marginBottom": "8px", "marginTop": "12px"}),
            *act_items,
        ]))

    # ── Sección 4: Trabajos realizados ──
    if jobs_done:
        job_rows = [
            html.Div(
                style={"display": "flex", "justifyContent": "space-between",
                       "marginBottom": "6px", "alignItems": "flex-start"},
                children=[
                    html.Div([
                        html.Span(job["job_name"],
                                  style={"fontWeight": "600", "fontSize": "11px"}),
                        html.Div(
                            f"{job['airport']}  ·  {job['hours']} h  ·  ${job['hourly_rate']:.2f}/h",
                            style={"fontSize": "10px", "color": COLORS["text_dim"]},
                        ),
                    ]),
                    html.Span(f"+${job['earnings']:.2f}",
                              style={"fontWeight": "700", "fontSize": "12px",
                                     "color": COLORS["ok"], "whiteSpace": "nowrap"}),
                ],
            )
            for job in jobs_done
        ]
        sections.append(html.Div([
            html.Div("Trabajos realizados",
                     style={**SECTION_TITLE, "marginBottom": "8px", "marginTop": "12px"}),
            *job_rows,
            html.Div(
                f"Total ganado: ${summary.get('total_earned', 0):.2f}",
                style={"fontSize": "12px", "fontWeight": "700",
                       "color": COLORS["ok"], "marginTop": "4px"},
            ),
        ]))

    # ── Sección 5: Resumen de totales ──
    subsidized_km = summary.get("subsidized_km", 0)
    total_km      = summary.get("total_km", 0)

    totals = html.Div(
        style={**CARD, "borderLeft": f"3px solid {COLORS['hub']}", "marginTop": "14px"},
        children=[
            html.Div("Resumen del viaje", style={**SECTION_TITLE, "marginBottom": "10px"}),
            *[
                html.Div(style={
                    "display": "flex", "justifyContent": "space-between",
                    "marginBottom": "5px", "fontSize": "12px",
                }, children=[
                    html.Span(label, style={"color": COLORS["text_dim"]}),
                    html.Span(value, style={"fontWeight": "700", "color": color}),
                ])
                for label, value, color in [
                    ("Presupuesto inicial",    f"${summary.get('initial_budget', 0):.2f}",  COLORS["text"]),
                    ("Total vuelos",           f"-${summary.get('total_cost', 0):.2f}",      COLORS["error"]),
                    ("Cargos obligatorios",    f"-${obligatory_total:.2f}",                  COLORS["error"]),
                    ("Ganado en trabajos",     f"+${summary.get('total_earned', 0):.2f}",    COLORS["ok"]),
                    ("Saldo final",            f"${summary.get('remaining_budget', 0):.2f}", COLORS["text"]),
                    ("Tiempo total del viaje", f"{summary.get('total_time_hours', 0):.1f} h", COLORS["text"]),
                    ("Destinos visitados",     str(summary.get("destinations_visited", 0)),  COLORS["text"]),
                ]
            ],
            html.Div(style={"borderTop": f"1px solid {COLORS['border']}", "margin": "8px 0 6px"}),
            html.Div(style={"display": "flex", "justifyContent": "space-between",
                            "marginBottom": "5px", "fontSize": "12px"}, children=[
                html.Span("Dist. subsidiada", style={"color": COLORS["text_dim"]}),
                html.Span(
                    f"{subsidized_km:.0f} / {total_km:.0f} km ({summary.get('subsidy_ratio', 0):.1f}%)",
                    style={"fontWeight": "700"},
                ),
            ]),
            html.Div(style={"display": "flex", "justifyContent": "space-between",
                            "fontSize": "12px"}, children=[
                html.Span("Límite 20%", style={"color": COLORS["text_dim"]}),
                html.Span(
                    "✔ Cumple" if summary.get("subsidy_valid") else "✘ Excede",
                    style={"fontWeight": "700",
                           "color": COLORS["ok"] if summary.get("subsidy_valid") else COLORS["error"]},
                ),
            ]),
        ],
    )

    return html.Div([*sections, totals])

# ── END ITEM 2.5 ──

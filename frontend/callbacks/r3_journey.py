# ── ITEM 2.3.a — Traveler obligatory activities (food + accommodation) + optional activities
# ── ITEM 2.3.b — Jobs at airports (earn additional budget when budget < 35%)
# ── ITEM 2.3.c — Transport costs (aircraft selection, flight cost/time, subsidised 20% rule)

from dash import html, Input, Output, State
import dash

from backend.services.graphService import build_graph_from_dict
from backend.services.dynamicService import (
    create_dynamic_state, get_available_flights,
    choose_flight, finish_itinerary, build_summary,
    get_available_jobs, work_at_job,
    do_optional_activity, get_optional_activities,
)
from frontend.config import COLORS, CARD, SECTION_TITLE, SHOW, HIDE

# Modal needs display:flex (not block) so the inner box centres properly
MODAL_SHOW = {
    "display": "flex",
    "position": "fixed", "top": "0", "left": "0", "right": "0", "bottom": "0",
    "backgroundColor": "rgba(0,0,0,0.5)",
    "zIndex": "1000",
    "justifyContent": "center",
    "alignItems": "center",
    "padding": "20px",
}


def register(app):

    @app.callback(
        Output("journey-store",       "data"),
        Output("blocked-edges-store", "data", allow_duplicate=True),
        Input("start-btn",              "n_clicks"),
        Input("fly-btn",                "n_clicks"),
        Input("end-btn",                "n_clicks"),
        Input("new-journey-btn",        "n_clicks"),
        Input("work-btn",               "n_clicks"),
        Input("confirm-activities-btn", "n_clicks"),
        State("planner-origin",         "value"),
        State("planner-budget",         "value"),
        State("flight-radio",           "value"),
        State("job-dropdown",           "value"),
        State("hours-input",            "value"),
        State("activity-checklist",     "value"),
        State("journey-store",          "data"),
        State("graph-store",            "data"),
        State("blocked-edges-store",    "data"),
        prevent_initial_call=True,
    )
    def handle_journey_action(start_n, fly_n, end_n, new_n, work_n, confirm_n,
                              origin, budget, flight_val,
                              job_val, hours_val, selected_activities,
                              journey_data, graph_data, blocked_edges_data):
        tid = dash.callback_context.triggered_id
        if not tid:
            raise dash.exceptions.PreventUpdate

        if tid == "new-journey-btn":
            # Clear both journey and blocked edges so the new trip starts clean
            return None, []

        if tid == "start-btn":
            if not origin or not budget or not graph_data:
                raise dash.exceptions.PreventUpdate
            state = create_dynamic_state(origin, float(budget))
            state["blocked_edges"] = blocked_edges_data or []
            return state, dash.no_update

        if not journey_data or not graph_data:
            raise dash.exceptions.PreventUpdate

        g = build_graph_from_dict(graph_data)

        if tid == "fly-btn":
            if flight_val is None:
                raise dash.exceptions.PreventUpdate
            journey_data["blocked_edges"] = blocked_edges_data or []
            journey_data["pending_flight"] = int(flight_val)
            journey_data["in_transit"] = True
            journey_data["transit_ticks"] = 0
            journey_data["show_activities"] = False
            # Limpiar aviso de reroute anterior
            journey_data.pop("reroute_notice", None)
            return journey_data, dash.no_update

        if tid == "confirm-activities-btn":
            journey_data["blocked_edges"] = blocked_edges_data or []

            if journey_data.get("in_transit"):
                journey_data["in_transit"] = False
                journey_data["show_activities"] = True

            elif journey_data.get("show_activities"):
                # 1. Procesar actividades opcionales seleccionadas
                selected = selected_activities or []
                journey_data.setdefault("activities_done", [])
                for idx_str in selected:
                    result = do_optional_activity(g, journey_data, int(idx_str))
                    if result.get("success"):
                        journey_data["activities_done"].append({
                            "airport": journey_data["current_id"],
                            "name": result["activity_name"],
                            "cost": result["cost_usd"],
                            "duration_min": result["duration_min"],
                        })

                # 2. Avanzar tiempo al mínimo de estadía si hay tiempo libre
                arrival_time_h  = journey_data.get("arrival_time_h", 0.0)
                minimum_stay_h  = journey_data.get("minimum_stay_h", 0.0)
                available_until = arrival_time_h + minimum_stay_h
                current_time_h  = journey_data["time_min"] / 60.0
                if current_time_h < available_until:
                    free_time_h = available_until - current_time_h
                    journey_data["time_min"] = round(available_until * 60.0, 2)
                    journey_data.setdefault("free_time_log", [])
                    journey_data["free_time_log"].append({
                        "airport": journey_data["current_id"],
                        "free_time_h": round(free_time_h, 2),
                    })

                # 3. check_obligatory al salir del panel — comida/alojamiento en destino
                from backend.models.traveler import Traveler
                vertex = g.get_vertex(journey_data["current_id"])
                if vertex:
                    traveler = Traveler(budget=journey_data["budget"])
                    traveler.current_time        = journey_data["time_min"] / 60.0
                    traveler.last_food           = journey_data["last_food_h"]
                    traveler.last_accommodation  = journey_data["last_accommodation_h"]
                    traveler.current_location    = vertex
                    oblig_result = traveler.check_obligatory(vertex)
                    obligatory_delta = round(traveler.total_cost, 2)
                    journey_data["budget"] = round(traveler.budget, 2)
                    journey_data["obligatory_cost_total"] = round(
                        journey_data.get("obligatory_cost_total", 0.0) + obligatory_delta, 2
                    )
                    journey_data["last_food_h"]          = traveler.last_food
                    journey_data["last_accommodation_h"] = traveler.last_accommodation
                    if not oblig_result.get("success"):
                        journey_data.setdefault("payment_warnings", [])
                        journey_data["payment_warnings"].append(oblig_result["error"])

                journey_data["show_activities"] = False

            return journey_data, dash.no_update

        if tid == "work-btn":
            if job_val is None or not hours_val:
                raise dash.exceptions.PreventUpdate
            journey_data["blocked_edges"] = blocked_edges_data or []
            journey_data.pop("_job_error", None)
            result = work_at_job(g, journey_data, int(job_val), float(hours_val))
            if not result.get("success"):
                journey_data["_job_error"] = result.get("error", "Error al procesar el trabajo.")
            return journey_data, dash.no_update

        if tid == "end-btn":
            finish_itinerary(journey_data)
            return journey_data, dash.no_update

        raise dash.exceptions.PreventUpdate

    @app.callback(
        Output("journey-status",          "children"),
        Output("setup-section",           "style"),
        Output("flying-section",          "style"),
        Output("flight-radio",            "options"),
        Output("flight-radio",            "value"),
        Output("arrival-section",         "style"),
        Output("arrival-info",            "children"),
        Output("job-section",             "style"),
        Output("job-dropdown",            "options"),
        Output("job-dropdown",            "value"),
        Output("hours-input",             "value"),
        Output("job-result",              "children"),
        Output("activity-checklist",      "options"),
        Output("activity-checklist",      "value"),
        Output("transit-section",         "style"),
        Output("journey-report",          "children"),
        Output("journey-modal",           "style"),
        Output("new-journey-container",   "style"),
        Input("journey-store",            "data"),
        Input("graph-store",              "data"),
        State("blocked-edges-store",      "data"),
    )
    def render_planner(journey_data, graph_data, blocked_edges_data):
        if not journey_data:
            return (None, SHOW, HIDE, [], None, HIDE, "", HIDE, [], None, None, "", [], [], HIDE, None, HIDE, HIDE)

        finished        = journey_data.get("finished", False)
        in_transit      = journey_data.get("in_transit", False)
        show_activities = journey_data.get("show_activities", False)
        g = build_graph_from_dict(graph_data) if graph_data else None

        budget          = journey_data["budget"]
        time_h          = journey_data["time_min"] / 60
        total_cost      = sum(s["cost"] for s in journey_data.get("segments", []))
        initial_budget  = journey_data.get("initial_budget", budget + total_cost)
        total_earned    = journey_data.get("total_earned", 0)
        obligatory_cost = journey_data.get("obligatory_cost_total", 0)
        pct = (budget / initial_budget * 100) if initial_budget > 0 else 0
        budget_color = (
            COLORS["ok"]      if pct > 50 else
            COLORS["warning"] if pct > 20 else
            COLORS["error"]
        )

        status_lines = [
            html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "6px"}, children=[
                html.Span(f"✈  {journey_data['current_id']}",
                          style={"fontWeight": "800", "fontSize": "16px", "color": COLORS["text"]}),
                html.Span(f"{len(journey_data['visited']) - 1} destinos",
                          style={"fontSize": "11px", "color": COLORS["text_dim"]}),
            ]),
            html.Div(style={"display": "flex", "justifyContent": "space-between"}, children=[
                html.Span(f"Presupuesto: ${budget:.2f}",
                          style={"fontSize": "12px", "fontWeight": "700", "color": budget_color}),
                html.Span(f"{pct:.1f}%", style={"fontSize": "12px", "color": budget_color}),
            ]),
            html.Div(style={
                "height": "5px", "backgroundColor": COLORS["border"], "borderRadius": "3px",
                "marginTop": "6px", "marginBottom": "6px", "overflow": "hidden",
            }, children=[html.Div(style={
                "width": f"{min(pct,100):.0f}%", "height": "100%",
                "backgroundColor": budget_color, "borderRadius": "3px",
            })]),
            html.Div(f"Tiempo: {time_h:.1f} h  ·  Gastado: ${total_cost:.2f} USD",
                     style={"fontSize": "11px", "color": COLORS["text_dim"]}),
        ]

        skm = journey_data.get("free_km", 0)
        tkm = journey_data.get("total_km", 0)
        if tkm > 0:
            spct = (skm / tkm) * 100
            status_lines.append(html.Div(
                f"Dist. subsidiada: {skm:.0f} / {tkm:.0f} km ({spct:.1f}%) — Límite: 20%",
                style={"fontSize": "10px", "color": COLORS["text_dim"],
                       "fontWeight": "600", "marginTop": "4px"},
            ))

        if total_earned > 0:
            status_lines.append(html.Div(
                f"Ganado con trabajos: ${total_earned:.2f}",
                style={"fontSize": "11px", "color": COLORS["ok"],
                       "marginTop": "4px", "fontWeight": "600"},
            ))

        if obligatory_cost > 0:
            status_lines.append(html.Div(
                f"Cargos obligatorios: -${obligatory_cost:.2f} USD (comida + alojamiento)",
                style={"fontSize": "11px", "color": COLORS["error"],
                       "marginTop": "4px", "fontWeight": "600"},
            ))

        # Actividades realizadas en el aeropuerto actual
        if not show_activities and not in_transit:
            activities_done  = journey_data.get("activities_done", [])
            current_airport  = journey_data["current_id"]
            last_activities  = [a for a in activities_done if a.get("airport") == current_airport]
            if last_activities:
                names           = "  ·  ".join(a["name"] for a in last_activities)
                total_act_cost  = sum(a["cost"] for a in last_activities)
                status_lines.append(html.Div(
                    f"✅ Actividades: {names}  ·  -${total_act_cost:.2f}",
                    style={"fontSize": "11px", "color": COLORS["highlight"],
                           "marginTop": "4px", "fontWeight": "600"},
                ))

            # Tiempo libre registrado en el aeropuerto actual
            free_time_log   = journey_data.get("free_time_log", [])
            last_free       = next((f for f in reversed(free_time_log)
                                    if f.get("airport") == current_airport), None)
            if last_free and last_free["free_time_h"] > 0:
                status_lines.append(html.Div(
                    f"🕐 Tiempo libre registrado: {last_free['free_time_h']:.2f} h",
                    style={"fontSize": "11px", "color": COLORS["text_dim"],
                           "marginTop": "4px", "fontStyle": "italic"},
                ))

        # Aviso de reroute por interrupción
        reroute_notice = journey_data.get("reroute_notice", "")
        if reroute_notice:
            status_lines.append(html.Div(
                f"⚠️ {reroute_notice}",
                style={"fontSize": "11px", "color": COLORS["warning"],
                       "marginTop": "6px", "fontWeight": "600",
                       "backgroundColor": "#fef3c7", "padding": "6px 8px",
                       "borderRadius": "4px", "lineHeight": "1.5"},
            ))

        # Advertencias de pago insuficiente (comida / alojamiento)
        payment_warnings = journey_data.get("payment_warnings", [])
        if payment_warnings:
            for warn_msg in payment_warnings:
                status_lines.append(html.Div(
                    f"🚫 {warn_msg}",
                    style={"fontSize": "11px", "color": "#dc2626",
                           "marginTop": "6px", "fontWeight": "700",
                           "backgroundColor": "#fef2f2", "padding": "6px 8px",
                           "borderRadius": "4px", "lineHeight": "1.5",
                           "border": "1px solid #fca5a5"},
                ))
            # Clear after display so they don't accumulate indefinitely
            journey_data["payment_warnings"] = []

        status = html.Div(
            style={**CARD, "borderLeft": f"3px solid {budget_color}", "marginBottom": "14px"},
            children=status_lines,
        )

        if finished:
            s = build_summary(journey_data)
            s["initial_budget"] = initial_budget
            report = _render_report(s, g)
            return (status, HIDE, HIDE, [], None, HIDE, "", HIDE, [], None, None, "", [], [], HIDE, report, MODAL_SHOW, SHOW)

        flight_opts          = []
        job_opts             = []
        job_visible          = HIDE
        job_result           = ""
        arrival_info_content = ""
        activity_opts        = []
        activity_vals        = []
        transit_style        = HIDE

        if g:
            journey_data["blocked_edges"] = journey_data.get("blocked_edges", [])
            result = get_available_flights(g, journey_data)
            if result.get("success"):
                for fl in result.get("available_flights", []):
                    sub  = fl.get("subsidized", False)
                    dis  = fl.get("disabled", False)
                    warn = fl.get("warning", "")
                    label = html.Div([
                        html.Span(
                            f"{fl['destination']}  ·  {fl['aircraft']}  "
                            f"${fl['cost']:.2f}  ·  {fl['time_min']:.0f} min  ·  {fl['distance_km']:.0f} km"
                            + (" (Subsidiada)" if sub else ""),
                            style={
                                "fontWeight": "600" if sub else "inherit",
                                "backgroundColor": "#f5f5f5" if dis else ("#fef2f2" if sub else "transparent"),
                                "color": "#999" if dis else ("#dc2626" if sub else "inherit"),
                                "padding": "4px 6px", "borderRadius": "4px",
                                "display": "flex", "alignItems": "center", "width": "100%",
                            }
                        ),
                        html.Span(f" ⚠ {warn}",
                                  style={"fontSize": "10px", "color": "#dc2626",
                                         "marginLeft": "4px", "fontWeight": "600"}) if warn else None,
                    ], style={"width": "100%"})
                    flight_opts.append({"label": label, "value": str(fl["id"]), "disabled": dis})

            if in_transit:
                transit_style = SHOW

            if show_activities:
                arrival_dest    = journey_data["current_id"]
                acts_result     = get_optional_activities(g, journey_data)
                remaining_h     = acts_result.get("remaining_window_h", 0.0) if acts_result.get("success") else 0.0
                min_stay_h      = acts_result.get("minimum_stay_h", 0.0)     if acts_result.get("success") else 0.0

                arrival_info_content = html.Div(
                    style={**CARD, "borderLeft": f"3px solid {COLORS['secondary']}", "marginBottom": "10px"},
                    children=[
                        html.Div(f"🛬 Llegaste a {arrival_dest}",
                                 style={"fontSize": "12px", "fontWeight": "700",
                                        "color": COLORS["secondary"], "marginBottom": "4px"}),
                        html.Div(
                            f"Estancia mínima: {min_stay_h * 60:.0f} min  ·  "
                            f"Tiempo disponible: {remaining_h:.2f} h",
                            style={"fontSize": "11px", "color": COLORS["text_dim"]},
                        ),
                    ],
                )

                if acts_result.get("success"):
                    for act in acts_result.get("activities", []):
                        fits_label = "" if act["fits_in_window"] else "  ⚠ tiempo insuficiente"
                        activity_opts.append({
                            "label": (f"{act['name']}  ·  {act['duration_min']} min"
                                      f"  ·  ${act['cost_usd']:.2f}{fits_label}"),
                            "value": str(act["id"]),
                            "disabled": not act["fits_in_window"],
                        })

            jobs_res = get_available_jobs(g, journey_data)
            if jobs_res.get("success") and jobs_res.get("show_jobs"):
                for j in jobs_res.get("jobs", []):
                    job_opts.append({
                        "label": f"{j['name']}  ·  ${j['hourly_rate']:.2f}/h  (quedan {j['hours_remaining']:.1f} h)",
                        "value": str(j["id"]),
                        "disabled": j["hours_remaining"] <= 0,
                    })
                if job_opts:
                    job_visible = SHOW
                    job_result  = journey_data.get("_job_error") or "Presupuesto bajo. Trabaja para ganar más."
                else:
                    job_result = "No hay trabajos disponibles en este aeropuerto."

        show_flying  = HIDE if (in_transit or show_activities) else SHOW
        show_arrival = SHOW if show_activities else HIDE

        return (status, HIDE, show_flying,
                flight_opts, None, show_arrival, arrival_info_content,
                job_visible, job_opts, None, None, job_result,
                activity_opts, activity_vals, transit_style, None, HIDE, HIDE)

    @app.callback(
        Output("journey-modal", "style", allow_duplicate=True),
        Input("close-modal-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def close_modal(n_clicks):
        if not n_clicks:
            raise dash.exceptions.PreventUpdate
        return HIDE


# ── ITEM 2.5 — Reporte final del viaje (R5) ──

def _render_report(s, g=None):
    # Builds the complete trip report with 5 sections: destinations, segments,
    # activities, jobs, and totals. Accepts the graph to look up airport metadata.

    def _vertex_info(airport_id):
        # Returns (name, city, country) from graph if available
        if g:
            v = g.get_vertex(airport_id)
            if v:
                return v.name, v.city, v.country
        return airport_id, "", ""

    sections      = []
    dest_log      = s.get("destination_log", [])
    acts_done     = s.get("activities_done", [])
    jobs_done     = s.get("jobs_done", [])
    segments      = s.get("segments", [])
    total_time_h  = s.get("total_time_hours", 0)

    # ── Sección 1: Destinos visitados ──
    if dest_log:
        dest_cards = []
        for entry in dest_log:
            airport_id  = entry["airport_id"]
            arrival_h   = entry.get("arrival_h")   # None for origin
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
            airport_acts = [a for a in acts_done if a.get("airport") == airport_id]
            act_cost = sum(a["cost"] for a in airport_acts)

            card_ch = [
                html.Div(style={"display": "flex", "justifyContent": "space-between",
                                "alignItems": "baseline", "marginBottom": "2px"}, children=[
                    html.Span(airport_id, style={"fontSize": "16px", "fontWeight": "800", "color": accent}),
                    html.Span(time_label, style={"fontSize": "10px", "color": COLORS["text_dim"]}),
                ]),
            ]
            if name != airport_id:
                card_ch.append(html.Div(
                    name, style={"fontSize": "11px", "fontStyle": "italic",
                                 "color": COLORS["text_dim"], "marginBottom": "2px"}))
            if city:
                card_ch.append(html.Div(
                    f"{city}, {country}",
                    style={"fontSize": "11px", "color": COLORS["text_dim"], "marginBottom": "6px"}))

            # Cost breakdown for this destination
            cost_parts = []
            if seg_cost is not None and seg_cost > 0:
                cost_parts.append(f"Vuelo: ${seg_cost:.2f}")
            if act_cost > 0:
                act_names = " / ".join(a["name"] for a in airport_acts)
                cost_parts.append(f"Actividades ({act_names}): ${act_cost:.2f}")
            if cost_parts:
                card_ch.append(html.Div(
                    "  ·  ".join(cost_parts),
                    style={"fontSize": "11px", "fontWeight": "600", "color": COLORS["error"]},
                ))

            dest_cards.append(html.Div(
                style={**CARD, "borderLeft": f"3px solid {accent}", "marginBottom": "6px"},
                children=card_ch,
            ))

        sections.append(html.Div([
            html.Div(f"Destinos visitados: {s.get('destinations_visited', 0)}",
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
    obligatory_total = s.get("obligatory_cost_total", 0.0)

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
    for a in acts_done:
        act_items.append(html.Div(
            style={"display": "flex", "justifyContent": "space-between",
                   "marginBottom": "6px", "alignItems": "flex-start"},
            children=[
                html.Div([
                    html.Span(a["name"], style={"fontWeight": "600", "fontSize": "11px"}),
                    html.Div(
                        f"Opcional  ·  {a['airport']}  ·  {a['duration_min']} min",
                        style={"fontSize": "10px", "color": COLORS["text_dim"]},
                    ),
                ]),
                html.Span(f"-${a['cost']:.2f}",
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
                        html.Span(j["job_name"],
                                  style={"fontWeight": "600", "fontSize": "11px"}),
                        html.Div(
                            f"{j['airport']}  ·  {j['hours']} h  ·  ${j['hourly_rate']:.2f}/h",
                            style={"fontSize": "10px", "color": COLORS["text_dim"]},
                        ),
                    ]),
                    html.Span(f"+${j['earnings']:.2f}",
                              style={"fontWeight": "700", "fontSize": "12px",
                                     "color": COLORS["ok"], "whiteSpace": "nowrap"}),
                ],
            )
            for j in jobs_done
        ]
        sections.append(html.Div([
            html.Div("Trabajos realizados",
                     style={**SECTION_TITLE, "marginBottom": "8px", "marginTop": "12px"}),
            *job_rows,
            html.Div(
                f"Total ganado: ${s.get('total_earned', 0):.2f}",
                style={"fontSize": "12px", "fontWeight": "700",
                       "color": COLORS["ok"], "marginTop": "4px"},
            ),
        ]))

    # ── Sección 5: Resumen de totales ──
    skm = s.get("subsidized_km", 0)
    tkm = s.get("total_km", 0)

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
                    ("Presupuesto inicial",    f"${s.get('initial_budget', 0):.2f}",     COLORS["text"]),
                    ("Total vuelos",           f"-${s.get('total_cost', 0):.2f}",         COLORS["error"]),
                    ("Cargos obligatorios",    f"-${obligatory_total:.2f}",               COLORS["error"]),
                    ("Ganado en trabajos",     f"+${s.get('total_earned', 0):.2f}",       COLORS["ok"]),
                    ("Saldo final",            f"${s.get('remaining_budget', 0):.2f}",    COLORS["text"]),
                    ("Tiempo total del viaje", f"{s.get('total_time_hours', 0):.1f} h",   COLORS["text"]),
                    ("Destinos visitados",     str(s.get("destinations_visited", 0)),      COLORS["text"]),
                ]
            ],
            html.Div(style={"borderTop": f"1px solid {COLORS['border']}", "margin": "8px 0 6px"}),
            html.Div(style={"display": "flex", "justifyContent": "space-between",
                            "marginBottom": "5px", "fontSize": "12px"}, children=[
                html.Span("Dist. subsidiada", style={"color": COLORS["text_dim"]}),
                html.Span(
                    f"{skm:.0f} / {tkm:.0f} km ({s.get('subsidy_ratio', 0):.1f}%)",
                    style={"fontWeight": "700"},
                ),
            ]),
            html.Div(style={"display": "flex", "justifyContent": "space-between",
                            "fontSize": "12px"}, children=[
                html.Span("Límite 20%", style={"color": COLORS["text_dim"]}),
                html.Span(
                    "✔ Cumple" if s.get("subsidy_valid") else "✘ Excede",
                    style={"fontWeight": "700",
                           "color": COLORS["ok"] if s.get("subsidy_valid") else COLORS["error"]},
                ),
            ]),
        ],
    )

    return html.Div([*sections, totals])

# ── END ITEM 2.5 ──

# ── END ITEM 2.3.a / 2.3.b / 2.3.c ──
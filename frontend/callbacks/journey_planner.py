# ── ITEM 2.3.a — Traveler obligatory activities (food + accommodation) + optional activities
# ── ITEM 2.3.b — Jobs at airports (earn additional budget when budget < 35%)
# ── ITEM 2.3.c — Transport costs (aircraft selection, flight cost/time, subsidised 20% rule)
# Note: the final trip report (R5) lives in trip_report.py — render_report().

from dash import html, Input, Output, State
import dash

from backend.services.graphService import build_graph_from_dict
from backend.services.dynamicService import (
    create_dynamic_state, get_available_flights,
    choose_flight, finish_itinerary, build_summary,
    get_available_jobs, work_at_job,
    do_optional_activity, get_optional_activities,
    _traveler_from_state, _sync_obligatory,
)
from frontend.config import COLORS, CARD, SHOW, HIDE
from frontend.callbacks.trip_report import render_report

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
        triggered_id = dash.callback_context.triggered_id
        if not triggered_id:
            raise dash.exceptions.PreventUpdate

        if triggered_id == "new-journey-btn":
            # Clear both journey and blocked edges so the new trip starts clean
            return None, []

        if triggered_id == "start-btn":
            if not origin or not budget or not graph_data:
                raise dash.exceptions.PreventUpdate
            state = create_dynamic_state(origin, float(budget))
            state["blocked_edges"] = blocked_edges_data or []
            return state, dash.no_update

        if not journey_data or not graph_data:
            raise dash.exceptions.PreventUpdate

        graph = build_graph_from_dict(graph_data)

        if triggered_id == "fly-btn":
            if flight_val is None:
                raise dash.exceptions.PreventUpdate
            journey_data["blocked_edges"] = blocked_edges_data or []
            flight_id = int(flight_val)
            journey_data["pending_flight"] = flight_id

            # Lock destination and aircraft NOW, before the options list can change
            # due to edge blocking during animation.
            from backend.services.dynamicService import _list_available_flights
            vertex = graph.get_vertex(journey_data["current_id"])
            if vertex:
                options = _list_available_flights(
                    vertex,
                    journey_data["visited"],
                    graph.aircraft_config,
                    journey_data["free_km"],
                    journey_data["total_km"],
                    journey_data["budget"],
                    journey_data["blocked_edges"],
                )
                if flight_id < len(options):
                    journey_data["pending_destination"] = options[flight_id]["destination"]
                    journey_data["pending_aircraft"]    = options[flight_id]["aircraft"]

            journey_data["in_transit"] = True
            journey_data["transit_ticks"] = 0
            journey_data["show_activities"] = False
            # Limpiar aviso de reroute anterior
            journey_data.pop("reroute_notice", None)
            return journey_data, dash.no_update

        if triggered_id == "confirm-activities-btn":
            journey_data["blocked_edges"] = blocked_edges_data or []

            if journey_data.get("in_transit"):
                journey_data["in_transit"] = False
                journey_data["show_activities"] = True

            elif journey_data.get("show_activities"):
                # 1. Procesar actividades opcionales seleccionadas
                selected = selected_activities or []
                journey_data.setdefault("activities_done", [])
                journey_data.setdefault("payment_warnings", [])
                for idx_str in selected:
                    result = do_optional_activity(graph, journey_data, int(idx_str))
                    if result.get("success"):
                        journey_data["activities_done"].append({
                            "airport": journey_data["current_id"],
                            "name": result["activity_name"],
                            "cost": result["cost_usd"],
                            "duration_min": result["duration_min"],
                        })
                        # Propagate any obligatory charge warnings triggered by this activity
                        if result.get("payment_warning"):
                            journey_data["payment_warnings"].append(result["payment_warning"])
                    else:
                        # Activity was rejected — inform the traveler explicitly
                        activity_name = "Actividad"
                        try:
                            current_vertex = graph.get_vertex(journey_data["current_id"])
                            airport_activities = getattr(current_vertex, "activities", []) or []
                            activity_index = int(idx_str)
                            if activity_index < len(airport_activities):
                                activity_name = airport_activities[activity_index].get("name", activity_name)
                        except Exception:
                            pass
                        journey_data["payment_warnings"].append(
                            result.get("error") or
                            f"No se pudo realizar '{activity_name}': tiempo o fondos insuficientes."
                        )

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
                vertex = graph.get_vertex(journey_data["current_id"])
                if vertex:
                    traveler = _traveler_from_state(journey_data, vertex)
                    oblig_result = traveler.check_obligatory(vertex)
                    _sync_obligatory(journey_data, traveler)
                    if not oblig_result.get("success"):
                        journey_data.setdefault("payment_warnings", [])
                        journey_data["payment_warnings"].append(oblig_result["error"])

                journey_data["show_activities"] = False

            return journey_data, dash.no_update

        if triggered_id == "work-btn":
            if job_val is None or not hours_val:
                raise dash.exceptions.PreventUpdate
            journey_data["blocked_edges"] = blocked_edges_data or []
            journey_data.pop("_job_error", None)
            result = work_at_job(graph, journey_data, int(job_val), float(hours_val))
            if not result.get("success"):
                journey_data["_job_error"] = result.get("error", "Error al procesar el trabajo.")
            return journey_data, dash.no_update

        if triggered_id == "end-btn":
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
        graph = build_graph_from_dict(graph_data) if graph_data else None

        budget          = journey_data["budget"]
        time_h          = journey_data["time_min"] / 60
        total_cost      = sum(seg["cost"] for seg in journey_data.get("segments", []))
        initial_budget  = journey_data.get("initial_budget", budget + total_cost)
        total_earned    = journey_data.get("total_earned", 0)
        obligatory_cost = journey_data.get("obligatory_cost_total", 0)
        budget_pct = (budget / initial_budget * 100) if initial_budget > 0 else 0
        budget_color = (
            COLORS["ok"]      if budget_pct > 50 else
            COLORS["warning"] if budget_pct > 20 else
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
                html.Span(f"{budget_pct:.1f}%", style={"fontSize": "12px", "color": budget_color}),
            ]),
            html.Div(style={
                "height": "5px", "backgroundColor": COLORS["border"], "borderRadius": "3px",
                "marginTop": "6px", "marginBottom": "6px", "overflow": "hidden",
            }, children=[html.Div(style={
                "width": f"{min(budget_pct,100):.0f}%", "height": "100%",
                "backgroundColor": budget_color, "borderRadius": "3px",
            })]),
            html.Div(f"Tiempo: {time_h:.1f} h  ·  Gastado: ${total_cost:.2f} USD",
                     style={"fontSize": "11px", "color": COLORS["text_dim"]}),
        ]

        subsidized_km = journey_data.get("free_km", 0)
        total_km      = journey_data.get("total_km", 0)
        if total_km > 0:
            subsidy_pct = (subsidized_km / total_km) * 100
            status_lines.append(html.Div(
                f"Dist. subsidiada: {subsidized_km:.0f} / {total_km:.0f} km ({subsidy_pct:.1f}%) — Límite: 20%",
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
            last_activities  = [activity for activity in activities_done if activity.get("airport") == current_airport]
            if last_activities:
                names           = "  ·  ".join(activity["name"] for activity in last_activities)
                total_act_cost  = sum(activity["cost"] for activity in last_activities)
                status_lines.append(html.Div(
                    f"✅ Actividades: {names}  ·  -${total_act_cost:.2f}",
                    style={"fontSize": "11px", "color": COLORS["highlight"],
                           "marginTop": "4px", "fontWeight": "600"},
                ))

            # Tiempo libre registrado en el aeropuerto actual
            free_time_log   = journey_data.get("free_time_log", [])
            last_free       = next((entry for entry in reversed(free_time_log)
                                    if entry.get("airport") == current_airport), None)
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
            summary = build_summary(journey_data)
            summary["initial_budget"] = initial_budget
            report = render_report(summary, graph)
            return (status, HIDE, HIDE, [], None, HIDE, "", HIDE, [], None, None, "", [], [], HIDE, report, MODAL_SHOW, SHOW)

        flight_opts          = []
        job_opts             = []
        job_visible          = HIDE
        job_result           = ""
        arrival_info_content = ""
        activity_opts        = []
        activity_vals        = []
        transit_style        = HIDE

        if graph:
            journey_data["blocked_edges"] = journey_data.get("blocked_edges", [])
            result = get_available_flights(graph, journey_data)
            if result.get("success"):
                for flight in result.get("available_flights", []):
                    is_subsidized = flight.get("subsidized", False)
                    is_disabled   = flight.get("disabled", False)
                    warning       = flight.get("warning", "")
                    label = html.Div([
                        html.Span(
                            f"{flight['destination']}  ·  {flight['aircraft']}  "
                            f"${flight['cost']:.2f}  ·  {flight['time_min']:.0f} min  ·  {flight['distance_km']:.0f} km"
                            + (" (Subsidiada)" if is_subsidized else ""),
                            style={
                                "fontWeight": "600" if is_subsidized else "inherit",
                                "backgroundColor": "#f5f5f5" if is_disabled else ("#fef2f2" if is_subsidized else "transparent"),
                                "color": "#999" if is_disabled else ("#dc2626" if is_subsidized else "inherit"),
                                "padding": "4px 6px", "borderRadius": "4px",
                                "display": "flex", "alignItems": "center", "width": "100%",
                            }
                        ),
                        html.Span(f" ⚠ {warning}",
                                  style={"fontSize": "10px", "color": "#dc2626",
                                         "marginLeft": "4px", "fontWeight": "600"}) if warning else None,
                    ], style={"width": "100%"})
                    flight_opts.append({"label": label, "value": str(flight["id"]), "disabled": is_disabled})

            if in_transit:
                transit_style = SHOW

            if show_activities:
                arrival_dest    = journey_data["current_id"]
                acts_result     = get_optional_activities(graph, journey_data)
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
                    for activity in acts_result.get("activities", []):
                        fits_label = "" if activity["fits_in_window"] else "  ⚠ tiempo insuficiente"
                        activity_opts.append({
                            "label": (f"{activity['name']}  ·  {activity['duration_min']} min"
                                      f"  ·  ${activity['cost_usd']:.2f}{fits_label}"),
                            "value": str(activity["id"]),
                            "disabled": not activity["fits_in_window"],
                        })

            jobs_res = get_available_jobs(graph, journey_data)
            if jobs_res.get("success") and jobs_res.get("show_jobs"):
                for job in jobs_res.get("jobs", []):
                    job_opts.append({
                        "label": f"{job['name']}  ·  ${job['hourly_rate']:.2f}/h  (quedan {job['hours_remaining']:.1f} h)",
                        "value": str(job["id"]),
                        "disabled": job["hours_remaining"] <= 0,
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

# ── END ITEM 2.3.a / 2.3.b / 2.3.c ──

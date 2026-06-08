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


def register(app):

    @app.callback(
        Output("journey-store", "data"),
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
    )
    def handle_journey_action(start_n, fly_n, end_n, new_n, work_n, confirm_n,
                              origin, budget, flight_val,
                              job_val, hours_val, selected_activities,
                              journey_data, graph_data, blocked_edges_data):
        tid = dash.callback_context.triggered_id
        if not tid:
            raise dash.exceptions.PreventUpdate

        if tid == "new-journey-btn":
            return None

        if tid == "start-btn":
            if not origin or not budget or not graph_data:
                raise dash.exceptions.PreventUpdate
            state = create_dynamic_state(origin, float(budget))
            state["blocked_edges"] = blocked_edges_data or []
            return state

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
            return journey_data

        if tid == "confirm-activities-btn":
            journey_data["blocked_edges"] = blocked_edges_data or []
            if journey_data.get("in_transit"):
                journey_data["in_transit"] = False
                journey_data["show_activities"] = True
            elif journey_data.get("show_activities"):
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
                journey_data["show_activities"] = False
            return journey_data

        if tid == "work-btn":
            if job_val is None or not hours_val:
                raise dash.exceptions.PreventUpdate
            journey_data["blocked_edges"] = blocked_edges_data or []
            work_at_job(g, journey_data, int(job_val), float(hours_val))
            return journey_data

        if tid == "end-btn":
            finish_itinerary(journey_data)
            return journey_data

        raise dash.exceptions.PreventUpdate

    @app.callback(
        Output("journey-status",     "children"),
        Output("setup-section",      "style"),
        Output("flying-section",     "style"),
        Output("complete-section",   "style"),
        Output("flight-radio",       "options"),
        Output("flight-radio",       "value"),
        Output("arrival-section",    "style"),
        Output("arrival-info",       "children"),
        Output("job-section",        "style"),
        Output("job-dropdown",       "options"),
        Output("job-dropdown",       "value"),
        Output("hours-input",        "value"),
        Output("job-result",         "children"),
        Output("activity-checklist", "options"),
        Output("activity-checklist", "value"),
        Output("transit-section",    "style"),
        Input("journey-store",       "data"),
        Input("graph-store",         "data"),
        State("blocked-edges-store", "data"),
    )
    def render_planner(journey_data, graph_data, blocked_edges_data):
        if not journey_data:
            return (None, SHOW, HIDE, HIDE, [], None, HIDE, "", HIDE, [], None, None, "", [], [], HIDE)

        finished      = journey_data.get("finished", False)
        in_transit    = journey_data.get("in_transit", False)
        show_activities = journey_data.get("show_activities", False)
        arrival_info  = journey_data.get("arrival_info", {})
        g = build_graph_from_dict(graph_data) if graph_data else None

        budget         = journey_data["budget"]
        time_h         = journey_data["time_min"] / 60
        total_cost     = sum(s["cost"] for s in journey_data.get("segments", []))
        initial_budget = journey_data.get("initial_budget", budget + total_cost)
        total_earned   = journey_data.get("total_earned", 0)
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

        # Activities summary after confirming
        if not show_activities and not in_transit:
            activities_done = journey_data.get("activities_done", [])
            current_airport = journey_data["current_id"]
            last_activities = [a for a in activities_done if a.get("airport") == current_airport]
            if last_activities:
                names = "  ·  ".join(a["name"] for a in last_activities)
                total_act_cost = sum(a["cost"] for a in last_activities)
                status_lines.append(html.Div(
                    f"✅ Activities: {names}  ·  -${total_act_cost:.2f}",
                    style={"fontSize": "11px", "color": COLORS["highlight"],
                           "marginTop": "4px", "fontWeight": "600"},
                ))

        status = html.Div(
            style={**CARD, "borderLeft": f"3px solid {budget_color}", "marginBottom": "14px"},
            children=status_lines,
        )

        if finished:
            s = build_summary(journey_data)
            s["initial_budget"] = initial_budget
            _render_report(s)
            return (status, HIDE, HIDE, SHOW, [], None, HIDE, "", HIDE, [], None, None, "", [], [], HIDE)

        flight_opts     = []
        job_opts        = []
        job_visible     = HIDE
        job_result      = ""
        arrival_info_content = ""
        activity_opts   = []
        activity_vals   = []
        transit_style   = HIDE

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
                arrival_dest = journey_data["current_id"]
                arrival_info_content = html.Div(
                    style={**CARD, "borderLeft": f"3px solid {COLORS['secondary']}", "marginBottom": "10px"},
                    children=[
                        html.Div(f"🛬 Llegaste a {arrival_dest}",
                                 style={"fontSize": "12px", "fontWeight": "700",
                                        "color": COLORS["secondary"], "marginBottom": "6px"}),
                    ],
                )
                acts_result = get_optional_activities(g, journey_data)
                if acts_result.get("success"):
                    remaining_h = acts_result.get("remaining_window_h", 0.0)
                    min_stay_h  = acts_result.get("minimum_stay_h", 0.0)
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
                    for act in acts_result.get("activities", []):
                        fits_label = "" if act["fits_in_window"] else "  ⚠ not enough time"
                        activity_opts.append({
                            "label": f"{act['name']}  ·  {act['duration_min']} min  ·  ${act['cost_usd']:.2f}{fits_label}",
                            "value": str(act["id"]),
                            "disabled": not act["fits_in_window"],
                        })

            jobs_res = get_available_jobs(g, journey_data)
            if jobs_res.get("success") and jobs_res.get("show_jobs"):
                for j in jobs_res.get("jobs", []):
                    job_opts.append({
                        "label": f"{j['name']}  ·  ${j['hourly_rate']:.2f}/h  (máx {j['max_hours']} h)",
                        "value": str(j["id"]),
                    })
                if job_opts:
                    job_visible = SHOW
                    job_result  = "Presupuesto bajo. Trabaja para ganar más."
                else:
                    job_result = "No hay trabajos disponibles en este aeropuerto."

        show_flying  = HIDE if (in_transit or show_activities) else SHOW
        show_arrival = SHOW if show_activities else HIDE

        return (status, HIDE, show_flying, HIDE,
                flight_opts, None, show_arrival, arrival_info_content,
                job_visible, job_opts, None, None, job_result,
                activity_opts, activity_vals, transit_style)


def _render_report(s):
    sections = []

    if s.get("segments"):
        rows = [
            html.Div(style={**CARD, "marginBottom": "8px"}, children=[
                html.Div(f"{seg['origin']} → {seg['destination']}",
                         style={"fontWeight": "700", "fontSize": "12px", "marginBottom": "4px"}),
                html.Div(f"Aeronave: {seg['aircraft']}  ·  {seg['distance_km']:.0f} km",
                         style={"fontSize": "11px", "color": COLORS["text_dim"]}),
                html.Div(f"Costo: ${seg['cost']:.2f}  ·  Tiempo: {seg['time_min']:.0f} min",
                         style={"fontSize": "11px", "color": COLORS["text_dim"]}),
            ])
            for seg in s["segments"]
        ]
        sections.append(html.Div([
            html.Div(f"Destinos visitados: {s.get('destinations_visited', 0)}",
                     style={**SECTION_TITLE, "marginBottom": "8px"}),
            *rows,
        ]))

    if s.get("jobs_done"):
        job_rows = [
            html.Div(style={"fontSize": "11px", "color": COLORS["text_dim"], "marginBottom": "4px"}, children=[
                html.Span(f"{j['job_name']} en {j['airport']}  ·  ", style={"fontWeight": "600"}),
                html.Span(f"{j['hours']} h  ·  +${j['earnings']:.2f}"),
            ])
            for j in s["jobs_done"]
        ]
        sections.append(html.Div([
            html.Div("Trabajos completados", style={**SECTION_TITLE, "marginBottom": "6px", "marginTop": "12px"}),
            *job_rows,
            html.Div(f"Total ganado: ${s.get('total_earned', 0):.2f}",
                     style={"fontSize": "12px", "fontWeight": "700",
                            "color": COLORS["ok"], "marginTop": "6px"}),
        ]))

    obligatory_total = s.get("obligatory_cost_total", 0.0)

    totals = html.Div(
        style={**CARD, "borderLeft": f"3px solid {COLORS['hub']}", "marginTop": "14px"},
        children=[
            html.Div("Resumen", style={**SECTION_TITLE, "marginBottom": "10px"}),
            *[
                html.Div(style={
                    "display": "flex", "justifyContent": "space-between",
                    "marginBottom": "5px", "fontSize": "12px",
                }, children=[
                    html.Span(label, style={"color": COLORS["text_dim"]}),
                    html.Span(value, style={"fontWeight": "700", "color": color}),
                ])
                for label, value, color in [
                    ("Presupuesto inicial", f"${s.get('initial_budget', 0):.2f}",   COLORS["text"]),
                    ("Total gastado",       f"${s.get('total_cost', 0):.2f}",       COLORS["error"]),
                    ("Cargos obligatorios", f"-${obligatory_total:.2f}",            COLORS["error"]),
                    ("Ganado en trabajos",  f"+${s.get('total_earned', 0):.2f}",    COLORS["ok"]),
                    ("Saldo final",         f"${s.get('remaining_budget', 0):.2f}", COLORS["text"]),
                    ("Tiempo total",        f"{s.get('total_time_hours', 0):.1f} h",COLORS["text"]),
                ]
            ],
            html.Div(style={"borderTop": f"1px solid {COLORS['border']}", "margin": "8px 0 6px"}),
            html.Div(style={"display": "flex", "justifyContent": "space-between",
                            "marginBottom": "5px", "fontSize": "12px"}, children=[
                html.Span("Dist. subsidiada", style={"color": COLORS["text_dim"]}),
                html.Span(
                    f"{s.get('subsidized_km', 0):.0f} / {s.get('total_km', 0):.0f} km"
                    f" ({s.get('subsidy_ratio', 0):.1f}%)",
                    style={"fontWeight": "700"},
                ),
            ]),
            html.Div(style={"display": "flex", "justifyContent": "space-between",
                            "fontSize": "12px"}, children=[
                html.Span("Límite 20%", style={"color": COLORS["text_dim"]}),
                html.Span(
                    "✔ Cumple" if s.get("subsidy_valid") else "✘ Excede",
                    style={"fontWeight": "700",
                           "color": "#16a34a" if s.get("subsidy_valid") else "#dc2626"},
                ),
            ]),
        ],
    )

    return html.Div([*sections, totals])

# ── END ITEM 2.3.a / 2.3.b / 2.3.c ──
# ── ITEM 2.3.a — Traveler obligatory activities (food + accommodation) + optional activities
# ── ITEM 2.3.b — Jobs at airports (earn additional budget when budget < 35%)
# ── ITEM 2.3.c — Transport costs (aircraft selection, flight cost/time, subsidised 20% rule) ──

from dash import html, Input, Output, State
import dash

from backend.services.graphService import build_graph_from_dict
from backend.services.dynamicService import (
    create_dynamic_state, get_available_flights,
    choose_flight, finish_itinerary, build_summary,
    get_available_jobs, work_at_job,
)
from frontend.config import COLORS, CARD, SECTION_TITLE, SHOW, HIDE


def register(app):

    @app.callback(
        Output("journey-store",          "data"),
        Input("start-btn",               "n_clicks"),
        Input("fly-btn",                 "n_clicks"),
        Input("end-btn",                 "n_clicks"),
        Input("new-journey-btn",         "n_clicks"),
        Input("work-btn",                "n_clicks"),
        State("planner-origin",          "value"),
        State("planner-budget",          "value"),
        State("flight-radio",            "value"),
        State("job-dropdown",            "value"),
        State("hours-input",             "value"),
        State("journey-store",           "data"),
        State("graph-store",             "data"),
    )
    def handle_journey_action(start_n, fly_n, end_n, new_n, work_n,
                              origin, budget, flight_val,
                              job_val, hours_val,
                              journey_data, graph_data):
        tid = dash.callback_context.triggered_id
        if not tid:
            raise dash.exceptions.PreventUpdate

        if tid == "new-journey-btn":
            return None

        if tid == "start-btn":
            if not origin or not budget or not graph_data:
                raise dash.exceptions.PreventUpdate
            return create_dynamic_state(origin, float(budget))

        if not journey_data or not graph_data:
            raise dash.exceptions.PreventUpdate
        g = build_graph_from_dict(graph_data)

        if tid == "fly-btn":
            if flight_val is None:
                raise dash.exceptions.PreventUpdate

            # ── ITEM 2.3.a — Reconstruct traveler and check obligatory activities ──
            from backend.models.traveler import Traveler
            traveler = Traveler(budget=journey_data["budget"])
            traveler.current_time = journey_data["time_min"] / 60
            traveler.last_food = journey_data.get("last_food", 0)
            traveler.last_accommodation = journey_data.get("last_accommodation", 0)
            traveler.current_location = g.get_vertex(journey_data["current_id"])

            choose_flight(g, journey_data, int(flight_val), traveler)

            # Save obligatory costs and traveler state back to journey_data
            journey_data["obligatory_cost"] = round(traveler.total_cost, 2)
            journey_data["last_food"] = traveler.last_food
            journey_data["last_accommodation"] = traveler.last_accommodation

            return journey_data

        if tid == "work-btn":
            if job_val is None or not hours_val:
                raise dash.exceptions.PreventUpdate
            work_at_job(g, journey_data, int(job_val), float(hours_val))
            return journey_data

        if tid == "end-btn":
            finish_itinerary(journey_data)
            return journey_data

        raise dash.exceptions.PreventUpdate

    @app.callback(
        Output("journey-status",          "children"),
        Output("setup-section",           "style"),
        Output("flying-section",          "style"),
        Output("complete-section",        "style"),
        Output("flight-radio",            "options"),
        Output("arrival-section",         "style"),
        Output("job-section",             "style"),
        Output("job-dropdown",            "options"),
        Output("job-dropdown",            "value"),
        Output("hours-input",             "value"),
        Output("job-result",              "children"),
        Input("journey-store",            "data"),
        Input("graph-store",              "data"),
    )
    def render_planner(journey_data, graph_data):
        if not journey_data:
            return (None, SHOW, HIDE, HIDE,
                    [], HIDE, HIDE,
                    [], None, None, "")

        finished = journey_data.get("finished", False)
        g = build_graph_from_dict(graph_data) if graph_data else None

        budget = journey_data["budget"]
        remaining = budget
        time_h = journey_data["time_min"] / 60
        total_cost = sum(s["cost"] for s in journey_data.get("segments", []))
        initial_budget = journey_data.get("initial_budget", remaining + total_cost)
        total_earned = journey_data.get("total_earned", 0)
        obligatory_cost = journey_data.get("obligatory_cost", 0)
        pct = (remaining / initial_budget * 100) if initial_budget > 0 else 0
        budget_color = COLORS["ok"] if pct > 50 else (COLORS["warning"] if pct > 20 else COLORS["error"])

        status_lines = [
            html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "6px"}, children=[
                html.Span(f"✈  {journey_data['current_id']}",
                          style={"fontWeight": "800", "fontSize": "16px", "color": COLORS["text"]}),
                html.Span(f"{len(journey_data['visited']) - 1} destinos",
                          style={"fontSize": "11px", "color": COLORS["text_dim"]}),
            ]),
            html.Div(style={"display": "flex", "justifyContent": "space-between"}, children=[
                html.Span(f"Presupuesto: ${remaining:.2f}",
                          style={"fontSize": "12px", "fontWeight": "700", "color": budget_color}),
                html.Span(f"{pct:.1f}%", style={"fontSize": "12px", "color": budget_color}),
            ]),
            html.Div(style={
                "height": "5px", "backgroundColor": COLORS["border"], "borderRadius": "3px",
                "marginTop": "6px", "marginBottom": "6px", "overflow": "hidden",
            }, children=[html.Div(style={"width": f"{min(pct,100):.0f}%", "height": "100%",
                                         "backgroundColor": budget_color, "borderRadius": "3px"})]),
            html.Div(f"Tiempo: {time_h:.1f} h  ·  Gastado: ${total_cost:.2f} USD",
                     style={"fontSize": "11px", "color": COLORS["text_dim"]}),
        ]

        skm = journey_data.get("free_km", 0)
        tkm = journey_data.get("total_km", 0)
        if tkm > 0:
            spct = (skm / tkm) * 100
            limit = 20.0
            status_lines.append(
                html.Div(
                    f"Dist. subsidiada: {skm:.0f} / {tkm:.0f} km ({spct:.1f}%) — Límite: {limit:.0f}%",
                    style={"fontSize": "10px", "color": COLORS["text_dim"], "fontWeight": "600",
                           "marginTop": "4px"}
                )
            )

        if total_earned > 0:
            status_lines.append(
                html.Div(f"Ganado con trabajos: ${total_earned:.2f}",
                         style={"fontSize": "11px", "color": COLORS["ok"], "marginTop": "4px", "fontWeight": "600"})
            )

        # ── ITEM 2.3.a — Show obligatory costs notification (food + accommodation) ──
        if obligatory_cost > 0:
            status_lines.append(
                html.Div(f"Obligatory charges: -${obligatory_cost:.2f} USD (food + accommodation)",
                         style={"fontSize": "11px", "color": COLORS["error"], "marginTop": "4px", "fontWeight": "600"})
            )

        status = html.Div(style={**CARD, "borderLeft": f"3px solid {budget_color}", "marginBottom": "14px"},
                          children=status_lines)

        if finished:
            s = build_summary(journey_data)
            s["initial_budget"] = initial_budget
            report = _render_report(s)
            return (status, HIDE, HIDE, SHOW,
                    [], HIDE, HIDE,
                    [], None, None, "")

        flight_opts = []
        job_opts = []
        job_visible = HIDE
        job_result = ""

        if g:
            result = get_available_flights(g, journey_data)
            if result.get("success"):
                for fl in result.get("available_flights", []):
                    sub = fl.get("subsidized", False)
                    dis = fl.get("disabled", False)
                    warn = fl.get("warning", "")
                    fid = str(fl["id"])

                    label = html.Div(
                        [
                            html.Span(
                                f"{fl['destination']}  ·  {fl['aircraft']}  "
                                f"${fl['cost']:.2f}  ·  {fl['time_min']:.0f} min  ·  {fl['distance_km']:.0f} km"
                                + (" (Subsidiada)" if sub else ""),
                                style={"fontWeight": "600" if sub else "inherit",
                                       "backgroundColor": "#f5f5f5" if dis else
                                                       ("#fef2f2" if sub else "transparent"),
                                       "color": "#999" if dis else
                                                   ("#dc2626" if sub else "inherit"),
                                       "padding": "4px 6px", "borderRadius": "4px",
                                       "display": "flex", "alignItems": "center", "width": "100%"}
                            ),
                            html.Span(f" ⚠ {warn}", style={"fontSize": "10px", "color": "#dc2626",
                                                           "marginLeft": "4px", "fontWeight": "600"}) if warn else None,
                        ],
                        style={"width": "100%"})
                    flight_opts.append({"label": label, "value": fid,
                                        "disabled": dis})

            jobs_res = get_available_jobs(g, journey_data)
            if jobs_res.get("success") and jobs_res.get("show_jobs"):
                for j in jobs_res.get("jobs", []):
                    label = (f"{j['name']}  ·  ${j['hourly_rate']:.2f}/h  "
                             f"(máx {j['max_hours']} h)")
                    job_opts.append({"label": label, "value": str(j["id"])})
                if job_opts:
                    job_visible = SHOW
                    if journey_data["budget"] <= initial_budget * 0.35:
                        job_result = "Low budget. Work to earn more."
                    else:
                        job_visible = HIDE
                else:
                    job_result = "No jobs available at this airport."

        return (status, HIDE, SHOW, HIDE,
                flight_opts, HIDE, job_visible,
                job_opts, None, None, job_result)


def _render_report(s):
    sections = []

    if s.get("segments"):
        rows = []
        for seg in s["segments"]:
            rows.append(html.Div(style={**CARD, "marginBottom": "8px"}, children=[
                html.Div(f"{seg['origin']} → {seg['destination']}",
                         style={"fontWeight": "700", "fontSize": "12px", "marginBottom": "4px"}),
                html.Div(f"Aircraft: {seg['aircraft']}  ·  {seg['distance_km']:.0f} km",
                         style={"fontSize": "11px", "color": COLORS["text_dim"]}),
                html.Div(f"Cost: ${seg['cost']:.2f}  ·  Time: {seg['time_min']:.0f} min",
                         style={"fontSize": "11px", "color": COLORS["text_dim"]}),
            ]))
        sections.append(html.Div([
            html.Div(f"Destinations visited: {s.get('destinations_visited', 0)}",
                     style={**SECTION_TITLE, "marginBottom": "8px"}),
            *rows,
        ]))

    if s.get("jobs_done"):
        job_rows = []
        for j in s["jobs_done"]:
            job_rows.append(html.Div(style={"fontSize": "11px", "color": COLORS["text_dim"], "marginBottom": "4px"},
                                     children=[
                html.Span(f"{j['job_name']} at {j['airport']}  ·  ",
                          style={"fontWeight": "600"}),
                html.Span(f"{j['hours']} h  ·  +${j['earnings']:.2f}"),
            ]))
        sections.append(html.Div([
            html.Div("Jobs completed", style={**SECTION_TITLE, "marginBottom": "6px", "marginTop": "12px"}),
            *job_rows,
            html.Div(f"Total earned: ${s.get('total_earned', 0):.2f}",
                     style={"fontSize": "12px", "fontWeight": "700", "color": COLORS["ok"], "marginTop": "6px"}),
        ]))

    totals = html.Div(style={**CARD, "borderLeft": f"3px solid {COLORS['hub']}", "marginTop": "14px"}, children=[
        html.Div("Totals", style={**SECTION_TITLE, "marginBottom": "10px"}),
        *[html.Div(style={"display": "flex", "justifyContent": "space-between",
                           "marginBottom": "5px", "fontSize": "12px"}, children=[
            html.Span(label, style={"color": COLORS["text_dim"]}),
            html.Span(value, style={"fontWeight": "700", "color": color}),
        ]) for label, value, color in [
            ("Initial budget",     f"${s.get('initial_budget', 0):.2f}", COLORS["text"]),
            ("Total spent",        f"${s.get('total_cost', 0):.2f}",     COLORS["error"]),
            ("Earned from jobs",   f"+${s.get('total_earned', 0):.2f}",  COLORS["ok"]),
            ("Final balance",      f"${s.get('remaining_budget', 0):.2f}", COLORS["text"]),
            ("Total time",         f"{s.get('total_time_hours', 0):.1f} h", COLORS["text"]),
        ]],
        html.Div(style={"borderTop": f"1px solid {COLORS['border']}", "margin": "8px 0 6px"}),
        html.Div(style={"display": "flex", "justifyContent": "space-between",
                        "marginBottom": "5px", "fontSize": "12px"}, children=[
            html.Span("Dist. subsidiada", style={"color": COLORS["text_dim"]}),
            html.Span(f"{s.get('subsidized_km', 0):.0f} / {s.get('total_km', 0):.0f} km"
                      f" ({s.get('subsidy_ratio', 0):.1f}%)",
                      style={"fontWeight": "700"}),
        ]),
        html.Div(style={"display": "flex", "justifyContent": "space-between",
                        "fontSize": "12px"}, children=[
            html.Span("Límite 20%", style={"color": COLORS["text_dim"]}),
            html.Span("✔ Cumple" if s.get("subsidy_valid") else "✘ Excede",
                      style={"fontWeight": "700",
                             "color": "#16a34a" if s.get("subsidy_valid") else "#dc2626"}),
        ]),
    ])

    return html.Div([*sections, totals])

# ── END ITEM 2.3.a / 2.3.b / 2.3.c ──

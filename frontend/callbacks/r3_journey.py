# R3 — Interactive journey planner: state management + UI rendering

from dash import html, dcc, Input, Output, State
import dash

from services.graphService import build_graph_from_dict
from services.dynamicService import (
    init_journey_state, get_flight_options, get_available_jobs,
    apply_flight, apply_arrival, apply_optional_activities,
    apply_job, finish_journey, build_summary,
)
from frontend.config import COLORS, CARD, SECTION_TITLE, SHOW, HIDE
from frontend.config import BTN_PRIMARY, BTN_SUCCESS, BTN_DANGER, BTN_NEUTRAL


def register(app):

    @app.callback(
        Output("journey-store",          "data"),
        Input("start-btn",               "n_clicks"),
        Input("fly-btn",                 "n_clicks"),
        Input("confirm-activities-btn",  "n_clicks"),
        Input("work-btn",                "n_clicks"),
        Input("end-btn",                 "n_clicks"),
        Input("new-journey-btn",         "n_clicks"),
        State("planner-origin",          "value"),
        State("planner-budget",          "value"),
        State("flight-radio",            "value"),
        State("activity-checklist",      "value"),
        State("job-dropdown",            "value"),
        State("hours-input",             "value"),
        State("journey-store",           "data"),
        State("graph-store",             "data"),
    )
    def handle_journey_action(start_n, fly_n, confirm_n, work_n, end_n, new_n,
                              origin, budget, flight_val, act_val,
                              job_val, hours_val, journey_data, graph_data):
        tid = dash.callback_context.triggered_id
        if not tid:
            raise dash.exceptions.PreventUpdate

        if tid == "new-journey-btn":
            return None

        if tid == "start-btn":
            if not origin or not budget or not graph_data:
                raise dash.exceptions.PreventUpdate
            g = build_graph_from_dict(graph_data)
            threshold = g.global_config.get("budgetThresholdPercent", 35)
            return init_journey_state(origin, float(budget), threshold)

        if not journey_data or not graph_data:
            raise dash.exceptions.PreventUpdate
        g = build_graph_from_dict(graph_data)

        if tid == "fly-btn":
            if not flight_val:
                raise dash.exceptions.PreventUpdate
            dest, aircraft = flight_val.split("|", 1)
            new_state = apply_flight(g, journey_data, dest, aircraft)
            return apply_arrival(new_state)

        if tid == "confirm-activities-btn":
            selected = [int(i) for i in (act_val or [])]
            return apply_optional_activities(journey_data, selected)

        if tid == "work-btn":
            if job_val is None or not hours_val:
                raise dash.exceptions.PreventUpdate
            return apply_job(g, journey_data, int(job_val), float(hours_val))

        if tid == "end-btn":
            return finish_journey(journey_data)

        raise dash.exceptions.PreventUpdate

    @app.callback(
        Output("journey-status",          "children"),
        Output("setup-section",           "style"),
        Output("flying-section",          "style"),
        Output("arrival-section",         "style"),
        Output("complete-section",        "style"),
        Output("flight-radio",            "options"),
        Output("flight-radio",            "value"),
        Output("activity-checklist",      "options"),
        Output("activity-checklist",      "value"),
        Output("job-dropdown",            "options"),
        Output("job-section",             "style"),
        Output("arrival-info",            "children"),
        Output("journey-report",          "children"),
        Input("journey-store",            "data"),
        State("graph-store",              "data"),
    )
    def render_planner(journey_data, graph_data):
        if not journey_data:
            return (None, SHOW, HIDE, HIDE, HIDE,
                    [], None, [], [], [], HIDE, None, None)

        phase = journey_data.get("phase", "flying")
        g     = build_graph_from_dict(graph_data) if graph_data else None

        budget      = journey_data["budget"]
        initial     = journey_data["initial_budget"]
        pct         = (budget / initial) * 100
        threshold   = journey_data.get("threshold_pct", 35)
        time_h      = journey_data["time_min"] / 60
        budget_color = COLORS["error"] if pct < threshold else (COLORS["warning"] if pct < 50 else COLORS["ok"])
        status = html.Div(style={**CARD, "borderLeft": f"3px solid {budget_color}", "marginBottom": "14px"}, children=[
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
            }, children=[html.Div(style={"width": f"{min(pct,100):.0f}%", "height": "100%",
                                         "backgroundColor": budget_color, "borderRadius": "3px"})]),
            html.Div(f"Tiempo: {time_h:.1f} h  ·  Gastado: ${initial - budget:.2f} USD",
                     style={"fontSize": "11px", "color": COLORS["text_dim"]}),
        ])

        if phase == "arrival":
            arrival = journey_data.get("arrival_data", {}) or {}
            arrival_card = html.Div(style={**CARD, "borderLeft": f"3px solid {COLORS['secondary']}"}, children=[
                html.Div(f"✈  Llegaste a {arrival.get('name', '')} ({arrival.get('id', '')})",
                         style={"fontWeight": "700", "fontSize": "14px", "color": COLORS["text"], "marginBottom": "4px"}),
                html.Div(f"{arrival.get('city', '')}, {arrival.get('country', '')}",
                         style={"fontSize": "12px", "color": COLORS["text_dim"], "marginBottom": "8px"}),
                *([] if arrival.get("stay_days", 0) == 0 else [
                    html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "6px"}, children=[
                        html.Div(style={"backgroundColor": "#fff", "borderRadius": "6px", "padding": "6px 8px",
                                        "border": f"1px solid {COLORS['border']}"}, children=[
                            html.Div("Alojamiento", style={"fontSize": "10px", "color": COLORS["text_dim"]}),
                            html.Div(f"${arrival.get('accommodation', 0):.2f}", style={"fontWeight": "700", "fontSize": "13px"}),
                        ]),
                        html.Div(style={"backgroundColor": "#fff", "borderRadius": "6px", "padding": "6px 8px",
                                        "border": f"1px solid {COLORS['border']}"}, children=[
                            html.Div("Alimentación", style={"fontSize": "10px", "color": COLORS["text_dim"]}),
                            html.Div(f"${arrival.get('food', 0):.2f}", style={"fontWeight": "700", "fontSize": "13px"}),
                        ]),
                    ]),
                ]),
                *([html.Div(f"Estadía mínima: {arrival['stay_days']} día(s)",
                            style={"fontSize": "11px", "color": COLORS["text_dim"], "marginTop": "6px"})]
                  if arrival.get("stay_days", 0) > 0 else []),
            ])

            mand = arrival.get("mandatory_activities", [])
            mand_items = []
            for act in mand:
                mand_items.append(html.Div(
                    f"⚠ {act['name']} — {act.get('durationMin', 0)} min — ${act.get('costUSD', 0):.2f} (obligatoria)",
                    style={"fontSize": "11px", "color": COLORS["warning"], "marginBottom": "4px"}))

            opt  = arrival.get("optional_activities", [])
            act_opts = [{"label": f" {a['name']}  ({a.get('durationMin',0)} min — ${a.get('costUSD',0):.2f})",
                         "value": str(i)} for i, a in enumerate(opt)]

            return (status, HIDE, HIDE, SHOW, HIDE,
                    [], None, act_opts, [], [], HIDE,
                    html.Div([arrival_card] + mand_items), None)

        if phase == "complete":
            s = build_summary(journey_data)
            report = _render_report(s)
            return (status, HIDE, HIDE, HIDE, SHOW,
                    [], None, [], [], [], HIDE, None, report)

        flight_opts = []
        if g:
            for fl in get_flight_options(g, journey_data):
                note = " 🟢 GRATIS" if fl["is_free"] else (" 💛 tarifa completa" if fl["is_subsidized"] else "")
                label = (f"{fl['destination']} ({fl['dest_name']})  ·  {fl['aircraft']}\n"
                         f"${fl['cost']:.2f}  ·  {fl['time_min']:.0f} min  ·  {fl['distance_km']:.0f} km{note}")
                flight_opts.append({"label": label, "value": f"{fl['destination']}|{fl['aircraft']}"})

        job_opts = []
        show_jobs = HIDE
        if g:
            jobs = get_available_jobs(g, journey_data)
            if jobs:
                job_opts = [{"label": f"{j['name']}  (${j['hourlyRate']}/h — máx {j['maxHours']}h)",
                             "value": str(i)} for i, j in enumerate(jobs)]
                show_jobs = SHOW

        return (status, HIDE, SHOW, HIDE, HIDE,
                flight_opts, None, [], [], job_opts, show_jobs, None, None)


def _render_report(s):
    sections = []

    if s["destination_details"]:
        rows = []
        for d in s["destination_details"]:
            rows.append(html.Div(style={**CARD, "marginBottom": "8px"}, children=[
                html.Div(f"{d['name']} ({d['id']}) — {d['city']}, {d['country']}",
                         style={"fontWeight": "700", "fontSize": "12px", "marginBottom": "4px"}),
                *([html.Div(f"Estadía: {d['stay_days']} día(s)  ·  Alojamiento: ${d['accommodation']:.2f}  ·  Comida: ${d['food']:.2f}",
                            style={"fontSize": "11px", "color": COLORS["text_dim"]})]
                  if d["stay_days"] > 0 else []),
                *([html.Div(f"Actividades: ${d['activity_cost']:.2f}  ({d['activity_time_min']} min)",
                            style={"fontSize": "11px", "color": COLORS["text_dim"]})]
                  if d["activity_cost"] > 0 else []),
                html.Div(f"Total en destino: ${d['total_cost']:.2f}",
                         style={"fontSize": "12px", "fontWeight": "700", "color": COLORS["secondary"],
                                "marginTop": "4px"}),
            ]))
        sections.append(html.Div([
            html.Div("Destinos visitados", style={**SECTION_TITLE, "marginBottom": "8px"}),
            *rows,
        ]))

    if s["segments"]:
        rows = [html.Tr([
            html.Th(h, style={"padding": "4px 6px", "fontSize": "10px", "color": COLORS["text_dim"],
                               "borderBottom": f"1px solid {COLORS['border']}", "textAlign": "left"})
            for h in ["Tramo", "Aeronave", "Dist.", "Tiempo", "Costo"]
        ])]
        for seg in s["segments"]:
            rows.append(html.Tr([
                html.Td(f"{seg['origin']}→{seg['destination']}", style={"padding": "4px 6px", "fontSize": "11px", "fontWeight": "600"}),
                html.Td(seg["aircraft"],   style={"padding": "4px 6px", "fontSize": "10px", "color": COLORS["text_dim"]}),
                html.Td(f"{seg['distance_km']:.0f}km", style={"padding": "4px 6px", "fontSize": "11px"}),
                html.Td(f"{seg['time_min']:.0f}m",     style={"padding": "4px 6px", "fontSize": "11px"}),
                html.Td(f"${seg['cost']:.2f}",          style={"padding": "4px 6px", "fontSize": "11px",
                                                                "fontWeight": "700", "color": COLORS["secondary"]}),
            ]))
        sections.append(html.Div(style={"marginTop": "14px"}, children=[
            html.Div("Tramos volados", style={**SECTION_TITLE, "marginBottom": "8px"}),
            html.Table(rows, style={"width": "100%", "borderCollapse": "collapse",
                                    "backgroundColor": "#fff", "borderRadius": "8px", "overflow": "hidden",
                                    "border": f"1px solid {COLORS['border']}"}),
        ]))

    if s["activities_done"]:
        act_rows = [html.Tr([
            html.Th(h, style={"padding": "4px 6px", "fontSize": "10px", "color": COLORS["text_dim"],
                               "borderBottom": f"1px solid {COLORS['border']}", "textAlign": "left"})
            for h in ["Aeropuerto", "Actividad", "Tipo", "Costo"]
        ])]
        for act in s["activities_done"]:
            act_rows.append(html.Tr([
                html.Td(act["airport"], style={"padding": "4px 6px", "fontSize": "11px", "fontWeight": "600"}),
                html.Td(act["name"],    style={"padding": "4px 6px", "fontSize": "10px"}),
                html.Td(act["type"],    style={"padding": "4px 6px", "fontSize": "10px", "color": COLORS["text_dim"]}),
                html.Td(f"${act['cost']:.2f}", style={"padding": "4px 6px", "fontSize": "11px",
                                                       "fontWeight": "700", "color": COLORS["secondary"]}),
            ]))
        sections.append(html.Div(style={"marginTop": "14px"}, children=[
            html.Div("Actividades realizadas", style={**SECTION_TITLE, "marginBottom": "8px"}),
            html.Table(act_rows, style={"width": "100%", "borderCollapse": "collapse",
                                        "backgroundColor": "#fff", "borderRadius": "8px",
                                        "border": f"1px solid {COLORS['border']}"}),
        ]))

    if s["jobs_taken"]:
        job_rows = [html.Tr([
            html.Th(h, style={"padding": "4px 6px", "fontSize": "10px", "color": COLORS["text_dim"],
                               "borderBottom": f"1px solid {COLORS['border']}", "textAlign": "left"})
            for h in ["Aeropuerto", "Trabajo", "Horas", "Ganado"]
        ])]
        for j in s["jobs_taken"]:
            job_rows.append(html.Tr([
                html.Td(j["airport"], style={"padding": "4px 6px", "fontSize": "11px", "fontWeight": "600"}),
                html.Td(j["job"],     style={"padding": "4px 6px", "fontSize": "10px"}),
                html.Td(f"{j['hours']:.1f}h", style={"padding": "4px 6px", "fontSize": "11px"}),
                html.Td(f"${j['earned']:.2f}", style={"padding": "4px 6px", "fontSize": "11px",
                                                       "fontWeight": "700", "color": COLORS["ok"]}),
            ]))
        sections.append(html.Div(style={"marginTop": "14px"}, children=[
            html.Div("Trabajos realizados", style={**SECTION_TITLE, "marginBottom": "8px"}),
            html.Table(job_rows, style={"width": "100%", "borderCollapse": "collapse",
                                        "backgroundColor": "#fff", "borderRadius": "8px",
                                        "border": f"1px solid {COLORS['border']}"}),
        ]))

    sub_pct = (s["subsidized_km"] / s["total_km"] * 100) if s["total_km"] > 0 else 0
    totals = html.Div(style={**CARD, "borderLeft": f"3px solid {COLORS['hub']}", "marginTop": "14px"}, children=[
        html.Div("Totales", style={**SECTION_TITLE, "marginBottom": "10px"}),
        *[html.Div(style={"display": "flex", "justifyContent": "space-between",
                           "marginBottom": "5px", "fontSize": "12px"}, children=[
            html.Span(label, style={"color": COLORS["text_dim"]}),
            html.Span(value, style={"fontWeight": "700", "color": color}),
        ]) for label, value, color in [
            ("Presupuesto inicial", f"${s['initial_budget']:.2f}", COLORS["text"]),
            ("Total gastado",       f"${s['total_cost']:.2f}",     COLORS["error"]),
            ("Total ganado (jobs)", f"${s['money_earned']:.2f}",   COLORS["ok"]),
            ("Saldo final",         f"${s['budget_remaining']:.2f}", COLORS["ok"] if s["budget_remaining"] >= 0 else COLORS["error"]),
            ("Tiempo total",        f"{s['total_time_hours']:.1f} h", COLORS["text"]),
            ("Km subsidiados",      f"{s['subsidized_km']:.0f} / {s['total_km']:.0f} km ({sub_pct:.1f}%)", COLORS["text_dim"]),
        ]],
    ])

    return html.Div([*sections, totals])

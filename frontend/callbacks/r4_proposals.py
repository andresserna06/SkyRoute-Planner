from dash import html, Input, Output, State
import dash

from backend.services.graphService import build_graph_from_dict
from backend.services.itineraryService import (
    propose_max_coverage_by_budget,
    propose_max_coverage_by_time,
)
from frontend.config import COLORS, CARD


def _build_result_card(title, result, accent_color):
    if not result["success"]:
        return html.Div(style={**CARD, "borderLeft": f"3px solid {COLORS['error']}"}, children=[
            html.Div(title, style={"fontSize": "12px", "fontWeight": "700", "color": COLORS["error"], "marginBottom": "6px"}),
            html.P(result.get("error", "Error desconocido"), style={"fontSize": "12px", "color": COLORS["text_dim"]}),
        ])

    if "note" in result:
        return html.Div(style={**CARD, "borderLeft": f"3px solid {COLORS['warning']}"}, children=[
            html.Div(title, style={"fontSize": "12px", "fontWeight": "700", "color": COLORS["warning"], "marginBottom": "6px"}),
            html.P(result["note"], style={"fontSize": "12px", "color": COLORS["text_dim"]}),
        ])

    rows = []
    for s in result["segments"]:
        if s.get("subsidized"):
            row_style = {"backgroundColor": "#fef2f2", "color": "#dc2626"}
            label_suffix = " (Subsidiada)"
        elif not s.get("destination_is_hub"):
            row_style = {"backgroundColor": "#dbeafe", "color": "#1d4ed8"}
            label_suffix = " (Secundario)"
        else:
            row_style = {}
            label_suffix = ""
        rows.append(html.Tr([
            html.Td(f"{s['origin']} → {s['destination']}",
                    style={"padding": "4px 6px", "fontSize": "11px", "fontWeight": "600", **row_style}),
            html.Td(f"{s['aircraft']}{label_suffix}",
                    style={"padding": "4px 6px", "fontSize": "10px", "color": COLORS["text_dim"], **row_style}),
            html.Td(f"${s['cost']:.2f}",
                    style={"padding": "4px 6px", "fontSize": "10px", "textAlign": "right", **row_style}),
            html.Td(f"{s['time_min']:.1f} min",
                    style={"padding": "4px 6px", "fontSize": "10px", "textAlign": "right", "color": COLORS["text_dim"], **row_style}),
        ]))

    return html.Div(style={**CARD, "borderLeft": f"3px solid {accent_color}"}, children=[
        html.Div(title, style={"fontSize": "12px", "fontWeight": "700", "color": accent_color, "marginBottom": "6px"}),
        html.Div(" → ".join(result["path"]),
                 style={"fontSize": "13px", "fontWeight": "600", "color": COLORS["text"], "marginBottom": "8px"}),
        html.Table(style={"width": "100%", "borderCollapse": "collapse", "marginBottom": "8px"}, children=[
            html.Thead(html.Tr([
                html.Th("Tramo", style={"padding": "3px 6px", "fontSize": "9px", "textAlign": "left",
                                        "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
                html.Th("Aeronave", style={"padding": "3px 6px", "fontSize": "9px", "textAlign": "left",
                                           "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
                html.Th("Costo", style={"padding": "3px 6px", "fontSize": "9px", "textAlign": "right",
                                        "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
                html.Th("Tiempo", style={"padding": "3px 6px", "fontSize": "9px", "textAlign": "right",
                                         "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
            ])),
            html.Tbody(rows),
        ]),
        html.Div(f"Destinos visitados: {result['destinations_visited']}  |  "
                 f"Costo total: ${result['total_cost']:.2f}  |  "
                 f"Tiempo total: {result['total_time_hours']:.2f} h",
                 style={"fontSize": "11px", "fontWeight": "600", "color": COLORS["text"], "textAlign": "right"}),
    ])


def register(app):

    @app.callback(
        Output("prop-a-origin", "options"),
        Input("graph-store", "data"),
    )
    def load_airports_a(graph_data):
        if not graph_data:
            raise dash.exceptions.PreventUpdate
        g = build_graph_from_dict(graph_data)
        return [{"label": f"{v.id} — {v.city}", "value": v.id}
                for v in sorted(g.vertices, key=lambda x: x.id)]

    @app.callback(
        Output("prop-b-origin", "options"),
        Input("graph-store", "data"),
    )
    def load_airports_b(graph_data):
        if not graph_data:
            raise dash.exceptions.PreventUpdate
        g = build_graph_from_dict(graph_data)
        return [{"label": f"{v.id} — {v.city}", "value": v.id}
                for v in sorted(g.vertices, key=lambda x: x.id)]

    @app.callback(
        Output("prop-a-results", "children"),
        Input("prop-a-btn", "n_clicks"),
        State("prop-a-origin", "value"),
        State("prop-a-budget", "value"),
        State("prop-a-time", "value"),
        State("graph-store", "data"),
    )
    def proposal_a(n_clicks, origin, budget, time_hours, graph_data):
        if not n_clicks or not origin or not graph_data:
            raise dash.exceptions.PreventUpdate
        if budget is None:
            return html.Div("⚠ Ingresa un presupuesto antes de calcular.",
                            style={"fontSize": "12px", "color": COLORS["warning"], "marginTop": "8px"})

        g = build_graph_from_dict(graph_data)
        budget_val = float(budget) if budget not in (None, "") else float("inf")
        time_val = float(time_hours) if time_hours not in (None, "") else float("inf")

        result = propose_max_coverage_by_budget(g, origin, budget_val, time_val)
        return _build_result_card("$ Propuesta A — Máximo por presupuesto", result, COLORS["ok"])

    @app.callback(
        Output("prop-b-results", "children"),
        Input("prop-b-btn", "n_clicks"),
        State("prop-b-origin", "value"),
        State("prop-b-time", "value"),
        State("prop-b-budget", "value"),
        State("graph-store", "data"),
    )
    def proposal_b(n_clicks, origin, time_hours, budget, graph_data):
        if not n_clicks or not origin or not graph_data:
            raise dash.exceptions.PreventUpdate
        if time_hours is None:
            return html.Div("⚠ Ingresa un tiempo disponible antes de calcular.",
                            style={"fontSize": "12px", "color": COLORS["warning"], "marginTop": "8px"})

        g = build_graph_from_dict(graph_data)
        time_val = float(time_hours) if time_hours not in (None, "") else float("inf")
        budget_val = float(budget) if budget not in (None, "") else float("inf")

        result = propose_max_coverage_by_time(g, origin, time_val, budget_val)
        return _build_result_card("🕐 Propuesta B — Máximo por tiempo", result, COLORS["secondary"])

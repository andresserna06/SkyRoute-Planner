# ── ITEM 2.2.a / 2.2.b — Web callbacks: Proposal A (max destinations by budget)
#                          and Proposal B (max destinations by time) ──

from dash import html, Input, Output, State
import dash

from backend.services.graphService import build_graph_from_dict
from backend.services.itineraryService import (
    propose_max_coverage_by_budget,
    propose_max_coverage_by_time,
)
from frontend.config import COLORS, CARD


def _build_proposal_card(result, accent):
    # Renders a proposal result: visited path, per-segment table, and totals.
    if not result.get("success"):
        return html.P(result.get("error", "No se pudo calcular la propuesta."),
                      style={"color": COLORS["error"], "fontSize": "12px"})

    # No reachable destination within the given limits
    if result.get("destinations_visited", 0) == 0:
        return html.P(result.get("note", "No se encontró una ruta válida con los límites dados."),
                      style={"color": COLORS["text_dim"], "fontSize": "12px"})

    rows = []
    for seg in result["segments"]:
        # Highlight subsidized routes (red) and secondary airports (blue)
        if seg.get("subsidized"):
            row_style = {"backgroundColor": "#fef2f2", "color": "#dc2626"}
            suffix = " (Subsidiada)"
        elif not seg.get("destination_is_hub"):
            row_style = {"backgroundColor": "#dbeafe", "color": "#1d4ed8"}
            suffix = " (Secundario)"
        else:
            row_style = {}
            suffix = ""
        rows.append(html.Tr([
            html.Td(f"{seg['origin']} → {seg['destination']}",
                    style={"padding": "5px 8px", "fontSize": "12px", "fontWeight": "600", **row_style}),
            html.Td(f"{seg['aircraft']}{suffix}",
                    style={"padding": "5px 8px", "fontSize": "11px", "color": COLORS["text_dim"], **row_style}),
            html.Td(f"${seg['cost']:.2f}",
                    style={"padding": "5px 8px", "fontSize": "11px", **row_style}),
            html.Td(f"{seg['time_min']:.0f} min",
                    style={"padding": "5px 8px", "fontSize": "11px", **row_style}),
        ]))

    return html.Div(style={**CARD, "borderLeft": f"3px solid {accent}"}, children=[
        html.Div(f"{result['destinations_visited']} destinos visitados",
                 style={"fontSize": "12px", "fontWeight": "700", "color": accent, "marginBottom": "8px"}),
        html.Div(" → ".join(result["path"]),
                 style={"fontSize": "13px", "fontWeight": "600", "color": COLORS["text"], "marginBottom": "10px"}),
        html.Table(style={"width": "100%", "borderCollapse": "collapse"}, children=[
            html.Thead(html.Tr([
                html.Th("Tramo",    style={"padding": "4px 8px", "fontSize": "10px", "textAlign": "left",
                                           "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
                html.Th("Aeronave", style={"padding": "4px 8px", "fontSize": "10px", "textAlign": "left",
                                           "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
                html.Th("Costo",    style={"padding": "4px 8px", "fontSize": "10px",
                                           "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
                html.Th("Tiempo",   style={"padding": "4px 8px", "fontSize": "10px",
                                           "color": COLORS["text_dim"], "borderBottom": f"1px solid {COLORS['border']}"}),
            ])),
            html.Tbody(rows),
        ]),
        html.Div(
            f"Total: ${result['total_cost']:.2f}  ·  {result['total_time_hours']:.2f} h  ·  "
            f"aeronaves: {', '.join(result['aircraft_used'])}",
            style={"fontSize": "12px", "fontWeight": "700", "color": accent,
                   "marginTop": "10px", "textAlign": "right"}),
    ])


def register(app):

    # ── ITEM 2.2.a — Proposal A: max destinations within budget ──
    @app.callback(
        Output("prop-a-results",          "children"),
        Output("proposal-highlight-store", "data", allow_duplicate=True),
        Input("prop-a-btn",      "n_clicks"),
        State("prop-a-origin",   "value"),
        State("prop-a-budget",   "value"),
        State("prop-a-time",     "value"),
        State("graph-store",     "data"),
        prevent_initial_call=True,
    )
    def prop_a_search(n_clicks, origin, budget, time_hours, graph_data):
        if not n_clicks or not origin or not graph_data:
            raise dash.exceptions.PreventUpdate
        if budget is None:
            return html.P("Ingresa un presupuesto.", style={"color": COLORS["error"], "fontSize": "12px"}), None
        graph = build_graph_from_dict(graph_data)
        result = propose_max_coverage_by_budget(
            graph, origin, float(budget),
            time_hours=float(time_hours) if time_hours else float("inf"),
        )
        # Highlight the visited path on the graph (only when there is a real route)
        highlight = {"path": result["path"]} if result.get("destinations_visited", 0) > 0 else None
        return _build_proposal_card(result, COLORS["ok"]), highlight

    # ── ITEM 2.2.b — Proposal B: max destinations within available time ──
    @app.callback(
        Output("prop-b-results",          "children"),
        Output("proposal-highlight-store", "data", allow_duplicate=True),
        Input("prop-b-btn",      "n_clicks"),
        State("prop-b-origin",   "value"),
        State("prop-b-time",     "value"),
        State("prop-b-budget",   "value"),
        State("graph-store",     "data"),
        prevent_initial_call=True,
    )
    def prop_b_search(n_clicks, origin, time_hours, budget, graph_data):
        if not n_clicks or not origin or not graph_data:
            raise dash.exceptions.PreventUpdate
        if time_hours is None:
            return html.P("Ingresa el tiempo disponible.", style={"color": COLORS["error"], "fontSize": "12px"}), None
        graph = build_graph_from_dict(graph_data)
        result = propose_max_coverage_by_time(
            graph, origin, float(time_hours),
            budget_usd=float(budget) if budget else float("inf"),
        )
        # Highlight the visited path on the graph (only when there is a real route)
        highlight = {"path": result["path"]} if result.get("destinations_visited", 0) > 0 else None
        return _build_proposal_card(result, COLORS["secondary"]), highlight

# ── END ITEM 2.2.a / 2.2.b ──

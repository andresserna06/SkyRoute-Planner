# ── ITEM 2.3 — Global editor for aircraft cost/km and time/km ──

from dash import html, ALL, Input, Output, State
import dash

from backend.services.graphService import DEFAULT_AIRCRAFT_CONFIG
from frontend.config import COLORS


AIRCRAFT_MAP = {
    "comercial": "Avión Comercial",
    "regional": "Jet Regional",
    "helice": "Avión de Hélice",
}


def register(app):

    @app.callback(
        Output("graph-store", "data", allow_duplicate=True),
        Output("aircraft-editor-msg", "children"),
        Input("aircraft-apply-btn", "n_clicks"),
        State({"type": "aircraft-cost", "index": ALL}, "value"),
        State({"type": "aircraft-time", "index": ALL}, "value"),
        State("graph-store", "data"),
        prevent_initial_call=True,
    )
    def apply_aircraft_config(n_clicks, cost_vals, time_vals, graph_data):
        if not n_clicks or not graph_data:
            raise dash.exceptions.PreventUpdate

        keys = ["comercial", "regional", "helice"]
        new_data = dict(graph_data)
        aircraft_cfg = {}
        for i, key in enumerate(keys):
            name = AIRCRAFT_MAP[key]
            cost_value = cost_vals[i] if i < len(cost_vals) else None
            time_value = time_vals[i] if i < len(time_vals) else None
            aircraft_cfg[name] = {
                "costPerKm": float(cost_value) if cost_value is not None else 0,
                "timePerKm": float(time_value) if time_value is not None else 0,
            }
        new_data["aircraft_config"] = aircraft_cfg
        return new_data, html.Span("Aplicado", style={"color": "#16a34a", "fontSize": "10px", "fontWeight": "600"})

    @app.callback(
        Output("graph-store", "data", allow_duplicate=True),
        Output("aircraft-editor-msg", "children", allow_duplicate=True),
        Input("aircraft-restore-btn", "n_clicks"),
        State("original-graph-store", "data"),
        State("graph-store", "data"),
        prevent_initial_call=True,
    )
    def restore_aircraft_config(n_clicks, orig_data, graph_data):
        if not n_clicks:
            raise dash.exceptions.PreventUpdate

        if orig_data:
            config = (
                orig_data.get("aircraft_config")
                or orig_data.get("aircraftConfig")
                or (orig_data.get("config") or {}).get("aircraft")
                or (orig_data.get("configuracionGlobal") or {}).get("aeronaves")
            )
        else:
            config = None

        if not config:
            config = DEFAULT_AIRCRAFT_CONFIG

        new_data = dict(graph_data) if graph_data else {}
        new_data["aircraft_config"] = dict(config)
        return new_data, html.Span("Restaurado", style={"color": COLORS["text_dim"], "fontSize": "10px", "fontWeight": "600"})

    @app.callback(
        Output({"type": "aircraft-cost", "index": ALL}, "value"),
        Output({"type": "aircraft-time", "index": ALL}, "value"),
        Input("graph-store", "data"),
    )
    def populate_aircraft_config(graph_data):
        keys = ["comercial", "regional", "helice"]
        if not graph_data:
            cost_vals = []
            time_vals = []
            for key in keys:
                name = AIRCRAFT_MAP[key]
                cost_vals.append(DEFAULT_AIRCRAFT_CONFIG.get(name, {}).get("costPerKm", 0))
                time_vals.append(DEFAULT_AIRCRAFT_CONFIG.get(name, {}).get("timePerKm", 0))
            return cost_vals, time_vals

        config = (
            graph_data.get("aircraft_config")
            or graph_data.get("aircraftConfig")
            or (graph_data.get("config") or {}).get("aircraft")
            or (graph_data.get("configuracionGlobal") or {}).get("aeronaves")
        )

        cost_vals = []
        time_vals = []
        for key in keys:
            name = AIRCRAFT_MAP[key]
            if config and name in config:
                cost_vals.append(config[name].get("costPerKm", DEFAULT_AIRCRAFT_CONFIG.get(name, {}).get("costPerKm", 0)))
                time_vals.append(config[name].get("timePerKm", DEFAULT_AIRCRAFT_CONFIG.get(name, {}).get("timePerKm", 0)))
            else:
                cost_vals.append(DEFAULT_AIRCRAFT_CONFIG.get(name, {}).get("costPerKm", 0))
                time_vals.append(DEFAULT_AIRCRAFT_CONFIG.get(name, {}).get("timePerKm", 0))

        return cost_vals, time_vals

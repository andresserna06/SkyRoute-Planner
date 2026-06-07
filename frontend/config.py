# ── ITEM 2.1 — Dashboard theme colours, layout presets, stat chips, reusable UI styles ──

from dash import html


COLORS = {
    "bg_canvas":  "#e8ecf2",
    "bg_panel":   "#f6f8fb",
    "bg_panel_2": "#eceff4",
    "border":     "#d4dbe5",
    "text":       "#1e293b",
    "text_dim":   "#5d6b80",
    "hub":        "#ea580c",
    "hub_border": "#c2410c",
    "secondary":  "#2563eb",
    "sec_border": "#1d4ed8",
    "route":      "#8a98ab",
    "subsidized": "#16a34a",
    "highlight":  "#7c3aed",
    "node_outline":"#1e293b",
    "ok":         "#16a34a",
    "error":      "#dc2626",
    "warning":    "#d97706",
}

LAYOUTS = {
    "cose": {"name": "cose", "animate": False, "randomize": False,
             "idealEdgeLength": 180, "nodeRepulsion": 9000, "gravity": 0.2,
             "nodeOverlap": 24, "fit": True, "padding": 60},
    "concentric": {"name": "concentric", "animate": False, "minNodeSpacing": 45,
                   "fit": True, "padding": 60},
    "circle": {"name": "circle", "animate": False, "fit": True, "padding": 60},
}

SECTION_TITLE = {"margin": "0 0 10px 0", "color": COLORS["text"], "fontSize": "11px",
                 "textTransform": "uppercase", "letterSpacing": "1.2px", "fontWeight": "700"}

CARD = {"backgroundColor": COLORS["bg_panel_2"], "border": f"1px solid {COLORS['border']}",
        "borderRadius": "8px", "padding": "12px 14px", "marginBottom": "12px"}

BTN = {"padding": "8px 14px", "borderRadius": "7px", "border": "none",
       "fontSize": "12px", "fontWeight": "600", "fontFamily": "Inter, Segoe UI, sans-serif",
       "cursor": "pointer"}

BTN_PRIMARY = {**BTN, "backgroundColor": COLORS["secondary"], "color": "#fff"}
BTN_SUCCESS = {**BTN, "backgroundColor": COLORS["ok"], "color": "#fff"}
BTN_DANGER  = {**BTN, "backgroundColor": COLORS["error"], "color": "#fff"}
BTN_NEUTRAL = {**BTN, "backgroundColor": COLORS["bg_panel_2"],
               "color": COLORS["text"], "border": f"1px solid {COLORS['border']}"}

LABEL = {"fontSize": "11px", "fontWeight": "600", "color": COLORS["text_dim"],
         "marginBottom": "4px", "display": "block", "textTransform": "uppercase",
         "letterSpacing": "0.8px"}

INPUT_STYLE = {"width": "100%", "padding": "7px 10px", "borderRadius": "6px",
               "border": f"1px solid {COLORS['border']}", "fontSize": "13px",
               "fontFamily": "Inter, Segoe UI, sans-serif", "boxSizing": "border-box",
               "marginBottom": "10px", "backgroundColor": "#fff"}

DROPDOWN_STYLE = {"fontSize": "13px", "marginBottom": "10px"}

SHOW = {"display": "block"}
HIDE = {"display": "none"}


def stat_chip(dot_color, span_id, label):
    return html.Div(style={
        "display": "flex", "alignItems": "center", "gap": "7px",
        "backgroundColor": COLORS["bg_panel_2"], "border": f"1px solid {COLORS['border']}",
        "color": COLORS["text"], "padding": "5px 14px", "borderRadius": "20px",
        "fontSize": "13px", "fontWeight": "600",
    }, children=[
        html.Span(style={"width": "8px", "height": "8px", "borderRadius": "50%",
                         "backgroundColor": dot_color, "flexShrink": 0}),
        html.Span("—", id=span_id, style={"fontWeight": "700"}),
        html.Span(label, style={"color": COLORS["text_dim"], "fontWeight": "500"}),
    ])


def _placeholder():
    return html.P("Haz clic en un aeropuerto para ver su información.",
                  style={"fontSize": "12px", "color": COLORS["text_dim"], "margin": 0, "lineHeight": "1.6"})


def legend_row(swatch_style, text):
    return html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px", "marginBottom": "9px"},
                    children=[html.Div(style={**swatch_style, "flexShrink": 0}),
                              html.Span(text, style={"fontSize": "13px", "color": COLORS["text_dim"]})])

# ── END ITEM 2.1 ──

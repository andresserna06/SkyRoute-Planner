# dashboard.py — SkyRoute Planner web interface
# Run: python dashboard.py  →  http://localhost:8050

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dash

from frontend.layout import build_layout
from frontend.callbacks import register_all

app = dash.Dash(
    __name__,
    title="SkyRoute Planner",
    suppress_callback_exceptions=True,
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
    ],
)

app.layout = build_layout()
register_all(app)

if __name__ == "__main__":
    print("SkyRoute Planner iniciando - http://localhost:8050")
    app.run(debug=True)

"""
chart_routes.py - Rotas de geracao de graficos.
"""

from __future__ import annotations

import io

from flask import send_file
import matplotlib.pyplot as plt

from charts import ChartBuilderFactory
from route_helpers import ensure_current_squad_workspace, get_workspace_planning_context


chart_factory = ChartBuilderFactory()


def _build_chart_response(fig):
    img = io.BytesIO()
    fig.tight_layout()
    fig.savefig(img, format="png", dpi=100, bbox_inches="tight")
    img.seek(0)
    plt.close(fig)
    response = send_file(img, mimetype="image/png")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


def register_chart_routes(routes_bp):
    @routes_bp.route("/generate_chart")
    def generate_chart():
        return generate_cumulative_chart()

    @routes_bp.route("/generate_cumulative_chart")
    def generate_cumulative_chart():
        workspace = ensure_current_squad_workspace()
        planning = get_workspace_planning_context(workspace) if workspace else {}
        history = planning.get("history", [])
        fig = chart_factory.create("cumulative").build(history)
        return _build_chart_response(fig)

    @routes_bp.route("/generate_cpi_chart")
    def generate_cpi_chart():
        workspace = ensure_current_squad_workspace()
        planning = get_workspace_planning_context(workspace) if workspace else {}
        history = planning.get("history", [])
        fig = chart_factory.create("cpi").build(history)
        return _build_chart_response(fig)

    @routes_bp.route("/generate_spi_chart")
    def generate_spi_chart():
        workspace = ensure_current_squad_workspace()
        planning = get_workspace_planning_context(workspace) if workspace else {}
        history = planning.get("history", [])
        fig = chart_factory.create("spi").build(history)
        return _build_chart_response(fig)

"""
routes.py - Composicao do blueprint principal e reexport de helpers.
"""

from __future__ import annotations

import os

from flask import Blueprint

from auth_routes import register_auth_routes
from chart_routes import register_chart_routes
from dashboard_routes import register_dashboard_routes
from planning_routes import register_planning_routes
from route_helpers import (
    build_sprint_record,
    calculate_release_projection,
    calculate_total_release_points,
    calculate_workspace_summary,
    ensure_current_squad_workspace,
    get_current_squad_name,
    get_current_user_id,
    get_current_username,
    get_or_create_workspace_for_squad,
    get_planning_totals as _get_planning_totals,
    get_squad_workspaces,
    get_squads_data,
    get_workspace_planning_context,
    is_authenticated,
    normalize_releases,
    parse_brazilian_float,
    planning_service,
    recalculate_history,
    save_current_squad_workspace,
)
from squad_routes import allowed_file, register_squad_routes


routes_bp = Blueprint("routes", __name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")

register_dashboard_routes(routes_bp)
register_auth_routes(routes_bp)
register_squad_routes(routes_bp, UPLOAD_FOLDER)
register_planning_routes(routes_bp)
register_chart_routes(routes_bp)

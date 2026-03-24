"""
dashboard_routes.py - Rotas de dashboard e navegacao principal.
"""

from __future__ import annotations

from flask import flash, redirect, render_template, request, session, url_for

from route_helpers import (
    calculate_workspace_summary,
    ensure_current_squad_workspace,
    get_current_squad_name,
    get_or_create_workspace_for_squad,
    get_squads_data,
)


def register_dashboard_routes(routes_bp):
    @routes_bp.route("/", methods=["GET"])
    def index():
        if get_squads_data():
            return redirect(url_for("routes.dashboard"))
        return redirect(url_for("routes.upload_file"))

    @routes_bp.route("/dashboard", methods=["GET"])
    def dashboard():
        squads_data = get_squads_data()
        if not squads_data:
            return redirect(url_for("routes.upload_file"))

        current_squad = get_current_squad_name()
        summaries = []

        if current_squad is None:
            current_squad = next(iter(squads_data.keys()), None)
            if current_squad is not None:
                session["current_squad_name"] = current_squad
                session.modified = True

        for squad_name, squad_info in squads_data.items():
            workspace = get_or_create_workspace_for_squad(squad_name)
            summaries.append(calculate_workspace_summary(squad_name, workspace, squad_info))

        current_summary = next((item for item in summaries if item["name"] == current_squad), None)
        return render_template(
            "dashboard.html",
            summaries=summaries,
            current_squad=current_squad,
            current_summary=current_summary,
        )

    @routes_bp.route("/dashboard/squad/<squad_name>", methods=["GET"])
    def squad_dashboard(squad_name):
        squads_data = get_squads_data()
        if squad_name not in squads_data:
            flash("Squad inválida.", "error")
            return redirect(url_for("routes.dashboard"))

        session["current_squad_name"] = squad_name
        workspace = get_or_create_workspace_for_squad(squad_name)
        session.modified = True

        current_summary = calculate_workspace_summary(squad_name, workspace, squads_data[squad_name])
        return render_template(
            "squad_dashboard.html",
            current_squad=squad_name,
            current_summary=current_summary,
        )

    @routes_bp.route("/switch_squad/<squad_name>", methods=["GET"])
    def switch_squad(squad_name):
        squads_data = get_squads_data()
        if squad_name not in squads_data:
            flash("Squad inválida.", "error")
            return redirect(url_for("routes.dashboard"))

        session["current_squad_name"] = squad_name
        ensure_current_squad_workspace()
        session.modified = True

        next_page = request.args.get("next", "routes.dashboard")
        try:
            return redirect(url_for(next_page))
        except Exception:
            return redirect(url_for("routes.dashboard"))

"""
report_routes.py - Rotas de exportacao de relatorios executivos em PDF.
"""

from __future__ import annotations

from flask import redirect, send_file, url_for

from reports import ExecutiveReportBuilder
from route_helpers import (
    calculate_workspace_summary,
    ensure_current_squad_workspace,
    get_current_squad_name,
    get_squads_data,
)


report_builder = ExecutiveReportBuilder()


def register_report_routes(routes_bp):
    @routes_bp.route("/export_sprint_report")
    def export_sprint_report():
        workspace = ensure_current_squad_workspace()
        current_squad = get_current_squad_name()
        squads_data = get_squads_data()
        if workspace is None or not current_squad or current_squad not in squads_data:
            return redirect(url_for("routes.select_squad"))

        summary = calculate_workspace_summary(current_squad, workspace, squads_data[current_squad])
        pdf = report_builder.build_project_report(summary)
        return send_file(
            pdf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"relatorio_projeto_{current_squad}.pdf",
        )

    @routes_bp.route("/export_project_report")
    def export_project_report():
        workspace = ensure_current_squad_workspace()
        current_squad = get_current_squad_name()
        squads_data = get_squads_data()
        if workspace is None or not current_squad or current_squad not in squads_data:
            return redirect(url_for("routes.select_squad"))

        summary = calculate_workspace_summary(current_squad, workspace, squads_data[current_squad])
        pdf = report_builder.build_project_report(summary)
        return send_file(
            pdf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"relatorio_projeto_{current_squad}.pdf",
        )

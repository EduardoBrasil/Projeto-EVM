"""
planning_routes.py - Rotas de planejamento, releases e sprints.
"""

from __future__ import annotations

from flask import flash, redirect, render_template, request, session, url_for

from route_helpers import (
    build_sprint_record,
    calculate_release_projection,
    calculate_total_release_points,
    ensure_current_squad_workspace,
    get_planning_totals,
    normalize_releases,
    parse_brazilian_float,
    recalculate_history,
    save_current_squad_workspace,
)


def register_planning_routes(routes_bp):
    def releases_are_locked(workspace):
        return bool(normalize_releases(workspace.get("releases", [])))

    @routes_bp.route("/plan", methods=["GET", "POST"])
    def plan():
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))

        if workspace.get("squad_cost", 0) <= 0:
            return redirect(url_for("routes.setup"))

        workspace.setdefault("releases", [])
        workspace["releases"] = normalize_releases(workspace.get("releases", []))
        workspace.setdefault("history", [])
        workspace.setdefault("default_sprint_weeks", 2)

        if request.method == "POST" and "create_releases" in request.form and not workspace["releases"]:
            num_releases = int(request.form.get("num_releases", 1))
            workspace["releases"] = [{"points": 50, "sprints": 5} for _ in range(num_releases)]
        elif request.method == "POST" and "create_releases" in request.form:
            flash("As releases ja foram configuradas e estao bloqueadas para edicao.", "warning")

        planning_totals = get_planning_totals(workspace)
        squad_cost = workspace.get("squad_cost", 0)
        current_squad = session.get("current_squad_name", "Squad")
        releases = list(enumerate(workspace.get("releases", []), 1))
        total_points = planning_totals["total_release_points"] if releases else 0
        total_sprints = planning_totals["total_release_sprints"] if releases else 0
        sprint_cost = planning_totals["sprint_cost"]
        bac = planning_totals["bac"]
        value_per_point = planning_totals["value_per_point"]
        default_sprint_weeks = planning_totals["default_sprint_weeks"]
        current_component_count = planning_totals["current_component_count"]

        history = recalculate_history(
            workspace.get("history", []),
            value_per_point,
            total_points,
            squad_cost,
            current_component_count,
        )
        workspace["history"] = history
        save_current_squad_workspace(workspace)
        current_sprint = len(history) + 1
        last_metrics = history[-1] if history else {
            "PV": 0,
            "EV": 0,
            "AC": 0,
            "CV": 0,
            "SV": 0,
            "CPI": 0,
            "SPI": 0,
            "sprint_no": 0,
            "status": "-",
            "completion_percentage": 0,
        }
        projection = calculate_release_projection(history, bac, total_sprints, total_points, sprint_cost)

        return render_template(
            "plan.html",
            current_squad=current_squad,
            squad_cost=squad_cost,
            sprint_cost=sprint_cost,
            value_per_point=value_per_point,
            bac=bac,
            releases=releases,
            total_points=total_points,
            total_sprints=total_sprints,
            current_sprint=current_sprint,
            history=history,
            last_metrics=last_metrics,
            projection=projection,
            default_sprint_weeks=default_sprint_weeks,
            current_component_count=current_component_count,
        )

    @routes_bp.route("/update_sprint_settings", methods=["POST"])
    def update_sprint_settings():
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))

        try:
            default_sprint_weeks = float(request.form.get("default_sprint_weeks", 2) or 2)
        except (ValueError, TypeError):
            flash("Informe uma duracao valida para a sprint.", "error")
            return redirect(url_for("routes.plan"))

        workspace["default_sprint_weeks"] = max(default_sprint_weeks, 0.5)
        save_current_squad_workspace(workspace)
        flash("Configuracao padrao da sprint atualizada com sucesso.", "success")
        return redirect(url_for("routes.plan"))

    @routes_bp.route("/update_release_points", methods=["POST"])
    def update_release_points():
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))
        if releases_are_locked(workspace):
            flash("As releases configuradas estao bloqueadas para edicao.", "warning")
            return redirect(url_for("routes.plan"))

        releases = normalize_releases(workspace.get("releases", []))
        release_index = int(request.form.get("release_index", 0))
        new_points = float(request.form.get("release_points", 50))

        if 0 <= release_index < len(releases):
            releases[release_index]["points"] = new_points
            workspace["releases"] = releases
            save_current_squad_workspace(workspace)
            flash(f"Release {release_index + 1} atualizada para {new_points} pontos.", "success")
        else:
            flash("Indice de release invalido.", "error")

        return redirect(url_for("routes.plan"))

    @routes_bp.route("/update_release_sprints", methods=["POST"])
    def update_release_sprints():
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))
        if releases_are_locked(workspace):
            flash("As releases configuradas estao bloqueadas para edicao.", "warning")
            return redirect(url_for("routes.plan"))

        releases = normalize_releases(workspace.get("releases", []))
        release_index = int(request.form.get("release_index", 0))
        new_sprints = int(request.form.get("release_sprints", 5))

        if 0 <= release_index < len(releases):
            releases[release_index]["sprints"] = new_sprints
            workspace["releases"] = releases
            save_current_squad_workspace(workspace)
            flash(f"Release {release_index + 1} atualizada para {new_sprints} sprints.", "success")
        else:
            flash("Indice de release invalido.", "error")

        return redirect(url_for("routes.plan"))

    @routes_bp.route("/add_release", methods=["POST"])
    def add_release():
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))
        if releases_are_locked(workspace):
            flash("As releases configuradas estao bloqueadas para edicao.", "warning")
            return redirect(url_for("routes.plan"))

        releases = normalize_releases(workspace.get("releases", []))
        releases.append(
            {
                "points": float(request.form.get("new_release_points", 50)),
                "sprints": int(request.form.get("new_release_sprints", 5)),
            }
        )
        workspace["releases"] = releases
        save_current_squad_workspace(workspace)
        flash("Nova release adicionada com sucesso.", "success")
        return redirect(url_for("routes.plan"))

    @routes_bp.route("/delete_release", methods=["POST"])
    def delete_release():
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))
        if releases_are_locked(workspace):
            flash("As releases configuradas estao bloqueadas para edicao.", "warning")
            return redirect(url_for("routes.plan"))

        releases = normalize_releases(workspace.get("releases", []))
        release_index = int(request.form.get("release_index", 0))

        if 0 <= release_index < len(releases):
            removed = releases.pop(release_index)
            workspace["releases"] = releases
            save_current_squad_workspace(workspace)
            flash(
                f"Release removida ({removed['points']} pontos, {removed['sprints']} sprints).",
                "success",
            )
        else:
            flash("Indice de release invalido.", "error")

        return redirect(url_for("routes.plan"))

    @routes_bp.route("/add_sprint", methods=["POST"])
    def add_sprint():
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))
        if workspace.get("squad_cost", 0) <= 0:
            return redirect(url_for("routes.setup"))

        planning_totals = get_planning_totals(workspace)
        releases = planning_totals["releases"]
        if not releases:
            flash("Por favor, configure as releases primeiro.", "warning")
            return redirect(url_for("routes.plan"))

        total_release_points = planning_totals["total_release_points"]
        value_per_point = planning_totals["value_per_point"]
        current_component_count = planning_totals["current_component_count"]

        try:
            sprint_plan_points = float(request.form.get("sprint_plan_points", 0))
            sprint_done_points = float(request.form.get("sprint_done_points", 0))
            sprint_added_points = float(request.form.get("sprint_added_points", 0))
            sprint_planned_value = parse_brazilian_float(request.form.get("sprint_planned_value", 0))
            sprint_actual_cost = parse_brazilian_float(request.form.get("sprint_actual_cost", 0))
            sprint_weeks = float(request.form.get("sprint_weeks", planning_totals["default_sprint_weeks"]) or 2)
        except (ValueError, TypeError):
            flash("Erro ao processar os valores inseridos.", "error")
            return redirect(url_for("routes.plan"))

        history = recalculate_history(
            workspace.get("history", []),
            value_per_point,
            total_release_points,
            workspace.get("squad_cost", 0),
            current_component_count,
        )
        sprint_number = len(history) + 1
        total_done_points = sum(record.get("done_points", 0) for record in history) + sprint_done_points
        updated_total_release_points = total_release_points + sprint_added_points
        updated_value_per_point = (
            planning_totals["bac"] / updated_total_release_points if updated_total_release_points > 0 else 0
        )

        record = build_sprint_record(
            sprint_number=sprint_number,
            planned_points=sprint_plan_points,
            earned_points=sprint_done_points,
            added_points=sprint_added_points,
            actual_cost=sprint_actual_cost,
            value_per_point=updated_value_per_point,
            cumulative_done_points=total_done_points,
            total_release_points=updated_total_release_points,
            planned_value=sprint_planned_value,
            sprint_weeks=sprint_weeks,
            component_count=current_component_count,
            squad_cost=workspace.get("squad_cost", 0),
        )

        history.append(record)
        final_total_release_points = calculate_total_release_points(releases, history)
        final_value_per_point = (
            planning_totals["bac"] / final_total_release_points if final_total_release_points > 0 else 0
        )
        workspace["history"] = recalculate_history(
            history,
            final_value_per_point,
            final_total_release_points,
            workspace.get("squad_cost", 0),
            current_component_count,
        )
        save_current_squad_workspace(workspace)
        flash(f"Sprint {sprint_number} registrada com sucesso!", "success")
        return redirect(url_for("routes.plan"))

    @routes_bp.route("/update_sprint/<int:sprint_no>", methods=["POST"])
    def update_sprint(sprint_no):
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))

        releases = normalize_releases(workspace.get("releases", []))
        if not releases:
            flash("Por favor, configure as releases antes de editar a sprint.", "warning")
            return redirect(url_for("routes.plan"))

        history = list(workspace.get("history", []))
        sprint_index = sprint_no - 1
        if sprint_index < 0 or sprint_index >= len(history):
            flash("Sprint nao encontrada para edicao.", "error")
            return redirect(url_for("routes.plan"))

        try:
            history[sprint_index]["plan_points"] = float(request.form.get("sprint_plan_points", 0))
            history[sprint_index]["done_points"] = float(request.form.get("sprint_done_points", 0))
            history[sprint_index]["added_points"] = float(request.form.get("sprint_added_points", 0))
            history[sprint_index]["PV"] = parse_brazilian_float(request.form.get("sprint_planned_value", 0))
            history[sprint_index]["AC"] = parse_brazilian_float(request.form.get("sprint_actual_cost", 0))
            history[sprint_index]["sprint_weeks"] = float(request.form.get("sprint_weeks", 2) or 2)
        except (ValueError, TypeError):
            flash("Erro ao processar os dados da sprint.", "error")
            return redirect(url_for("routes.plan"))

        planning_totals = get_planning_totals(workspace)
        total_release_sprints = sum(release.get("sprints", 0) for release in releases)
        sprint_cost = planning_totals["sprint_cost"]
        bac = sprint_cost * total_release_sprints
        total_release_points = calculate_total_release_points(releases, history)
        value_per_point = bac / total_release_points if total_release_points > 0 else 0
        workspace["history"] = recalculate_history(
            history,
            value_per_point,
            total_release_points,
            workspace.get("squad_cost", 0),
            planning_totals["current_component_count"],
        )
        save_current_squad_workspace(workspace)
        flash(f"Sprint {sprint_no} atualizada com sucesso!", "success")
        return redirect(url_for("routes.plan"))

    @routes_bp.route("/delete_sprint/<int:sprint_no>", methods=["POST"])
    def delete_sprint(sprint_no):
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))

        history = list(workspace.get("history", []))
        sprint_index = sprint_no - 1
        if sprint_index < 0 or sprint_index >= len(history):
            flash("Sprint nao encontrada para exclusao.", "error")
            return redirect(url_for("routes.plan"))

        history.pop(sprint_index)
        releases = normalize_releases(workspace.get("releases", []))
        planning_totals = get_planning_totals(workspace)
        total_release_sprints = sum(release.get("sprints", 0) for release in releases)
        sprint_cost = planning_totals["sprint_cost"]
        bac = sprint_cost * total_release_sprints
        total_release_points = calculate_total_release_points(releases, history)
        value_per_point = bac / total_release_points if total_release_points > 0 else 0
        workspace["history"] = recalculate_history(
            history,
            value_per_point,
            total_release_points,
            workspace.get("squad_cost", 0),
            planning_totals["current_component_count"],
        )
        save_current_squad_workspace(workspace)
        flash(f"Sprint {sprint_no} excluida com sucesso!", "success")
        return redirect(url_for("routes.plan"))

"""
squad_routes.py - Rotas de upload, selecao e configuracao de squad.
"""

from __future__ import annotations

import os
import secrets

from flask import current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from formula_helpers import calculate_file_member_monthly_cost, calculate_manual_member_monthly_cost
from models import SquadLoader
from route_helpers import (
    ensure_current_squad_workspace,
    get_current_username,
    parse_brazilian_float,
    get_squads_data,
    save_current_squad_workspace,
)
from storage import upsert_squad
from storage import delete_squad as delete_squad_record


ALLOWED_EXTENSIONS = {"xlsx", "xls", "csv"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _recalculate_workspace_costs(workspace):
    file_members = workspace.get("squad_members_from_file", [])
    members = workspace.get("members", [])

    recalculated_file_members = []
    total_file_cost = 0.0
    for member in file_members:
        updated_member = dict(member)
        updated_member["total_grupo"] = round(
            calculate_file_member_monthly_cost(
                updated_member.get("qtde", 1),
                updated_member.get("preco_mhh", 0),
            ),
            2,
        )
        total_file_cost += updated_member["total_grupo"]
        recalculated_file_members.append(updated_member)

    manual_cost = sum(
        calculate_manual_member_monthly_cost(
            member.get("salary", 0),
            member.get("hourly", 0),
            member.get("quantity", 1),
        )
        for member in members
    )
    infrastructure_cost = round(parse_brazilian_float(workspace.get("infrastructure_cost", 0)), 2)
    health_plan_cost = round(parse_brazilian_float(workspace.get("health_plan_cost", 0)), 2)
    meal_allowance_cost = round(parse_brazilian_float(workspace.get("meal_allowance_cost", 0)), 2)
    additional_costs_total = round(infrastructure_cost + health_plan_cost + meal_allowance_cost, 2)
    squad_cost = total_file_cost + manual_cost + additional_costs_total

    workspace["infrastructure_cost"] = infrastructure_cost
    workspace["health_plan_cost"] = health_plan_cost
    workspace["meal_allowance_cost"] = meal_allowance_cost
    workspace["additional_costs_total"] = additional_costs_total
    workspace["squad_members_from_file"] = recalculated_file_members
    workspace["squad_total_cost"] = total_file_cost
    workspace["squad_cost"] = squad_cost
    return total_file_cost, manual_cost, additional_costs_total, squad_cost


def register_squad_routes(routes_bp, upload_folder):
    @routes_bp.route("/upload", methods=["GET", "POST"])
    def upload_file():
        existing_squads = get_squads_data()
        upload_locked = bool(existing_squads)

        if request.method == "POST":
            if upload_locked:
                flash(
                    "A importacao de planilha fica disponivel apenas na carga inicial para preservar os dados ja cadastrados.",
                    "warning",
                )
                return redirect(url_for("routes.select_squad"))

            if "file" not in request.files:
                flash("Nenhum arquivo selecionado", "error")
                return redirect(request.url)

            file = request.files["file"]
            if file.filename == "":
                flash("Arquivo vazio", "error")
                return redirect(request.url)

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(upload_folder, f"{secrets.token_hex(8)}_{filename}")
                file.save(filepath)

                try:
                    uploaded_squads = SquadLoader.load_file(filepath)
                    imported_count = 0

                    for squad_name, squad_info in uploaded_squads.items():
                        existing_squads[squad_name] = squad_info
                        upsert_squad(
                            current_app.config["DATABASE_PATH"],
                            get_current_username(),
                            squad_name,
                            squad_info,
                        )
                        imported_count += 1

                    session["squads_data"] = existing_squads
                    session["squads_list"] = list(existing_squads.keys())
                    session.setdefault("squad_workspaces", {})
                    session.modified = True

                    flash(
                        f"Arquivo carregado com sucesso! {imported_count} squad(s) importada(s).",
                        "success",
                    )

                    if not session.get("current_squad_name") and existing_squads:
                        session["current_squad_name"] = next(iter(existing_squads.keys()))

                    return redirect(url_for("routes.select_squad"))
                except Exception as exc:
                    current_app.logger.exception("Erro ao processar upload de squads: %s", exc)
                    flash("Erro ao processar arquivo. Verifique o formato e tente novamente.", "error")
                    return redirect(request.url)
                finally:
                    try:
                        if os.path.exists(filepath):
                            os.remove(filepath)
                    except OSError:
                        pass

            flash("Formato de arquivo nao permitido. Use Excel (.xlsx) ou CSV.", "error")

        return render_template(
            "upload.html",
            has_existing_squads=bool(existing_squads),
            existing_squads_count=len(existing_squads),
            upload_locked=upload_locked,
        )

    @routes_bp.route("/select_squad", methods=["GET", "POST"])
    def select_squad():
        squads_data = get_squads_data()
        squads_list = list(squads_data.keys())

        if request.method == "POST" and "create_squad" in request.form:
            new_squad_name = request.form.get("new_squad_name", "").strip()

            if not new_squad_name:
                flash("Informe um nome para a nova squad.", "error")
                return redirect(request.url)

            if new_squad_name in squads_data:
                flash("Ja existe uma squad com esse nome.", "error")
                return redirect(request.url)

            squads_data[new_squad_name] = {"members": [], "total_cost": 0}
            upsert_squad(
                current_app.config["DATABASE_PATH"],
                get_current_username(),
                new_squad_name,
                squads_data[new_squad_name],
            )
            session["squads_data"] = squads_data
            session["squads_list"] = list(squads_data.keys())
            session["current_squad_name"] = new_squad_name
            session.modified = True
            ensure_current_squad_workspace()
            flash(f"Squad '{new_squad_name}' criada com sucesso.", "success")
            return redirect(url_for("routes.setup"))

        if not squads_list:
            flash("Nenhuma squad carregada. Faca upload de arquivo.", "warning")
            return redirect(url_for("routes.upload_file"))

        if request.method == "POST":
            selected_squad = request.form.get("selected_squad")
            if selected_squad not in squads_data:
                flash("Squad invalida.", "error")
                return redirect(request.url)

            session["current_squad_name"] = selected_squad
            session.modified = True
            ensure_current_squad_workspace()
            return redirect(url_for("routes.setup"))

        return render_template("select_squad.html", squads=squads_data)

    @routes_bp.route("/setup", methods=["GET", "POST"])
    def setup():
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))

        current_squad = session.get("current_squad_name", "Squad desconhecida")
        members_from_file = workspace.get("squad_members_from_file", [])
        total_file_cost = workspace.get("squad_total_cost", 0)
        workspace.setdefault("infrastructure_cost", 0)
        workspace.setdefault("health_plan_cost", 0)
        workspace.setdefault("meal_allowance_cost", 0)
        workspace.setdefault("additional_costs_total", 0)

        if request.method == "POST":
            role = request.form.get("role", "").strip()
            function = request.form.get("function", "").strip()
            try:
                salary = float(request.form.get("salary", 0) or 0)
                hourly = float(request.form.get("hourly", 0) or 0)
                quantity = float(request.form.get("quantity", 1) or 1)
            except ValueError:
                salary = 0
                hourly = 0
                quantity = 1

            if role and function and salary >= 0 and hourly >= 0 and quantity > 0:
                members = workspace.get("members", [])
                members.append(
                    {
                        "role": role,
                        "function": function,
                        "salary": salary,
                        "hourly": hourly,
                        "quantity": quantity,
                        "source": "manual",
                    }
                )
                workspace["members"] = members
                save_current_squad_workspace(workspace)

        members = workspace.get("members", [])
        total_file_cost, manual_cost, additional_costs_total, squad_cost = _recalculate_workspace_costs(workspace)
        save_current_squad_workspace(workspace)

        return render_template(
            "setup.html",
            current_squad=current_squad,
            members=members,
            members_from_file=members_from_file,
            squad_cost=squad_cost,
            file_cost=total_file_cost,
            manual_cost=manual_cost,
            infrastructure_cost=workspace.get("infrastructure_cost", 0),
            health_plan_cost=workspace.get("health_plan_cost", 0),
            meal_allowance_cost=workspace.get("meal_allowance_cost", 0),
            additional_costs_total=additional_costs_total,
        )

    @routes_bp.route("/update_additional_costs", methods=["POST"])
    def update_additional_costs():
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))

        workspace["infrastructure_cost"] = parse_brazilian_float(request.form.get("infrastructure_cost", 0))
        workspace["health_plan_cost"] = parse_brazilian_float(request.form.get("health_plan_cost", 0))
        workspace["meal_allowance_cost"] = parse_brazilian_float(request.form.get("meal_allowance_cost", 0))
        _recalculate_workspace_costs(workspace)
        save_current_squad_workspace(workspace)
        flash("Custos complementares da squad atualizados com sucesso.", "success")
        return redirect(url_for("routes.setup"))

    @routes_bp.route("/update_file_members", methods=["POST"])
    def update_file_members():
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))

        file_members = workspace.get("squad_members_from_file", [])
        updated_members = []
        for index, member in enumerate(file_members):
            try:
                quantity = max(float(request.form.get(f"file_member_quantity_{index}", member.get("qtde", 1)) or 1), 0)
            except (TypeError, ValueError):
                quantity = float(member.get("qtde", 1) or 1)

            updated_member = dict(member)
            updated_member["qtde"] = quantity
            updated_members.append(updated_member)

        workspace["squad_members_from_file"] = updated_members
        _recalculate_workspace_costs(workspace)
        save_current_squad_workspace(workspace)
        flash("Composicao da planilha atualizada com sucesso.", "success")
        return redirect(url_for("routes.setup"))

    @routes_bp.route("/update_manual_members", methods=["POST"])
    def update_manual_members():
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))

        members = workspace.get("members", [])
        updated_members = []
        for index, member in enumerate(members):
            updated_member = dict(member)
            updated_member["role"] = request.form.get(f"manual_role_{index}", member.get("role", "")).strip()
            updated_member["function"] = request.form.get(f"manual_function_{index}", member.get("function", "")).strip()
            try:
                updated_member["salary"] = float(request.form.get(f"manual_salary_{index}", member.get("salary", 0)) or 0)
                updated_member["hourly"] = float(request.form.get(f"manual_hourly_{index}", member.get("hourly", 0)) or 0)
                updated_member["quantity"] = max(float(request.form.get(f"manual_quantity_{index}", member.get("quantity", 1)) or 1), 0.25)
            except (TypeError, ValueError):
                updated_member["salary"] = member.get("salary", 0)
                updated_member["hourly"] = member.get("hourly", 0)
                updated_member["quantity"] = member.get("quantity", 1)
            updated_members.append(updated_member)

        workspace["members"] = updated_members
        _recalculate_workspace_costs(workspace)
        save_current_squad_workspace(workspace)
        flash("Membros adicionais atualizados com sucesso.", "success")
        return redirect(url_for("routes.setup"))

    @routes_bp.route("/remove_member/<int:member_index>", methods=["POST"])
    def remove_member(member_index):
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))
        members = workspace.get("members", [])

        if 0 <= member_index < len(members):
            removed = members.pop(member_index)
            workspace["members"] = members
            _recalculate_workspace_costs(workspace)
            save_current_squad_workspace(workspace)
            flash(f"Membro '{removed['role']}' removido com sucesso.", "success")
        else:
            flash("Indice de membro invalido.", "error")

        return redirect(url_for("routes.setup"))

    @routes_bp.route("/remove_file_member/<int:member_index>", methods=["POST"])
    def remove_file_member(member_index):
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))
        file_members = workspace.get("squad_members_from_file", [])

        if 0 <= member_index < len(file_members):
            removed = file_members.pop(member_index)
            workspace["squad_members_from_file"] = file_members
            _recalculate_workspace_costs(workspace)
            save_current_squad_workspace(workspace)
            flash(f"Membro '{removed['cargo']}' removido com sucesso.", "success")
        else:
            flash("Indice de membro invalido.", "error")

        return redirect(url_for("routes.setup"))

    @routes_bp.route("/delete_squad/<squad_name>", methods=["POST"])
    def delete_squad(squad_name):
        squads_data = get_squads_data()
        if squad_name not in squads_data:
            flash("Squad invalida.", "error")
            return redirect(url_for("routes.select_squad"))

        deleted = delete_squad_record(
            current_app.config["DATABASE_PATH"],
            get_current_username(),
            squad_name,
        )
        if not deleted:
            flash("Nao foi possivel remover a squad.", "error")
            return redirect(url_for("routes.select_squad"))

        squads_data.pop(squad_name, None)
        session["squads_data"] = squads_data
        session["squads_list"] = list(squads_data.keys())

        workspaces = session.get("squad_workspaces", {})
        workspaces.pop(squad_name, None)
        session["squad_workspaces"] = workspaces

        if session.get("current_squad_name") == squad_name:
            session["current_squad_name"] = next(iter(squads_data.keys()), None)

        session.modified = True
        flash(f"Squad '{squad_name}' removida com sucesso.", "success")
        return redirect(url_for("routes.select_squad"))

    @routes_bp.route("/reset", methods=["POST"])
    def reset():
        flash(
            "Novo upload desabilitado no planejamento para preservar os dados ja cadastrados.",
            "warning",
        )
        return redirect(url_for("routes.plan"))

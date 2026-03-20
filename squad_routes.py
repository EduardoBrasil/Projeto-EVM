"""
squad_routes.py - Rotas de upload, selecao e configuracao de squad.
"""

from __future__ import annotations

import os

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from models import SquadLoader
from route_helpers import ensure_current_squad_workspace, save_current_squad_workspace


ALLOWED_EXTENSIONS = {"xlsx", "xls", "csv"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def register_squad_routes(routes_bp, upload_folder):
    @routes_bp.route("/upload", methods=["GET", "POST"])
    def upload_file():
        if request.method == "POST":
            if "file" not in request.files:
                flash("Nenhum arquivo selecionado", "error")
                return redirect(request.url)

            file = request.files["file"]
            if file.filename == "":
                flash("Arquivo vazio", "error")
                return redirect(request.url)

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)

                try:
                    squads_data = SquadLoader.load_file(filepath)
                    session["squads_data"] = squads_data
                    session["squads_list"] = list(squads_data.keys())
                    session.pop("squad_workspaces", None)
                    session.pop("current_squad_name", None)
                    session.modified = True
                    flash(
                        f"Arquivo carregado com sucesso! {len(squads_data)} squads encontradas.",
                        "success",
                    )
                    return redirect(url_for("routes.select_squad"))
                except Exception as exc:
                    flash(f"Erro ao processar arquivo: {str(exc)}", "error")
                    return redirect(request.url)

            flash("Formato de arquivo não permitido. Use Excel (.xlsx) ou CSV.", "error")

        return render_template("upload.html")

    @routes_bp.route("/select_squad", methods=["GET", "POST"])
    def select_squad():
        squads_data = session.get("squads_data", {})
        squads_list = list(squads_data.keys())

        if request.method == "POST" and "create_squad" in request.form:
            new_squad_name = request.form.get("new_squad_name", "").strip()

            if not new_squad_name:
                flash("Informe um nome para a nova squad.", "error")
                return redirect(request.url)

            if new_squad_name in squads_data:
                flash("Já existe uma squad com esse nome.", "error")
                return redirect(request.url)

            squads_data[new_squad_name] = {"members": [], "total_cost": 0}
            session["squads_data"] = squads_data
            session["squads_list"] = list(squads_data.keys())
            session["current_squad_name"] = new_squad_name
            session.modified = True
            ensure_current_squad_workspace()
            flash(f"Squad '{new_squad_name}' criada com sucesso.", "success")
            return redirect(url_for("routes.setup"))

        if not squads_list:
            flash("Nenhuma squad carregada. Faça upload de arquivo.", "warning")
            return redirect(url_for("routes.upload_file"))

        if request.method == "POST":
            selected_squad = request.form.get("selected_squad")
            if selected_squad not in squads_data:
                flash("Squad inválida", "error")
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

        if request.method == "POST":
            role = request.form.get("role", "").strip()
            function = request.form.get("function", "").strip()
            try:
                salary = float(request.form.get("salary", 0) or 0)
                hourly = float(request.form.get("hourly", 0) or 0)
            except ValueError:
                salary = 0
                hourly = 0

            if role and function and salary >= 0 and hourly >= 0:
                members = workspace.get("members", [])
                members.append(
                    {
                        "role": role,
                        "function": function,
                        "salary": salary,
                        "hourly": hourly,
                        "source": "manual",
                    }
                )
                workspace["members"] = members
                save_current_squad_workspace(workspace)

        members = workspace.get("members", [])
        manual_cost = sum(member["salary"] + 160 * member["hourly"] for member in members)
        squad_cost = total_file_cost + manual_cost
        workspace["squad_cost"] = squad_cost
        save_current_squad_workspace(workspace)

        return render_template(
            "setup.html",
            current_squad=current_squad,
            members=members,
            members_from_file=members_from_file,
            squad_cost=squad_cost,
            file_cost=total_file_cost,
            manual_cost=manual_cost,
        )

    @routes_bp.route("/remove_member/<int:member_index>", methods=["POST"])
    def remove_member(member_index):
        workspace = ensure_current_squad_workspace()
        if workspace is None:
            return redirect(url_for("routes.select_squad"))
        members = workspace.get("members", [])

        if 0 <= member_index < len(members):
            removed = members.pop(member_index)
            workspace["members"] = members
            save_current_squad_workspace(workspace)
            flash(f"Membro '{removed['role']}' removido com sucesso.", "success")
        else:
            flash("Índice de membro inválido.", "error")

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
            workspace["squad_total_cost"] = sum(member["total_grupo"] for member in file_members)
            save_current_squad_workspace(workspace)
            flash(f"Membro '{removed['cargo']}' removido com sucesso.", "success")
        else:
            flash("Índice de membro inválido.", "error")

        return redirect(url_for("routes.setup"))

    @routes_bp.route("/reset", methods=["GET"])
    def reset():
        session.clear()
        flash("Sessão resetada. Carregue um novo arquivo.", "success")
        return redirect(url_for("routes.upload_file"))

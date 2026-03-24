"""
auth_routes.py - Rotas de autenticacao e sessao.
"""

from __future__ import annotations

import sqlite3

from flask import current_app, flash, redirect, render_template, request, session, url_for

from storage import authenticate_user, create_user


def register_auth_routes(routes_bp):
    @routes_bp.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("user_id") and session.get("username"):
            return redirect(url_for("routes.dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            user = authenticate_user(current_app.config["DATABASE_PATH"], username, password)
            if not user:
                flash("Usuario ou senha invalidos.", "error")
                return render_template("auth.html", auth_mode="login", username=username)

            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session.modified = True
            flash("Login realizado com sucesso.", "success")
            return redirect(url_for("routes.dashboard"))

        return render_template("auth.html", auth_mode="login")

    @routes_bp.route("/register", methods=["GET", "POST"])
    def register():
        if session.get("user_id") and session.get("username"):
            return redirect(url_for("routes.dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            if len(username) < 3:
                flash("O usuario deve ter pelo menos 3 caracteres.", "error")
                return render_template("auth.html", auth_mode="register", username=username)

            if len(password) < 6:
                flash("A senha deve ter pelo menos 6 caracteres.", "error")
                return render_template("auth.html", auth_mode="register", username=username)

            if password != confirm_password:
                flash("A confirmacao de senha nao confere.", "error")
                return render_template("auth.html", auth_mode="register", username=username)

            try:
                user_id = create_user(current_app.config["DATABASE_PATH"], username, password)
            except sqlite3.IntegrityError:
                flash("Ja existe um usuario com esse nome.", "error")
                return render_template("auth.html", auth_mode="register", username=username)

            session.clear()
            session["user_id"] = user_id
            session["username"] = username
            session.modified = True
            flash("Conta criada com sucesso.", "success")
            return redirect(url_for("routes.upload_file"))

        return render_template("auth.html", auth_mode="register")

    @routes_bp.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        flash("Sessao encerrada com sucesso.", "success")
        return redirect(url_for("routes.login"))

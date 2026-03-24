"""
app.py - Aplicacao Flask para EVM (Earned Value Management).
"""

from __future__ import annotations

import os

from flask import Flask, redirect, request, session, url_for

from routes import routes_bp
from storage import init_db, load_all_squads, load_all_workspaces


def format_currency(value):
    """Formata um valor numerico como moeda brasileira."""
    try:
        numeric_value = float(value)
        return f"R$ {numeric_value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"


def create_app(test_config=None):
    """Factory Method para construir a aplicacao Flask."""
    app = Flask(__name__)
    app.secret_key = "dev-secret-key-change-in-production"
    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    app.config["DATABASE_PATH"] = os.path.join(os.path.dirname(__file__), "evm.db")

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    init_db(app.config["DATABASE_PATH"])
    app.register_blueprint(routes_bp)
    app.jinja_env.filters["currency"] = format_currency

    public_endpoints = {
        "routes.login",
        "routes.register",
        "static",
    }

    @app.before_request
    def hydrate_session_from_database():
        if request.endpoint in public_endpoints:
            return None

        if "user_id" not in session or "username" not in session:
            return redirect(url_for("routes.login"))

        if "squads_data" not in session:
            squads_data = load_all_squads(
                app.config["DATABASE_PATH"],
                session["username"],
            )
            session["squads_data"] = squads_data
            session["squads_list"] = list(squads_data.keys())
            session["squad_workspaces"] = load_all_workspaces(
                app.config["DATABASE_PATH"],
                session["username"],
            )
            session.modified = True
        return None

    @app.context_processor
    def inject_navigation_context():
        squads_data = session.get("squads_data")
        username = session.get("username")
        if username and not squads_data:
            squads_data = load_all_squads(app.config["DATABASE_PATH"], username)
        if squads_data is None:
            squads_data = {}
        return {
            "nav_squads": list(squads_data.keys()),
            "nav_current_squad": session.get("current_squad_name"),
            "nav_username": username,
            "nav_is_authenticated": bool(session.get("user_id") and username),
        }

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)

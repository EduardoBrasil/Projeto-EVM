"""
app.py - Aplicacao Flask para EVM (Earned Value Management).
"""

from __future__ import annotations

import os

from flask import Flask, session

from routes import routes_bp


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

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.register_blueprint(routes_bp)
    app.jinja_env.filters["currency"] = format_currency

    @app.context_processor
    def inject_navigation_context():
        squads_data = session.get("squads_data", {})
        return {
            "nav_squads": list(squads_data.keys()),
            "nav_current_squad": session.get("current_squad_name"),
        }

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)

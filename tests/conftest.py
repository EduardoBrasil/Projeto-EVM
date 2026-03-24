from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path):
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()
    database_path = tmp_path / "evm.db"
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "UPLOAD_FOLDER": str(uploads_dir),
            "DATABASE_PATH": str(database_path),
        }
    )
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def sample_squads_data():
    return {
        "Alpha": {
            "members": [
                {
                    "cargo": "Dev",
                    "area": "Backend",
                    "qtde": 1,
                    "custo_mhh": 100,
                    "preco_mhh": 120,
                    "total_grupo": 4032,
                }
            ],
            "total_cost": 4032,
        },
        "Beta": {
            "members": [],
            "total_cost": 0,
        },
    }


def seed_session(client, squads_data, current_squad="Alpha", workspace=None):
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "tester"
        session["squads_data"] = squads_data
        session["squads_list"] = list(squads_data.keys())
        session["current_squad_name"] = current_squad
        if workspace is not None:
            session["squad_workspaces"] = {current_squad: workspace}

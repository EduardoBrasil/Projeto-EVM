import io
from pathlib import Path

from app import format_currency
from storage import upsert_squad


def test_format_currency_handles_numbers_and_invalid_values():
    assert format_currency(1234.5) == "R$ 1.234,50"
    assert format_currency("abc") == "R$ 0,00"


def test_create_app_injects_navigation_context(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "tester"
        session["squads_data"] = {"Alpha": {}, "Beta": {}}
        session["current_squad_name"] = "Beta"

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_create_app_sets_security_defaults(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["MAX_CONTENT_LENGTH"] == 16 * 1024 * 1024
    assert app.config["SECRET_KEY"]


def test_persistence_keeps_uploaded_squad_data_between_clients(app):
    first_client = app.test_client()
    with first_client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "alice"

    csv_bytes = (
        "SQUAD,CARGO,ÁREA,QTDE,Custo M H/H,Preço M/HH,TOTAL GRUPO\n"
        "Alpha,Dev,Backend,1,10,20,0\n"
    ).encode("utf-8")

    upload_response = first_client.post(
        "/upload",
        data={"file": (io.BytesIO(csv_bytes), "squads.csv")},
        content_type="multipart/form-data",
    )

    assert upload_response.status_code == 302

    second_client = app.test_client()
    with second_client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "alice"

    dashboard_response = second_client.get("/dashboard")

    assert dashboard_response.status_code == 200
    assert b"Alpha" in dashboard_response.data


def test_persistence_is_isolated_by_username(app):
    first_client = app.test_client()
    with first_client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "alice"

    csv_bytes = (
        "SQUAD,CARGO,ÁREA,QTDE,Custo M H/H,Preço M/HH,TOTAL GRUPO\n"
        "Alpha,Dev,Backend,1,10,20,0\n"
    ).encode("utf-8")
    first_client.post(
        "/upload",
        data={"file": (io.BytesIO(csv_bytes), "alice.csv")},
        content_type="multipart/form-data",
    )

    second_client = app.test_client()
    with second_client.session_transaction() as session:
        session["user_id"] = 2
        session["username"] = "bob"

    response = second_client.get("/dashboard")

    assert response.status_code == 302
    assert response.location.endswith("/upload")


def test_upload_file_is_removed_after_processing(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "alice"

    csv_bytes = (
        "SQUAD,CARGO,ÃREA,QTDE,Custo M H/H,PreÃ§o M/HH,TOTAL GRUPO\n"
        "Alpha,Dev,Backend,1,10,20,0\n"
    ).encode("utf-8")

    response = client.post(
        "/upload",
        data={"file": (io.BytesIO(csv_bytes), "squads.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert not any(Path(app.config["UPLOAD_FOLDER"]).iterdir())


def test_delete_squad_updates_current_selection(app):
    upsert_squad(app.config["DATABASE_PATH"], "alice", "Alpha", {"members": [], "total_cost": 0})
    upsert_squad(app.config["DATABASE_PATH"], "alice", "Beta", {"members": [], "total_cost": 0})

    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "alice"
        session["squads_data"] = {
            "Alpha": {"members": [], "total_cost": 0},
            "Beta": {"members": [], "total_cost": 0},
        }
        session["squads_list"] = ["Alpha", "Beta"]
        session["current_squad_name"] = "Alpha"
        session["squad_workspaces"] = {"Alpha": {"members": [], "releases": [], "history": []}}

    response = client.post("/delete_squad/Alpha")

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert "Alpha" not in session["squads_data"]
        assert session["current_squad_name"] == "Beta"

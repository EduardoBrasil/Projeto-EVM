from app import create_app, format_currency


def test_format_currency_handles_numbers_and_invalid_values():
    assert format_currency(1234.5) == "R$ 1.234,50"
    assert format_currency("abc") == "R$ 0,00"


def test_create_app_injects_navigation_context(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session["squads_data"] = {"Alpha": {}, "Beta": {}}
        session["current_squad_name"] = "Beta"

    response = client.get("/upload")

    assert response.status_code == 200
    assert b"Dashboard" in response.data

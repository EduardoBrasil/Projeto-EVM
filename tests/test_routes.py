from __future__ import annotations

import io

import routes
from tests.conftest import build_squad_csv_bytes, seed_session


def planning_workspace():
    return {
        "members": [],
        "releases": [{"points": 40, "sprints": 4}],
        "history": [],
        "squad_members_from_file": [
            {
                "cargo": "Dev",
                "area": "Backend",
                "qtde": 1,
                "custo_mhh": 100,
                "preco_mhh": 120,
                "total_grupo": 4032,
            }
        ],
        "squad_total_cost": 4032,
        "squad_cost": 4032,
    }


def authenticate_session(client, username="tester", user_id=1):
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["username"] = username


def test_dashboard_redirects_without_data(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.location.endswith("/login")


def test_upload_page_and_invalid_extension(client):
    authenticate_session(client)

    response = client.get("/upload")
    assert response.status_code == 200

    response = client.post(
        "/upload",
        data={"file": (io.BytesIO(b"bad"), "bad.txt")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_upload_page_is_locked_after_initial_import(client, sample_squads_data):
    seed_session(client, sample_squads_data, workspace=planning_workspace())

    response = client.get("/upload")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "importacao de planilha fica bloqueada apos a carga inicial".lower() in html.lower()
    assert 'type="file"' in html
    assert 'disabled' in html


def test_dashboard_and_plan_do_not_expose_active_upload_action_after_initial_import(client, sample_squads_data):
    seed_session(client, sample_squads_data, workspace=planning_workspace())

    dashboard_response = client.get("/dashboard")
    plan_response = client.get("/plan")

    assert dashboard_response.status_code == 200
    assert plan_response.status_code == 200
    assert 'href="/upload"' not in dashboard_response.get_data(as_text=True)
    assert 'href="/upload"' not in plan_response.get_data(as_text=True)


def test_upload_valid_csv_populates_session(client):
    authenticate_session(client)

    response = client.post(
        "/upload",
        data={"file": (io.BytesIO(build_squad_csv_bytes()), "squads.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert response.location.endswith("/select_squad")


def test_end_to_end_workflow_supports_utf8_csv_upload(client):
    register_response = client.post(
        "/register",
        data={"username": "alice", "password": "secret1", "confirm_password": "secret1"},
    )
    assert register_response.status_code == 302
    assert register_response.location.endswith("/upload")

    upload_response = client.post(
        "/upload",
        data={"file": (io.BytesIO(build_squad_csv_bytes()), "squads.csv")},
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 302
    assert upload_response.location.endswith("/select_squad")

    with client.session_transaction() as session:
        assert session["squads_data"]["Alpha"]["members"][0]["area"] == "Backend"

    select_response = client.post("/select_squad", data={"selected_squad": "Alpha"})
    assert select_response.status_code == 302
    assert select_response.location.endswith("/setup")

    setup_response = client.get("/setup")
    assert setup_response.status_code == 200

    add_member_response = client.post(
        "/setup",
        data={"role": "QA", "function": "Quality", "salary": "1000", "hourly": "10", "quantity": "1"},
        follow_redirects=True,
    )
    assert add_member_response.status_code == 200
    assert b"QA" in add_member_response.data

    assert client.get("/dashboard").status_code == 200
    assert client.get("/plan").status_code == 200

    create_baseline_response = client.post("/create_baseline")
    assert create_baseline_response.status_code == 302
    assert create_baseline_response.location.endswith("/plan")

    add_sprint_response = client.post(
        "/add_sprint",
        data={
            "sprint_plan_points": 10,
            "sprint_done_points": 8,
            "sprint_added_points": 1,
            "sprint_planned_value": "100,00",
            "sprint_actual_cost": "90,00",
        },
    )
    assert add_sprint_response.status_code == 302
    assert add_sprint_response.location.endswith("/plan")

    baseline_response = client.get("/baseline")
    assert baseline_response.status_code == 200
    assert b"Baseline do Projeto" in baseline_response.data
    assert b"PDF Projeto" in baseline_response.data

    cumulative_chart_response = client.get("/generate_cumulative_chart")
    assert cumulative_chart_response.status_code == 200
    assert cumulative_chart_response.mimetype == "image/png"

    project_report_response = client.get("/export_project_report")
    assert project_report_response.status_code == 200
    assert project_report_response.mimetype == "application/pdf"


def test_auth_register_login_and_logout(client):
    register_response = client.post(
        "/register",
        data={"username": "alice", "password": "secret1", "confirm_password": "secret1"},
    )
    assert register_response.status_code == 302
    assert register_response.location.endswith("/upload")

    logout_response = client.post("/logout")
    assert logout_response.status_code == 302
    assert logout_response.location.endswith("/login")

    login_response = client.post(
        "/login",
        data={"username": "alice", "password": "secret1"},
    )
    assert login_response.status_code == 302
    assert login_response.location.endswith("/dashboard")


def test_select_squad_create_and_switch(client, sample_squads_data):
    seed_session(client, sample_squads_data, current_squad="Alpha")

    response = client.post("/select_squad", data={"create_squad": "1", "new_squad_name": "Nova"})
    assert response.status_code == 302
    assert response.location.endswith("/setup")

    response = client.post("/select_squad", data={"selected_squad": "Beta"})
    assert response.status_code == 302
    assert response.location.endswith("/setup")


def test_setup_adds_manual_member(client, sample_squads_data):
    seed_session(client, sample_squads_data, workspace=planning_workspace())

    response = client.post(
        "/setup",
        data={"role": "QA", "function": "Quality", "salary": "1000", "hourly": "10", "quantity": "2"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"QA" in response.data


def test_setup_updates_file_and_manual_members(client, sample_squads_data):
    workspace = planning_workspace()
    workspace["members"] = [{"role": "QA", "function": "Quality", "salary": 1000, "hourly": 10, "quantity": 1}]
    seed_session(client, sample_squads_data, workspace=workspace)

    assert client.post("/update_file_members", data={"file_member_quantity_0": "0.5"}).status_code == 302
    assert client.post(
        "/update_additional_costs",
        data={
            "infrastructure_cost": "500,00",
            "health_plan_cost": "300,00",
            "meal_allowance_cost": "200,00",
        },
    ).status_code == 302
    assert client.post(
        "/update_manual_members",
        data={
            "manual_role_0": "QA Lead",
            "manual_function_0": "Quality",
            "manual_salary_0": "1200",
            "manual_hourly_0": "12",
            "manual_quantity_0": "0.25",
        },
    ).status_code == 302

    dashboard_response = client.get("/dashboard/squad/Alpha")
    assert dashboard_response.status_code == 200
    dashboard_html = dashboard_response.get_data(as_text=True)
    assert "Custo da Squad" in dashboard_html
    assert "R$ 11.380,00" in dashboard_html
    assert "Inclui R$ 1.000,00 de custos complementares." in dashboard_html


def test_release_configuration_stays_editable_until_first_sprint(client, sample_squads_data):
    workspace = planning_workspace()
    workspace["releases"] = []
    seed_session(client, sample_squads_data, workspace=workspace)

    response = client.get("/plan")
    assert response.status_code == 200
    empty_plan_html = response.get_data(as_text=True)
    assert 'name="num_releases"' in empty_plan_html
    assert 'name="release_points"' in empty_plan_html
    assert 'name="release_sprints"' in empty_plan_html

    response = client.post(
        "/plan",
        data={
            "create_releases": "1",
            "num_releases": "2",
            "release_points": ["65", "30"],
            "release_sprints": ["7", "3"],
        },
    )
    assert response.status_code == 200
    plan_html = response.get_data(as_text=True)
    assert 'name="release_points"' in plan_html
    assert 'name="release_sprints"' in plan_html
    assert "Adicionar mais uma release" in plan_html
    assert 'name="new_release_points"' not in plan_html
    assert client.post("/add_release").status_code == 302

    with client.session_transaction() as session:
        releases = session["squad_workspaces"]["Alpha"]["releases"]
        assert releases[0]["points"] == 65
        assert releases[0]["sprints"] == 7
        assert releases[1]["points"] == 30
        assert releases[1]["sprints"] == 3
        assert releases[2]["points"] == 50.0
        assert releases[2]["sprints"] == 5
        assert len(releases) == 3

    assert client.post(
        "/add_sprint",
        data={
            "sprint_plan_points": 10,
            "sprint_done_points": 8,
            "sprint_added_points": 0,
            "sprint_planned_value": "100,00",
            "sprint_actual_cost": "80,00",
        },
    ).status_code == 302

    locked_response = client.get("/plan")
    assert locked_response.status_code == 200
    locked_html = locked_response.get_data(as_text=True)
    assert 'name="release_points"' in locked_html
    assert 'name="release_sprints"' in locked_html
    assert "Adicionar mais uma release" not in locked_html
    assert 'name="new_release_points"' not in locked_html


def test_plan_crud_release_and_sprint_flow(client, sample_squads_data):
    workspace = planning_workspace()
    seed_session(client, sample_squads_data, workspace=workspace)

    assert client.get("/plan").status_code == 200
    assert client.get("/baseline").status_code == 200
    assert client.post("/create_baseline").status_code == 302

    response = client.post("/update_release_points", data={"release_index": 0, "release_points": 50})
    assert response.status_code == 302

    response = client.post("/update_release_sprints", data={"release_index": 0, "release_sprints": 5})
    assert response.status_code == 302

    response = client.post("/add_release")
    assert response.status_code == 302

    response = client.post(
        "/add_sprint",
        data={
            "sprint_plan_points": 10,
            "sprint_done_points": 8,
            "sprint_added_points": 0,
            "sprint_planned_value": "100,00",
            "sprint_actual_cost": "80,00",
        },
    )
    assert response.status_code == 302

    response = client.post(
        "/update_sprint/1",
        data={
            "sprint_plan_points": 10,
            "sprint_done_points": 9,
            "sprint_added_points": 2,
            "sprint_planned_value": "120,00",
            "sprint_actual_cost": "90,00",
        },
    )
    assert response.status_code == 302

    response = client.get("/plan")
    assert response.status_code == 200
    assert b"Hist" in response.data
    assert b"Baseline" in response.data

    baseline_response = client.get("/baseline")
    assert baseline_response.status_code == 200
    assert b"Comparativo Atual x Baseline" in baseline_response.data

    response = client.post("/delete_sprint/1")
    assert response.status_code == 302


def test_release_structure_is_locked_after_first_sprint_but_values_remain_editable(client, sample_squads_data):
    workspace = planning_workspace()
    workspace["history"] = [{"sprint_no": 1}]
    seed_session(client, sample_squads_data, workspace=workspace)

    plan_response = client.get("/plan")
    assert plan_response.status_code == 200
    plan_html = plan_response.get_data(as_text=True)
    assert 'name="release_points"' in plan_html
    assert 'name="release_sprints"' in plan_html
    assert "Adicionar mais uma release" not in plan_html
    assert 'name="new_release_points"' not in plan_html

    assert client.post("/update_release_points", data={"release_index": 0, "release_points": 99}).status_code == 302
    assert client.post("/update_release_sprints", data={"release_index": 0, "release_sprints": 8}).status_code == 302
    assert client.post("/add_release").status_code == 302
    assert client.post("/delete_release", data={"release_index": 0}).status_code == 302

    with client.session_transaction() as session:
        assert session["squad_workspaces"]["Alpha"]["releases"] == [{"points": 99.0, "sprints": 8}]


def test_charts_and_navigation_routes(client, sample_squads_data):
    workspace = planning_workspace()
    workspace["history"] = [
        {
            "sprint_no": 1,
            "plan_points": 10,
            "done_points": 8,
            "added_points": 2,
            "PV": 100,
            "EV": 80,
            "AC": 90,
            "CV": -10,
            "SV": -20,
            "CPI": 0.89,
            "SPI": 0.8,
            "status": "Atencao: Acima do custo e atrasado",
            "completion_percentage": 20,
        }
    ]
    seed_session(client, sample_squads_data, workspace=workspace)

    assert client.get("/dashboard").status_code == 200
    assert client.get("/dashboard/squad/Alpha").status_code == 200
    assert client.get("/switch_squad/Alpha").status_code == 302
    assert client.get("/generate_chart").status_code == 200
    assert client.get("/generate_cumulative_chart").mimetype == "image/png"
    assert client.get("/generate_cpi_chart").mimetype == "image/png"
    assert client.get("/generate_spi_chart").mimetype == "image/png"
    assert client.get("/export_sprint_report").mimetype == "application/pdf"
    assert client.get("/export_project_report").mimetype == "application/pdf"


def test_member_removal_and_reset(client, sample_squads_data):
    workspace = planning_workspace()
    workspace["members"] = [{"role": "QA", "function": "Quality", "salary": 1000, "hourly": 10}]
    seed_session(client, sample_squads_data, workspace=workspace)

    assert client.post("/remove_member/0").status_code == 302
    assert client.post("/remove_file_member/0").status_code == 302
    assert client.post("/delete_squad/Alpha").status_code == 302
    assert client.post("/reset").status_code == 302


def test_reset_route_no_longer_clears_planning_data(client, sample_squads_data):
    seed_session(client, sample_squads_data, workspace=planning_workspace())

    response = client.post("/reset")
    assert response.status_code == 302
    assert response.location.endswith("/plan")

    with client.session_transaction() as session:
        assert "Alpha" in session["squads_data"]
        assert "Alpha" in session["squad_workspaces"]


def test_route_helpers_cover_parsing_and_workspace_branches(app):
    with app.test_request_context("/"):
        assert routes.parse_brazilian_float("100") == 100
        assert routes.parse_brazilian_float("1.234,56") == 1234.56
        assert routes.parse_brazilian_float("abc") == 0
        assert routes.ensure_current_squad_workspace() is None

        from flask import session

        session["user_id"] = 1
        session["username"] = "tester"
        session["current_squad_name"] = "Alpha"
        session["squads_data"] = {"Alpha": {"members": [{"cargo": "Dev"}], "total_cost": 100}}
        workspace = routes.ensure_current_squad_workspace()

        assert workspace["squad_total_cost"] == 100
        assert routes.calculate_total_release_points([{"points": 10}], [{"added_points": 2}]) == 12


def test_invalid_navigation_branches(client, sample_squads_data):
    seed_session(client, sample_squads_data, workspace=planning_workspace())

    assert client.get("/switch_squad/Invalida").status_code == 302
    assert client.get("/dashboard/squad/Invalida").status_code == 302
    assert client.post("/delete_squad/Invalida").status_code == 302
    assert client.post("/update_sprint/99").status_code == 302
    assert client.post("/delete_sprint/99").status_code == 302
    assert client.post("/remove_member/99").status_code == 302
    assert client.post("/remove_file_member/99").status_code == 302

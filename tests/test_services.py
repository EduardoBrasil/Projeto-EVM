from services import (
    PlanningService,
    PlannedValueMetricsStrategy,
    PointsBasedMetricsStrategy,
    SprintMetricsStrategyFactory,
)


def test_strategy_factory_selects_expected_strategy():
    factory = SprintMetricsStrategyFactory()
    assert isinstance(factory.create(None), PointsBasedMetricsStrategy)
    assert isinstance(factory.create(100), PlannedValueMetricsStrategy)


def test_parse_and_normalize_helpers():
    service = PlanningService()
    assert service.parse_brazilian_float("1.234,56") == 1234.56
    assert service.parse_brazilian_float("12") == 12
    assert service.parse_brazilian_float(None) == 0
    assert service.parse_brazilian_float("abc") == 0
    assert service.parse_brazilian_float("1.2.3") == 0
    assert service.normalize_releases([10, {"points": 20, "sprints": 2}]) == [
        {"points": 10.0, "sprints": 5},
        {"points": 20, "sprints": 2},
    ]


def test_build_sprint_record_with_manual_planned_value():
    service = PlanningService()
    record = service.build_sprint_record(
        sprint_number=1,
        planned_points=10,
        earned_points=5,
        added_points=2,
        actual_cost=60,
        value_per_point=10,
        cumulative_done_points=5,
        total_release_points=20,
        planned_value=100,
    )

    assert record["PV"] == 100
    assert record["EV"] == 50
    assert record["SPI"] == 0.5
    assert record["completion_percentage"] == 25.0


def test_points_based_strategy_uses_evm_calculator():
    strategy = PointsBasedMetricsStrategy()
    metrics = strategy.calculate_metrics(10, 8, 70, 10)
    assert metrics["PV"] == 100
    assert metrics["EV"] == 80


def test_recalculate_history_considers_added_scope_progressively():
    service = PlanningService()
    history = [
        {"plan_points": 10, "done_points": 5, "added_points": 4, "AC": 50, "PV": 100},
        {"plan_points": 10, "done_points": 8, "added_points": 2, "AC": 70, "PV": 100},
    ]

    recalculated = service.recalculate_history(history, value_per_point=10, total_release_points=26)

    assert recalculated[0]["completion_percentage"] == round((5 / 24) * 100, 2)
    assert recalculated[1]["completion_percentage"] == 50.0


def test_projection_uses_cost_and_scope():
    service = PlanningService()
    history = [
        {"PV": 100, "EV": 80, "AC": 120, "done_points": 8},
        {"PV": 100, "EV": 90, "AC": 110, "done_points": 9},
    ]

    projection = service.calculate_release_projection(
        history=history,
        bac=1000,
        total_sprints=5,
        total_release_points=60,
        sprint_cost=100,
    )

    assert projection["eac"] >= 1000
    assert projection["projected_total_sprints"] >= 5
    assert projection["projected_remaining_sprints"] >= 0


def test_projection_without_history_returns_defaults():
    service = PlanningService()
    projection = service.calculate_release_projection([], 1000, 5, 50, 100)
    assert projection["eac"] == 1000
    assert projection["projected_total_sprints"] == 5


def test_planning_context_and_summary_include_added_points():
    service = PlanningService()
    workspace = {
        "releases": [{"points": 40, "sprints": 4}],
        "history": [
            {"plan_points": 10, "done_points": 8, "added_points": 4, "AC": 80, "PV": 100}
        ],
        "members": [{"salary": 1000, "hourly": 10, "quantity": 2}],
        "squad_members_from_file": [{"cargo": "Dev", "qtde": 3}],
        "squad_cost": 2000,
    }
    squad_info = {"members": [{"cargo": "Dev", "qtde": 3}], "total_cost": 2000}

    context = service.get_planning_context(workspace)
    summary = service.calculate_workspace_summary("Alpha", workspace, squad_info)

    assert context.total_points == 44
    assert summary["total_points"] == 44
    assert summary["history_count"] == 1
    assert summary["last_metrics"]["completion_percentage"] > 0
    assert context.current_component_count == 5


def test_component_count_supports_fractional_allocations():
    service = PlanningService()
    workspace = {
        "squad_members_from_file": [{"qtde": 0.5}, {"qtde": 1}],
        "members": [{"quantity": 0.25}, {"quantity": 1}],
    }

    assert service.calculate_component_count(workspace) == 2.75


def test_executive_status_considers_project_projection_delay():
    service = PlanningService()
    workspace = {
        "releases": [{"points": 40, "sprints": 4}],
        "history": [
            {"plan_points": 10, "done_points": 4, "added_points": 8, "AC": 80, "PV": 100},
            {"plan_points": 10, "done_points": 4, "added_points": 8, "AC": 80, "PV": 100},
        ],
        "members": [],
        "squad_members_from_file": [],
        "squad_cost": 2000,
    }
    squad_info = {"members": [], "total_cost": 2000}

    summary = service.calculate_workspace_summary("Alpha", workspace, squad_info)

    assert summary["projection"]["delay_sprints"] > 0
    assert "atrasado" in summary["status"].lower()

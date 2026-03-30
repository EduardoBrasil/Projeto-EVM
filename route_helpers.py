"""
route_helpers.py - Helpers compartilhados entre modulos de rota.
"""

from __future__ import annotations

import copy

from flask import current_app, session

from services import PlanningService
from storage import load_all_squads, load_all_workspaces, save_workspace


planning_service = PlanningService()


def normalize_releases(releases):
    return planning_service.normalize_releases(releases)


def parse_brazilian_float(value):
    return planning_service.parse_brazilian_float(value)


def get_current_username():
    return session.get("username")


def get_current_user_id():
    return session.get("user_id")


def is_authenticated():
    return bool(get_current_user_id() and get_current_username())


def get_squads_data():
    if not is_authenticated():
        return {}

    squads_data = session.get("squads_data")
    if squads_data:
        return squads_data

    squads_data = load_all_squads(
        current_app.config["DATABASE_PATH"],
        get_current_username(),
    )
    session["squads_data"] = squads_data
    session["squads_list"] = list(squads_data.keys())
    session.modified = True
    return squads_data


def get_squad_workspaces():
    if not is_authenticated():
        return {}

    workspaces = session.get("squad_workspaces")
    if workspaces is not None:
        return workspaces

    workspaces = load_all_workspaces(
        current_app.config["DATABASE_PATH"],
        get_current_username(),
    )
    session["squad_workspaces"] = workspaces
    session.modified = True
    return workspaces


def get_current_squad_name():
    return session.get("current_squad_name")


def ensure_current_squad_workspace():
    squad_name = get_current_squad_name()
    if not squad_name:
        return None

    squads_data = get_squads_data() or {}
    squad_info = squads_data.get(squad_name, {})
    base_members = copy.deepcopy(squad_info.get("members", []))
    base_total_cost = squad_info.get("total_cost", 0)

    workspaces = get_squad_workspaces()
    if squad_name not in workspaces:
        workspaces[squad_name] = {
            "members": [],
            "releases": [],
            "history": [],
            "squad_members_from_file": base_members,
            "squad_total_cost": base_total_cost,
        }
        session["squad_workspaces"] = workspaces
        save_workspace(
            current_app.config["DATABASE_PATH"],
            get_current_username(),
            squad_name,
            workspaces[squad_name],
        )
        session.modified = True

    workspace = workspaces[squad_name]
    workspace.setdefault("members", [])
    workspace.setdefault("releases", [])
    workspace.setdefault("history", [])
    workspace.setdefault("squad_members_from_file", copy.deepcopy(base_members))
    workspace.setdefault("squad_total_cost", base_total_cost)
    workspace.setdefault("infrastructure_cost", 0)
    workspace.setdefault("health_plan_cost", 0)
    workspace.setdefault("meal_allowance_cost", 0)
    workspace.setdefault("additional_costs_total", 0)
    return workspace


def save_current_squad_workspace(workspace):
    squad_name = get_current_squad_name()
    if not squad_name:
        return
    workspaces = get_squad_workspaces()
    workspaces[squad_name] = workspace
    session["squad_workspaces"] = workspaces
    save_workspace(
        current_app.config["DATABASE_PATH"],
        get_current_username(),
        squad_name,
        workspace,
    )
    session.modified = True


def get_or_create_workspace_for_squad(squad_name):
    current_squad = get_current_squad_name()
    session["current_squad_name"] = squad_name
    workspace = ensure_current_squad_workspace()
    session["current_squad_name"] = current_squad
    session.modified = True
    return workspace


def calculate_total_release_points(releases, history=None):
    return planning_service.calculate_total_release_points(releases, history)


def calculate_workspace_summary(squad_name, workspace, squad_info):
    return planning_service.calculate_workspace_summary(squad_name, workspace, squad_info)


def get_workspace_planning_context(workspace):
    context = planning_service.get_planning_context(workspace)
    return {
        "releases": context.releases,
        "squad_cost": context.squad_cost,
        "total_points": context.total_points,
        "total_sprints": context.total_sprints,
        "sprint_cost": context.sprint_cost,
        "bac": context.bac,
        "value_per_point": context.value_per_point,
        "history": context.history,
        "default_sprint_weeks": context.default_sprint_weeks,
        "current_component_count": context.current_component_count,
    }


def build_sprint_record(
    sprint_number,
    planned_points,
    earned_points,
    added_points,
    actual_cost,
    value_per_point,
    cumulative_done_points,
    total_release_points,
    planned_value=None,
    sprint_weeks=2.0,
    component_count=0,
    squad_cost=0,
):
    return planning_service.build_sprint_record(
        sprint_number=sprint_number,
        planned_points=planned_points,
        earned_points=earned_points,
        added_points=added_points,
        actual_cost=actual_cost,
        value_per_point=value_per_point,
        cumulative_done_points=cumulative_done_points,
        total_release_points=total_release_points,
        planned_value=planned_value,
        sprint_weeks=sprint_weeks,
        component_count=component_count,
        squad_cost=squad_cost,
    )


def recalculate_history(history, value_per_point, total_release_points, squad_cost=0, component_count=0):
    return planning_service.recalculate_history(
        history,
        value_per_point,
        total_release_points,
        squad_cost,
        component_count,
    )


def calculate_release_projection(history, bac, total_sprints, total_release_points=0, sprint_cost=0):
    return planning_service.calculate_release_projection(
        history,
        bac,
        total_sprints,
        total_release_points,
        sprint_cost,
    )


def get_planning_totals(workspace):
    return planning_service.calculate_planning_totals(workspace)

"""
route_helpers.py - Helpers compartilhados entre modulos de rota.
"""

from __future__ import annotations

import copy

from flask import session

from services import PlanningService


planning_service = PlanningService()


def normalize_releases(releases):
    return planning_service.normalize_releases(releases)


def parse_brazilian_float(value):
    return planning_service.parse_brazilian_float(value)


def get_squad_workspaces():
    return session.setdefault("squad_workspaces", {})


def get_current_squad_name():
    return session.get("current_squad_name")


def ensure_current_squad_workspace():
    squad_name = get_current_squad_name()
    if not squad_name:
        return None

    squads_data = session.get("squads_data", {})
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
        session.modified = True

    workspace = workspaces[squad_name]
    workspace.setdefault("members", [])
    workspace.setdefault("releases", [])
    workspace.setdefault("history", [])
    workspace.setdefault("squad_members_from_file", copy.deepcopy(base_members))
    workspace.setdefault("squad_total_cost", base_total_cost)
    return workspace


def save_current_squad_workspace(workspace):
    squad_name = get_current_squad_name()
    if not squad_name:
        return
    workspaces = get_squad_workspaces()
    workspaces[squad_name] = workspace
    session["squad_workspaces"] = workspaces
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
    )


def recalculate_history(history, value_per_point, total_release_points):
    return planning_service.recalculate_history(history, value_per_point, total_release_points)


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

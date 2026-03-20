"""
services.py - Servicos de planejamento e metricas do projeto.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from models import EVMCalculator


@dataclass
class PlanningContext:
    """Snapshot consolidado do planejamento."""

    releases: list
    squad_cost: float
    total_points: float
    total_sprints: int
    sprint_cost: float
    bac: float
    value_per_point: float
    history: list


class SprintMetricsStrategy(ABC):
    """Strategy para calculo de metricas da sprint."""

    @abstractmethod
    def calculate_metrics(
        self,
        planned_points: float,
        earned_points: float,
        actual_cost: float,
        value_per_point: float,
        planned_value: float | None = None,
    ) -> dict:
        """Retorna as metricas da sprint."""


class PointsBasedMetricsStrategy(SprintMetricsStrategy):
    """Calcula metricas com base no valor por ponto."""

    def calculate_metrics(
        self,
        planned_points: float,
        earned_points: float,
        actual_cost: float,
        value_per_point: float,
        planned_value: float | None = None,
    ) -> dict:
        return EVMCalculator.calculate_sprint_metrics(
            planned_points=planned_points,
            earned_points=earned_points,
            actual_cost=actual_cost,
            value_per_point=value_per_point,
        )


class PlannedValueMetricsStrategy(SprintMetricsStrategy):
    """Calcula metricas quando o PV e informado manualmente."""

    def calculate_metrics(
        self,
        planned_points: float,
        earned_points: float,
        actual_cost: float,
        value_per_point: float,
        planned_value: float | None = None,
    ) -> dict:
        pv = planned_value or 0
        completion_ratio = (earned_points / planned_points) if planned_points > 0 else 0
        ev = pv * completion_ratio
        cv = ev - actual_cost
        sv = ev - pv
        cpi = ev / actual_cost if actual_cost > 0 else 0
        spi = ev / pv if pv > 0 else 0
        return {
            "PV": pv,
            "EV": ev,
            "AC": actual_cost,
            "CV": cv,
            "SV": sv,
            "CPI": cpi,
            "SPI": spi,
            "status": EVMCalculator.get_status(cpi, spi),
        }


class SprintMetricsStrategyFactory:
    """Factory Method para a estrategia de metricas."""

    @staticmethod
    def create(planned_value: float | None) -> SprintMetricsStrategy:
        if planned_value is None:
            return PointsBasedMetricsStrategy()
        return PlannedValueMetricsStrategy()


class PlanningService:
    """Facade para regras de planejamento e EVM."""

    def __init__(self, strategy_factory: SprintMetricsStrategyFactory | None = None):
        self.strategy_factory = strategy_factory or SprintMetricsStrategyFactory()

    def normalize_releases(self, releases):
        if not releases:
            return []

        normalized = []
        for release in releases:
            if isinstance(release, dict):
                normalized.append(release)
            else:
                normalized.append({"points": float(release), "sprints": 5})
        return normalized

    def parse_brazilian_float(self, value):
        if isinstance(value, (int, float)):
            return float(value)
        if not isinstance(value, str):
            return 0.0

        value = value.strip()
        if "." not in value and "," not in value:
            try:
                return float(value)
            except ValueError:
                return 0.0

        if "." in value and "," in value:
            try:
                return float(value.replace(".", "").replace(",", "."))
            except ValueError:
                return 0.0

        if "," in value:
            try:
                return float(value.replace(",", "."))
            except ValueError:
                return 0.0

        try:
            return float(value)
        except ValueError:
            return 0.0

    def calculate_total_release_points(self, releases, history=None):
        base_points = sum(release.get("points", 0) for release in releases)
        added_points = sum(
            float(record.get("added_points", 0) or 0) for record in (history or [])
        )
        return base_points + added_points

    def build_sprint_record(
        self,
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
        strategy = self.strategy_factory.create(planned_value)
        metrics = strategy.calculate_metrics(
            planned_points=planned_points,
            earned_points=earned_points,
            actual_cost=actual_cost,
            value_per_point=value_per_point,
            planned_value=planned_value,
        )
        completion_percentage = (
            (cumulative_done_points / total_release_points) * 100
            if total_release_points > 0
            else 0
        )
        return {
            "sprint_no": sprint_number,
            "plan_points": planned_points,
            "done_points": earned_points,
            "added_points": added_points,
            "PV": metrics["PV"],
            "EV": metrics["EV"],
            "AC": metrics["AC"],
            "CV": metrics["CV"],
            "SV": metrics["SV"],
            "CPI": round(metrics["CPI"], 2),
            "SPI": round(metrics["SPI"], 2),
            "status": metrics["status"],
            "completion_percentage": round(completion_percentage, 2),
        }

    def recalculate_history(self, history, value_per_point, total_release_points):
        recalculated_history = []
        cumulative_done_points = 0.0
        cumulative_added_points = 0.0
        total_added_points = sum(float(record.get("added_points", 0) or 0) for record in history)
        base_total_release_points = max(total_release_points - total_added_points, 0)

        for index, record in enumerate(history, start=1):
            planned_points = float(record.get("plan_points", 0) or 0)
            done_points = float(record.get("done_points", 0) or 0)
            added_points = float(record.get("added_points", 0) or 0)
            actual_cost = self.parse_brazilian_float(record.get("AC", 0))
            planned_value = (
                self.parse_brazilian_float(record.get("PV", 0))
                if record.get("PV") is not None
                else None
            )

            cumulative_done_points += done_points
            cumulative_added_points += added_points
            current_total_release_points = base_total_release_points + cumulative_added_points
            recalculated_history.append(
                self.build_sprint_record(
                    sprint_number=index,
                    planned_points=planned_points,
                    earned_points=done_points,
                    added_points=added_points,
                    actual_cost=actual_cost,
                    value_per_point=value_per_point,
                    cumulative_done_points=cumulative_done_points,
                    total_release_points=current_total_release_points,
                    planned_value=planned_value,
                )
            )
        return recalculated_history

    def calculate_release_projection(
        self,
        history,
        bac,
        total_sprints,
        total_release_points=0,
        sprint_cost=0,
    ):
        if not history:
            return {
                "cpi": 0,
                "spi": 0,
                "eac": bac,
                "cost_variance_at_completion": 0,
                "projected_total_sprints": total_sprints,
                "delay_sprints": 0,
                "planned_remaining_sprints": total_sprints,
                "projected_remaining_sprints": total_sprints,
            }

        cumulative_ac = sum(record.get("AC", 0) for record in history)
        cumulative_ev = sum(record.get("EV", 0) for record in history)
        cumulative_pv = sum(record.get("PV", 0) for record in history)
        total_done_points = sum(record.get("done_points", 0) for record in history)
        executed_sprints = len(history)

        cpi = (cumulative_ev / cumulative_ac) if cumulative_ac > 0 else 0
        spi = (cumulative_ev / cumulative_pv) if cumulative_pv > 0 else 0

        eac_cpi = (bac / cpi) if cpi > 0 else bac
        projected_total_sprints_spi = (total_sprints / spi) if spi > 0 else total_sprints
        average_velocity = (total_done_points / executed_sprints) if executed_sprints > 0 else 0
        remaining_points = max(total_release_points - total_done_points, 0)
        projected_remaining_sprints_velocity = (
            remaining_points / average_velocity
            if average_velocity > 0
            else max(total_sprints - executed_sprints, 0)
        )
        projected_total_sprints_velocity = executed_sprints + projected_remaining_sprints_velocity
        projected_total_sprints = max(
            projected_total_sprints_spi,
            projected_total_sprints_velocity,
        )
        eac_schedule = projected_total_sprints * sprint_cost if sprint_cost > 0 else bac
        eac = max(eac_cpi, eac_schedule)
        delay_sprints = projected_total_sprints - total_sprints if projected_total_sprints > 0 else 0
        remaining_sprints = max(total_sprints - executed_sprints, 0)
        projected_remaining_sprints = (
            max(projected_total_sprints - executed_sprints, 0)
            if projected_total_sprints > 0
            else 0
        )

        return {
            "cpi": round(cpi, 2),
            "spi": round(spi, 2),
            "eac": round(eac, 2),
            "cost_variance_at_completion": round(eac - bac, 2),
            "projected_total_sprints": round(projected_total_sprints, 2),
            "delay_sprints": round(delay_sprints, 2),
            "planned_remaining_sprints": remaining_sprints,
            "projected_remaining_sprints": round(projected_remaining_sprints, 2),
        }

    def calculate_planning_totals(self, workspace):
        releases = self.normalize_releases(workspace.get("releases", []))
        squad_cost = workspace.get("squad_cost", 0)
        total_release_sprints = sum(release.get("sprints", 0) for release in releases)
        sprint_cost = squad_cost / 2 if squad_cost > 0 else 0
        bac = sprint_cost * total_release_sprints
        total_release_points = self.calculate_total_release_points(
            releases,
            workspace.get("history", []),
        )
        value_per_point = bac / total_release_points if total_release_points > 0 else 0
        return {
            "releases": releases,
            "total_release_points": total_release_points,
            "total_release_sprints": total_release_sprints,
            "sprint_cost": sprint_cost,
            "bac": bac,
            "value_per_point": value_per_point,
        }

    def get_planning_context(self, workspace):
        totals = self.calculate_planning_totals(workspace)
        history = self.recalculate_history(
            workspace.get("history", []),
            totals["value_per_point"],
            totals["total_release_points"],
        )
        return PlanningContext(
            releases=totals["releases"],
            squad_cost=workspace.get("squad_cost", 0),
            total_points=totals["total_release_points"],
            total_sprints=totals["total_release_sprints"],
            sprint_cost=totals["sprint_cost"],
            bac=totals["bac"],
            value_per_point=totals["value_per_point"],
            history=history,
        )

    def calculate_workspace_summary(self, squad_name, workspace, squad_info):
        file_members = workspace.get("squad_members_from_file", squad_info.get("members", []))
        members = workspace.get("members", [])
        manual_cost = sum(
            member.get("salary", 0) + 160 * member.get("hourly", 0)
            for member in members
        )
        base_total_cost = squad_info.get("total_cost", 0)
        squad_cost = workspace.get("squad_cost", base_total_cost + manual_cost)
        context = self.get_planning_context({**workspace, "squad_cost": squad_cost})
        last_metrics = context.history[-1] if context.history else None
        projection = self.calculate_release_projection(
            context.history,
            context.bac,
            context.total_sprints,
            context.total_points,
            context.sprint_cost,
        )
        return {
            "name": squad_name,
            "members_from_file": len(file_members),
            "manual_members": len(members),
            "squad_cost": squad_cost,
            "sprint_cost": context.sprint_cost,
            "releases_count": len(context.releases),
            "total_points": context.total_points,
            "total_sprints": context.total_sprints,
            "history_count": len(context.history),
            "bac": context.bac,
            "completion_percentage": last_metrics.get("completion_percentage", 0) if last_metrics else 0,
            "status": last_metrics.get("status", "Não iniciado") if last_metrics else "Não iniciado",
            "last_metrics": last_metrics,
            "projection": projection,
        }


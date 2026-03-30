"""
formula_helpers.py - Regras compartilhadas para custos e duracao.
"""

from __future__ import annotations


DEFAULT_MONTHLY_HOURS = 160.0
DEFAULT_WEEKS_PER_MONTH = 4.0


def _to_non_negative_float(value, default=0.0):
    try:
        return max(float(value or 0), 0.0)
    except (TypeError, ValueError):
        return default


def calculate_manual_member_monthly_cost(
    salary,
    hourly_rate,
    quantity=1.0,
    monthly_hours=DEFAULT_MONTHLY_HOURS,
):
    salary_value = _to_non_negative_float(salary)
    hourly_value = _to_non_negative_float(hourly_rate)
    quantity_value = _to_non_negative_float(quantity, 1.0)
    return (salary_value + (hourly_value * monthly_hours)) * quantity_value


def calculate_file_member_monthly_cost(
    quantity,
    hourly_rate,
    monthly_hours=DEFAULT_MONTHLY_HOURS,
):
    quantity_value = _to_non_negative_float(quantity, 1.0)
    hourly_value = _to_non_negative_float(hourly_rate)
    return quantity_value * hourly_value * monthly_hours


def calculate_sprint_cost_from_monthly_cost(
    monthly_cost,
    sprint_weeks=2.0,
    weeks_per_month=DEFAULT_WEEKS_PER_MONTH,
):
    monthly_cost_value = _to_non_negative_float(monthly_cost)
    sprint_weeks_value = _to_non_negative_float(sprint_weeks)
    weeks_per_month_value = _to_non_negative_float(weeks_per_month)

    if monthly_cost_value <= 0 or sprint_weeks_value <= 0 or weeks_per_month_value <= 0:
        return 0.0

    return monthly_cost_value * (sprint_weeks_value / weeks_per_month_value)

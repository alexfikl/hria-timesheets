"""Turn submitted form data into a :class:`Timesheet` and template context.

Pure functions with no FastAPI dependency, so they can be unit tested directly.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from timesheet import intervals
from timesheet.holidays import ro_holidays, weekday_name, weekday_short
from timesheet.model import (
    DEFAULT_LEADER,
    MAX_CONTRACTS,
    Cell,
    Project,
    Timesheet,
    daily_total,
)
from timesheet.template import MONTHS_RO


def _int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "on", "da", "yes")


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _build_days(year: int, month: int, count: int, cells: dict) -> list[dict]:
    holidays = ro_holidays(year)
    rows: list[dict] = []
    days_in_month = Timesheet(year=year, month=month).days_in_month
    for day in range(1, days_in_month + 1):
        current = date(year, month, day)
        weekend = current.weekday() >= 5
        if current in holidays:
            css = "holiday"
        elif weekend:
            css = "weekend"
        else:
            css = ""

        hours: list[str] = []
        intervals_out: list[str] = []
        for index in range(count):
            cell = cells.get((day, index))
            hours.append(f"{cell.hours:g}" if cell and cell.hours else "")
            intervals_out.append(cell.interval if cell else "")
        rows.append(
            {
                "day": day,
                "weekday": weekday_short(current),
                "label": holidays.get(current) or weekday_name(current),
                "css": css,
                "blocked": weekend,
                "hours": hours,
                "intervals": intervals_out,
            }
        )
    return rows


def build_context(
    form: Mapping[str, Any], today: date | None = None
) -> tuple[Timesheet, dict]:
    today = today or date.today()
    month = _clamp(_int(form.get("month"), today.month), 1, 12)
    year = _clamp(_int(form.get("year"), today.year), 2000, 2100)
    count = _clamp(_int(form.get("count"), 1), 1, MAX_CONTRACTS)
    gray = _bool(form.get("gray"), True)

    contracts = []
    projects = []
    for index in range(count):
        contract = _text(form.get(f"contract_{index}"))
        project_name = _text(form.get(f"project_{index}"))
        raw_max = _text(form.get(f"max_hours_{index}")) if index >= 1 else ""
        max_hours = None
        if raw_max:
            try:
                max_hours = float(raw_max.replace(",", "."))
            except ValueError:
                max_hours = None
        contracts.append(
            {"contract": contract, "project": project_name, "max_hours": raw_max}
        )
        # Contract 1 is always the NB main job; it has no max hours.
        projects.append(
            Project(
                contract=contract,
                project=project_name,
                is_main=(index == 0),
                max_hours=max_hours,
            )
        )

    timesheet = Timesheet(
        family_name=_text(form.get("family_name")),
        given_name=_text(form.get("given_name")),
        cnp=_text(form.get("cnp")),
        function=_text(form.get("function")),
        euro_rate=_text(form.get("euro_rate")),
        ron_rate=_text(form.get("ron_rate")),
        leader=DEFAULT_LEADER,
        year=year,
        month=month,
        projects=projects,
    )

    for day in range(1, timesheet.days_in_month + 1):
        # Weekends cannot be filled; ignore anything submitted for them.
        if date(year, month, day).weekday() >= 5:
            continue
        for index in range(count):
            raw = _text(form.get(f"interval_{day}_{index}"))
            if not raw:
                continue
            try:
                ranges = intervals.parse(raw)
            except ValueError:
                timesheet.cells[(day, index)] = Cell(hours=0.0, interval=raw)
                continue
            timesheet.cells[(day, index)] = Cell(
                hours=round(intervals.total_hours(ranges), 2),
                interval=intervals.format(ranges),
            )

    context = {
        "family_name": timesheet.family_name,
        "given_name": timesheet.given_name,
        "cnp": timesheet.cnp,
        "function": timesheet.function,
        "euro_rate": timesheet.euro_rate,
        "ron_rate": timesheet.ron_rate,
        "leader": timesheet.leader,
        "month": month,
        "year": year,
        "count": count,
        "gray": gray,
        "months": MONTHS_RO,
        "max_contracts": MAX_CONTRACTS,
        "contracts": contracts,
        "days": _build_days(year, month, count, timesheet.cells),
        "total": sum(
            daily_total(timesheet, day)
            for day in range(1, timesheet.days_in_month + 1)
        ),
        "errors": [],
        "warnings": [],
    }
    return timesheet, context

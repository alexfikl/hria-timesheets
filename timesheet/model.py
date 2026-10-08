# SPDX-FileCopyrightText: 2026 Alexandru Fikl <alexfikl@gmail.com>
# SPDX-License-Identifier: MIT

"""In-memory model for a timesheet plus its validation rules."""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field

from . import intervals

DAILY_HOUR_LIMIT = 12
MAX_CONTRACTS = 12

# The leader/partner is always the same for this tool's use, so it is fixed.
DEFAULT_LEADER = "Prof. Dr. Viorel NEGRU"

CONTRACT_BASE = "Contract Individual de Muncă/Act administrativ de numire. Nr."

# BNR reference rate used to convert the euro limit into lei.
EUR_RON_RATE = 4.9765


@dataclass
class Project:
    """One contract/grant occupying a pair of columns in the form."""

    contract: str = ""
    project: str = ""
    is_main: bool = False
    # Monthly hour cap; only meaningful for non-main (non-NB) contracts.
    max_hours: float | None = None

    @property
    def header(self) -> str:
        text = f"{CONTRACT_BASE} {self.contract}".strip()
        if self.project:
            text += f" ({self.project})"
        if self.is_main:
            text += " (NB)"
        return text


@dataclass
class Cell:
    hours: float = 0.0
    interval: str = ""


@dataclass
class Timesheet:
    family_name: str = ""
    given_name: str = ""
    cnp: str = ""
    function: str = ""
    euro_rate: str = ""
    ron_rate: str = ""
    leader: str = ""
    year: int = 2026
    month: int = 1
    projects: list[Project] = field(default_factory=list)
    # (day-of-month, project index) -> Cell
    cells: dict[tuple[int, int], Cell] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        family = (self.family_name or "").strip()
        given = (self.given_name or "").strip()
        return f"{family.upper()} {given.title()}".strip()

    @property
    def days_in_month(self) -> int:
        return calendar.monthrange(self.year, self.month)[1]


@dataclass
class Issue:
    day: int | None
    level: str  # "error" | "warning"
    message: str


def daily_total(ts: Timesheet, day: int) -> float:
    return sum(
        float(cell.hours or 0.0)
        for (cell_day, _), cell in ts.cells.items()
        if cell_day == day
    )


def validate(ts: Timesheet) -> list[Issue]:
    """Return every error/warning found in ``ts`` (empty means clean)."""
    issues: list[Issue] = []
    parsed: dict[tuple[int, int], list[intervals.TimeRange]] = {}

    for (day, project_index), cell in ts.cells.items():
        text = (cell.interval or "").strip()
        if not text:
            continue
        try:
            ranges = intervals.parse(text)
        except ValueError as exc:
            issues.append(
                Issue(
                    day,
                    "error",
                    f"Ziua {day}, proiect {project_index + 1}: {exc}.",
                )
            )
            continue
        parsed[(day, project_index)] = ranges

        # Intervals inside a single cell must not overlap either.
        same_cell_overlap = any(
            intervals.overlap(ranges[i], ranges[j])
            for i in range(len(ranges))
            for j in range(i + 1, len(ranges))
        )
        if same_cell_overlap:
            issues.append(
                Issue(
                    day,
                    "error",
                    f"Ziua {day}, proiect {project_index + 1}: "
                    "intervalele se suprapun.",
                )
            )

    for day in range(1, ts.days_in_month + 1):
        total = sum(
            intervals.total_hours(parsed.get((day, index), []))
            for index in range(len(ts.projects))
        )
        if total > DAILY_HOUR_LIMIT:
            issues.append(
                Issue(
                    day,
                    "error",
                    f"Ziua {day}: {total:g} h depășesc limita de "
                    f"{DAILY_HOUR_LIMIT} h/zi.",
                )
            )

    for day in range(1, ts.days_in_month + 1):
        per_project = [
            (project_index, ranges)
            for (cell_day, project_index), ranges in parsed.items()
            if cell_day == day and ranges
        ]
        for i in range(len(per_project)):
            for j in range(i + 1, len(per_project)):
                index_a, ranges_a = per_project[i]
                index_b, ranges_b = per_project[j]
                if any(intervals.overlap(a, b) for a in ranges_a for b in ranges_b):
                    issues.append(
                        Issue(
                            day,
                            "error",
                            f"Ziua {day}: intervalele proiectelor "
                            f"{index_a + 1} și {index_b + 1} se suprapun.",
                        )
                    )

    # Non-NB contracts must declare a monthly maximum and stay within it.
    for index in range(1, len(ts.projects)):
        project = ts.projects[index]
        total = sum(
            intervals.total_hours(parsed.get((day, index), []))
            for day in range(1, ts.days_in_month + 1)
        )
        if project.max_hours is None or project.max_hours <= 0:
            issues.append(
                Issue(None, "error", f"Proiect {index + 1}: completați orele maxime.")
            )
        elif total > project.max_hours + 1e-9:
            issues.append(
                Issue(
                    None,
                    "error",
                    f"Proiect {index + 1}: {total:g} h depășesc maximul de "
                    f"{project.max_hours:g} h.",
                )
            )

    return issues

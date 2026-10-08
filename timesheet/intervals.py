# SPDX-FileCopyrightText: 2026 Alexandru Fikl <alexfikl@gmail.com>
# SPDX-License-Identifier: MIT

"""Parsing and normalising of the free-text time intervals used by Anexa 1.

The form stores intervals as text such as ``"8:00-12:00; 16:00-20:00"``. Ranges
may be separated by semicolons, commas, whitespace or newlines. They are parsed
into minute ranges so hours can be counted, overlaps detected and slots marked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_RANGE_RE = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")
MINUTES_PER_DAY = 24 * 60


@dataclass(frozen=True)
class TimeRange:
    """A half-open interval ``[start, end)`` in minutes from midnight."""

    start: int
    end: int

    @property
    def minutes(self) -> int:
        return self.end - self.start


def parse(text: object) -> list[TimeRange]:
    """Parse ``text`` into ranges, raising :class:`ValueError` if malformed."""
    if text is None:
        return []
    text = str(text).strip()
    if not text:
        return []

    ranges: list[TimeRange] = []
    for match in _RANGE_RE.finditer(text):
        start_h, start_m, end_h, end_m = (int(g) for g in match.groups())
        if (
            start_h > 24
            or end_h > 24
            or start_m > 59
            or end_m > 59
            or (start_h == 24 and start_m > 0)
            or (end_h == 24 and end_m > 0)
        ):
            raise ValueError(f"oră invalidă în {match.group(0)!r}")
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m
        if end <= start:
            raise ValueError(f"interval inversat sau gol: {match.group(0)!r}")
        ranges.append(TimeRange(start, end))

    leftover = re.sub(r"[\s,;]+", "", _RANGE_RE.sub("", text))
    if leftover:
        raise ValueError(f"text nerecunoscut: {leftover!r}")
    if not ranges:
        raise ValueError("niciun interval găsit")
    ranges.sort(key=lambda r: (r.start, r.end))
    return ranges


def format(ranges: list[TimeRange]) -> str:
    """Render ranges back to a normalised text form (no leading zero hour)."""

    def hm(minutes: int) -> str:
        hour, minute = divmod(minutes, 60)
        return f"{hour}:{minute:02d}"

    return "; ".join(f"{hm(r.start)}-{hm(r.end)}" for r in ranges)


def total_hours(ranges: list[TimeRange]) -> float:
    return sum(r.minutes for r in ranges) / 60


def overlap(a: TimeRange, b: TimeRange) -> bool:
    return a.start < b.end and b.start < a.end

# SPDX-FileCopyrightText: 2026 Alexandru Fikl <alexfikl@gmail.com>
# SPDX-License-Identifier: MIT

"""Romanian public holidays and weekday helpers.

Implemented directly (no third-party dependency) so the app deploys with a
minimal dependency set. The Orthodox Easter computation and the +13 day Julian
offset are valid for 1900-2099, which covers this tool's use.
"""

from __future__ import annotations

from datetime import date, timedelta

WEEKDAYS_RO = [
    "luni",
    "marți",
    "miercuri",
    "joi",
    "vineri",
    "sâmbătă",
    "duminică",
]

WEEKDAYS_SHORT = ["Lu", "Ma", "Mi", "Jo", "Vi", "Sâ", "Du"]


def orthodox_easter(year: int) -> date:
    """Gregorian date of Orthodox Easter for ``year`` (1900-2099)."""
    a = year % 4
    b = year % 7
    c = year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day = ((d + e + 114) % 31) + 1
    # The algorithm yields a Julian-calendar date; +13 days gives Gregorian.
    return date(year, month, day) + timedelta(days=13)


def ro_holidays(year: int) -> dict[date, str]:
    """Map non-working Romanian public holidays to a human-readable name."""
    easter = orthodox_easter(year)
    pentecost = easter + timedelta(days=49)  # Rusalii

    holidays: dict[date, str] = {
        date(year, 1, 1): "Anul Nou",
        date(year, 1, 2): "Anul Nou",
        date(year, 1, 24): "Unirea Principatelor",
        easter - timedelta(days=2): "Vinerea Mare",
        easter: "Paștele",
        easter + timedelta(days=1): "Paștele",
        date(year, 5, 1): "Ziua Muncii",
        date(year, 6, 1): "Ziua Copilului",
        pentecost: "Rusalii",
        pentecost + timedelta(days=1): "Rusalii",
        date(year, 8, 15): "Adormirea Maicii Domnului",
        date(year, 11, 30): "Sfântul Andrei",
        date(year, 12, 1): "Ziua Națională",
        date(year, 12, 25): "Crăciunul",
        date(year, 12, 26): "Crăciunul",
    }
    if year >= 2024:
        holidays[date(year, 1, 6)] = "Boboteaza"
        holidays[date(year, 1, 7)] = "Sfântul Ioan Botezătorul"
    return holidays


def weekday_name(value: date) -> str:
    return WEEKDAYS_RO[value.weekday()]


def weekday_short(value: date) -> str:
    return WEEKDAYS_SHORT[value.weekday()]


def is_weekend(value: date) -> bool:
    return value.weekday() >= 5

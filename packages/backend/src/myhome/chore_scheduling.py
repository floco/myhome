"""Chore due-date advancement, shared by the REST /complete routes and the MCP complete_chore tool."""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta

from .models_chores import Chore

WEEKDAY_NAMES: dict[str, int] = {
    "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4,
    "friday": 5, "saturday": 6, "sunday": 7,
    "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7,
}


def add_months(dt: datetime, months: int) -> datetime:
    total = dt.month - 1 + months
    year = dt.year + total // 12
    month = total % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def add_years(dt: datetime, years: int) -> datetime:
    try:
        return dt.replace(year=dt.year + years)
    except ValueError:
        return dt.replace(year=dt.year + years, month=3, day=1)


def to_weekday_num(d: object) -> int:
    """Convert a Donetick weekday value (int or name string) to a 1-based int."""
    if isinstance(d, str):
        name = d.lower().strip()
        if name in WEEKDAY_NAMES:
            return WEEKDAY_NAMES[name]
        return int(name)
    return int(d)


def next_due_from_schedule(chore: Chore, from_dt: datetime) -> datetime:
    ft = chore.frequencyType
    freq = chore.frequency
    meta: dict = chore.frequencyMetadata or {}
    unit = meta.get("unit", "days")
    if ft == "day_of_the_month":
        allowed_months: set[int] = set(meta.get("months") or range(1, 13))
        next_m = add_months(from_dt.replace(day=1), 1)
        for _ in range(12):
            if next_m.month in allowed_months:
                break
            next_m = add_months(next_m, 1)
        day = min(freq, calendar.monthrange(next_m.year, next_m.month)[1])
        return next_m.replace(day=day)
    if ft == "days_of_the_week":
        days = sorted((to_weekday_num(d) - 1) % 7 for d in (meta.get("days") or []))
        if not days:
            return from_dt + timedelta(weeks=1)
        wd = from_dt.weekday()
        for d in days:
            if d > wd:
                return from_dt + timedelta(days=d - wd)
        return from_dt + timedelta(days=7 - wd + days[0])
    if ft == "weekly":
        return from_dt + timedelta(weeks=freq)
    if ft in ("monthly", "month"):
        return add_months(from_dt, freq)
    if ft in ("yearly", "year"):
        return add_years(from_dt, freq)
    if ft == "interval":
        if unit == "years":
            return add_years(from_dt, freq)
        if unit == "months":
            return add_months(from_dt, freq)
        if unit == "weeks":
            return from_dt + timedelta(weeks=freq)
        return from_dt + timedelta(days=freq)
    return from_dt + timedelta(days=chore.periodDays)

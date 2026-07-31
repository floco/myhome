"""Chore due-date advancement, shared by the REST /complete routes and the MCP complete_chore tool."""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta

from .models_chores import Chore, CompletionRecord

WEEKDAY_NAMES: dict[str, int] = {
    "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4,
    "friday": 5, "saturday": 6, "sunday": 7,
    "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7,
}

MONTH_NAMES: dict[str, int] = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
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


def to_month_num(m: object) -> int:
    """Convert a Donetick month value (int, or full/abbreviated name string) to a 1-based int.

    Donetick's own `FrequencyMetadata.Months` field is `[]*string` of full
    English month names (e.g. "March"), compared case-insensitively -- never
    ints -- so imported `day_of_the_month` chores need this same conversion
    the scheduler already does for weekday names via `to_weekday_num`.
    """
    if isinstance(m, str):
        name = m.lower().strip()
        if name in MONTH_NAMES:
            return MONTH_NAMES[name]
        return int(name)
    return int(m)


def adaptive_period_days(chore: Chore, completions_for_chore: list[CompletionRecord]) -> float:
    """Average of the gaps (in days) between the chore's last 5 completions.

    Falls back to the chore's current `periodDays` (its seed value at
    creation, or whatever this function last computed it to be) when there
    are fewer than 2 completions to derive a gap from.
    """
    if len(completions_for_chore) < 2:
        return chore.periodDays
    ordered = sorted(completions_for_chore, key=lambda c: c.completedAt)
    timestamps = [datetime.fromisoformat(c.completedAt.replace("Z", "+00:00")) for c in ordered]
    gaps = [(timestamps[i] - timestamps[i - 1]).total_seconds() / 86400 for i in range(1, len(timestamps))]
    recent = gaps[-5:]
    return sum(recent) / len(recent)


def next_due_from_schedule(chore: Chore, from_dt: datetime, completions: list[CompletionRecord] | None = None) -> datetime:
    ft = chore.frequencyType
    freq = chore.frequency
    meta: dict = chore.frequencyMetadata or {}
    unit = meta.get("unit", "days")
    if ft == "day_of_the_month":
        raw_months = meta.get("months")
        allowed_months: set[int] = {to_month_num(m) for m in raw_months} if raw_months else set(range(1, 13))
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
    if ft == "daily":
        return from_dt + timedelta(days=1)
    # Donetick's own scheduler always advances "daily"/"weekly"/"monthly"/"yearly"
    # chores by exactly 1 unit and ignores `frequency` for them entirely -- that
    # multiplier only applies to the "interval" type (see upstream
    # internal/chore/scheduler.go). A chore imported with a stray `frequency`
    # value on one of these literal types must not be multiplied.
    if ft == "weekly":
        return from_dt + timedelta(weeks=1)
    if ft in ("monthly", "month"):
        return add_months(from_dt, 1)
    if ft in ("yearly", "year"):
        return add_years(from_dt, 1)
    if ft == "interval":
        if unit == "years":
            return add_years(from_dt, freq)
        if unit == "months":
            return add_months(from_dt, freq)
        if unit == "weeks":
            return from_dt + timedelta(weeks=freq)
        return from_dt + timedelta(days=freq)
    if ft == "adaptive":
        return from_dt + timedelta(days=adaptive_period_days(chore, completions or []))
    return from_dt + timedelta(days=chore.periodDays)

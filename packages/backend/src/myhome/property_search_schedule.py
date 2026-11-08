# packages/backend/src/myhome/property_search_schedule.py
"""When is a property search due? Evaluated lazily by the runner's claim."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .backup_scheduler import _should_run_today
from .models_property_search import PropertySearch, PropertySearchRun

MAX_USAGE_LIMIT_RETRIES = 3
_LOOKBACK_DAYS = 62


def _local_tz():
    name = os.environ.get("TZ")
    if not name:
        return timezone.utc
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc


def local_now() -> datetime:
    return datetime.now(_local_tz())


def _parse(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def latest_slot(s: PropertySearch, now: datetime) -> datetime | None:
    hour, minute = (int(x) for x in s.time.split(":"))
    for back in range(_LOOKBACK_DAYS + 1):
        day = now - timedelta(days=back)
        slot = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if slot > now or not _should_run_today(s.frequency, s.dayOfWeek, s.dayOfMonth, day):
            continue
        return slot if slot >= _parse(s.createdAt) else None
    return None


def is_due(s: PropertySearch, runs_for_slot: list[PropertySearchRun], now: datetime) -> tuple[bool, str | None]:
    if s.runRequestedAt:
        slot_key = f"manual:{s.runRequestedAt}"
    else:
        if not s.enabled:
            return (False, None)
        slot = latest_slot(s, now)
        if slot is None:
            return (False, None)
        slot_key = slot.isoformat()
    same = [r for r in runs_for_slot if r.slot == slot_key]
    if any(r.status in ("succeeded", "failed", "running") for r in same):
        return (False, None)
    if sum(1 for r in same if r.status == "usage_limited") >= MAX_USAGE_LIMIT_RETRIES:
        return (False, None)
    return (True, slot_key)

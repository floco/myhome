# packages/backend/src/myhome/property_search_cleanup.py
"""Daily retention cleanup for the property-search suggestions inbox.

Deletes untriaged (``new``) and ``rejected`` suggestions older than the
home's retention period, and run history older than 90 days. Never touches
``pinned``/``accepted`` suggestions or the ``property_seen`` ledger, so a
cleaned-up listing is still never suggested again.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from . import persistence_property_search as ps
from .persistence_homes import load_homes
from .property_search_schedule import local_now

log = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60
RUN_HISTORY_DAYS = 90

_last_cleanup_date: str | None = None


def cleanup_home(home_id: str, now: datetime) -> int:
    retention = ps.load_config(home_id).retentionDays
    deleted = ps.delete_suggestions_older_than(
        home_id, ["new", "rejected"], (now - timedelta(days=retention)).isoformat(),
    )
    ps.delete_runs_older_than(home_id, (now - timedelta(days=RUN_HISTORY_DAYS)).isoformat())
    return deleted


def run_cleanup_once(now: datetime | None = None) -> bool:
    """Clean every home at most once per local date. Returns True if it ran."""
    global _last_cleanup_date
    now = now or local_now()
    today = now.date().isoformat()
    if _last_cleanup_date == today:
        return False
    for home in load_homes().homes:
        n = cleanup_home(home.id, now)
        if n:
            log.info("Property search cleanup: %d suggestion(s) removed for home %s", n, home.id)
    _last_cleanup_date = today
    return True


async def property_search_cleanup_loop() -> None:
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        try:
            run_cleanup_once()
        except Exception:
            log.exception("property search cleanup iteration failed")

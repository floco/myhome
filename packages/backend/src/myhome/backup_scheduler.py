from __future__ import annotations

import asyncio
import calendar
import logging
from datetime import datetime, timezone

from .persistence_backup import create_backup, load_backup_config, load_backup_state, save_backup_state

log = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60


def _should_run_today(frequency: str, day_of_week: int, day_of_month: int, now: datetime) -> bool:
    if frequency == "daily":
        return True
    if frequency == "weekly":
        return now.isoweekday() == day_of_week
    if frequency == "monthly":
        last_day = calendar.monthrange(now.year, now.month)[1]
        target_day = min(day_of_month, last_day)
        return now.day == target_day
    return False


async def check_and_run_scheduled_backup(now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    today = now.date().isoformat()
    config = load_backup_config()
    if not config.enabled:
        return
    state = load_backup_state()
    if state.lastRunDate == today:
        return
    if now.strftime("%H:%M") < config.time:
        return
    if not _should_run_today(config.frequency, config.dayOfWeek, config.dayOfMonth, now):
        return
    create_backup()
    state.lastRunDate = today
    save_backup_state(state)


async def scheduled_backup_loop() -> None:
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        try:
            await check_and_run_scheduled_backup()
        except Exception:
            log.exception("scheduled backup loop iteration failed")

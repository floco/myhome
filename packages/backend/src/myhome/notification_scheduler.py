from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from .notifications import compute_notifications
from .persistence_homes import load_homes
from .persistence_notifications import load_notification_state, save_notification_state
from .persistence_settings import load_settings
from .routes.ha import call_ha_service

log = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60


def _format_digest(notifications) -> str:
    chores = sum(1 for n in notifications if n.type == "chore")
    low_stock = sum(1 for n in notifications if n.type == "low_stock")
    warranty = sum(1 for n in notifications if n.type == "warranty")
    parts = []
    if chores:
        parts.append(f"{chores} chore{'s' if chores != 1 else ''} due/overdue")
    if low_stock:
        parts.append(f"{low_stock} item{'s' if low_stock != 1 else ''} low on stock")
    if warranty:
        parts.append(f"{warranty} warranty notice{'s' if warranty != 1 else ''}")
    return ", ".join(parts) if parts else "No notifications"


async def check_and_send_digests(now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    today = now.date().isoformat()
    current_time = now.strftime("%H:%M")

    for home in load_homes().homes:
        settings = load_settings(home.id).notifications
        if not settings.haPushEnabled or not settings.haNotifyService:
            continue
        state = load_notification_state(home.id)
        if state.lastPushDigestDate == today:
            continue
        if current_time < settings.haPushTime:
            continue

        notifications = compute_notifications(home.id)
        if notifications:
            try:
                domain, service = settings.haNotifyService.split(".", 1)
            except ValueError:
                log.warning("Malformed haNotifyService %r for home %s", settings.haNotifyService, home.id)
                continue
            try:
                await call_ha_service(domain, service, {"message": _format_digest(notifications)})
            except (httpx.HTTPError, RuntimeError):
                log.warning("HA push digest failed for home %s, will retry", home.id)
                continue

        # Reload: compute_notifications may have persisted a warrantyNotified update.
        state = load_notification_state(home.id)
        state.lastPushDigestDate = today
        save_notification_state(home.id, state)


async def notification_digest_loop() -> None:
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        try:
            await check_and_send_digests()
        except Exception:
            log.exception("notification digest loop iteration failed")

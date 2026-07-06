from __future__ import annotations

from datetime import datetime, timezone

from .models_chores import ChoreDocument
from .models_consumables import ConsumableDocument
from .models_inventory import InventoryDocument
from .models_notifications import Notification, NotificationState


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _format_due(now: datetime, due: datetime) -> str:
    days = (due.date() - now.date()).days
    if days < 0:
        return f"{-days}d overdue"
    if days == 0:
        return "Due today"
    if days == 1:
        return "Due tomorrow"
    return f"In {days}d"


def _chore_notifications(doc: ChoreDocument, threshold: float) -> list[Notification]:
    now = datetime.now(timezone.utc)
    best: dict[str, tuple[float, datetime]] = {}
    for a in doc.assignments:
        if not a.nextDueDate:
            continue
        chore = next((c for c in doc.chores if c.id == a.choreId), None)
        if chore is None or chore.periodDays <= 0:
            continue
        due = _parse_iso(a.nextDueDate)
        period_seconds = chore.periodDays * 86400
        pct = max(0.0, min(1.0, (due - now).total_seconds() / period_seconds))
        if chore.id not in best or pct < best[chore.id][0]:
            best[chore.id] = (pct, due)

    results: list[Notification] = []
    for chore in doc.chores:
        entry = best.get(chore.id)
        if entry is None or entry[0] > threshold:
            continue
        pct, due = entry
        overdue = due < now
        results.append(Notification(
            type="chore",
            refId=chore.id,
            title=chore.name,
            detail=_format_due(now, due),
            severity="critical" if overdue else "warning",
        ))
    return results

from __future__ import annotations

from datetime import datetime, timezone

from .models_build import BuildDocument
from .models_chores import ChoreDocument
from .models_consumables import ConsumableDocument
from .models_inventory import InventoryDocument
from .models_notifications import Notification, NotificationState
from .persistence_build import load_build
from .persistence_chores import load_chores
from .persistence_consumables import load_consumables
from .persistence_inventory import load_inventory
from .persistence_notifications import load_notification_state, save_notification_state
from .persistence_settings import load_settings


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


def _low_stock_notifications(doc: ConsumableDocument) -> list[Notification]:
    results: list[Notification] = []
    for c in doc.consumables:
        if c.quantity <= 0:
            results.append(Notification(
                type="low_stock", refId=c.id, title=c.name,
                detail="Out of stock", severity="critical",
            ))
        elif c.quantity <= c.minQuantity:
            results.append(Notification(
                type="low_stock", refId=c.id, title=c.name,
                detail=f"Low stock: {c.quantity} {c.unit} left", severity="warning",
            ))
    return results


def _warranty_notifications(
    doc: InventoryDocument, days_threshold: int, state: NotificationState,
) -> tuple[list[Notification], NotificationState]:
    now = datetime.now(timezone.utc)
    notified = dict(state.warrantyNotified)
    fired: list[Notification] = []
    changed = False

    for item in doc.items:
        if not item.warrantyExpiryDate:
            continue
        if notified.get(item.id) == item.warrantyExpiryDate:
            continue
        expiry = _parse_iso(item.warrantyExpiryDate)
        days_left = (expiry.date() - now.date()).days
        if days_left > days_threshold:
            continue
        detail = "Warranty expired" if days_left < 0 else f"Warranty expires in {days_left}d"
        fired.append(Notification(
            type="warranty", refId=item.id, title=item.name, detail=detail, severity="info",
        ))
        notified[item.id] = item.warrantyExpiryDate
        changed = True

    new_state = state.model_copy(update={"warrantyNotified": notified}) if changed else state
    return fired, new_state


def _build_notifications(
    doc: BuildDocument, threshold_days: int, state: NotificationState,
) -> tuple[list[Notification], NotificationState]:
    if doc.project is None:
        return [], state

    now = datetime.now(timezone.utc)
    results: list[Notification] = []

    for task in doc.tasks:
        if task.status == "completed":
            continue
        if task.plannedDueDate:
            due = _parse_iso(task.plannedDueDate)
            days_left = (due.date() - now.date()).days
            if days_left <= threshold_days:
                title = task.titleOverride or task.titleKey or task.id
                results.append(Notification(
                    type="build_task_due", refId=task.id, title=title,
                    detail=_format_due(now, due), severity="critical" if days_left < 0 else "warning",
                ))
        if task.validationRequired and task.validationStatus == "pending_validation":
            title = task.titleOverride or task.titleKey or task.id
            results.append(Notification(
                type="build_validation", refId=task.id, title=title,
                detail="Validation pending", severity="info",
            ))

    notified = list(state.buildPhasesNotified)
    changed = False
    for phase in doc.phases:
        if phase.status == "completed" and phase.id not in notified:
            title = phase.nameOverride or phase.nameKey or phase.id
            results.append(Notification(
                type="build_phase_complete", refId=phase.id, title=title,
                detail="Phase complete", severity="info",
            ))
            notified.append(phase.id)
            changed = True

    new_state = state.model_copy(update={"buildPhasesNotified": notified}) if changed else state
    return results, new_state


def compute_notifications(home_id: str) -> list[Notification]:
    settings = load_settings(home_id).notifications
    if not settings.enabled:
        return []

    state = load_notification_state(home_id)
    chores_doc = load_chores(home_id)
    consumables_doc = load_consumables(home_id)
    inventory_doc = load_inventory(home_id)
    build_doc = load_build(home_id)

    results: list[Notification] = []
    results += _chore_notifications(chores_doc, settings.choresDueSoonThreshold)
    results += _low_stock_notifications(consumables_doc)
    fired, updated_state = _warranty_notifications(
        inventory_doc, settings.warrantyDaysThreshold, state,
    )
    results += fired
    build_fired, updated_state = _build_notifications(
        build_doc, settings.buildTaskDueSoonThreshold, updated_state,
    )
    results += build_fired
    if updated_state != state:
        save_notification_state(home_id, updated_state)
    return results

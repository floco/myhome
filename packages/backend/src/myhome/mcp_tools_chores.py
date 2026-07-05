from __future__ import annotations

import uuid
from datetime import datetime, timezone

from mcp.server.fastmcp import Context

from .chore_scheduling import next_due_from_schedule
from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_chores import Chore, CompletionRecord
from .persistence_chores import load_chores, save_chores


def _list_chores_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_chores(resolved).model_dump()


def _create_chore_impl(
    home_id: str | None,
    name: str,
    emoji: str,
    period_days: float,
    next_due_date: str,
    description: str = "",
    frequency_type: str = "interval",
    frequency: int = 0,
    frequency_metadata: dict | None = None,
    schedule_from_due: bool = False,
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_chores(resolved)
    freq = frequency
    meta = frequency_metadata or {}
    if freq == 0:
        freq = max(1, round(period_days))
        meta = {"unit": "days"}
    chore = Chore(
        id=str(uuid.uuid4()),
        name=name,
        emoji=emoji,
        periodDays=period_days,
        nextDueDate=next_due_date,
        description=description,
        frequencyType=frequency_type,
        frequency=freq,
        frequencyMetadata=meta,
        scheduleFromDue=schedule_from_due,
    )
    doc.chores.append(chore)
    save_chores(resolved, doc)
    return chore.model_dump()


def _update_chore_impl(home_id: str | None, chore_id: str, **fields) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_chores(resolved)
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise ValueError(f"Unknown chore_id {chore_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(chore, field, value)
    save_chores(resolved, doc)
    return chore.model_dump()


def _delete_chore_impl(home_id: str | None, chore_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_chores(resolved)
    if not any(c.id == chore_id for c in doc.chores):
        raise ValueError(f"Unknown chore_id {chore_id!r}")
    doc.chores = [c for c in doc.chores if c.id != chore_id]
    doc.assignments = [a for a in doc.assignments if a.choreId != chore_id]
    save_chores(resolved, doc)
    return {"deleted": chore_id}


def _complete_chore_impl(home_id: str | None, chore_id: str, notes: str = "") -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_chores(resolved)
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise ValueError(f"Unknown chore_id {chore_id!r}")
    now = datetime.now(timezone.utc)
    if chore.scheduleFromDue and chore.nextDueDate:
        try:
            from_dt = datetime.fromisoformat(chore.nextDueDate.replace("Z", "+00:00"))
        except ValueError:
            from_dt = now
    else:
        from_dt = now
    next_due = next_due_from_schedule(chore, from_dt)
    next_due_str = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    doc.completions.append(CompletionRecord(
        id=str(uuid.uuid4()),
        choreId=chore_id,
        completedAt=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        scheduledDue=chore.nextDueDate,
        notes=notes,
    ))
    for a in doc.assignments:
        if a.choreId == chore_id:
            a.nextDueDate = next_due_str
    chore.nextDueDate = next_due_str
    save_chores(resolved, doc)
    return chore.model_dump()


def _undo_chore_completion_impl(home_id: str | None, completion_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_chores(resolved)
    if not any(r.id == completion_id for r in doc.completions):
        raise ValueError(f"Unknown completion_id {completion_id!r}")
    doc.completions = [r for r in doc.completions if r.id != completion_id]
    save_chores(resolved, doc)
    return {"deleted": completion_id}


@mcp.tool()
async def list_chores(ctx: Context, home_id: str | None = None) -> dict:
    """List all chores, room assignments, and completion history for a home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_chores_impl(home_id)


@mcp.tool()
async def create_chore(
    ctx: Context,
    name: str,
    emoji: str,
    period_days: float,
    next_due_date: str,
    home_id: str | None = None,
    description: str = "",
    frequency_type: str = "interval",
    frequency: int = 0,
    frequency_metadata: dict | None = None,
    schedule_from_due: bool = False,
) -> dict:
    """Create a new recurring chore. next_due_date is ISO-8601. frequency_type is one of
    'interval' (every N days/weeks/months/years, set via frequency_metadata={'unit': ...}),
    'weekly', 'monthly', 'yearly', 'day_of_the_month', or 'days_of_the_week'. Leave
    frequency at 0 to derive it from period_days for a simple daily interval."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_chore_impl(
        home_id, name, emoji, period_days, next_due_date, description,
        frequency_type, frequency, frequency_metadata, schedule_from_due,
    )


@mcp.tool()
async def update_chore(
    ctx: Context,
    chore_id: str,
    home_id: str | None = None,
    name: str | None = None,
    emoji: str | None = None,
    period_days: float | None = None,
    next_due_date: str | None = None,
    description: str | None = None,
    frequency_type: str | None = None,
    frequency: int | None = None,
    frequency_metadata: dict | None = None,
    schedule_from_due: bool | None = None,
) -> dict:
    """Update fields on an existing chore. Only pass the fields you want to change."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_chore_impl(
        home_id, chore_id,
        name=name, emoji=emoji, periodDays=period_days, nextDueDate=next_due_date,
        description=description, frequencyType=frequency_type, frequency=frequency,
        frequencyMetadata=frequency_metadata, scheduleFromDue=schedule_from_due,
    )


@mcp.tool()
async def delete_chore(ctx: Context, chore_id: str, home_id: str | None = None) -> dict:
    """Delete a chore and its room assignments. Completion history is kept."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_chore_impl(home_id, chore_id)


@mcp.tool()
async def complete_chore(ctx: Context, chore_id: str, home_id: str | None = None, notes: str = "") -> dict:
    """Mark a chore as done now, recording a completion and advancing its next due date
    according to its schedule."""
    await _require_role(ctx.request_context.request, "normal")
    return _complete_chore_impl(home_id, chore_id, notes)


@mcp.tool()
async def undo_chore_completion(ctx: Context, completion_id: str, home_id: str | None = None) -> dict:
    """Delete a completion record (undoes a mistaken complete_chore call). Does not
    revert the chore's next due date."""
    await _require_role(ctx.request_context.request, "normal")
    return _undo_chore_completion_impl(home_id, completion_id)

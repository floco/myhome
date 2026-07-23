from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_build import BuildTask
from .persistence_build import load_build, save_build

_VALID_TASK_STATUSES = ("not_started", "ready", "in_progress", "waiting", "blocked", "completed")
_VALID_PHASE_STATUSES = ("not_started", "in_progress", "completed")


def _list_build_phases_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_build(resolved)
    return {"phases": [p.model_dump() for p in doc.phases]}


def _list_build_tasks_impl(home_id: str | None, phase_id: str | None = None) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_build(resolved)
    tasks = doc.tasks if phase_id is None else [t for t in doc.tasks if t.phaseId == phase_id]
    return {"tasks": [t.model_dump() for t in tasks]}


def _create_build_task_impl(
    home_id: str | None, phase_id: str, title: str,
    description: str = "", validation_required: bool = False,
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_build(resolved)
    if not any(p.id == phase_id for p in doc.phases):
        raise ValueError(f"Unknown phase_id {phase_id!r}")
    siblings = [t for t in doc.tasks if t.phaseId == phase_id]
    task = BuildTask(
        id=str(uuid.uuid4()), phaseId=phase_id, displayOrder=len(siblings),
        titleOverride=title, descriptionOverride=description, validationRequired=validation_required,
    )
    doc.tasks.append(task)
    save_build(resolved, doc)
    return task.model_dump()


def _update_build_task_impl(home_id: str | None, task_id: str, **fields) -> dict:
    if fields.get("status") is not None and fields["status"] not in _VALID_TASK_STATUSES:
        raise ValueError(f"status must be one of {_VALID_TASK_STATUSES}")
    resolved = _resolve_home_id(home_id)
    doc = load_build(resolved)
    task = next((t for t in doc.tasks if t.id == task_id), None)
    if task is None:
        raise ValueError(f"Unknown task_id {task_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(task, field, value)
    save_build(resolved, doc)
    return task.model_dump()


def _update_build_phase_impl(home_id: str | None, phase_id: str, **fields) -> dict:
    if fields.get("status") is not None and fields["status"] not in _VALID_PHASE_STATUSES:
        raise ValueError(f"status must be one of {_VALID_PHASE_STATUSES}")
    resolved = _resolve_home_id(home_id)
    doc = load_build(resolved)
    phase = next((p for p in doc.phases if p.id == phase_id), None)
    if phase is None:
        raise ValueError(f"Unknown phase_id {phase_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(phase, field, value)
    save_build(resolved, doc)
    return phase.model_dump()


@mcp.tool()
async def list_build_phases(ctx: Context, home_id: str | None = None) -> dict:
    """List build tracking phases for a home's construction project."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_build_phases_impl(home_id)


@mcp.tool()
async def list_build_tasks(ctx: Context, home_id: str | None = None, phase_id: str | None = None) -> dict:
    """List build tracking tasks for a home, optionally filtered to one phase_id."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_build_tasks_impl(home_id, phase_id)


@mcp.tool()
async def create_build_task(
    ctx: Context, phase_id: str, title: str,
    home_id: str | None = None, description: str = "", validation_required: bool = False,
) -> dict:
    """Create a custom build task within an existing phase."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_build_task_impl(home_id, phase_id, title, description, validation_required)


@mcp.tool()
async def update_build_task(
    ctx: Context, task_id: str, home_id: str | None = None,
    status: str | None = None, contractor_id: str | None = None,
    planned_due_date: str | None = None, actual_cost: float | None = None,
    validation_status: str | None = None, notes: str | None = None,
) -> dict:
    """Update a build task's status, contractor, dates, cost, or validation status."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_build_task_impl(
        home_id, task_id, status=status, contractorId=contractor_id,
        plannedDueDate=planned_due_date, actualCost=actual_cost,
        validationStatus=validation_status, notes=notes,
    )


@mcp.tool()
async def update_build_phase(
    ctx: Context, phase_id: str, home_id: str | None = None, status: str | None = None,
) -> dict:
    """Update a build phase's status."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_build_phase_impl(home_id, phase_id, status=status)

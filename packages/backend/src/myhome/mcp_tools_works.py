from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_works import Work
from .persistence_works import load_works, save_works

_VALID_STATUSES = ("planned", "in_progress", "done")


def _list_works_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_works(resolved).model_dump()


def _create_work_impl(
    home_id: str | None,
    title: str,
    date: str,
    description: str = "",
    status: str = "planned",
    category_id: str | None = None,
    total_cost: float | None = None,
    supplier_id: str | None = None,
    notes: str = "",
) -> dict:
    if status not in _VALID_STATUSES:
        raise ValueError(f"status must be one of {_VALID_STATUSES}")
    resolved = _resolve_home_id(home_id)
    doc = load_works(resolved)
    work = Work(
        id=str(uuid.uuid4()), title=title, description=description, status=status,
        categoryId=category_id, date=date, totalCost=total_cost, supplierId=supplier_id, notes=notes,
    )
    doc.works.append(work)
    save_works(resolved, doc)
    return work.model_dump()


def _update_work_impl(home_id: str | None, work_id: str, **fields) -> dict:
    if fields.get("status") is not None and fields["status"] not in _VALID_STATUSES:
        raise ValueError(f"status must be one of {_VALID_STATUSES}")
    resolved = _resolve_home_id(home_id)
    doc = load_works(resolved)
    work = next((w for w in doc.works if w.id == work_id), None)
    if work is None:
        raise ValueError(f"Unknown work_id {work_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(work, field, value)
    save_works(resolved, doc)
    return work.model_dump()


def _delete_work_impl(home_id: str | None, work_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_works(resolved)
    before = len(doc.works)
    doc.works = [w for w in doc.works if w.id != work_id]
    if len(doc.works) == before:
        raise ValueError(f"Unknown work_id {work_id!r}")
    save_works(resolved, doc)
    return {"deleted": work_id}


@mcp.tool()
async def list_works(ctx: Context, home_id: str | None = None) -> dict:
    """List home improvement/renovation works for a home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_works_impl(home_id)


@mcp.tool()
async def create_work(
    ctx: Context,
    title: str,
    date: str,
    home_id: str | None = None,
    description: str = "",
    status: str = "planned",
    category_id: str | None = None,
    total_cost: float | None = None,
    supplier_id: str | None = None,
    notes: str = "",
) -> dict:
    """Create a home improvement/work project entry. status is 'planned', 'in_progress',
    or 'done'. category_id and supplier_id should match ids from get_settings."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_work_impl(home_id, title, date, description, status, category_id, total_cost, supplier_id, notes)


@mcp.tool()
async def update_work(
    ctx: Context,
    work_id: str,
    home_id: str | None = None,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    category_id: str | None = None,
    date: str | None = None,
    total_cost: float | None = None,
    supplier_id: str | None = None,
    notes: str | None = None,
) -> dict:
    """Update fields on an existing work, including transitioning its status."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_work_impl(
        home_id, work_id, title=title, description=description, status=status,
        categoryId=category_id, date=date, totalCost=total_cost, supplierId=supplier_id, notes=notes,
    )


@mcp.tool()
async def delete_work(ctx: Context, work_id: str, home_id: str | None = None) -> dict:
    """Delete a work entry."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_work_impl(home_id, work_id)

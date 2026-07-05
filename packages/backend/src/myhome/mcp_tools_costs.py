from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_costs import CostEntry
from .persistence_costs import load_costs, save_costs


def _list_cost_entries_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_costs(resolved).model_dump()


def _create_cost_entry_impl(
    home_id: str | None,
    category_id: str,
    date: str,
    total_amount: float,
    quantity: float | None = None,
    unit_price: float | None = None,
    supplier_id: str | None = None,
    notes: str = "",
    room_id: str | None = None,
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_costs(resolved)
    entry = CostEntry(
        id=str(uuid.uuid4()), categoryId=category_id, date=date, totalAmount=total_amount,
        quantity=quantity, unitPrice=unit_price, supplierId=supplier_id, notes=notes, roomId=room_id,
    )
    doc.entries.append(entry)
    save_costs(resolved, doc)
    return entry.model_dump()


def _update_cost_entry_impl(home_id: str | None, entry_id: str, **fields) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_costs(resolved)
    entry = next((e for e in doc.entries if e.id == entry_id), None)
    if entry is None:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(entry, field, value)
    save_costs(resolved, doc)
    return entry.model_dump()


def _delete_cost_entry_impl(home_id: str | None, entry_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_costs(resolved)
    before = len(doc.entries)
    doc.entries = [e for e in doc.entries if e.id != entry_id]
    if len(doc.entries) == before:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    save_costs(resolved, doc)
    return {"deleted": entry_id}


@mcp.tool()
async def list_cost_entries(ctx: Context, home_id: str | None = None) -> dict:
    """List all cost/expense entries for a home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_cost_entries_impl(home_id)


@mcp.tool()
async def create_cost_entry(
    ctx: Context,
    category_id: str,
    date: str,
    total_amount: float,
    home_id: str | None = None,
    quantity: float | None = None,
    unit_price: float | None = None,
    supplier_id: str | None = None,
    notes: str = "",
    room_id: str | None = None,
) -> dict:
    """Log a cost entry. category_id and supplier_id should match ids from
    get_settings (costCategories / suppliers). date is ISO-8601."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_cost_entry_impl(
        home_id, category_id, date, total_amount, quantity, unit_price, supplier_id, notes, room_id,
    )


@mcp.tool()
async def update_cost_entry(
    ctx: Context,
    entry_id: str,
    home_id: str | None = None,
    category_id: str | None = None,
    date: str | None = None,
    total_amount: float | None = None,
    quantity: float | None = None,
    unit_price: float | None = None,
    supplier_id: str | None = None,
    notes: str | None = None,
    room_id: str | None = None,
) -> dict:
    """Update fields on an existing cost entry. Only pass the fields you want to change."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_cost_entry_impl(
        home_id, entry_id, categoryId=category_id, date=date, totalAmount=total_amount,
        quantity=quantity, unitPrice=unit_price, supplierId=supplier_id, notes=notes, roomId=room_id,
    )


@mcp.tool()
async def delete_cost_entry(ctx: Context, entry_id: str, home_id: str | None = None) -> dict:
    """Delete a cost entry."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_cost_entry_impl(home_id, entry_id)

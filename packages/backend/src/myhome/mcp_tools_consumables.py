from __future__ import annotations

import uuid
from datetime import datetime, timezone

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_consumables import Consumable, ConsumableTransaction
from .persistence_consumables import load_consumables, save_consumables


def _list_consumables_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_consumables(resolved).model_dump()


def _create_consumable_impl(
    home_id: str | None,
    name: str,
    emoji: str = "🛒",
    unit: str = "count",
    quantity: float = 0.0,
    min_quantity: float = 1.0,
    category_id: str | None = None,
    description: str = "",
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_consumables(resolved)
    item = Consumable(
        id=str(uuid.uuid4()), name=name, emoji=emoji, unit=unit, quantity=quantity,
        minQuantity=min_quantity, categoryId=category_id, description=description,
    )
    doc.consumables.append(item)
    save_consumables(resolved, doc)
    return item.model_dump()


def _update_consumable_impl(home_id: str | None, consumable_id: str, **fields) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_consumables(resolved)
    item = next((c for c in doc.consumables if c.id == consumable_id), None)
    if item is None:
        raise ValueError(f"Unknown consumable_id {consumable_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(item, field, value)
    save_consumables(resolved, doc)
    return item.model_dump()


def _delete_consumable_impl(home_id: str | None, consumable_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_consumables(resolved)
    before = len(doc.consumables)
    doc.consumables = [c for c in doc.consumables if c.id != consumable_id]
    if len(doc.consumables) == before:
        raise ValueError(f"Unknown consumable_id {consumable_id!r}")
    doc.transactions = [t for t in doc.transactions if t.consumableId != consumable_id]
    save_consumables(resolved, doc)
    return {"deleted": consumable_id}


def _adjust_consumable_stock_impl(home_id: str | None, consumable_id: str, quantity: float, note: str = "") -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_consumables(resolved)
    item = next((c for c in doc.consumables if c.id == consumable_id), None)
    if item is None:
        raise ValueError(f"Unknown consumable_id {consumable_id!r}")
    delta = quantity - item.quantity
    item.quantity = quantity
    tx = ConsumableTransaction(
        id=str(uuid.uuid4()), consumableId=consumable_id, delta=delta,
        quantityAfter=quantity, note=note, timestamp=datetime.now(timezone.utc).isoformat(),
    )
    doc.transactions.append(tx)
    save_consumables(resolved, doc)
    return item.model_dump()


@mcp.tool()
async def list_consumables(ctx: Context, home_id: str | None = None) -> dict:
    """List consumable stock items and their transaction history for a home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_consumables_impl(home_id)


@mcp.tool()
async def create_consumable(
    ctx: Context,
    name: str,
    home_id: str | None = None,
    emoji: str = "🛒",
    unit: str = "count",
    quantity: float = 0.0,
    min_quantity: float = 1.0,
    category_id: str | None = None,
    description: str = "",
) -> dict:
    """Add a consumable stock item (e.g. batteries, detergent). unit and category_id
    should match values from get_settings (consumableUnits / consumableCategories)."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_consumable_impl(home_id, name, emoji, unit, quantity, min_quantity, category_id, description)


@mcp.tool()
async def update_consumable(
    ctx: Context,
    consumable_id: str,
    home_id: str | None = None,
    name: str | None = None,
    emoji: str | None = None,
    unit: str | None = None,
    min_quantity: float | None = None,
    category_id: str | None = None,
    description: str | None = None,
) -> dict:
    """Update fields on a consumable. To change the quantity itself, use
    adjust_consumable_stock instead (it also records a transaction)."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_consumable_impl(
        home_id, consumable_id, name=name, emoji=emoji, unit=unit,
        minQuantity=min_quantity, categoryId=category_id, description=description,
    )


@mcp.tool()
async def delete_consumable(ctx: Context, consumable_id: str, home_id: str | None = None) -> dict:
    """Delete a consumable and its transaction history."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_consumable_impl(home_id, consumable_id)


@mcp.tool()
async def adjust_consumable_stock(
    ctx: Context, consumable_id: str, quantity: float, home_id: str | None = None, note: str = "",
) -> dict:
    """Set a consumable's ABSOLUTE quantity (not a delta) and record a stock
    transaction. E.g. to record using 2 units from a stock of 10, pass quantity=8."""
    await _require_role(ctx.request_context.request, "normal")
    return _adjust_consumable_stock_impl(home_id, consumable_id, quantity, note)

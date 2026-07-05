from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_inventory import InventoryItem
from .persistence_inventory import load_inventory, save_inventory


def _list_inventory_items_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_inventory(resolved).model_dump()


def _create_inventory_item_impl(
    home_id: str | None,
    name: str,
    emoji: str = "📦",
    category: str = "",
    brand: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
    purchase_date: str | None = None,
    purchase_price: float | None = None,
    warranty_expiry_date: str | None = None,
    notes: str = "",
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_inventory(resolved)
    item = InventoryItem(
        id=str(uuid.uuid4()), name=name, emoji=emoji, category=category, brand=brand,
        model=model, serialNumber=serial_number, purchaseDate=purchase_date,
        purchasePrice=purchase_price, warrantyExpiryDate=warranty_expiry_date, notes=notes,
    )
    doc.items.append(item)
    save_inventory(resolved, doc)
    return item.model_dump()


def _update_inventory_item_impl(home_id: str | None, item_id: str, **fields) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_inventory(resolved)
    item = next((i for i in doc.items if i.id == item_id), None)
    if item is None:
        raise ValueError(f"Unknown item_id {item_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(item, field, value)
    save_inventory(resolved, doc)
    return item.model_dump()


def _delete_inventory_item_impl(home_id: str | None, item_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_inventory(resolved)
    before = len(doc.items)
    doc.items = [i for i in doc.items if i.id != item_id]
    if len(doc.items) == before:
        raise ValueError(f"Unknown item_id {item_id!r}")
    save_inventory(resolved, doc)
    return {"deleted": item_id}


@mcp.tool()
async def list_inventory_items(ctx: Context, home_id: str | None = None) -> dict:
    """List all inventory items for a home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_inventory_items_impl(home_id)


@mcp.tool()
async def create_inventory_item(
    ctx: Context,
    name: str,
    home_id: str | None = None,
    emoji: str = "📦",
    category: str = "",
    brand: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
    purchase_date: str | None = None,
    purchase_price: float | None = None,
    warranty_expiry_date: str | None = None,
    notes: str = "",
) -> dict:
    """Add an inventory item. category should match an inventoryCategories name from
    get_settings (e.g. Electronics, Furniture, Appliance, Tool, Artwork, Other)."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_inventory_item_impl(
        home_id, name, emoji, category, brand, model, serial_number,
        purchase_date, purchase_price, warranty_expiry_date, notes,
    )


@mcp.tool()
async def update_inventory_item(
    ctx: Context,
    item_id: str,
    home_id: str | None = None,
    name: str | None = None,
    emoji: str | None = None,
    category: str | None = None,
    brand: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
    purchase_date: str | None = None,
    purchase_price: float | None = None,
    warranty_expiry_date: str | None = None,
    notes: str | None = None,
) -> dict:
    """Update fields on an existing inventory item. Only pass the fields you want to change."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_inventory_item_impl(
        home_id, item_id, name=name, emoji=emoji, category=category, brand=brand,
        model=model, serialNumber=serial_number, purchaseDate=purchase_date,
        purchasePrice=purchase_price, warrantyExpiryDate=warranty_expiry_date, notes=notes,
    )


@mcp.tool()
async def delete_inventory_item(ctx: Context, item_id: str, home_id: str | None = None) -> dict:
    """Delete an inventory item."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_inventory_item_impl(home_id, item_id)

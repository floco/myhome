from __future__ import annotations

import uuid
from collections.abc import Callable

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_inventory import InventoryItem
from .models_settings import InventoryCategory, Owner, Store
from .persistence_inventory import load_inventory, save_inventory
from .persistence_settings import load_settings, save_settings


def _resolve_or_create(entries: list, name: str | None, make: Callable[[str, str], object]) -> str | None:
    """Match `name` case-insensitively against `entries` (a list of objects
    with .id/.name, e.g. Owner/Store/InventoryCategory); append a new entry
    (mutating `entries` in place) via `make(new_id, name)` if no match.
    Returns the matching/new entry's id, or None if name is blank/None."""
    if not name or not name.strip():
        return None
    text = name.strip()
    for entry in entries:
        if entry.name.strip().lower() == text.lower():
            return entry.id
    new_id = str(uuid.uuid4())
    entries.append(make(new_id, text))
    return new_id


def _list_inventory_items_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_inventory(resolved).model_dump()


def _create_inventory_item_impl(
    home_id: str | None,
    name: str,
    emoji: str = "📦",
    category: str = "",
    owner: str | None = None,
    store: str | None = None,
    brand: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
    purchase_date: str | None = None,
    purchase_price: float | None = None,
    warranty_expiry_date: str | None = None,
    notes: str = "",
) -> dict:
    resolved = _resolve_home_id(home_id)
    settings_doc = load_settings(resolved)
    category_id = _resolve_or_create(settings_doc.inventoryCategories, category, lambda i, n: InventoryCategory(id=i, name=n))
    owner_id = _resolve_or_create(settings_doc.owners, owner, lambda i, n: Owner(id=i, name=n))
    store_id = _resolve_or_create(settings_doc.stores, store, lambda i, n: Store(id=i, name=n))
    save_settings(resolved, settings_doc)

    doc = load_inventory(resolved)
    item = InventoryItem(
        id=str(uuid.uuid4()), name=name, emoji=emoji, categoryId=category_id, ownerId=owner_id,
        storeId=store_id, brand=brand, model=model, serialNumber=serial_number,
        purchaseDate=purchase_date, purchasePrice=purchase_price,
        warrantyExpiryDate=warranty_expiry_date, notes=notes,
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
    owner: str | None = None,
    store: str | None = None,
    brand: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
    purchase_date: str | None = None,
    purchase_price: float | None = None,
    warranty_expiry_date: str | None = None,
    notes: str = "",
) -> dict:
    """Add an inventory item. category/owner/store should match existing names from
    get_settings (inventoryCategories, owners, stores respectively, e.g. category
    Electronics/Furniture/Appliance/Tool/Artwork/Other) -- a name with no match
    automatically creates a new entry in that list."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_inventory_item_impl(
        home_id, name, emoji, category, owner, store, brand, model, serial_number,
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
    owner: str | None = None,
    store: str | None = None,
    brand: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
    purchase_date: str | None = None,
    purchase_price: float | None = None,
    warranty_expiry_date: str | None = None,
    notes: str | None = None,
) -> dict:
    """Update fields on an existing inventory item. Only pass the fields you want to
    change. category/owner/store are name-based, same auto-create behavior as
    create_inventory_item; passing one leaves the item's existing value in place."""
    await _require_role(ctx.request_context.request, "normal")
    resolved = _resolve_home_id(home_id)
    settings_doc = load_settings(resolved)
    category_id = _resolve_or_create(settings_doc.inventoryCategories, category, lambda i, n: InventoryCategory(id=i, name=n)) if category else None
    owner_id = _resolve_or_create(settings_doc.owners, owner, lambda i, n: Owner(id=i, name=n)) if owner else None
    store_id = _resolve_or_create(settings_doc.stores, store, lambda i, n: Store(id=i, name=n)) if store else None
    if category or owner or store:
        save_settings(resolved, settings_doc)
    return _update_inventory_item_impl(
        home_id, item_id, name=name, emoji=emoji, categoryId=category_id, ownerId=owner_id,
        storeId=store_id, brand=brand, model=model, serialNumber=serial_number,
        purchaseDate=purchase_date, purchasePrice=purchase_price,
        warrantyExpiryDate=warranty_expiry_date, notes=notes,
    )


@mcp.tool()
async def delete_inventory_item(ctx: Context, item_id: str, home_id: str | None = None) -> dict:
    """Delete an inventory item."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_inventory_item_impl(home_id, item_id)

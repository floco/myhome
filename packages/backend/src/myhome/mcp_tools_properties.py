from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_properties import Property
from .persistence_properties import load_properties, save_properties

_VALID_TYPES = ("land", "house", "new_build")
_VALID_STATUSES = ("watching", "visited", "proposal_made", "purchased", "rejected")


def _list_properties_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_properties(resolved).model_dump()


def _create_property_impl(
    home_id: str | None,
    name: str,
    type: str,
    status: str = "watching",
    location_id: str | None = None,
    address: str = "",
    price: float | None = None,
    land_size: float | None = None,
    built_size: float | None = None,
    bedrooms: int | None = None,
    bathrooms: int | None = None,
    listing_url: str | None = None,
    contact: str = "",
    notes: str = "",
) -> dict:
    if type not in _VALID_TYPES:
        raise ValueError(f"type must be one of {_VALID_TYPES}")
    if status not in _VALID_STATUSES:
        raise ValueError(f"status must be one of {_VALID_STATUSES}")
    resolved = _resolve_home_id(home_id)
    doc = load_properties(resolved)
    item = Property(
        id=str(uuid.uuid4()), name=name, type=type, status=status,
        locationId=location_id, address=address, price=price, landSize=land_size, builtSize=built_size,
        bedrooms=bedrooms, bathrooms=bathrooms, listingUrl=listing_url, contact=contact, notes=notes,
    )
    doc.properties.append(item)
    save_properties(resolved, doc)
    return item.model_dump()


def _update_property_impl(home_id: str | None, property_id: str, **fields) -> dict:
    if fields.get("status") is not None and fields["status"] not in _VALID_STATUSES:
        raise ValueError(f"status must be one of {_VALID_STATUSES}")
    if fields.get("type") is not None and fields["type"] not in _VALID_TYPES:
        raise ValueError(f"type must be one of {_VALID_TYPES}")
    resolved = _resolve_home_id(home_id)
    doc = load_properties(resolved)
    item = next((p for p in doc.properties if p.id == property_id), None)
    if item is None:
        raise ValueError(f"Unknown property_id {property_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(item, field, value)
    save_properties(resolved, doc)
    return item.model_dump()


def _delete_property_impl(home_id: str | None, property_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_properties(resolved)
    before = len(doc.properties)
    doc.properties = [p for p in doc.properties if p.id != property_id]
    if len(doc.properties) == before:
        raise ValueError(f"Unknown property_id {property_id!r}")
    save_properties(resolved, doc)
    return {"deleted": property_id}


@mcp.tool()
async def list_properties(ctx: Context, home_id: str | None = None) -> dict:
    """List property listings (land/house/new-build) being tracked for a home search."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_properties_impl(home_id)


@mcp.tool()
async def create_property(
    ctx: Context,
    name: str,
    type: str,
    home_id: str | None = None,
    status: str = "watching",
    location_id: str | None = None,
    address: str = "",
    price: float | None = None,
    land_size: float | None = None,
    built_size: float | None = None,
    bedrooms: int | None = None,
    bathrooms: int | None = None,
    listing_url: str | None = None,
    contact: str = "",
    notes: str = "",
) -> dict:
    """Add a property listing. type is 'land', 'house', or 'new_build'. status is
    'watching', 'visited', 'proposal_made', 'purchased', or 'rejected'. location_id
    should match an id from list_locations if set. Sizes are in square meters."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_property_impl(
        home_id, name, type, status, location_id, address, price, land_size, built_size,
        bedrooms, bathrooms, listing_url, contact, notes,
    )


@mcp.tool()
async def update_property(
    ctx: Context,
    property_id: str,
    home_id: str | None = None,
    name: str | None = None,
    type: str | None = None,
    status: str | None = None,
    location_id: str | None = None,
    address: str | None = None,
    price: float | None = None,
    land_size: float | None = None,
    built_size: float | None = None,
    bedrooms: int | None = None,
    bathrooms: int | None = None,
    listing_url: str | None = None,
    contact: str | None = None,
    notes: str | None = None,
) -> dict:
    """Update fields on an existing property, including transitioning its status."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_property_impl(
        home_id, property_id, name=name, type=type, status=status, locationId=location_id,
        address=address, price=price, landSize=land_size, builtSize=built_size,
        bedrooms=bedrooms, bathrooms=bathrooms, listingUrl=listing_url, contact=contact, notes=notes,
    )


@mcp.tool()
async def delete_property(ctx: Context, property_id: str, home_id: str | None = None) -> dict:
    """Delete a property listing."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_property_impl(home_id, property_id)

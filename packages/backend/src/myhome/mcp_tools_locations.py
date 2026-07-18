from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_locations import Location, LocationCriterion, LocationRating
from .persistence_locations import load_locations, save_locations


def _list_locations_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_locations(resolved).model_dump()


def _create_location_criterion_impl(
    home_id: str | None, name: str, description: str = "", weight: str = "medium",
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_locations(resolved)
    item = LocationCriterion(id=str(uuid.uuid4()), name=name, description=description, weight=weight)
    doc.criteria.append(item)
    save_locations(resolved, doc)
    return item.model_dump()


def _update_location_criterion_impl(home_id: str | None, criterion_id: str, **fields) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_locations(resolved)
    item = next((c for c in doc.criteria if c.id == criterion_id), None)
    if item is None:
        raise ValueError(f"Unknown criterion_id {criterion_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(item, field, value)
    save_locations(resolved, doc)
    return item.model_dump()


def _delete_location_criterion_impl(home_id: str | None, criterion_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_locations(resolved)
    before = len(doc.criteria)
    doc.criteria = [c for c in doc.criteria if c.id != criterion_id]
    if len(doc.criteria) == before:
        raise ValueError(f"Unknown criterion_id {criterion_id!r}")
    doc.ratings = [r for r in doc.ratings if r.criterionId != criterion_id]
    save_locations(resolved, doc)
    return {"deleted": criterion_id}


def _create_location_impl(home_id: str | None, name: str, emoji: str = "📍") -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_locations(resolved)
    item = Location(id=str(uuid.uuid4()), name=name, emoji=emoji)
    doc.locations.append(item)
    save_locations(resolved, doc)
    return item.model_dump()


def _update_location_impl(home_id: str | None, location_id: str, **fields) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_locations(resolved)
    item = next((l for l in doc.locations if l.id == location_id), None)
    if item is None:
        raise ValueError(f"Unknown location_id {location_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(item, field, value)
    save_locations(resolved, doc)
    return item.model_dump()


def _delete_location_impl(home_id: str | None, location_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_locations(resolved)
    before = len(doc.locations)
    doc.locations = [l for l in doc.locations if l.id != location_id]
    if len(doc.locations) == before:
        raise ValueError(f"Unknown location_id {location_id!r}")
    doc.ratings = [r for r in doc.ratings if r.locationId != location_id]
    save_locations(resolved, doc)
    return {"deleted": location_id}


def _set_location_rating_impl(
    home_id: str | None, location_id: str, criterion_id: str, score: int | None = None, note: str = "",
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_locations(resolved)
    if not any(l.id == location_id for l in doc.locations):
        raise ValueError(f"Unknown location_id {location_id!r}")
    if not any(c.id == criterion_id for c in doc.criteria):
        raise ValueError(f"Unknown criterion_id {criterion_id!r}")
    doc.ratings = [r for r in doc.ratings if not (r.locationId == location_id and r.criterionId == criterion_id)]
    rating = LocationRating(locationId=location_id, criterionId=criterion_id, score=score, note=note)
    doc.ratings.append(rating)
    save_locations(resolved, doc)
    return rating.model_dump()


@mcp.tool()
async def list_locations(ctx: Context, home_id: str | None = None) -> dict:
    """List candidate locations, comparison criteria, and ratings for a Project home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_locations_impl(home_id)


@mcp.tool()
async def create_location_criterion(
    ctx: Context, name: str, home_id: str | None = None, description: str = "", weight: str = "medium",
) -> dict:
    """Add a comparison criterion (e.g. "Healthcare", "Cost of Living"). weight is
    one of "low", "medium", "high" and controls how much it counts toward the
    overall weighted score."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_location_criterion_impl(home_id, name, description, weight)


@mcp.tool()
async def update_location_criterion(
    ctx: Context, criterion_id: str, home_id: str | None = None,
    name: str | None = None, description: str | None = None, weight: str | None = None,
) -> dict:
    """Update a comparison criterion's name, description, or weight."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_location_criterion_impl(home_id, criterion_id, name=name, description=description, weight=weight)


@mcp.tool()
async def delete_location_criterion(ctx: Context, criterion_id: str, home_id: str | None = None) -> dict:
    """Delete a comparison criterion and its ratings across all locations."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_location_criterion_impl(home_id, criterion_id)


@mcp.tool()
async def create_location(ctx: Context, name: str, home_id: str | None = None, emoji: str = "📍") -> dict:
    """Add a candidate location (country, city, region) to compare."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_location_impl(home_id, name, emoji)


@mcp.tool()
async def update_location(
    ctx: Context, location_id: str, home_id: str | None = None, name: str | None = None, emoji: str | None = None,
) -> dict:
    """Update a candidate location's name or emoji."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_location_impl(home_id, location_id, name=name, emoji=emoji)


@mcp.tool()
async def delete_location(ctx: Context, location_id: str, home_id: str | None = None) -> dict:
    """Delete a candidate location and its ratings across all criteria."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_location_impl(home_id, location_id)


@mcp.tool()
async def set_location_rating(
    ctx: Context, location_id: str, criterion_id: str, home_id: str | None = None,
    score: int | None = None, note: str = "",
) -> dict:
    """Rate a location against a criterion. score is 1-5 (best), or omit/null to
    clear the score while keeping the note."""
    await _require_role(ctx.request_context.request, "normal")
    return _set_location_rating_impl(home_id, location_id, criterion_id, score, note)

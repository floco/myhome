from __future__ import annotations

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, mcp
from .persistence_homes import (
    create_home as ph_create_home,
    delete_home as ph_delete_home,
    load_homes,
    patch_home,
)


def _list_homes_impl() -> list[dict]:
    return [h.model_dump() for h in load_homes().homes]


def _create_home_impl(name: str, home_type: str) -> dict:
    if home_type not in ("existing", "project"):
        raise ValueError("type must be 'existing' or 'project'")
    return ph_create_home(name, home_type).model_dump()


def _update_home_impl(
    home_id: str,
    name: str | None = None,
    home_type: str | None = None,
    enabled_modules: list[str] | None = None,
) -> dict:
    if home_type is not None and home_type not in ("existing", "project"):
        raise ValueError("type must be 'existing' or 'project'")
    home = patch_home(home_id, name, home_type, enabled_modules)
    if home is None:
        raise ValueError(f"Unknown home_id {home_id!r}")
    return home.model_dump()


def _delete_home_impl(home_id: str) -> dict:
    if not ph_delete_home(home_id):
        raise ValueError(f"Unknown home_id {home_id!r}")
    return {"deleted": home_id}


@mcp.tool()
async def list_homes(ctx: Context) -> list[dict]:
    """List every home in this MyHome installation, with id, name, type, and enabled modules."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_homes_impl()


@mcp.tool()
async def create_home(ctx: Context, name: str, type: str) -> dict:
    """Create a new home. type must be 'existing' or 'project'."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_home_impl(name, type)


@mcp.tool()
async def update_home(
    ctx: Context,
    home_id: str,
    name: str | None = None,
    type: str | None = None,
    enabled_modules: list[str] | None = None,
) -> dict:
    """Rename a home, change its type ('existing'/'project'), or change which modules are enabled."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_home_impl(home_id, name, type, enabled_modules)


@mcp.tool()
async def delete_home(ctx: Context, home_id: str) -> dict:
    """Permanently delete a home and ALL of its data (chores, inventory, costs, works,
    KB, consumables). This cannot be undone."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_home_impl(home_id)

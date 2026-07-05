from __future__ import annotations

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .persistence_settings import load_settings


def _get_settings_impl(home_id: str) -> dict:
    return load_settings(home_id).model_dump()


@mcp.tool()
async def get_settings(ctx: Context, home_id: str | None = None) -> dict:
    """Get the cost categories, inventory categories, work categories, suppliers,
    consumable units, and consumable categories configured for a home. Use this to
    find valid categoryId/supplierId values before creating cost entries, works,
    or consumables."""
    await _require_role(ctx.request_context.request, "ro")
    resolved = _resolve_home_id(home_id)
    return _get_settings_impl(resolved)

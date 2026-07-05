from __future__ import annotations

import uuid
from datetime import datetime, timezone

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_kb import KBEntry
from .persistence_kb import delete_entry, load_all, load_entry, save_entry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _list_kb_entries_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return {"entries": [e.model_dump() for e in load_all(resolved)]}


def _create_kb_entry_impl(home_id: str | None, title: str, content: str = "") -> dict:
    resolved = _resolve_home_id(home_id)
    now = _now()
    entry = KBEntry(id=str(uuid.uuid4()), title=title, content=content, createdAt=now, updatedAt=now)
    save_entry(resolved, entry)
    return entry.model_dump()


def _update_kb_entry_impl(
    home_id: str | None, entry_id: str, title: str | None = None, content: str | None = None,
) -> dict:
    resolved = _resolve_home_id(home_id)
    entry = load_entry(resolved, entry_id)
    if entry is None:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    if title is not None:
        entry.title = title
    if content is not None:
        entry.content = content
    entry.updatedAt = _now()
    save_entry(resolved, entry)
    return entry.model_dump()


def _delete_kb_entry_impl(home_id: str | None, entry_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    if not delete_entry(resolved, entry_id):
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    return {"deleted": entry_id}


@mcp.tool()
async def list_kb_entries(ctx: Context, home_id: str | None = None) -> dict:
    """List all knowledge base articles for a home. There is no server-side search --
    fetch the list and filter/search over titles and content yourself."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_kb_entries_impl(home_id)


@mcp.tool()
async def create_kb_entry(ctx: Context, title: str, home_id: str | None = None, content: str = "") -> dict:
    """Create a knowledge base article. content supports Markdown."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_kb_entry_impl(home_id, title, content)


@mcp.tool()
async def update_kb_entry(
    ctx: Context, entry_id: str, home_id: str | None = None, title: str | None = None, content: str | None = None,
) -> dict:
    """Update the title and/or content of a knowledge base article."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_kb_entry_impl(home_id, entry_id, title, content)


@mcp.tool()
async def delete_kb_entry(ctx: Context, entry_id: str, home_id: str | None = None) -> dict:
    """Delete a knowledge base article."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_kb_entry_impl(home_id, entry_id)

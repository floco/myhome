from __future__ import annotations

import uuid
from datetime import datetime, timezone

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_kb import KBEntry
from .persistence_kb import (
    delete_entry,
    empty_trash,
    list_trash,
    load_all,
    load_entry,
    next_order,
    restore_subtree,
    save_entry,
    soft_delete_subtree,
    would_create_cycle,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _live_entry(home_id: str, entry_id: str) -> KBEntry | None:
    entry = load_entry(home_id, entry_id)
    if entry is None or entry.deletedAt is not None:
        return None
    return entry


def _list_kb_entries_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return {"entries": [e.model_dump() for e in load_all(resolved)]}


def _create_kb_entry_impl(
    home_id: str | None, title: str, content: str = "", parent_id: str | None = None, icon: str = "📄",
) -> dict:
    resolved = _resolve_home_id(home_id)
    if parent_id is not None and _live_entry(resolved, parent_id) is None:
        raise ValueError(f"Unknown parent_id {parent_id!r}")
    now = _now()
    entry = KBEntry(
        id=str(uuid.uuid4()), title=title, content=content, parentId=parent_id, icon=icon,
        order=next_order(resolved, parent_id), createdAt=now, updatedAt=now,
    )
    save_entry(resolved, entry)
    return entry.model_dump()


def _update_kb_entry_impl(
    home_id: str | None, entry_id: str, title: str | None = None, content: str | None = None,
    icon: str | None = None,
) -> dict:
    resolved = _resolve_home_id(home_id)
    entry = _live_entry(resolved, entry_id)
    if entry is None:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    if title is not None:
        entry.title = title
    if content is not None:
        entry.content = content
    if icon is not None:
        entry.icon = icon
    entry.updatedAt = _now()
    save_entry(resolved, entry)
    return entry.model_dump()


def _move_kb_entry_impl(home_id: str | None, entry_id: str, parent_id: str | None = None) -> dict:
    resolved = _resolve_home_id(home_id)
    entry = _live_entry(resolved, entry_id)
    if entry is None:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    if parent_id is not None:
        if _live_entry(resolved, parent_id) is None:
            raise ValueError(f"Unknown parent_id {parent_id!r}")
        if would_create_cycle(resolved, entry_id, parent_id):
            raise ValueError("Cannot move a page into itself or a descendant")
    entry.parentId = parent_id
    entry.order = next_order(resolved, parent_id)
    entry.updatedAt = _now()
    save_entry(resolved, entry)
    return entry.model_dump()


def _delete_kb_entry_impl(home_id: str | None, entry_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    if _live_entry(resolved, entry_id) is None:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    deleted_ids = soft_delete_subtree(resolved, entry_id)
    return {"deleted": entry_id, "deletedCount": len(deleted_ids)}


def _list_kb_trash_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return {"entries": [e.model_dump() for e in list_trash(resolved)]}


def _restore_kb_entry_impl(home_id: str | None, entry_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    entry = load_entry(resolved, entry_id)
    if entry is None or entry.deletedAt is None:
        raise ValueError(f"Unknown trashed entry_id {entry_id!r}")
    restored_ids = restore_subtree(resolved, entry_id)
    return {"restored": entry_id, "restoredCount": len(restored_ids)}


def _permanently_delete_kb_entry_impl(home_id: str | None, entry_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    entry = load_entry(resolved, entry_id)
    if entry is None or entry.deletedAt is None:
        raise ValueError(f"Unknown trashed entry_id {entry_id!r}")
    delete_entry(resolved, entry_id)
    return {"deleted": entry_id}


def _empty_kb_trash_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    deleted_ids = empty_trash(resolved)
    return {"deletedCount": len(deleted_ids)}


@mcp.tool()
async def list_kb_entries(ctx: Context, home_id: str | None = None) -> dict:
    """List all knowledge base pages for a home. There is no server-side search --
    fetch the list and filter/search over titles and content yourself. Each page
    has a parent_id; pages with children display as folders in the UI."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_kb_entries_impl(home_id)


@mcp.tool()
async def create_kb_entry(
    ctx: Context, title: str, home_id: str | None = None, content: str = "",
    parent_id: str | None = None, icon: str = "📄",
) -> dict:
    """Create a knowledge base page. content supports Markdown. Optionally nest it
    under an existing page via parent_id (see list_kb_entries) -- the parent then
    displays as a folder in the UI."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_kb_entry_impl(home_id, title, content, parent_id, icon)


@mcp.tool()
async def update_kb_entry(
    ctx: Context, entry_id: str, home_id: str | None = None,
    title: str | None = None, content: str | None = None, icon: str | None = None,
) -> dict:
    """Update the title, content, and/or icon of a knowledge base page. To move it
    between parents, use move_kb_entry instead."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_kb_entry_impl(home_id, entry_id, title, content, icon)


@mcp.tool()
async def move_kb_entry(ctx: Context, entry_id: str, home_id: str | None = None, parent_id: str | None = None) -> dict:
    """Move a knowledge base page under parent_id, or to the top level if parent_id is omitted."""
    await _require_role(ctx.request_context.request, "normal")
    return _move_kb_entry_impl(home_id, entry_id, parent_id)


@mcp.tool()
async def delete_kb_entry(ctx: Context, entry_id: str, home_id: str | None = None) -> dict:
    """Delete a knowledge base page. This is a soft delete: the page and any child
    pages nested under it move to Trash and can be restored with restore_kb_entry
    until someone empties the trash."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_kb_entry_impl(home_id, entry_id)


@mcp.tool()
async def list_kb_trash(ctx: Context, home_id: str | None = None) -> dict:
    """List knowledge base pages currently in Trash."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_kb_trash_impl(home_id)


@mcp.tool()
async def restore_kb_entry(ctx: Context, entry_id: str, home_id: str | None = None) -> dict:
    """Restore a knowledge base page from Trash, along with any child pages that
    were trashed in the same delete."""
    await _require_role(ctx.request_context.request, "normal")
    return _restore_kb_entry_impl(home_id, entry_id)


@mcp.tool()
async def permanently_delete_kb_entry(ctx: Context, entry_id: str, home_id: str | None = None) -> dict:
    """Permanently delete a single knowledge base page from Trash. This cannot be undone."""
    await _require_role(ctx.request_context.request, "normal")
    return _permanently_delete_kb_entry_impl(home_id, entry_id)


@mcp.tool()
async def empty_kb_trash(ctx: Context, home_id: str | None = None) -> dict:
    """Permanently delete every knowledge base page currently in Trash. This cannot be undone."""
    await _require_role(ctx.request_context.request, "normal")
    return _empty_kb_trash_impl(home_id)

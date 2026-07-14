from __future__ import annotations

import uuid
from datetime import datetime, timezone

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_kb import KBEntry
from .persistence_kb import delete_entry, load_all, load_entry, save_entry
from .persistence_kb_folders import (
    create_folder,
    delete_folder,
    get_folder,
    list_folders,
    move_folder,
    rename_folder,
    would_create_cycle,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _list_kb_entries_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return {"entries": [e.model_dump() for e in load_all(resolved)]}


def _create_kb_entry_impl(
    home_id: str | None, title: str, content: str = "", folder_id: str | None = None,
) -> dict:
    resolved = _resolve_home_id(home_id)
    if folder_id is not None and get_folder(resolved, folder_id) is None:
        raise ValueError(f"Unknown folder_id {folder_id!r}")
    now = _now()
    entry = KBEntry(
        id=str(uuid.uuid4()), title=title, content=content, folderId=folder_id, createdAt=now, updatedAt=now,
    )
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


def _move_kb_entry_impl(home_id: str | None, entry_id: str, folder_id: str | None = None) -> dict:
    resolved = _resolve_home_id(home_id)
    entry = load_entry(resolved, entry_id)
    if entry is None:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    if folder_id is not None and get_folder(resolved, folder_id) is None:
        raise ValueError(f"Unknown folder_id {folder_id!r}")
    entry.folderId = folder_id
    entry.updatedAt = _now()
    save_entry(resolved, entry)
    return entry.model_dump()


def _delete_kb_entry_impl(home_id: str | None, entry_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    if not delete_entry(resolved, entry_id):
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    return {"deleted": entry_id}


def _list_kb_folders_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return {"folders": [f.model_dump() for f in list_folders(resolved)]}


def _create_kb_folder_impl(home_id: str | None, name: str, parent_id: str | None = None) -> dict:
    resolved = _resolve_home_id(home_id)
    if parent_id is not None and get_folder(resolved, parent_id) is None:
        raise ValueError(f"Unknown parent_id {parent_id!r}")
    return create_folder(resolved, name, parent_id).model_dump()


def _rename_kb_folder_impl(home_id: str | None, folder_id: str, name: str) -> dict:
    resolved = _resolve_home_id(home_id)
    folder = rename_folder(resolved, folder_id, name)
    if folder is None:
        raise ValueError(f"Unknown folder_id {folder_id!r}")
    return folder.model_dump()


def _move_kb_folder_impl(home_id: str | None, folder_id: str, parent_id: str | None = None) -> dict:
    resolved = _resolve_home_id(home_id)
    if parent_id is not None:
        if get_folder(resolved, parent_id) is None:
            raise ValueError(f"Unknown parent_id {parent_id!r}")
        if would_create_cycle(resolved, folder_id, parent_id):
            raise ValueError("Cannot move a folder into itself or a descendant")
    folder = move_folder(resolved, folder_id, parent_id)
    if folder is None:
        raise ValueError(f"Unknown folder_id {folder_id!r}")
    return folder.model_dump()


def _delete_kb_folder_impl(home_id: str | None, folder_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    subfolders = [f for f in list_folders(resolved) if f.parentId == folder_id]
    entries = [e for e in load_all(resolved) if e.folderId == folder_id]
    if subfolders or entries:
        raise ValueError("Folder must be empty before it can be deleted")
    if not delete_folder(resolved, folder_id):
        raise ValueError(f"Unknown folder_id {folder_id!r}")
    return {"deleted": folder_id}


@mcp.tool()
async def list_kb_entries(ctx: Context, home_id: str | None = None) -> dict:
    """List all knowledge base articles for a home. There is no server-side search --
    fetch the list and filter/search over titles and content yourself."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_kb_entries_impl(home_id)


@mcp.tool()
async def create_kb_entry(
    ctx: Context, title: str, home_id: str | None = None, content: str = "", folder_id: str | None = None,
) -> dict:
    """Create a knowledge base article. content supports Markdown. Optionally file it
    into an existing folder via folder_id (see list_kb_folders)."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_kb_entry_impl(home_id, title, content, folder_id)


@mcp.tool()
async def update_kb_entry(
    ctx: Context, entry_id: str, home_id: str | None = None, title: str | None = None, content: str | None = None,
) -> dict:
    """Update the title and/or content of a knowledge base article. To move it between
    folders, use move_kb_entry instead."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_kb_entry_impl(home_id, entry_id, title, content)


@mcp.tool()
async def move_kb_entry(ctx: Context, entry_id: str, home_id: str | None = None, folder_id: str | None = None) -> dict:
    """Move a knowledge base article into folder_id, or to the top level if folder_id is omitted."""
    await _require_role(ctx.request_context.request, "normal")
    return _move_kb_entry_impl(home_id, entry_id, folder_id)


@mcp.tool()
async def delete_kb_entry(ctx: Context, entry_id: str, home_id: str | None = None) -> dict:
    """Delete a knowledge base article."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_kb_entry_impl(home_id, entry_id)


@mcp.tool()
async def list_kb_folders(ctx: Context, home_id: str | None = None) -> dict:
    """List all knowledge base folders for a home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_kb_folders_impl(home_id)


@mcp.tool()
async def create_kb_folder(ctx: Context, name: str, home_id: str | None = None, parent_id: str | None = None) -> dict:
    """Create a knowledge base folder, optionally nested under parent_id (see list_kb_folders)."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_kb_folder_impl(home_id, name, parent_id)


@mcp.tool()
async def rename_kb_folder(ctx: Context, folder_id: str, name: str, home_id: str | None = None) -> dict:
    """Rename a knowledge base folder."""
    await _require_role(ctx.request_context.request, "normal")
    return _rename_kb_folder_impl(home_id, folder_id, name)


@mcp.tool()
async def move_kb_folder(ctx: Context, folder_id: str, home_id: str | None = None, parent_id: str | None = None) -> dict:
    """Move a knowledge base folder under parent_id, or to the top level if parent_id is omitted."""
    await _require_role(ctx.request_context.request, "normal")
    return _move_kb_folder_impl(home_id, folder_id, parent_id)


@mcp.tool()
async def delete_kb_folder(ctx: Context, folder_id: str, home_id: str | None = None) -> dict:
    """Delete an empty knowledge base folder (it must contain no entries or subfolders)."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_kb_folder_impl(home_id, folder_id)

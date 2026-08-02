"""Generic MCP tools for uploading, deleting, and fetching attachments across every
module that supports them. MCP tool arguments must be JSON, so file bytes travel as
a base64 string (data_base64) rather than the multipart upload the REST routes use;
this module base64-decodes and then calls the exact same persistence functions
(save_attachment/delete_attachment/get_attachment_path/generate_pdf_thumbnail) those
REST routes already use, so a file attached via MCP is indistinguishable on disk from
one uploaded through the web UI."""
from __future__ import annotations

import base64
import binascii
import mimetypes
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import Context, Image

from . import persistence_build as _bld
from . import persistence_chores as _chr
from . import persistence_costs as _cst
from . import persistence_insurance as _ins
from . import persistence_inventory as _inv
from . import persistence_kb as _kb
from . import persistence_properties as _prop
from . import persistence_works as _wrk
from .attachment_validation import (
    ALLOWED_EXTENSIONS,
    sanitise_filename,
    validate_filename,
    validate_id,
)
from .mcp_server import _require_role, _resolve_home_id, mcp


_IMAGE_FORMATS = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


Finder = Callable[[str, str], tuple[object | None, Callable[[], None]]]


@dataclass
class _ModuleAdapter:
    find: Finder
    save_attachment: Callable[[str, str, str, bytes], None]
    get_attachment_path: Callable[[str, str, str], Path]
    delete_attachment: Callable[[str, str, str], bool]
    generate_pdf_thumbnail: Callable[[Path, Path], None]


def _inventory_find(home_id: str, item_id: str):
    doc = _inv.load_inventory(home_id)
    item = next((i for i in doc.items if i.id == item_id), None)
    return item, (lambda: _inv.save_inventory(home_id, doc))


def _kb_find(home_id: str, item_id: str):
    entry = _kb.load_entry(home_id, item_id)
    if entry is None:
        return None, (lambda: None)

    def _save() -> None:
        entry.updatedAt = _now_iso()
        _kb.save_entry(home_id, entry)

    return entry, _save


def _works_find(home_id: str, item_id: str):
    doc = _wrk.load_works(home_id)
    item = next((w for w in doc.works if w.id == item_id), None)
    return item, (lambda: _wrk.save_works(home_id, doc))


def _costs_find(home_id: str, item_id: str):
    doc = _cst.load_costs(home_id)
    item = next((e for e in doc.entries if e.id == item_id), None)
    return item, (lambda: _cst.save_costs(home_id, doc))


def _properties_find(home_id: str, item_id: str):
    doc = _prop.load_properties(home_id)
    item = next((p for p in doc.properties if p.id == item_id), None)
    return item, (lambda: _prop.save_properties(home_id, doc))


def _build_find(home_id: str, item_id: str):
    doc = _bld.load_build(home_id)
    item = next((t for t in doc.tasks if t.id == item_id), None)
    return item, (lambda: _bld.save_build(home_id, doc))


def _chores_find(home_id: str, item_id: str):
    doc = _chr.load_chores(home_id)
    item = next((c for c in doc.chores if c.id == item_id), None)
    return item, (lambda: _chr.save_chores(home_id, doc))


def _insurance_find(home_id: str, item_id: str):
    doc = _ins.load_insurance(home_id)
    item = next((p for p in doc.policies if p.id == item_id), None)
    return item, (lambda: _ins.save_insurance(home_id, doc))


_MODULES: dict[str, _ModuleAdapter] = {
    "inventory": _ModuleAdapter(
        _inventory_find, _inv.save_attachment, _inv.get_attachment_path,
        _inv.delete_attachment, _inv.generate_pdf_thumbnail,
    ),
    "kb": _ModuleAdapter(
        _kb_find, _kb.save_attachment, _kb.get_attachment_path,
        _kb.delete_attachment, _kb.generate_pdf_thumbnail,
    ),
    "works": _ModuleAdapter(
        _works_find, _wrk.save_attachment, _wrk.get_attachment_path,
        _wrk.delete_attachment, _wrk.generate_pdf_thumbnail,
    ),
    "costs": _ModuleAdapter(
        _costs_find, _cst.save_attachment, _cst.get_attachment_path,
        _cst.delete_attachment, _cst.generate_pdf_thumbnail,
    ),
    "properties": _ModuleAdapter(
        _properties_find, _prop.save_attachment, _prop.get_attachment_path,
        _prop.delete_attachment, _prop.generate_pdf_thumbnail,
    ),
    "build": _ModuleAdapter(
        _build_find, _bld.save_attachment, _bld.get_attachment_path,
        _bld.delete_attachment, _bld.generate_pdf_thumbnail,
    ),
    "chores": _ModuleAdapter(
        _chores_find, _chr.save_attachment, _chr.get_attachment_path,
        _chr.delete_attachment, _chr.generate_pdf_thumbnail,
    ),
    "insurance": _ModuleAdapter(
        _insurance_find, _ins.save_attachment, _ins.get_attachment_path,
        _ins.delete_attachment, _ins.generate_pdf_thumbnail,
    ),
}


def _get_adapter(module: str) -> _ModuleAdapter:
    adapter = _MODULES.get(module)
    if adapter is None:
        raise ValueError(f"Unknown module {module!r}. Valid modules: {sorted(_MODULES)}")
    return adapter


def _upload_attachment_impl(
    home_id: str | None, module: str, item_id: str, filename: str, data_base64: str,
) -> dict:
    resolved = _resolve_home_id(home_id)
    adapter = _get_adapter(module)
    validate_id(item_id)
    item, save = adapter.find(resolved, item_id)
    if item is None:
        raise ValueError(f"Unknown item_id {item_id!r} for module {module!r}")
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type {ext!r} not supported. Allowed: {sorted(ALLOWED_EXTENSIONS)}")
    safe_filename = sanitise_filename(filename)
    validate_filename(safe_filename)
    try:
        data = base64.b64decode(data_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"Invalid base64 data: {exc}") from exc
    adapter.save_attachment(resolved, item_id, safe_filename, data)
    if ext == ".pdf":
        pdf_path = adapter.get_attachment_path(resolved, item_id, safe_filename)
        thumb_path = pdf_path.with_name(pdf_path.name + ".thumb.jpg")
        adapter.generate_pdf_thumbnail(pdf_path, thumb_path)
    if safe_filename not in item.attachments:
        item.attachments.append(safe_filename)
    save()
    return {"filename": safe_filename}


def _delete_attachment_impl(home_id: str | None, module: str, item_id: str, filename: str) -> dict:
    resolved = _resolve_home_id(home_id)
    adapter = _get_adapter(module)
    validate_id(item_id)
    validate_filename(filename)
    item, save = adapter.find(resolved, item_id)
    if item is None:
        raise ValueError(f"Unknown item_id {item_id!r} for module {module!r}")
    if not adapter.delete_attachment(resolved, item_id, filename):
        raise ValueError(f"Attachment {filename!r} not found")
    item.attachments = [a for a in item.attachments if a != filename]
    save()
    return {"deleted": filename}


def _get_attachment_impl(home_id: str | None, module: str, item_id: str, filename: str):
    resolved = _resolve_home_id(home_id)
    adapter = _get_adapter(module)
    validate_id(item_id)
    validate_filename(filename)
    item, _find_save = adapter.find(resolved, item_id)
    if item is None:
        raise ValueError(f"Unknown item_id {item_id!r} for module {module!r}")
    path = adapter.get_attachment_path(resolved, item_id, filename)
    if not path.is_file():
        raise ValueError(f"Attachment {filename!r} not found")
    ext = os.path.splitext(filename.lower())[1]
    if ext in _IMAGE_FORMATS:
        return Image(data=path.read_bytes(), format=_IMAGE_FORMATS[ext])
    mime, _ = mimetypes.guess_type(filename)
    return {
        "filename": filename,
        "mimeType": mime or "application/octet-stream",
        "size": path.stat().st_size,
        "note": "Binary preview isn't supported over MCP for this file type; view or download it from the web UI.",
    }


@mcp.tool()
async def upload_attachment(
    ctx: Context, module: str, item_id: str, filename: str, data_base64: str,
    home_id: str | None = None,
) -> dict:
    """Attach a file (photo or PDF) to an item. module: one of "inventory", "kb",
    "works", "costs", "properties", "build", "chores", "insurance" -- for "build",
    item_id is the task id (see list_build_tasks). filename must include its
    extension (.pdf, .jpg, .jpeg, .png, or .webp). data_base64 is the raw file
    bytes, base64-encoded (no data: URI prefix)."""
    await _require_role(ctx.request_context.request, "normal")
    return _upload_attachment_impl(home_id, module, item_id, filename, data_base64)


@mcp.tool()
async def delete_attachment(
    ctx: Context, module: str, item_id: str, filename: str, home_id: str | None = None,
) -> dict:
    """Remove an attachment from an item. See upload_attachment for valid module
    values."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_attachment_impl(home_id, module, item_id, filename)


@mcp.tool()
async def get_attachment(ctx: Context, module: str, item_id: str, filename: str, home_id: str | None = None):
    """Fetch an item's attachment. Images (.jpg/.jpeg/.png/.webp) are returned as an
    inline image; PDFs return metadata only (filename/mimeType/size) since there's no
    way to preview a PDF inline over MCP -- view or download PDFs via the web UI. See
    upload_attachment for valid module values."""
    await _require_role(ctx.request_context.request, "ro")
    return _get_attachment_impl(home_id, module, item_id, filename)

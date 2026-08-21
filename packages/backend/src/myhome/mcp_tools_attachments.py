"""Generic MCP tools for uploading, deleting, and fetching attachments across every
module that supports them. MCP tool arguments must be JSON, so file bytes travel as
a base64 string (data_base64) rather than the multipart upload the REST routes use;
this module base64-decodes and then calls the exact same per-module adapters
(attachment_modules.py) those REST routes use, so a file attached via MCP is
indistinguishable on disk from one uploaded through the web UI.

For anything but a small payload, prefer request_attachment_upload (a two-phase
flow: mint a short-lived upload URL here, then curl the file to it directly) --
inlining a whole file as base64 in a tool-call argument means the calling model
has to generate every base64 character as an output token, which is fine for a
few KB but becomes minutes-to-hours of generation time for a multi-MB photo."""
from __future__ import annotations

import base64
import binascii
import mimetypes
import os

from mcp.server.fastmcp import Context, Image
from starlette.requests import Request

from .attachment_modules import get_adapter
from .attachment_tokens import mint_download_token, mint_upload_token
from .attachment_validation import (
    ALLOWED_EXTENSIONS,
    sanitise_filename,
    validate_filename,
    validate_id,
)
from .mcp_server import _require_role, _resolve_home_id, mcp


_IMAGE_FORMATS = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}

# Below this size, get_attachment still inlines the image directly (cheap and
# convenient); at or above it, a download_url is returned instead so the
# agent fetches the bytes itself rather than paying to receive them as tokens.
_INLINE_IMAGE_MAX_BYTES = 50_000


def _base_url(request: Request | None) -> str:
    """Best-effort origin for building an absolute attachment upload/download
    URL from the incoming MCP request. Correct for a direct connection; behind
    a reverse proxy (e.g. Home Assistant ingress) that doesn't forward
    X-Forwarded-* headers, the scheme/host here may not match what's actually
    reachable from outside -- callers should substitute whatever host they
    used to reach this MCP server if this doesn't work, keeping the path."""
    if request is None:
        return ""
    return str(request.base_url).rstrip("/")


def _upload_attachment_impl(
    home_id: str | None, module: str, item_id: str, filename: str, data_base64: str,
) -> dict:
    resolved = _resolve_home_id(home_id)
    adapter = get_adapter(module)
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


def _request_attachment_upload_impl(
    request: Request | None, home_id: str | None, module: str, item_id: str, filename: str,
) -> dict:
    resolved = _resolve_home_id(home_id)
    adapter = get_adapter(module)
    validate_id(item_id)
    item, _save = adapter.find(resolved, item_id)
    if item is None:
        raise ValueError(f"Unknown item_id {item_id!r} for module {module!r}")
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type {ext!r} not supported. Allowed: {sorted(ALLOWED_EXTENSIONS)}")
    safe_filename = sanitise_filename(filename)
    validate_filename(safe_filename)
    token, expires_at = mint_upload_token(resolved, module, item_id, safe_filename)
    return {
        "upload_url": f"{_base_url(request)}/api/attachments/upload/{token}",
        "filename": safe_filename,
        "expires_at": expires_at.isoformat(),
    }


def _delete_attachment_impl(home_id: str | None, module: str, item_id: str, filename: str) -> dict:
    resolved = _resolve_home_id(home_id)
    adapter = get_adapter(module)
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


def _get_attachment_impl(request: Request | None, home_id: str | None, module: str, item_id: str, filename: str):
    resolved = _resolve_home_id(home_id)
    adapter = get_adapter(module)
    validate_id(item_id)
    validate_filename(filename)
    item, _find_save = adapter.find(resolved, item_id)
    if item is None:
        raise ValueError(f"Unknown item_id {item_id!r} for module {module!r}")
    path = adapter.get_attachment_path(resolved, item_id, filename)
    if not path.is_file():
        raise ValueError(f"Attachment {filename!r} not found")
    size = path.stat().st_size
    ext = os.path.splitext(filename.lower())[1]
    if ext in _IMAGE_FORMATS and size < _INLINE_IMAGE_MAX_BYTES:
        return Image(data=path.read_bytes(), format=_IMAGE_FORMATS[ext])
    mime, _ = mimetypes.guess_type(filename)
    token, expires_at = mint_download_token(resolved, module, item_id, filename)
    return {
        "filename": filename,
        "mimeType": mime or "application/octet-stream",
        "size": size,
        "download_url": f"{_base_url(request)}/api/attachments/download/{token}",
        "expires_at": expires_at.isoformat(),
    }


@mcp.tool()
async def upload_attachment(
    ctx: Context, module: str, item_id: str, filename: str, data_base64: str,
    home_id: str | None = None,
) -> dict:
    """Attach a file (photo or PDF) to an item by sending its bytes inline as
    base64. Only use this for small files (well under 1MB) -- data_base64 is a
    tool-call argument you have to generate character-by-character, so a
    multi-MB photo can take minutes to hours to produce this way. For anything
    bigger, call request_attachment_upload instead and curl the file directly.

    module: one of "inventory", "kb", "works", "costs", "properties", "build",
    "chores", "insurance", "locations" -- for "build", item_id is the task id (see
    list_build_tasks). filename must include its extension (.pdf, .jpg, .jpeg,
    .png, or .webp). data_base64 is the raw file bytes, base64-encoded (no
    data: URI prefix)."""
    await _require_role(ctx.request_context.request, "normal")
    return _upload_attachment_impl(home_id, module, item_id, filename, data_base64)


@mcp.tool()
async def request_attachment_upload(
    ctx: Context, module: str, item_id: str, filename: str, home_id: str | None = None,
) -> dict:
    """Get a one-time upload link for attaching a file to an item, without
    sending its bytes through this tool call -- the preferred way to attach
    anything but a tiny file (see upload_attachment for why).

    Returns upload_url, valid once for 10 minutes for exactly this file. From
    a shell, run: curl -X POST --data-binary @/path/to/file "<upload_url>"
    -- bytes go straight from local disk to the server. If that request
    fails to connect, your MCP client may be reaching this server through a
    proxy/tunnel with a different externally-visible host than the one in
    upload_url; retry with the scheme+host you use to reach this MCP server
    instead, keeping the rest of the URL as returned.

    See upload_attachment for valid module values and filename requirements."""
    await _require_role(ctx.request_context.request, "normal")
    return _request_attachment_upload_impl(ctx.request_context.request, home_id, module, item_id, filename)


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
    """Fetch an item's attachment. Small images (under 50KB) are returned inline;
    everything else (larger images, PDFs, etc.) returns metadata plus a
    download_url instead of inlining bytes -- run `curl -o <local_path>
    "<download_url>"` from a shell to fetch it (valid once, for 10 minutes). See
    upload_attachment for valid module values, and request_attachment_upload's
    docstring for what to do if download_url isn't reachable from where you're
    running (e.g. behind a proxy/tunnel)."""
    await _require_role(ctx.request_context.request, "ro")
    return _get_attachment_impl(ctx.request_context.request, home_id, module, item_id, filename)

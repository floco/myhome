# MCP attachment tools — design

## Problem

The myhome REST API supports uploading/downloading/deleting attachments (photos, PDFs)
on 8 modules — Inventory, KB, Works, Costs, Properties, Build (tasks), Chores, and
Insurance — via `multipart/form-data` upload endpoints that write files to disk and
store the resulting filename in the parent item's `attachments: list[str]`.

None of this is exposed over MCP. All ~63 `@mcp.tool()` functions across
`mcp_tools_*.py` return plain JSON dicts; none accept file/binary input or read
attachment bytes back out. An MCP client (e.g. an assistant with access to a camera
roll or downloaded file) has no way to attach a photo to an inventory item, work
order, KB page, etc.

## Goals

- Add MCP tools to upload, delete, and fetch attachments, covering all 8 modules that
  already support attachments in the REST API.
- Reuse the existing persistence layer (`save_attachment`, `delete_attachment`,
  `get_attachment_path`, `generate_pdf_thumbnail` in each `persistence_*.py`) and the
  same on-disk storage/thumbnail behavior — no schema or REST API changes.
- Keep the tool surface small: one generic tool per operation (upload/delete/get),
  dispatched by a `module` argument, rather than 24 near-duplicate per-module tools.

## Non-goals

- No new REST endpoints or DB schema changes.
- No attachment metadata model (id, mimeType, size, createdAt) — attachments remain
  identified by sanitized filename within a parent item's directory, exactly as today.
- No batch upload (one call per file, matching how the REST endpoint and frontend
  already work — one request per file).
- No file-size limit beyond what already exists (REST currently enforces none either).

## Design

### Transport constraint

The MCP server (`mcp_server.py`) runs FastMCP over **Streamable HTTP**, mounted at
`/mcp` in the main FastAPI app — not stdio. Tool arguments must be JSON-serializable;
there is no multipart/binary argument type in the MCP tool-call protocol, and the
client and server do not share a filesystem (this runs behind LAN/HA-ingress). So the
only viable input shape is a **base64-encoded string** parameter, mirroring how MCP's
own `Image`/`Audio` output helpers (`mcp.server.fastmcp.utilities.types`) already
base64-encode binary data for the wire.

### New file: `mcp_tools_attachments.py`

Three generic tools:

```python
@mcp.tool()
async def upload_attachment(
    ctx: Context, module: str, item_id: str, filename: str, data_base64: str,
    home_id: str | None = None,
) -> dict:  # {"filename": str}

@mcp.tool()
async def delete_attachment(
    ctx: Context, module: str, item_id: str, filename: str,
    home_id: str | None = None,
) -> dict:  # {"deleted": True}

@mcp.tool()
async def get_attachment(
    ctx: Context, module: str, item_id: str, filename: str,
    home_id: str | None = None,
) -> Image | dict:
```

Docstrings enumerate the valid `module` values (`inventory`, `kb`, `works`, `costs`,
`properties`, `build`, `chores`, `insurance`) and note that for `build`, `item_id` is
the task id.

Role checks match existing conventions: `upload`/`delete` require `_require_role(...,
"normal")`; `get` requires `"ro"`.

### Module registry / dispatch

7 of the 8 modules load a document containing a list (`doc.items`, `doc.works`,
`doc.tasks` for build, `doc.policies`, etc.) and find the item by id; KB is the
exception, loading/saving a single entry directly via `load_entry`/`save_entry`. To
normalize this, each module gets a small adapter function returning `(item,
save_callback)`, e.g.:

```python
def _inventory_adapter(home_id, item_id):
    doc = load_inventory(home_id)
    item = next((i for i in doc.items if i.id == item_id), None)
    return item, (lambda: save_inventory(home_id, doc))
```

All 8 adapters are collected in a `dict[str, ModuleAdapter]` keyed by module name.
Each tool looks up the adapter, calls it to get `(item, save_callback)`, checks
`item is not None`, then delegates to that module's already-imported
`persistence_<module>` functions for the actual file I/O — `save_attachment`,
`delete_attachment`, `get_attachment_path`, `generate_pdf_thumbnail` — exactly as the
REST routes do, followed by `item.attachments.append(filename)` /
`item.attachments.remove(filename)` and `save_callback()`.

An unknown `module` value raises `ValueError` listing the valid names.

### Validation

The REST routes each duplicate 4 helpers per file today (`_ALLOWED_EXTENSIONS =
{".pdf", ".jpg", ".jpeg", ".png", ".webp"}`, `_sanitise_filename`, `_validate_id`,
`_validate_filename`) — there's no shared module. Rather than refactor all 8 route
files (out of scope, unrelated to this feature), add one **new** shared module,
`attachment_validation.py`, with those same 4 helpers (same whitelist, same regexes),
used only by `mcp_tools_attachments.py`. Base64-decoded bytes are validated and
persisted through the exact same `save_attachment()` call the REST path uses, so a
file attached via MCP is indistinguishable on disk from one uploaded through the web
UI.

### `get_attachment` return shape

- For image extensions (`.jpg/.jpeg/.png/.webp`): returns an
  `mcp.server.fastmcp.utilities.types.Image` (constructed with the decoded bytes and
  detected mime type). FastMCP converts this into an `ImageContent` block, so the
  attachment comes back to the client as an actual inline image, not a base64 text
  dump.
- For `.pdf`: returns a plain dict `{"filename", "mimeType", "size", "note"}` where
  `note` points to viewing/downloading it via the web UI — there's no MCP content
  block for inline PDF rendering, and dumping raw base64 as text would be both
  unreadable and expensive in context.
- If the attachment file doesn't exist on disk, raises `ValueError`.

### Error handling

Matches the existing `_xxx_impl` convention used throughout the other `mcp_tools_*.py`
files (e.g. `_update_inventory_item_impl` raising `ValueError(f"Unknown item_id
{item_id!r}")`): plain `ValueError` with a descriptive message for unknown module,
invalid id/filename format, item not found, disallowed extension, invalid base64
payload, and attachment-not-found on delete/get. No new error-handling convention is
introduced.

## Testing

New `test_mcp_tools_attachments.py`:

- Happy path per module (all 8): `upload_attachment` → filename appears in the
  parent's `attachments` list → bytes on disk match the original (round-tripped
  through base64) → `delete_attachment` removes it from disk and from the list.
- `get_attachment` returns an `Image` for image types; returns the dict+note shape for
  `.pdf`.
- Error cases: unknown `module`, disallowed extension, invalid base64, missing
  item_id, missing attachment on delete/get.
- Build module specifically: confirm `item_id` maps to a task id, not a phase id.

## Open questions / risks

- Base64 inflates payload size ~33%; there's no size limit today (REST or MCP side).
  Not adding one now since it matches existing REST behavior, but very large files
  could hit MCP client-side request-size limits — not something this design can fix
  server-side.

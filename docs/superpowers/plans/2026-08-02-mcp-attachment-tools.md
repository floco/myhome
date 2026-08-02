# MCP Attachment Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let MCP clients upload, delete, and fetch attachments (photos, PDFs) on the 8 modules that already support attachments in the REST API (Inventory, KB, Works, Costs, Properties, Build tasks, Chores, Insurance).

**Architecture:** One new shared validation module (`attachment_validation.py`) plus one new MCP tool module (`mcp_tools_attachments.py`) exposing 3 generic tools — `upload_attachment`, `delete_attachment`, `get_attachment` — dispatched by a `module: str` argument to a small per-module adapter registry. Each adapter delegates to that module's existing `persistence_<module>.py` functions (`save_attachment`, `delete_attachment`, `get_attachment_path`, `generate_pdf_thumbnail`), the exact same functions the REST upload routes already use. No REST/DB changes.

**Tech Stack:** Python 3.12, FastAPI, `mcp` SDK (`mcp.server.fastmcp`, pinned `>=1.28,<2`), pytest.

Design doc: `docs/superpowers/specs/2026-08-02-mcp-attachment-tools-design.md`.

## Global Constraints

- MCP tool arguments must be JSON-serializable — no multipart/binary argument type exists in the MCP tool-call protocol. File bytes travel as a base64-encoded `str` parameter (`data_base64`), decoded server-side.
- Allowed attachment extensions: `{".pdf", ".jpg", ".jpeg", ".png", ".webp"}` — same whitelist the REST routes already enforce. No new extensions, no size limit (REST enforces none either).
- Role checks match existing tool conventions: mutating tools (`upload_attachment`, `delete_attachment`) require `_require_role(..., "normal")`; read-only (`get_attachment`) requires `_require_role(..., "ro")`.
- **`get_attachment` must NOT have a `-> Image | dict` (or any `Image`-containing) return type annotation.** Verified empirically: FastMCP's `Tool.from_function` builds a pydantic output-schema model from the return annotation at decoration time, and `Image` isn't a pydantic-compatible type — annotating the return type this way raises `PydanticSchemaGenerationError` **at import time** (i.e. `mcp_app.py` would crash on startup, taking down the whole MCP server, not just this tool). Omitting the return annotation entirely avoids schema generation for the return value, and FastMCP still correctly converts a returned `Image` instance into an `ImageContent` block at call time regardless of the annotation — confirmed by calling `mcp.call_tool(...)` directly against a throwaway `Image`-returning tool during design research.
- Follow the existing `_xxx_impl(...)` / `@mcp.tool() async def xxx(ctx, ...)` split used throughout `mcp_tools_*.py`: the plain sync `_impl` function does the work and raises `ValueError` on any user-facing error; the `async def` wrapper does the role check then delegates. Tests target the `_impl` functions directly (see `test_mcp_tools_inventory.py` for the established pattern), not the async wrappers.

---

## File Structure

- **Create** `packages/backend/src/myhome/attachment_validation.py` — shared `ALLOWED_EXTENSIONS`, `sanitise_filename`, `validate_id`, `validate_filename`. New file rather than reusing any route file's private copies (each `routes/*.py` already duplicates these independently; adding a 9th private copy inside `mcp_tools_attachments.py` would be one more duplicate of a pattern already established 8 times, but a small shared module is cleaner for the new code without touching the 8 existing route files).
- **Create** `packages/backend/tests/test_attachment_validation.py`
- **Create** `packages/backend/src/myhome/mcp_tools_attachments.py` — the module adapter registry and all 3 tools.
- **Create** `packages/backend/tests/test_mcp_tools_attachments.py`
- **Modify** `packages/backend/src/myhome/mcp_app.py` — register the new module for its `@mcp.tool()` side effects.

---

## Task 1: Shared attachment validation helpers

**Files:**
- Create: `packages/backend/src/myhome/attachment_validation.py`
- Test: `packages/backend/tests/test_attachment_validation.py`

**Interfaces:**
- Produces: `ALLOWED_EXTENSIONS: set[str]`, `sanitise_filename(name: str) -> str`, `validate_id(value: str) -> None` (raises `ValueError`), `validate_filename(filename: str) -> None` (raises `ValueError`) — all consumed by Task 2/3/4.

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_attachment_validation.py`:

```python
import pytest

from myhome.attachment_validation import (
    ALLOWED_EXTENSIONS,
    sanitise_filename,
    validate_filename,
    validate_id,
)


def test_allowed_extensions():
    assert ALLOWED_EXTENSIONS == {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


def test_sanitise_filename_strips_spaces_and_unsafe_chars():
    assert sanitise_filename("my photo (1).JPG") == "my_photo_1.JPG"


def test_sanitise_filename_falls_back_when_result_is_empty():
    assert sanitise_filename("???") == "attachment"


def test_validate_id_accepts_valid_id():
    validate_id("abc-123_XYZ")  # must not raise


def test_validate_id_rejects_path_traversal():
    with pytest.raises(ValueError):
        validate_id("../etc/passwd")


def test_validate_filename_accepts_valid_filename():
    validate_filename("photo.jpg")  # must not raise


def test_validate_filename_rejects_leading_dot():
    with pytest.raises(ValueError):
        validate_filename(".hidden")


def test_validate_filename_rejects_path_separator():
    with pytest.raises(ValueError):
        validate_filename("a/b.jpg")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest packages/backend/tests/test_attachment_validation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.attachment_validation'`

- [ ] **Step 3: Write the implementation**

Create `packages/backend/src/myhome/attachment_validation.py`:

```python
"""Shared filename/id validation for MCP attachment tools. The REST attachment
routes (routes/inventory.py etc.) each already duplicate an identical set of these
helpers per file; this is the one shared copy used by mcp_tools_attachments.py so
it doesn't need to import a private helper out of an unrelated route module."""
from __future__ import annotations

import re

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}

_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
_FILENAME_RE = re.compile(r"[A-Za-z0-9._-]+")


def sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"


def validate_id(value: str) -> None:
    if not _ID_RE.fullmatch(value):
        raise ValueError(f"Invalid id {value!r}")


def validate_filename(filename: str) -> None:
    if not _FILENAME_RE.fullmatch(filename) or filename.startswith("."):
        raise ValueError(f"Invalid filename {filename!r}")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest packages/backend/tests/test_attachment_validation.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/attachment_validation.py packages/backend/tests/test_attachment_validation.py
git commit -m "feat(backend): add shared attachment filename/id validation helpers"
```

---

## Task 2: Module registry + `upload_attachment` tool

**Files:**
- Create: `packages/backend/src/myhome/mcp_tools_attachments.py`
- Modify: `packages/backend/src/myhome/mcp_app.py`
- Test: `packages/backend/tests/test_mcp_tools_attachments.py`

**Interfaces:**
- Consumes: `ALLOWED_EXTENSIONS`, `sanitise_filename`, `validate_id`, `validate_filename` from `myhome.attachment_validation` (Task 1); `_require_role`, `_resolve_home_id`, `mcp` from `myhome.mcp_server`; each module's `load_*`/`save_*`/`save_attachment`/`get_attachment_path`/`delete_attachment`/`generate_pdf_thumbnail` from its `persistence_*.py`.
- Produces (consumed by Tasks 3 & 4, same file): `_ModuleAdapter` dataclass, `_MODULES: dict[str, _ModuleAdapter]`, `_get_adapter(module: str) -> _ModuleAdapter` (raises `ValueError`), `_now_iso() -> str`, `_upload_attachment_impl(home_id, module, item_id, filename, data_base64) -> dict`.

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_mcp_tools_attachments.py`:

```python
import base64

import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


_ALL_MODULES = [
    "inventory", "kb", "works", "costs", "properties", "build", "chores", "insurance",
]


def _make_item(home_id: str, module: str) -> str:
    """Create one parent item in `module` and return its id (a task id for
    'build')."""
    if module == "inventory":
        from myhome.mcp_tools_inventory import _create_inventory_item_impl
        return _create_inventory_item_impl(home_id, "Drill")["id"]
    if module == "kb":
        from myhome.mcp_tools_kb import _create_kb_entry_impl
        return _create_kb_entry_impl(home_id, "Page")["id"]
    if module == "works":
        from myhome.mcp_tools_works import _create_work_impl
        return _create_work_impl(home_id, "Roof repair", "2026-01-01")["id"]
    if module == "costs":
        from myhome.mcp_tools_costs import _create_cost_entry_impl
        return _create_cost_entry_impl(home_id, "cat1", "2026-01-01", 100.0)["id"]
    if module == "properties":
        from myhome.mcp_tools_properties import _create_property_impl
        return _create_property_impl(home_id, "Lakeview", "house")["id"]
    if module == "build":
        from myhome.build_template import seed_default_build
        from myhome.mcp_tools_build import _create_build_task_impl
        from myhome.persistence_build import load_build, save_build
        save_build(home_id, seed_default_build())
        phase_id = load_build(home_id).phases[0].id
        return _create_build_task_impl(home_id, phase_id, "Frame walls")["id"]
    if module == "chores":
        from myhome.mcp_tools_chores import _create_chore_impl
        return _create_chore_impl(home_id, "Mow lawn", "🌱", 7, "2026-01-01")["id"]
    if module == "insurance":
        from myhome.mcp_tools_insurance import _create_insurance_policy_impl
        return _create_insurance_policy_impl(home_id, "Home Policy", "cat1")["id"]
    raise ValueError(module)


@pytest.mark.parametrize("module", _ALL_MODULES)
def test_upload_attachment_adds_filename_to_item(home_id, module):
    from myhome.mcp_tools_attachments import _MODULES, _upload_attachment_impl
    item_id = _make_item(home_id, module)
    data = base64.b64encode(b"fake-bytes").decode()
    result = _upload_attachment_impl(home_id, module, item_id, "photo.jpg", data)
    assert result == {"filename": "photo.jpg"}
    item, _save = _MODULES[module].find(home_id, item_id)
    assert "photo.jpg" in item.attachments


@pytest.mark.parametrize("module", _ALL_MODULES)
def test_upload_attachment_writes_original_bytes_to_disk(home_id, module):
    from myhome.mcp_tools_attachments import _MODULES, _upload_attachment_impl
    item_id = _make_item(home_id, module)
    original = b"fake-bytes-for-" + module.encode()
    data = base64.b64encode(original).decode()
    _upload_attachment_impl(home_id, module, item_id, "doc.pdf", data)
    path = _MODULES[module].get_attachment_path(home_id, item_id, "doc.pdf")
    assert path.read_bytes() == original


def test_upload_attachment_unknown_module_raises(home_id):
    from myhome.mcp_tools_attachments import _upload_attachment_impl
    data = base64.b64encode(b"x").decode()
    with pytest.raises(ValueError, match="Unknown module"):
        _upload_attachment_impl(home_id, "not-a-module", "x", "a.jpg", data)


def test_upload_attachment_unknown_item_id_raises(home_id):
    from myhome.mcp_tools_attachments import _upload_attachment_impl
    data = base64.b64encode(b"x").decode()
    with pytest.raises(ValueError, match="Unknown item_id"):
        _upload_attachment_impl(home_id, "inventory", "nonexistent", "a.jpg", data)


def test_upload_attachment_disallowed_extension_raises(home_id):
    from myhome.mcp_tools_attachments import _upload_attachment_impl
    from myhome.mcp_tools_inventory import _create_inventory_item_impl
    item_id = _create_inventory_item_impl(home_id, "Drill")["id"]
    data = base64.b64encode(b"x").decode()
    with pytest.raises(ValueError, match="not supported"):
        _upload_attachment_impl(home_id, "inventory", item_id, "malware.exe", data)


def test_upload_attachment_invalid_base64_raises(home_id):
    from myhome.mcp_tools_attachments import _upload_attachment_impl
    from myhome.mcp_tools_inventory import _create_inventory_item_impl
    item_id = _create_inventory_item_impl(home_id, "Drill")["id"]
    with pytest.raises(ValueError, match="Invalid base64"):
        _upload_attachment_impl(home_id, "inventory", item_id, "photo.jpg", "not valid base64!!")


def test_upload_attachment_bumps_kb_updated_at(home_id):
    from myhome.mcp_tools_attachments import _upload_attachment_impl
    from myhome.mcp_tools_kb import _create_kb_entry_impl
    from myhome.persistence_kb import load_entry
    entry = _create_kb_entry_impl(home_id, "Page")
    data = base64.b64encode(b"x").decode()
    _upload_attachment_impl(home_id, "kb", entry["id"], "photo.jpg", data)
    reloaded = load_entry(home_id, entry["id"])
    assert reloaded.updatedAt != entry["updatedAt"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest packages/backend/tests/test_mcp_tools_attachments.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.mcp_tools_attachments'`

- [ ] **Step 3: Write the implementation**

Create `packages/backend/src/myhome/mcp_tools_attachments.py`:

```python
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
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import Context

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
```

- [ ] **Step 4: Register the module in `mcp_app.py`**

In `packages/backend/src/myhome/mcp_app.py`, add `mcp_tools_attachments` to the
alphabetized import list:

```python
from . import (  # noqa: F401 - imported for the side effect of registering tools
    mcp_tools_attachments,
    mcp_tools_build,
    mcp_tools_chores,
    mcp_tools_consumables,
    mcp_tools_contacts,
    mcp_tools_costs,
    mcp_tools_homes,
    mcp_tools_insurance,
    mcp_tools_inventory,
    mcp_tools_kb,
    mcp_tools_locations,
    mcp_tools_properties,
    mcp_tools_settings,
    mcp_tools_works,
)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest packages/backend/tests/test_mcp_tools_attachments.py -v`
Expected: PASS (21 tests: 8 modules × 2 parametrized tests + 4 error cases + 1 KB-specific)

- [ ] **Step 6: Run the full backend suite to check nothing else broke**

Run: `pytest packages/backend`
Expected: PASS (all tests, including the pre-existing suite)

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_attachments.py packages/backend/src/myhome/mcp_app.py packages/backend/tests/test_mcp_tools_attachments.py
git commit -m "feat(backend): add generic upload_attachment MCP tool across all 8 attachment-capable modules"
```

---

## Task 3: `delete_attachment` tool

**Files:**
- Modify: `packages/backend/src/myhome/mcp_tools_attachments.py`
- Modify: `packages/backend/tests/test_mcp_tools_attachments.py`

**Interfaces:**
- Consumes: `_get_adapter`, `_MODULES`, `validate_id`, `validate_filename` from Task 2 (same file).
- Produces: `_delete_attachment_impl(home_id, module, item_id, filename) -> dict` (consumed by Task 4's tests only incidentally, no other task depends on it).

- [ ] **Step 1: Write the failing tests**

Append to `packages/backend/tests/test_mcp_tools_attachments.py`:

```python
@pytest.mark.parametrize("module", _ALL_MODULES)
def test_delete_attachment_removes_filename_and_file(home_id, module):
    from myhome.mcp_tools_attachments import (
        _MODULES,
        _delete_attachment_impl,
        _upload_attachment_impl,
    )
    item_id = _make_item(home_id, module)
    data = base64.b64encode(b"fake-bytes").decode()
    _upload_attachment_impl(home_id, module, item_id, "photo.jpg", data)

    result = _delete_attachment_impl(home_id, module, item_id, "photo.jpg")

    assert result == {"deleted": "photo.jpg"}
    item, _save = _MODULES[module].find(home_id, item_id)
    assert "photo.jpg" not in item.attachments
    path = _MODULES[module].get_attachment_path(home_id, item_id, "photo.jpg")
    assert not path.is_file()


def test_delete_attachment_unknown_item_id_raises(home_id):
    from myhome.mcp_tools_attachments import _delete_attachment_impl
    with pytest.raises(ValueError, match="Unknown item_id"):
        _delete_attachment_impl(home_id, "inventory", "nonexistent", "photo.jpg")


def test_delete_attachment_missing_file_raises(home_id):
    from myhome.mcp_tools_attachments import _delete_attachment_impl
    from myhome.mcp_tools_inventory import _create_inventory_item_impl
    item_id = _create_inventory_item_impl(home_id, "Drill")["id"]
    with pytest.raises(ValueError, match="not found"):
        _delete_attachment_impl(home_id, "inventory", item_id, "nonexistent.jpg")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest packages/backend/tests/test_mcp_tools_attachments.py -v -k delete_attachment`
Expected: FAIL — `ImportError: cannot import name '_delete_attachment_impl'`

- [ ] **Step 3: Write the implementation**

Append to `packages/backend/src/myhome/mcp_tools_attachments.py` (after
`_upload_attachment_impl` and before the `upload_attachment` tool, or anywhere
below the registry — exact position doesn't matter, but keep impl functions grouped
together above the `@mcp.tool()` wrappers for readability):

```python
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
```

And add the tool wrapper at the end of the file, after `upload_attachment`:

```python
@mcp.tool()
async def delete_attachment(
    ctx: Context, module: str, item_id: str, filename: str, home_id: str | None = None,
) -> dict:
    """Remove an attachment from an item. See upload_attachment for valid module
    values."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_attachment_impl(home_id, module, item_id, filename)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest packages/backend/tests/test_mcp_tools_attachments.py -v -k delete_attachment`
Expected: PASS (10 tests: 8 modules + 2 error cases)

- [ ] **Step 5: Run the full backend suite**

Run: `pytest packages/backend`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_attachments.py packages/backend/tests/test_mcp_tools_attachments.py
git commit -m "feat(backend): add delete_attachment MCP tool"
```

---

## Task 4: `get_attachment` tool

**Files:**
- Modify: `packages/backend/src/myhome/mcp_tools_attachments.py`
- Modify: `packages/backend/tests/test_mcp_tools_attachments.py`

**Interfaces:**
- Consumes: `_get_adapter`, `validate_id`, `validate_filename` from Task 2/3 (same file); `mcp.server.fastmcp.Image`.
- Produces: `_get_attachment_impl(home_id, module, item_id, filename) -> Image | dict` (no other task depends on this; it's the final tool in the file).

- [ ] **Step 1: Write the failing tests**

Append to `packages/backend/tests/test_mcp_tools_attachments.py`:

```python
def test_get_attachment_image_returns_image(home_id):
    from mcp.server.fastmcp import Image
    from myhome.mcp_tools_attachments import _get_attachment_impl, _upload_attachment_impl
    from myhome.mcp_tools_inventory import _create_inventory_item_impl

    item_id = _create_inventory_item_impl(home_id, "Drill")["id"]
    original = b"\xff\xd8\xff-fake-jpeg-bytes"
    _upload_attachment_impl(home_id, "inventory", item_id, "photo.jpg", base64.b64encode(original).decode())

    result = _get_attachment_impl(home_id, "inventory", item_id, "photo.jpg")

    assert isinstance(result, Image)
    assert result.data == original
    content = result.to_image_content()
    assert content.mimeType == "image/jpeg"
    assert base64.b64decode(content.data) == original


def test_get_attachment_pdf_returns_metadata_dict(home_id):
    from myhome.mcp_tools_attachments import _get_attachment_impl, _upload_attachment_impl
    from myhome.mcp_tools_inventory import _create_inventory_item_impl

    item_id = _create_inventory_item_impl(home_id, "Drill")["id"]
    original = b"%PDF-1.4 fake pdf bytes"
    _upload_attachment_impl(home_id, "inventory", item_id, "manual.pdf", base64.b64encode(original).decode())

    result = _get_attachment_impl(home_id, "inventory", item_id, "manual.pdf")

    assert result["filename"] == "manual.pdf"
    assert result["mimeType"] == "application/pdf"
    assert result["size"] == len(original)
    assert "web UI" in result["note"]


def test_get_attachment_missing_file_raises(home_id):
    from myhome.mcp_tools_attachments import _get_attachment_impl
    from myhome.mcp_tools_inventory import _create_inventory_item_impl
    item_id = _create_inventory_item_impl(home_id, "Drill")["id"]
    with pytest.raises(ValueError, match="not found"):
        _get_attachment_impl(home_id, "inventory", item_id, "nonexistent.jpg")


def test_get_attachment_unknown_module_raises(home_id):
    from myhome.mcp_tools_attachments import _get_attachment_impl
    with pytest.raises(ValueError, match="Unknown module"):
        _get_attachment_impl(home_id, "not-a-module", "x", "photo.jpg")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest packages/backend/tests/test_mcp_tools_attachments.py -v -k get_attachment`
Expected: FAIL — `ImportError: cannot import name '_get_attachment_impl'`

- [ ] **Step 3: Write the implementation**

Add the import at the top of `packages/backend/src/myhome/mcp_tools_attachments.py`
(extend the existing `from mcp.server.fastmcp import Context` line):

```python
import mimetypes

from mcp.server.fastmcp import Context, Image
```

Add near the top of the file, alongside the other module-level constants:

```python
_IMAGE_FORMATS = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}
```

Add the impl function (grouped with the other `_xxx_impl` functions):

```python
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
```

Add the tool wrapper at the end of the file. Note the **missing return type
annotation is intentional** — see the Global Constraints section above:

```python
@mcp.tool()
async def get_attachment(ctx: Context, module: str, item_id: str, filename: str, home_id: str | None = None):
    """Fetch an item's attachment. Images (.jpg/.jpeg/.png/.webp) are returned as an
    inline image; PDFs return metadata only (filename/mimeType/size) since there's no
    way to preview a PDF inline over MCP -- view or download PDFs via the web UI. See
    upload_attachment for valid module values."""
    await _require_role(ctx.request_context.request, "ro")
    return _get_attachment_impl(home_id, module, item_id, filename)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest packages/backend/tests/test_mcp_tools_attachments.py -v -k get_attachment`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the full backend suite**

Run: `pytest packages/backend`
Expected: PASS (every test in the backend suite, old and new)

- [ ] **Step 6: Manually verify the MCP server still boots**

Run: `cd packages/backend && python -c "from myhome.mcp_app import mcp_asgi_app; print('OK')"`
Expected: prints `OK` with no traceback — this is the check that would have caught
the `Image | dict` return-annotation crash described in Global Constraints, since
that error only surfaces at tool-registration time (i.e. at import), not at test
time if a test happens to import the module in a way that skips decoration... in
practice `mcp_tools_attachments.py` is always fully executed on import so pytest
already exercises this, but this step double-checks the exact import path
`mcp_app.py` uses in production.

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_attachments.py packages/backend/tests/test_mcp_tools_attachments.py
git commit -m "feat(backend): add get_attachment MCP tool with inline image / PDF-metadata response"
```

---

## Self-Review Notes

- **Spec coverage:** All 3 tools (upload/delete/get) × all 8 modules covered by the registry; base64 transport, extension whitelist, filename sanitization, role checks, KB `updatedAt` bump, image-vs-PDF `get_attachment` behavior, and the `Image` return-annotation pitfall are all implemented and tested.
- **Type consistency:** `_ModuleAdapter.find` returns `(item | None, save_callback)` consistently across all 8 adapters and all 3 impl functions that call it. `_get_adapter`/`_MODULES`/`ALLOWED_EXTENSIONS`/`sanitise_filename`/`validate_id`/`validate_filename` are named identically everywhere they're used across Tasks 2-4.
- **No placeholders:** every step has complete, runnable code — no TBD/TODO or "similar to Task N" shortcuts.

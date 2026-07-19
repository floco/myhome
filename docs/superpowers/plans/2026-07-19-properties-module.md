# Properties Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `#/properties` placeholder with a real tool for tracking individual property listings (land / existing house / new-build) during a house search — price, size, pros/cons, pipeline status, optional link to a Locations entry, and photo attachments.

**Architecture:** A standalone module following the existing Works/Costs pattern exactly — new backend files (models, persistence, routes, MCP tools) backed by a new SQL table, plus new frontend files (store, page, modal, home widget), wired into the existing multi-home / nav / routing infrastructure. No floor-plan integration and no manual reordering (properties are prospective, not the user's own home; the table is sortable client-side instead).

**Tech Stack:** FastAPI + Pydantic + SQLAlchemy (SQLite) on the backend; Svelte 5 (runes) + Vitest on the frontend. No new dependencies.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-19-properties-module-design.md` — read it before starting; every task below implements a piece of it.
- Persistence is SQLite via SQLAlchemy Core, **not** JSON files: a `properties` `Table` in `schema.py`, and `load_properties`/`save_properties` functions that truncate-and-reinsert all rows for a `home_id` on every save (identical pattern to `persistence_works.py`). `metadata.create_all()` (called from `db.get_engine()`) picks up the new table automatically — no Alembic, no `migrations.py` entry needed for an additive table.
- `Property` fields (see spec §1 for the full type): `id, name, emoji="🏠", type: "land"|"house"|"new_build", status: "watching"|"visited"|"proposal_made"|"purchased"|"rejected"="watching", locationId: str|None, address="", price: float|None, landSize: float|None, builtSize: float|None, bedrooms: int|None, bathrooms: int|None, listingUrl: str|None, contact="", pros: list[str]=[], cons: list[str]=[], notes="", attachments: list[str]=[]`. `pros`/`cons`/`attachments` are stored as JSON-encoded `Text` columns, same as `attachments` on `works`/`cost_entries`.
- `locationId` is a soft reference (no `ForeignKey`, not validated against the Locations document at write time) — same convention as `Work.categoryId`/`Work.supplierId`. The frontend resolves it for display and shows "—" if the referenced location no longer exists.
- Every module that calls `log_activity(..., module, ...)` needs that module name in two places or it breaks: `ActivityEntry.module` (a closed `Literal` in `models_activity.py` — an unlisted value raises `pydantic.ValidationError` on `log_activity`, which the route does not catch, so create/update/delete would 500) and `MODULE_NOUNS` (a plain `dict` in `persistence_activity.py`, indexed with `[entry.module]` with **no** `.get()` fallback in `describe()` — a missing key raises `KeyError` when the Activity Log page is viewed, 500ing the *entire* log for that home, not just hiding that module's entries). Task 2 adds `"properties"` to both, and also fixes a pre-existing gap where `"locations"` was added to the `Literal` when that module shipped but never added to `MODULE_NOUNS` — a real, currently-reachable bug, fixed here as a one-line drive-by since we're already editing this exact file for the same reason.
- `mcp_tools_properties.py` (Task 4) registers its `@mcp.tool()`-decorated functions on the shared `mcp` singleton purely as an import side effect — creating the file does nothing on its own. It **must** also be added to the import tuple in `mcp_app.py`, exactly like `mcp_tools_works` etc. already are.
- **Attachment URL bug to avoid, not copy:** `WorkModal.svelte`, `InventoryModal.svelte`, `CostsEntryModal.svelte`, `ChoreEditModal.svelte`, and `KBPage.svelte` all build their `MediaGallery`/`Lightbox` image URLs as `` apiUrl(`/api/works/${id}/attachments/${name}`) `` — omitting the `/homes/{home_id}/` prefix the backend routes actually require (confirmed: no such prefix-less route exists in any `routes/*.py` file). This is a pre-existing bug in five other modals (broken thumbnails/lightbox images) that is out of scope to fix here. `PropertyModal.svelte` (Task 6) must **not** reproduce it: import the `homesStore` singleton directly (`import { homesStore } from "../homesStore.svelte";`, exactly as `SettingsGeneral.svelte`/`SettingsActivityLog.svelte` already do) and build attachment URLs as `` apiUrl(`/api/homes/${homesStore.activeHomeId}/properties/${property.id}/attachments/${fname}`) ``.
- Per this repo's known Svelte 5 + jsdom testing gotcha: components under test must be mounted to a node attached to `document.body`, and any manually-dispatched DOM events need `bubbles: true`, or handlers silently never fire.
- Backend tests run from `packages/backend` (`python -m pytest ...`); frontend tests run from `packages/editor` (`npx vitest run ...`).

---

### Task 1: Backend data layer — schema, models, persistence

**Files:**
- Modify: `packages/backend/src/myhome/schema.py` (append 1 table at end of file, after `location_ratings`)
- Create: `packages/backend/src/myhome/models_properties.py`
- Create: `packages/backend/src/myhome/persistence_properties.py`
- Test: `packages/backend/tests/test_properties_persistence.py`

**Interfaces:**
- Produces: `Property(id, name, emoji="🏠", type, status="watching", locationId=None, address="", price=None, landSize=None, builtSize=None, bedrooms=None, bathrooms=None, listingUrl=None, contact="", pros=[], cons=[], notes="", attachments=[])`, `PropertiesDocument(version=1, properties=[])`, `PropertyCreate`, `PropertyUpdate` — all in `models_properties.py`.
- Produces: `load_properties(home_id) -> PropertiesDocument`, `save_properties(home_id, doc) -> None`, `get_attachment_path(home_id, property_id, filename) -> Path`, `save_attachment(home_id, property_id, filename, data: bytes) -> None`, `delete_attachment(home_id, property_id, filename) -> bool`, `delete_all_attachments(home_id, property_id) -> None`, `generate_pdf_thumbnail(pdf_path, thumb_path) -> None` — all in `persistence_properties.py`. Consumed by Tasks 2, 3, 4.

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_properties_persistence.py`:

```python
from myhome.models_properties import Property, PropertiesDocument
from myhome.persistence_properties import (
    delete_attachment,
    get_attachment_path,
    load_properties,
    save_attachment,
    save_properties,
)

HOME_ID = "test-home"


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)
    # Per-home tables FK-reference homes.id (for cascade-delete-on-home-
    # delete), so a row must exist there before any per-home table insert.
    from myhome.db import get_engine
    from myhome.schema import homes as homes_table
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(homes_table.insert().values(
            id=HOME_ID, name="Test Home", type="existing", created_at="2026-01-01T00:00:00+00:00",
        ))


def make_doc() -> PropertiesDocument:
    return PropertiesDocument(
        properties=[Property(id="p1", name="Casa da Rua das Flores", type="house", status="watching")]
    )


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = load_properties(HOME_ID)
    assert doc.properties == []


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_properties(HOME_ID, make_doc())
    loaded = load_properties(HOME_ID)
    p = loaded.properties[0]
    assert p.id == "p1"
    assert p.name == "Casa da Rua das Flores"
    assert p.type == "house"
    assert p.status == "watching"
    assert p.pros == []
    assert p.cons == []
    assert p.attachments == []


def test_round_trip_preserves_full_fields_and_order(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = PropertiesDocument(properties=[
        Property(
            id="p1", name="Terreno Norte", type="land", status="proposal_made",
            locationId="loc1", address="Rua Norte 5", price=90000.0, landSize=850.0,
            listingUrl="https://example.com/listing", contact="Maria, +351 912 345 678",
            pros=["Great light", "Walk to town"], cons=["No garage"], notes="Needs survey",
        ),
        Property(id="p2", name="Casa Sul", type="house", status="watching"),
    ])
    save_properties(HOME_ID, doc)
    loaded = load_properties(HOME_ID)
    assert [p.id for p in loaded.properties] == ["p1", "p2"]
    first = loaded.properties[0]
    assert first.locationId == "loc1"
    assert first.price == 90000.0
    assert first.landSize == 850.0
    assert first.pros == ["Great light", "Walk to town"]
    assert first.cons == ["No garage"]
    assert first.notes == "Needs survey"


def test_attachment_save_and_delete(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_attachment(HOME_ID, "p1", "listing.pdf", b"%PDF test")
    path = get_attachment_path(HOME_ID, "p1", "listing.pdf")
    assert path.exists()
    assert path.read_bytes() == b"%PDF test"
    assert delete_attachment(HOME_ID, "p1", "listing.pdf") is True
    assert not path.exists()


def test_delete_attachment_missing_returns_false(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert delete_attachment(HOME_ID, "p1", "nope.pdf") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_properties_persistence.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.models_properties'`

- [ ] **Step 3: Write minimal implementation**

Append to `packages/backend/src/myhome/schema.py` (after the `location_ratings` table at the end of the file):

```python
properties = Table(
    "properties", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
    Column("type", String, nullable=False),
    Column("status", String, nullable=False),
    Column("location_id", String),
    Column("address", String, nullable=False),
    Column("price", Float),
    Column("land_size", Float),
    Column("built_size", Float),
    Column("bedrooms", Integer),
    Column("bathrooms", Integer),
    Column("listing_url", String),
    Column("contact", String, nullable=False),
    Column("pros", Text, nullable=False),
    Column("cons", Text, nullable=False),
    Column("notes", String, nullable=False),
    Column("attachments", Text, nullable=False),
)
```

Create `packages/backend/src/myhome/models_properties.py`:

```python
# packages/backend/src/myhome/models_properties.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

PropertyType = Literal["land", "house", "new_build"]
PropertyStatus = Literal["watching", "visited", "proposal_made", "purchased", "rejected"]


class Property(BaseModel):
    id: str
    name: str
    emoji: str = "🏠"
    type: PropertyType
    status: PropertyStatus = "watching"
    locationId: str | None = None
    address: str = ""
    price: float | None = None
    landSize: float | None = None
    builtSize: float | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    listingUrl: str | None = None
    contact: str = ""
    pros: list[str] = []
    cons: list[str] = []
    notes: str = ""
    attachments: list[str] = []


class PropertiesDocument(BaseModel):
    version: int = 1
    properties: list[Property] = []


class PropertyCreate(BaseModel):
    name: str
    emoji: str = "🏠"
    type: PropertyType
    status: PropertyStatus = "watching"
    locationId: str | None = None
    address: str = ""
    price: float | None = None
    landSize: float | None = None
    builtSize: float | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    listingUrl: str | None = None
    contact: str = ""
    pros: list[str] = []
    cons: list[str] = []
    notes: str = ""


class PropertyUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None
    type: PropertyType | None = None
    status: PropertyStatus | None = None
    locationId: str | None = None
    address: str | None = None
    price: float | None = None
    landSize: float | None = None
    builtSize: float | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    listingUrl: str | None = None
    contact: str | None = None
    pros: list[str] | None = None
    cons: list[str] | None = None
    notes: str | None = None
```

Create `packages/backend/src/myhome/persistence_properties.py`:

```python
# packages/backend/src/myhome/persistence_properties.py
from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from sqlalchemy import select

from .db import get_engine
from .ids import InvalidIdError
from .models_properties import Property, PropertiesDocument
from .schema import properties as properties_table

_log = logging.getLogger(__name__)


def _home_dir(home_id: str) -> Path:
    # Normalize lexically (no filesystem access) then verify containment
    # within homes_root -- same shape as persistence_works.py's _home_dir,
    # which documents why this is CodeQL's own recommended sanitizer form.
    homes_root = os.path.normpath(os.path.join(os.environ.get("DATA_DIR", "/data"), "homes"))
    candidate = os.path.normpath(os.path.join(homes_root, home_id))
    if not candidate.startswith(homes_root + os.sep):
        raise InvalidIdError(f"Invalid home_id: {home_id!r}")
    return Path(candidate)


def _attachments_dir(home_id: str, property_id: str) -> Path:
    base = os.path.normpath(str(_home_dir(home_id) / "properties-attachments"))
    candidate = os.path.normpath(os.path.join(base, property_id))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid property_id: {property_id!r}")
    return Path(candidate)


def load_properties(home_id: str) -> PropertiesDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(properties_table).where(properties_table.c.home_id == home_id)
            .order_by(properties_table.c.order_index)
        ).mappings().all()
    return PropertiesDocument(properties=[
        Property(
            id=r["id"], name=r["name"], emoji=r["emoji"], type=r["type"], status=r["status"],
            locationId=r["location_id"], address=r["address"], price=r["price"],
            landSize=r["land_size"], builtSize=r["built_size"], bedrooms=r["bedrooms"], bathrooms=r["bathrooms"],
            listingUrl=r["listing_url"], contact=r["contact"], pros=json.loads(r["pros"]), cons=json.loads(r["cons"]),
            notes=r["notes"], attachments=json.loads(r["attachments"]),
        )
        for r in rows
    ])


def save_properties(home_id: str, doc: PropertiesDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(properties_table.delete().where(properties_table.c.home_id == home_id))
        if doc.properties:
            conn.execute(properties_table.insert(), [
                {
                    "id": p.id, "home_id": home_id, "order_index": i, "name": p.name, "emoji": p.emoji,
                    "type": p.type, "status": p.status, "location_id": p.locationId, "address": p.address,
                    "price": p.price, "land_size": p.landSize, "built_size": p.builtSize,
                    "bedrooms": p.bedrooms, "bathrooms": p.bathrooms, "listing_url": p.listingUrl,
                    "contact": p.contact, "pros": json.dumps(p.pros), "cons": json.dumps(p.cons),
                    "notes": p.notes, "attachments": json.dumps(p.attachments),
                }
                for i, p in enumerate(doc.properties)
            ])


def get_attachment_path(home_id: str, property_id: str, filename: str) -> Path:
    base = os.path.normpath(str(_attachments_dir(home_id, property_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    return Path(candidate)


def save_attachment(home_id: str, property_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, property_id)
    base = os.path.normpath(str(path))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path.mkdir(parents=True, exist_ok=True)
    Path(candidate).write_bytes(data)


def delete_attachment(home_id: str, property_id: str, filename: str) -> bool:
    base = os.path.normpath(str(_attachments_dir(home_id, property_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path = Path(candidate)
    if not path.exists():
        return False
    path.unlink()
    thumb = path.with_name(path.name + ".thumb.jpg")
    if thumb.exists():
        thumb.unlink()
    return True


def delete_all_attachments(home_id: str, property_id: str) -> None:
    path = _attachments_dir(home_id, property_id)
    if path.exists():
        shutil.rmtree(path)


def generate_pdf_thumbnail(pdf_path: Path, thumb_path: Path) -> None:
    try:
        import fitz  # pymupdf
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        pix.save(str(thumb_path))
    except Exception as exc:
        _log.warning("PDF thumbnail generation failed for %s: %s", pdf_path, exc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_properties_persistence.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/models_properties.py packages/backend/src/myhome/persistence_properties.py packages/backend/tests/test_properties_persistence.py
git commit -m "feat(properties): add data layer — schema, models, persistence"
```

---

### Task 2: Backend REST routes — CRUD

**Files:**
- Create: `packages/backend/src/myhome/routes/properties.py`
- Modify: `packages/backend/src/myhome/main.py:19` (add `properties` to the routes import, alphabetically between `notifications` and `settings`) and add `app.include_router(properties.router)` near the other `include_router` calls (after `locations.router`)
- Modify: `packages/backend/src/myhome/models_activity.py:11` (`ActivityEntry.module` is a closed `Literal` — add `"properties"`)
- Modify: `packages/backend/src/myhome/persistence_activity.py:16-19` (`MODULE_NOUNS` — add `"properties": "property"`, and fix the pre-existing missing `"locations": "location"` entry in the same edit)
- Test: `packages/backend/tests/test_properties.py`

**Interfaces:**
- Consumes: `load_properties`, `save_properties` from `persistence_properties.py` (Task 1); `Property`, `PropertyCreate`, `PropertyUpdate`, `PropertiesDocument` from `models_properties.py` (Task 1); `log_activity` from `persistence_activity.py` (existing); `get_current_user_id` from `deps.py` (existing).
- Produces: REST endpoints `GET/POST /api/homes/{home_id}/properties`, `PUT/DELETE /api/homes/{home_id}/properties/{id}`. Consumed by Task 5 (frontend store).

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_properties.py`:

```python
import pytest
from myhome.models_properties import Property, PropertiesDocument
from myhome.persistence_properties import save_properties


def make_doc() -> PropertiesDocument:
    return PropertiesDocument(
        properties=[Property(id="p1", name="Casa da Rua das Flores", type="house", status="watching")]
    )


def test_get_properties_empty_when_none(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/properties")
    assert resp.status_code == 200
    assert resp.json()["properties"] == []


def test_get_properties_returns_saved_data(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.get(f"/api/homes/{home_id}/properties")
    assert resp.status_code == 200
    assert resp.json()["properties"][0]["id"] == "p1"


def test_create_property(client, home_id):
    payload = {"name": "Terreno Norte", "type": "land"}
    resp = client.post(f"/api/homes/{home_id}/properties", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Terreno Norte"
    assert data["type"] == "land"
    assert data["status"] == "watching"
    assert data["emoji"] == "🏠"
    assert data["pros"] == []
    assert data["cons"] == []
    assert data["attachments"] == []
    assert "id" in data
    assert len(client.get(f"/api/homes/{home_id}/properties").json()["properties"]) == 1


def test_create_property_full_fields(client, home_id):
    payload = {
        "name": "Casa Sul",
        "emoji": "🏡",
        "type": "house",
        "status": "visited",
        "locationId": "loc1",
        "address": "Rua Sul 5",
        "price": 250000.0,
        "landSize": 500.0,
        "builtSize": 180.0,
        "bedrooms": 3,
        "bathrooms": 2,
        "listingUrl": "https://example.com/listing",
        "contact": "Maria, +351 912 345 678",
        "pros": ["Great light", "Walk to town"],
        "cons": ["No garage"],
        "notes": "Needs a new roof",
    }
    resp = client.post(f"/api/homes/{home_id}/properties", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["price"] == 250000.0
    assert data["locationId"] == "loc1"
    assert data["pros"] == ["Great light", "Walk to town"]
    assert data["cons"] == ["No garage"]
    assert data["bedrooms"] == 3


def test_update_property_partial(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.put(f"/api/homes/{home_id}/properties/p1", json={"status": "visited", "price": 250000.0})
    assert resp.status_code == 204
    item = client.get(f"/api/homes/{home_id}/properties").json()["properties"][0]
    assert item["status"] == "visited"
    assert item["price"] == 250000.0
    assert item["name"] == "Casa da Rua das Flores"  # unchanged


def test_update_property_404(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/properties/nope", json={"status": "visited"})
    assert resp.status_code == 404


def test_delete_property(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.delete(f"/api/homes/{home_id}/properties/p1")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/properties").json()["properties"] == []


def test_delete_property_404(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/properties/nope")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_properties.py -v`
Expected: FAIL with 404s (no route registered) on every request

- [ ] **Step 3: Write minimal implementation**

Create `packages/backend/src/myhome/routes/properties.py`:

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user_id
from ..models_properties import PropertiesDocument, Property, PropertyCreate, PropertyUpdate
from ..persistence_activity import log_activity
from ..persistence_properties import load_properties, save_properties

router = APIRouter()


@router.get("/api/homes/{home_id}/properties", response_model=PropertiesDocument)
def get_properties(home_id: str) -> PropertiesDocument:
    return load_properties(home_id)


@router.post("/api/homes/{home_id}/properties", response_model=Property, status_code=201)
def create_property(
    home_id: str, body: PropertyCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Property:
    doc = load_properties(home_id)
    item = Property(id=str(uuid.uuid4()), **body.model_dump())
    doc.properties.append(item)
    save_properties(home_id, doc)
    log_activity(home_id, current_user_id, "properties", "create", item.name, item.id)
    return item


@router.put("/api/homes/{home_id}/properties/{id}", status_code=204)
def update_property(
    home_id: str, id: str, body: PropertyUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_properties(home_id)
    item = next((p for p in doc.properties if p.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    save_properties(home_id, doc)
    log_activity(home_id, current_user_id, "properties", "update", item.name, id)


@router.delete("/api/homes/{home_id}/properties/{id}", status_code=204)
def delete_property(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_properties(home_id)
    item = next((p for p in doc.properties if p.id == id), None)
    if item is None:
        raise HTTPException(status_code=404)
    doc.properties = [p for p in doc.properties if p.id != id]
    save_properties(home_id, doc)
    log_activity(home_id, current_user_id, "properties", "delete", item.name, id)
```

Modify `packages/backend/src/myhome/main.py:19` — add `properties` to the import list (keep alphabetical, between `notifications` and `settings`):

```python
from .routes import activity, auth, backup, chores, consumables, costs, ha, homes, house, inventory, kb, locations, mcp_config, notifications, properties, settings, svg, works
```

Add a new `include_router` call next to `app.include_router(locations.router)`:

```python
app.include_router(properties.router)
```

Modify `packages/backend/src/myhome/models_activity.py:11` — add `"properties"` to the closed `Literal`:

```python
    module: Literal["chores", "works", "costs", "inventory", "consumables", "kb", "locations", "properties"]
```

Modify `packages/backend/src/myhome/persistence_activity.py:16-19` — add `"properties"`, and fix the pre-existing missing `"locations"` entry:

```python
MODULE_NOUNS = {
    "chores": "chore", "works": "work", "costs": "cost entry",
    "inventory": "inventory item", "consumables": "consumable", "kb": "KB article",
    "locations": "location", "properties": "property",
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_properties.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Run the full backend suite to confirm the locations fix didn't break anything**

Run: `cd packages/backend && python -m pytest -q`
Expected: PASS (all existing tests, including `test_locations.py` and `test_mcp_tools_locations.py`)

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/routes/properties.py packages/backend/src/myhome/main.py packages/backend/src/myhome/models_activity.py packages/backend/src/myhome/persistence_activity.py packages/backend/tests/test_properties.py
git commit -m "feat(properties): add REST CRUD routes; fix pre-existing locations activity-log KeyError"
```

---

### Task 3: Backend REST routes — attachments

**Files:**
- Modify: `packages/backend/src/myhome/routes/properties.py` (append attachment endpoints)
- Modify: `packages/backend/tests/test_properties.py` (append attachment tests)

**Interfaces:**
- Consumes: `get_attachment_path`, `save_attachment`, `delete_attachment`, `delete_all_attachments`, `generate_pdf_thumbnail` from `persistence_properties.py` (Task 1).
- Produces: `POST/GET/DELETE /api/homes/{home_id}/properties/{id}/attachments[/{filename}]`. Consumed by Task 6 (frontend `PropertyModal`) via Task 5's store.

- [ ] **Step 1: Write the failing test**

Append to `packages/backend/tests/test_properties.py`:

```python
def test_upload_invalid_id_rejected(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.post(
        f"/api/homes/{home_id}/properties/p!1/attachments",
        files={"file": ("listing.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 400


def test_get_attachment_traversal_rejected(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.get(f"/api/homes/{home_id}/properties/p1/attachments/.hidden")
    assert resp.status_code == 400


def test_delete_attachment_traversal_rejected(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.delete(f"/api/homes/{home_id}/properties/p1/attachments/.hidden")
    assert resp.status_code == 400


def test_upload_attachment(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("listing.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "listing.pdf"
    item = client.get(f"/api/homes/{home_id}/properties").json()["properties"][0]
    assert "listing.pdf" in item["attachments"]


def test_upload_sanitises_filename(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("my listing 2025.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "my_listing_2025.pdf"


def test_upload_unsupported_type_rejected(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_image_jpeg_accepted(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
    )
    assert resp.status_code == 201
    item = client.get(f"/api/homes/{home_id}/properties").json()["properties"][0]
    assert "photo.jpg" in item["attachments"]


def test_upload_attachment_property_not_found(client, home_id):
    resp = client.post(
        f"/api/homes/{home_id}/properties/nope/attachments",
        files={"file": ("listing.pdf", b"%PDF test", "application/pdf")},
    )
    assert resp.status_code == 404


def test_get_attachment(client, home_id):
    save_properties(home_id, make_doc())
    client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("listing.pdf", b"%PDF-1.4 test content", "application/pdf")},
    )
    resp = client.get(f"/api/homes/{home_id}/properties/p1/attachments/listing.pdf")
    assert resp.status_code == 200
    assert "pdf" in resp.headers["content-type"]


def test_get_attachment_not_found(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.get(f"/api/homes/{home_id}/properties/p1/attachments/nope.pdf")
    assert resp.status_code == 404


def test_delete_attachment(client, home_id):
    save_properties(home_id, make_doc())
    client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("listing.pdf", b"%PDF test", "application/pdf")},
    )
    resp = client.delete(f"/api/homes/{home_id}/properties/p1/attachments/listing.pdf")
    assert resp.status_code == 204
    item = client.get(f"/api/homes/{home_id}/properties").json()["properties"][0]
    assert "listing.pdf" not in item["attachments"]


def test_delete_attachment_not_found(client, home_id):
    save_properties(home_id, make_doc())
    resp = client.delete(f"/api/homes/{home_id}/properties/p1/attachments/nope.pdf")
    assert resp.status_code == 404


def test_delete_property_removes_attachments(client, tmp_path, home_id):
    save_properties(home_id, make_doc())
    client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("listing.pdf", b"%PDF test", "application/pdf")},
    )
    client.delete(f"/api/homes/{home_id}/properties/p1")
    attach_dir = tmp_path / "homes" / home_id / "properties-attachments" / "p1"
    assert not attach_dir.exists()


def _make_valid_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    return doc.write()


def test_upload_pdf_creates_thumbnail(client, tmp_path, home_id):
    save_properties(home_id, make_doc())
    pdf_bytes = _make_valid_pdf()
    resp = client.post(
        f"/api/homes/{home_id}/properties/p1/attachments",
        files={"file": ("listing.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 201
    thumb = tmp_path / "homes" / home_id / "properties-attachments" / "p1" / "listing.pdf.thumb.jpg"
    assert thumb.exists(), "thumbnail should be created on PDF upload"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_properties.py -v`
Expected: FAIL — the new tests 404 (no attachment routes registered yet)

- [ ] **Step 3: Write minimal implementation**

Modify `packages/backend/src/myhome/routes/properties.py` — replace the import block at the top with:

```python
import mimetypes
import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..deps import get_current_user_id
from ..models_properties import PropertiesDocument, Property, PropertyCreate, PropertyUpdate
from ..persistence_activity import log_activity
from ..persistence_properties import (
    delete_all_attachments,
    delete_attachment,
    generate_pdf_thumbnail,
    get_attachment_path,
    load_properties,
    save_attachment,
    save_properties,
)

router = APIRouter()

_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"


def _validate_id(property_id: str) -> None:
    if not _ID_RE.fullmatch(property_id):
        raise HTTPException(status_code=400, detail="Invalid id")


def _validate_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")
```

Then append these routes at the end of the file (after `delete_property`):

```python
@router.post("/api/homes/{home_id}/properties/{id}/attachments", status_code=201)
async def upload_property_attachment(home_id: str, id: str, file: UploadFile) -> dict:
    _validate_id(id)
    doc = load_properties(home_id)
    item = next((p for p in doc.properties if p.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    ext = os.path.splitext(original)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(home_id, id, filename, data)
    if ext == ".pdf":
        pdf_path = get_attachment_path(home_id, id, filename)
        thumb_path = pdf_path.with_name(pdf_path.name + ".thumb.jpg")
        generate_pdf_thumbnail(pdf_path, thumb_path)
    if filename not in item.attachments:
        item.attachments.append(filename)
    save_properties(home_id, doc)
    return {"filename": filename}


@router.get("/api/homes/{home_id}/properties/{id}/attachments/{filename}")
def get_property_attachment(home_id: str, id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    path = get_attachment_path(home_id, id, filename)
    if not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")


@router.delete("/api/homes/{home_id}/properties/{id}/attachments/{filename}", status_code=204)
def remove_property_attachment(home_id: str, id: str, filename: str) -> None:
    _validate_id(id)
    _validate_filename(filename)
    doc = load_properties(home_id)
    item = next((p for p in doc.properties if p.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    if not delete_attachment(home_id, id, filename):
        raise HTTPException(status_code=404)
    item.attachments = [a for a in item.attachments if a != filename]
    save_properties(home_id, doc)
```

Also update `delete_property` (added in Task 2) to clean up attachments on delete — change it to:

```python
@router.delete("/api/homes/{home_id}/properties/{id}", status_code=204)
def delete_property(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_properties(home_id)
    item = next((p for p in doc.properties if p.id == id), None)
    if item is None:
        raise HTTPException(status_code=404)
    doc.properties = [p for p in doc.properties if p.id != id]
    save_properties(home_id, doc)
    delete_all_attachments(home_id, id)
    log_activity(home_id, current_user_id, "properties", "delete", item.name, id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_properties.py -v`
Expected: PASS (22 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/properties.py packages/backend/tests/test_properties.py
git commit -m "feat(properties): add attachment upload/get/delete routes"
```

---

### Task 4: Backend MCP tools

**Files:**
- Create: `packages/backend/src/myhome/mcp_tools_properties.py`
- Modify: `packages/backend/src/myhome/mcp_app.py` (add to the registration import tuple, alphabetically)
- Test: `packages/backend/tests/test_mcp_tools_properties.py`

**Interfaces:**
- Consumes: `load_properties`, `save_properties` from `persistence_properties.py` (Task 1); `Property` from `models_properties.py` (Task 1); `_require_role`, `_resolve_home_id`, `mcp` from `mcp_server.py` (existing, same pattern as `mcp_tools_works.py`).
- Produces: MCP tools `list_properties`, `create_property`, `update_property`, `delete_property`.

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_mcp_tools_properties.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_property(home_id):
    from myhome.mcp_tools_properties import _create_property_impl, _list_properties_impl
    item = _create_property_impl(home_id, "Terreno Norte", "land")
    doc = _list_properties_impl(home_id)
    assert doc["properties"][0]["id"] == item["id"]
    assert doc["properties"][0]["status"] == "watching"


def test_create_property_rejects_invalid_type(home_id):
    from myhome.mcp_tools_properties import _create_property_impl
    with pytest.raises(ValueError):
        _create_property_impl(home_id, "Bad", "castle")


def test_create_property_rejects_invalid_status(home_id):
    from myhome.mcp_tools_properties import _create_property_impl
    with pytest.raises(ValueError):
        _create_property_impl(home_id, "Bad", "land", status="nope")


def test_update_property_transitions_status(home_id):
    from myhome.mcp_tools_properties import _create_property_impl, _update_property_impl
    item = _create_property_impl(home_id, "Casa Sul", "house")
    updated = _update_property_impl(home_id, item["id"], status="visited")
    assert updated["status"] == "visited"


def test_update_property_rejects_invalid_status(home_id):
    from myhome.mcp_tools_properties import _create_property_impl, _update_property_impl
    item = _create_property_impl(home_id, "Casa Sul", "house")
    with pytest.raises(ValueError):
        _update_property_impl(home_id, item["id"], status="nope")


def test_delete_property(home_id):
    from myhome.mcp_tools_properties import _create_property_impl, _delete_property_impl, _list_properties_impl
    item = _create_property_impl(home_id, "Old Listing", "land")
    _delete_property_impl(home_id, item["id"])
    assert _list_properties_impl(home_id)["properties"] == []


def test_delete_property_unknown_id_raises(home_id):
    from myhome.mcp_tools_properties import _delete_property_impl
    with pytest.raises(ValueError):
        _delete_property_impl(home_id, "nonexistent")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_mcp_tools_properties.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.mcp_tools_properties'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/backend/src/myhome/mcp_tools_properties.py`:

```python
from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_properties import Property
from .persistence_properties import load_properties, save_properties

_VALID_TYPES = ("land", "house", "new_build")
_VALID_STATUSES = ("watching", "visited", "proposal_made", "purchased", "rejected")


def _list_properties_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_properties(resolved).model_dump()


def _create_property_impl(
    home_id: str | None,
    name: str,
    type: str,
    status: str = "watching",
    location_id: str | None = None,
    address: str = "",
    price: float | None = None,
    land_size: float | None = None,
    built_size: float | None = None,
    bedrooms: int | None = None,
    bathrooms: int | None = None,
    listing_url: str | None = None,
    contact: str = "",
    notes: str = "",
) -> dict:
    if type not in _VALID_TYPES:
        raise ValueError(f"type must be one of {_VALID_TYPES}")
    if status not in _VALID_STATUSES:
        raise ValueError(f"status must be one of {_VALID_STATUSES}")
    resolved = _resolve_home_id(home_id)
    doc = load_properties(resolved)
    item = Property(
        id=str(uuid.uuid4()), name=name, type=type, status=status,
        locationId=location_id, address=address, price=price, landSize=land_size, builtSize=built_size,
        bedrooms=bedrooms, bathrooms=bathrooms, listingUrl=listing_url, contact=contact, notes=notes,
    )
    doc.properties.append(item)
    save_properties(resolved, doc)
    return item.model_dump()


def _update_property_impl(home_id: str | None, property_id: str, **fields) -> dict:
    if fields.get("status") is not None and fields["status"] not in _VALID_STATUSES:
        raise ValueError(f"status must be one of {_VALID_STATUSES}")
    if fields.get("type") is not None and fields["type"] not in _VALID_TYPES:
        raise ValueError(f"type must be one of {_VALID_TYPES}")
    resolved = _resolve_home_id(home_id)
    doc = load_properties(resolved)
    item = next((p for p in doc.properties if p.id == property_id), None)
    if item is None:
        raise ValueError(f"Unknown property_id {property_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(item, field, value)
    save_properties(resolved, doc)
    return item.model_dump()


def _delete_property_impl(home_id: str | None, property_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_properties(resolved)
    before = len(doc.properties)
    doc.properties = [p for p in doc.properties if p.id != property_id]
    if len(doc.properties) == before:
        raise ValueError(f"Unknown property_id {property_id!r}")
    save_properties(resolved, doc)
    return {"deleted": property_id}


@mcp.tool()
async def list_properties(ctx: Context, home_id: str | None = None) -> dict:
    """List property listings (land/house/new-build) being tracked for a home search."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_properties_impl(home_id)


@mcp.tool()
async def create_property(
    ctx: Context,
    name: str,
    type: str,
    home_id: str | None = None,
    status: str = "watching",
    location_id: str | None = None,
    address: str = "",
    price: float | None = None,
    land_size: float | None = None,
    built_size: float | None = None,
    bedrooms: int | None = None,
    bathrooms: int | None = None,
    listing_url: str | None = None,
    contact: str = "",
    notes: str = "",
) -> dict:
    """Add a property listing. type is 'land', 'house', or 'new_build'. status is
    'watching', 'visited', 'proposal_made', 'purchased', or 'rejected'. location_id
    should match an id from list_locations if set. Sizes are in square meters."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_property_impl(
        home_id, name, type, status, location_id, address, price, land_size, built_size,
        bedrooms, bathrooms, listing_url, contact, notes,
    )


@mcp.tool()
async def update_property(
    ctx: Context,
    property_id: str,
    home_id: str | None = None,
    name: str | None = None,
    type: str | None = None,
    status: str | None = None,
    location_id: str | None = None,
    address: str | None = None,
    price: float | None = None,
    land_size: float | None = None,
    built_size: float | None = None,
    bedrooms: int | None = None,
    bathrooms: int | None = None,
    listing_url: str | None = None,
    contact: str | None = None,
    notes: str | None = None,
) -> dict:
    """Update fields on an existing property, including transitioning its status."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_property_impl(
        home_id, property_id, name=name, type=type, status=status, locationId=location_id,
        address=address, price=price, landSize=land_size, builtSize=built_size,
        bedrooms=bedrooms, bathrooms=bathrooms, listingUrl=listing_url, contact=contact, notes=notes,
    )


@mcp.tool()
async def delete_property(ctx: Context, property_id: str, home_id: str | None = None) -> dict:
    """Delete a property listing."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_property_impl(home_id, property_id)
```

Modify `packages/backend/src/myhome/mcp_app.py` — add `mcp_tools_properties` to the import tuple (keep alphabetical):

```python
from . import (  # noqa: F401 - imported for the side effect of registering tools
    mcp_tools_chores,
    mcp_tools_consumables,
    mcp_tools_costs,
    mcp_tools_homes,
    mcp_tools_inventory,
    mcp_tools_kb,
    mcp_tools_locations,
    mcp_tools_properties,
    mcp_tools_settings,
    mcp_tools_works,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_mcp_tools_properties.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_properties.py packages/backend/src/myhome/mcp_app.py packages/backend/tests/test_mcp_tools_properties.py
git commit -m "feat(properties): add MCP tools"
```

---

### Task 5: Frontend store

**Files:**
- Create: `packages/editor/src/lib/propertiesStore.svelte.ts`
- Test: `packages/editor/test/propertiesStore.test.ts`

**Interfaces:**
- Produces: types `PropertyType`, `PropertyStatus`, `Property`, `PropertiesDocument`; factory `createPropertiesStore(getHomeId)` returning `{ properties, loaded, loadError, createProperty, updateProperty, deleteProperty, uploadAttachment, deleteAttachment, reload }`. Consumed by Tasks 6–8.

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/propertiesStore.test.ts`:

```typescript
import { describe, it, expect, afterEach, vi } from "vitest";
import { createPropertiesStore } from "../src/lib/propertiesStore.svelte";
import type { Property } from "../src/lib/propertiesStore.svelte";

const HOME = "home-123";
const getHomeId = () => HOME;

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

function makeProperty(overrides: Partial<Property> = {}): Property {
  return {
    id: "p1", name: "Casa da Rua das Flores", emoji: "🏠", type: "house", status: "watching",
    locationId: null, address: "", price: null, landSize: null, builtSize: null,
    bedrooms: null, bathrooms: null, listingUrl: null, contact: "",
    pros: [], cons: [], notes: "", attachments: [],
    ...overrides,
  };
}

const emptyDoc = { version: 1, properties: [] };

describe("propertiesStore — init", () => {
  it("loads properties from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, properties: [makeProperty()] }));
    const store = createPropertiesStore(getHomeId);
    await tick();
    expect(store.properties.length).toBe(1);
    expect(store.properties[0].id).toBe("p1");
    expect(store.loaded).toBe(true);
  });

  it("marks loaded on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("net fail")));
    const store = createPropertiesStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("net fail");
  });

  it("does not fetch when no homeId provided", async () => {
    const fetchFn = vi.fn();
    vi.stubGlobal("fetch", fetchFn);
    const store = createPropertiesStore();
    await tick();
    expect(fetchFn).not.toHaveBeenCalled();
    expect(store.loaded).toBe(true);
  });
});

describe("propertiesStore — createProperty", () => {
  it("posts to /api/homes/{homeId}/properties and refreshes", async () => {
    const created = makeProperty({ id: "p2", name: "Terreno Norte", type: "land" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, properties: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createPropertiesStore(getHomeId);
    await tick();
    await store.createProperty({
      name: "Terreno Norte", emoji: "🏠", type: "land", status: "watching",
      locationId: null, address: "", price: null, landSize: null, builtSize: null,
      bedrooms: null, bathrooms: null, listingUrl: null, contact: "", pros: [], cons: [], notes: "",
    });
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/properties`);
    expect(fetchFn.mock.calls[1][1].method).toBe("POST");
    expect(store.properties.length).toBe(1);
  });
});

describe("propertiesStore — updateProperty", () => {
  it("calls PUT /api/homes/{homeId}/properties/{id}", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createPropertiesStore(getHomeId);
    await tick();
    await store.updateProperty("p1", { status: "visited" });
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/properties/p1`);
    expect(fetchFn.mock.calls[1][1].method).toBe("PUT");
  });
});

describe("propertiesStore — deleteProperty", () => {
  it("calls DELETE /api/homes/{homeId}/properties/{id}", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createPropertiesStore(getHomeId);
    await tick();
    await store.deleteProperty("p1");
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/properties/p1`);
    expect(fetchFn.mock.calls[1][1].method).toBe("DELETE");
  });
});

describe("propertiesStore — uploadAttachment", () => {
  it("POSTs FormData to /api/homes/{homeId}/properties/{id}/attachments", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({ filename: "listing.pdf" }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createPropertiesStore(getHomeId);
    await tick();
    const file = new File(["%PDF"], "listing.pdf", { type: "application/pdf" });
    const filename = await store.uploadAttachment("p1", file);
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/properties/p1/attachments`);
    expect(filename).toBe("listing.pdf");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/propertiesStore.test.ts`
Expected: FAIL — cannot find module `../src/lib/propertiesStore.svelte`

- [ ] **Step 3: Write minimal implementation**

Create `packages/editor/src/lib/propertiesStore.svelte.ts`:

```typescript
// packages/editor/src/lib/propertiesStore.svelte.ts

export type PropertyType = "land" | "house" | "new_build";
export type PropertyStatus = "watching" | "visited" | "proposal_made" | "purchased" | "rejected";

export interface Property {
  id: string;
  name: string;
  emoji: string;
  type: PropertyType;
  status: PropertyStatus;
  locationId: string | null;
  address: string;
  price: number | null;
  landSize: number | null;
  builtSize: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  listingUrl: string | null;
  contact: string;
  pros: string[];
  cons: string[];
  notes: string;
  attachments: string[];
}

export interface PropertiesDocument {
  version: number;
  properties: Property[];
}

export function createPropertiesStore(getHomeId: () => string | null = () => null) {
  const properties = $state<Property[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/properties`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: PropertiesDocument = await resp.json();
      properties.length = 0;
      for (const p of doc.properties) properties.push(p);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createProperty(
    data: Omit<Property, "id" | "attachments">
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/properties`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateProperty(
    id: string,
    patch: Partial<Omit<Property, "id" | "attachments">>
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/properties/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteProperty(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/properties/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function uploadAttachment(id: string, file: File): Promise<string> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`/api/homes/${homeId}/properties/${id}/attachments`, {
      method: "POST",
      body: form,
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();
    await init();
    return result.filename as string;
  }

  async function deleteAttachment(id: string, filename: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/properties/${id}/attachments/${filename}`, {
      method: "DELETE",
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  init();

  return {
    get properties() { return properties as Property[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createProperty,
    updateProperty,
    deleteProperty,
    uploadAttachment,
    deleteAttachment,
    reload: init,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/propertiesStore.test.ts`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/propertiesStore.svelte.ts packages/editor/test/propertiesStore.test.ts
git commit -m "feat(properties): add frontend store"
```

---

### Task 6: Frontend PropertyModal

**Files:**
- Create: `packages/editor/src/lib/components/PropertyModal.svelte`
- Test: `packages/editor/test/PropertyModal.test.ts`

**Interfaces:**
- Consumes: `createPropertiesStore`, `Property`, `PropertyType`, `PropertyStatus` from `propertiesStore.svelte.ts` (Task 5); `createLocationsStore` from `locationsStore.svelte.ts` (existing); `homesStore` from `homesStore.svelte.ts` (existing); shared UI components `Modal`, `Input`, `Button`, `EmojiPicker`, `Tabs`, `MediaGallery`, `Lightbox` (existing, same imports as `WorkModal.svelte`/`InventoryModal.svelte`).
- Produces: `PropertyModal` component with props `{ property: Property | null; store: PropertiesStore; locationsStore: LocationsStore; onclose: () => void }`. Consumed by Task 7.

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/PropertyModal.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import PropertyModal from "../src/lib/components/PropertyModal.svelte";
import { homesStore } from "../src/lib/homesStore.svelte";
import type { Property } from "../src/lib/propertiesStore.svelte";

function makeProperty(overrides: Partial<Property> = {}): Property {
  return {
    id: "p1", name: "Casa da Rua das Flores", emoji: "🏠", type: "house", status: "watching",
    locationId: null, address: "", price: null, landSize: null, builtSize: null,
    bedrooms: null, bathrooms: null, listingUrl: null, contact: "",
    pros: [], cons: [], notes: "", attachments: ["photo.jpg"],
    ...overrides,
  };
}

function makeStore(properties: Property[]) {
  return {
    properties, loaded: true, loadError: null,
    createProperty: vi.fn(), updateProperty: vi.fn(), deleteProperty: vi.fn(),
    uploadAttachment: vi.fn(), deleteAttachment: vi.fn(), reload: vi.fn(),
  };
}

function makeLocationsStore() {
  return { locations: [{ id: "loc1", name: "Lisbon", emoji: "🇵🇹" }] };
}

describe("PropertyModal", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    homesStore.setActiveHomeId("home-1");
  });

  afterEach(() => {
    homesStore._reset();
    target.remove();
  });

  it("adds and removes pros/cons entries", () => {
    const store = makeStore([]);
    const comp = mount(PropertyModal, {
      target,
      props: { property: null, store, locationsStore: makeLocationsStore(), onclose: vi.fn() },
    });
    flushSync();

    // Switch to the Pros/Cons tab.
    const tabs = Array.from(target.querySelectorAll(".tab")) as HTMLButtonElement[];
    const prosConsTab = tabs.find((t) => t.textContent === "Pros / Cons")!;
    prosConsTab.click();
    flushSync();

    const proInput = target.querySelector(".pc-col:first-child input") as HTMLInputElement;
    proInput.value = "Great light";
    proInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const addButtons = Array.from(target.querySelectorAll(".pc-add button")) as HTMLButtonElement[];
    addButtons[0].click();
    flushSync();

    expect(target.querySelector(".pc-col:first-child .pc-list")?.textContent).toContain("Great light");

    unmount(comp);
  });

  it("builds media item URLs with the home id prefix", () => {
    const store = makeStore([makeProperty()]);
    const comp = mount(PropertyModal, {
      target,
      props: { property: makeProperty(), store, locationsStore: makeLocationsStore(), onclose: vi.fn() },
    });
    flushSync();

    const tabs = Array.from(target.querySelectorAll(".tab")) as HTMLButtonElement[];
    const mediaTab = tabs.find((t) => t.textContent?.startsWith("Media"))!;
    mediaTab.click();
    flushSync();

    const img = target.querySelector("img, [src]") as HTMLElement | null;
    // MediaGallery renders items with the constructed URL somewhere in the DOM;
    // assert via the underlying anchor/img src rather than assuming exact markup.
    const anySrcEl = target.querySelector("[src*='attachments']") as HTMLImageElement | null;
    expect(anySrcEl?.getAttribute("src")).toContain("/api/homes/home-1/properties/p1/attachments/photo.jpg");

    unmount(comp);
  });

  it("calls store.createProperty with trimmed fields on save", () => {
    const store = makeStore([]);
    const onclose = vi.fn();
    const comp = mount(PropertyModal, {
      target,
      props: { property: null, store, locationsStore: makeLocationsStore(), onclose },
    });
    flushSync();

    const nameInput = target.querySelector(".ui-input") as HTMLInputElement;
    nameInput.value = "  Terreno Norte  ";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    const saveBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Create")!;
    saveBtn.click();
    flushSync();

    expect(store.createProperty).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Terreno Norte" }),
    );

    unmount(comp);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/PropertyModal.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/PropertyModal.svelte`

- [ ] **Step 3: Write minimal implementation**

Create `packages/editor/src/lib/components/PropertyModal.svelte`:

```svelte
<script lang="ts">
  import type { createPropertiesStore, Property, PropertyType, PropertyStatus } from "../propertiesStore.svelte";
  import type { createLocationsStore } from "../locationsStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import { apiUrl } from "../apiUrl";
  import { homesStore } from "../homesStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";
  import Tabs from "./ui/Tabs.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type PropertiesStore = ReturnType<typeof createPropertiesStore>;
  type LocationsStore = ReturnType<typeof createLocationsStore>;

  interface Props {
    property: Property | null;
    store: PropertiesStore;
    locationsStore: LocationsStore;
    onclose: () => void;
  }

  let { property, store, locationsStore, onclose }: Props = $props();

  const isCreate = property === null;

  let activeTab = $state<"info" | "pros_cons" | "notes" | "media">("info");
  let name = $state(property?.name ?? "");
  let emoji = $state(property?.emoji ?? "🏠");
  let type = $state<PropertyType>(property?.type ?? "house");
  let status = $state<PropertyStatus>(property?.status ?? "watching");
  let locationId = $state(property?.locationId ?? "");
  let address = $state(property?.address ?? "");
  let price = $state<string>(property?.price != null ? String(property.price) : "");
  let landSize = $state<string>(property?.landSize != null ? String(property.landSize) : "");
  let builtSize = $state<string>(property?.builtSize != null ? String(property.builtSize) : "");
  let bedrooms = $state<string>(property?.bedrooms != null ? String(property.bedrooms) : "");
  let bathrooms = $state<string>(property?.bathrooms != null ? String(property.bathrooms) : "");
  let listingUrl = $state(property?.listingUrl ?? "");
  let contact = $state(property?.contact ?? "");
  let pros = $state<string[]>(property?.pros ? [...property.pros] : []);
  let cons = $state<string[]>(property?.cons ? [...property.cons] : []);
  let newPro = $state("");
  let newCon = $state("");
  let notes = $state(property?.notes ?? "");

  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  function addPro(): void {
    const v = newPro.trim();
    if (!v) return;
    pros = [...pros, v];
    newPro = "";
  }
  function removePro(index: number): void {
    pros = pros.filter((_, i) => i !== index);
  }
  function addCon(): void {
    const v = newCon.trim();
    if (!v) return;
    cons = [...cons, v];
    newCon = "";
  }
  function removeCon(index: number): void {
    cons = cons.filter((_, i) => i !== index);
  }

  function parseNum(v: string): number | null {
    if (!v) return null;
    const n = parseFloat(v);
    return isNaN(n) ? null : n;
  }
  function parseIntOrNull(v: string): number | null {
    if (!v) return null;
    const n = parseInt(v, 10);
    return isNaN(n) ? null : n;
  }

  async function handleSave(): Promise<void> {
    if (!name.trim()) { error = "Name is required"; return; }
    saving = true; error = null;
    const patch = {
      name: name.trim(),
      emoji: emoji || "🏠",
      type,
      status,
      locationId: locationId || null,
      address: address.trim(),
      price: parseNum(price),
      landSize: parseNum(landSize),
      builtSize: parseNum(builtSize),
      bedrooms: parseIntOrNull(bedrooms),
      bathrooms: parseIntOrNull(bathrooms),
      listingUrl: listingUrl.trim() || null,
      contact: contact.trim(),
      pros,
      cons,
      notes: notes.trim(),
    };
    try {
      if (isCreate) {
        await store.createProperty(patch);
      } else {
        await store.updateProperty(property!.id, patch);
      }
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!property) return;
    deleting = true;
    try {
      await store.deleteProperty(property.id);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Delete failed";
      deleting = false;
    }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!property) return;
    uploading = true; uploadError = null;
    try {
      for (const file of files) await store.uploadAttachment(property.id, file);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : "Upload failed";
    } finally {
      uploading = false;
    }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!property) return;
    try {
      await store.deleteAttachment(property.id, id);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : "Delete failed";
    }
  }

  function handleItemClick(index: number): void {
    lightboxIndex = index;
    lightboxOpen = true;
  }

  const currentProperty = $derived(
    property ? (store.properties.find((p) => p.id === property.id) ?? property) : null
  );
  const attachmentCount = $derived(currentProperty?.attachments.length ?? 0);

  const mediaItems = $derived<MediaItem[]>(
    (currentProperty?.attachments ?? []).map((fname) => {
      const homeId = homesStore.activeHomeId;
      const url = apiUrl(`/api/homes/${homeId}/properties/${property!.id}/attachments/${fname}`);
      const isPdf = fname.toLowerCase().endsWith(".pdf");
      return { id: fname, name: fname, url, thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url, type: isPdf ? "document" : "image" };
    })
  );
</script>

<Modal open={true} title={isCreate ? "＋ New property" : "Edit property"} {onclose} width="min(92vw, 820px)">
  <Tabs
    tabs={[
      { id: "info", label: "Info" },
      { id: "pros_cons", label: "Pros / Cons" },
      { id: "notes", label: "Notes" },
      { id: "media", label: attachmentCount > 0 ? `Media (${attachmentCount})` : "Media", disabled: isCreate },
    ]}
    active={activeTab}
    onchange={(id) => { activeTab = id as typeof activeTab; }}
  />

  {#if activeTab === "info"}
    <div class="row">
      <label>Emoji</label>
      <EmojiPicker bind:value={emoji} />
      <label style="margin-left:16px">Name *</label>
      <div class="flex-grow"><Input bind:value={name} placeholder="Casa da Rua das Flores" /></div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>Type</label>
        <select class="native-input" bind:value={type}>
          <option value="land">Land only</option>
          <option value="house">Existing house</option>
          <option value="new_build">New-build (off-plan)</option>
        </select>
      </div>
      <div class="row">
        <label>Status</label>
        <select class="native-input" bind:value={status}>
          <option value="watching">Watching</option>
          <option value="visited">Visited</option>
          <option value="proposal_made">Proposal made</option>
          <option value="purchased">Purchased</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>
    </div>
    <div class="row">
      <label>Location</label>
      <select class="native-input" bind:value={locationId}>
        <option value="">— None —</option>
        {#each locationsStore.locations as loc}
          <option value={loc.id}>{loc.emoji} {loc.name}</option>
        {/each}
      </select>
    </div>
    <div class="row">
      <label>Address</label>
      <div class="flex-grow"><Input bind:value={address} placeholder="Rua das Flores 12" /></div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>Price (€)</label>
        <input class="native-input" type="number" min="0" step="0.01" bind:value={price} placeholder="0.00" />
      </div>
      <div class="row">
        <label>Listing URL</label>
        <input class="native-input" type="url" bind:value={listingUrl} placeholder="https://…" />
      </div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>Land size (m²)</label>
        <input class="native-input" type="number" min="0" step="1" bind:value={landSize} placeholder="0" />
      </div>
      <div class="row">
        <label>Built size (m²)</label>
        <input class="native-input" type="number" min="0" step="1" bind:value={builtSize} placeholder="0" />
      </div>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>Bedrooms</label>
        <input class="native-input" type="number" min="0" step="1" bind:value={bedrooms} placeholder="0" />
      </div>
      <div class="row">
        <label>Bathrooms</label>
        <input class="native-input" type="number" min="0" step="1" bind:value={bathrooms} placeholder="0" />
      </div>
    </div>
    <div class="row">
      <label>Agent / contact</label>
      <div class="flex-grow"><Input bind:value={contact} placeholder="Maria Silva, Century21, +351 912 345 678" /></div>
    </div>
    {#if error}<div class="modal-error">{error}</div>{/if}
  {:else if activeTab === "pros_cons"}
    <div class="pros-cons-grid">
      <div class="pc-col">
        <div class="pc-label">Pros</div>
        <ul class="pc-list">
          {#each pros as pro, i}
            <li><span>{pro}</span><button type="button" class="pc-remove" onclick={() => removePro(i)}>✕</button></li>
          {/each}
        </ul>
        <div class="pc-add">
          <input
            class="native-input"
            bind:value={newPro}
            placeholder="Add a pro…"
            onkeydown={(e) => { if (e.key === "Enter") { e.preventDefault(); addPro(); } }}
          />
          <Button variant="secondary" onclick={addPro}>Add</Button>
        </div>
      </div>
      <div class="pc-col">
        <div class="pc-label">Cons</div>
        <ul class="pc-list">
          {#each cons as con, i}
            <li><span>{con}</span><button type="button" class="pc-remove" onclick={() => removeCon(i)}>✕</button></li>
          {/each}
        </ul>
        <div class="pc-add">
          <input
            class="native-input"
            bind:value={newCon}
            placeholder="Add a con…"
            onkeydown={(e) => { if (e.key === "Enter") { e.preventDefault(); addCon(); } }}
          />
          <Button variant="secondary" onclick={addCon}>Add</Button>
        </div>
      </div>
    </div>
  {:else if activeTab === "notes"}
    <textarea class="native-input notes-area" bind:value={notes} placeholder="Additional notes…" rows="10"></textarea>
  {:else}
    <MediaGallery
      items={mediaItems}
      {uploading}
      {uploadError}
      onUpload={handleUpload}
      onDelete={handleDeleteAttachment}
      onItemClick={handleItemClick}
    />
  {/if}

  {#snippet footer()}
    {#if !isCreate}
      {#if confirmDelete}
        <span class="confirm-text">Delete?</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>✓ Confirm</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>✕</Button>
      {:else}
        <Button variant="danger" onclick={() => { confirmDelete = true; }}>🗑 Delete</Button>
      {/if}
    {/if}
    <span class="spacer"></span>
    <Button variant="primary" disabled={saving} onclick={handleSave}>
      {saving ? "Saving…" : isCreate ? "Create" : "Save"}
    </Button>
  {/snippet}
</Modal>

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .row { display: flex; flex-direction: column; gap: 4px; margin-bottom: var(--space-3); }
  .row-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: var(--space-3); }
  .row-pair .row { margin-bottom: 0; }
  label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; }
  .flex-grow { flex: 1; min-width: 0; }

  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans);
    width: 100%; box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  select.native-input { cursor: pointer; }
  .notes-area { resize: vertical; min-height: 160px; }

  .pros-cons-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .pc-col { display: flex; flex-direction: column; gap: 8px; }
  .pc-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; }
  .pc-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .pc-list li {
    display: flex; align-items: center; justify-content: space-between; gap: 8px;
    background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 6px 10px; font-size: 12px; color: var(--text);
  }
  .pc-remove { background: none; border: none; color: var(--text-faint); cursor: pointer; font-size: 12px; padding: 0; }
  .pc-remove:hover { color: var(--danger); }
  .pc-add { display: flex; gap: 6px; }
  .pc-add .native-input { flex: 1; }

  .modal-error { padding: 8px 0 0; font-size: 11px; color: var(--danger); }
  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/PropertyModal.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/PropertyModal.svelte packages/editor/test/PropertyModal.test.ts
git commit -m "feat(properties): add create/edit modal with pros/cons and media"
```

---

### Task 7: Frontend PropertiesPage

**Files:**
- Create: `packages/editor/src/lib/components/PropertiesPage.svelte`
- Test: `packages/editor/test/PropertiesPage.test.ts`

**Interfaces:**
- Consumes: `createPropertiesStore`, `Property` from `propertiesStore.svelte.ts` (Task 5); `createLocationsStore` from `locationsStore.svelte.ts` (existing); `PropertyModal` (Task 6); shared `Button`, `Input`, `SortableTable`, `Card`, `Column` type (existing, same imports as `WorksPage.svelte`).
- Produces: `PropertiesPage` component with props `{ store: PropertiesStore; locationsStore: LocationsStore; selectedItemId?: string | null; onclearselection?: () => void }`. Consumed by Task 9 (`App.svelte` routing).

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/PropertiesPage.test.ts`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import PropertiesPage from "../src/lib/components/PropertiesPage.svelte";
import type { Property } from "../src/lib/propertiesStore.svelte";

function makeProperty(overrides: Partial<Property> = {}): Property {
  return {
    id: "p1", name: "Casa da Rua das Flores", emoji: "🏠", type: "house", status: "watching",
    locationId: null, address: "", price: null, landSize: null, builtSize: null,
    bedrooms: null, bathrooms: null, listingUrl: null, contact: "",
    pros: [], cons: [], notes: "", attachments: [],
    ...overrides,
  };
}

function makeStore(properties: Property[]) {
  return {
    properties, loaded: true, loadError: null,
    createProperty: vi.fn(), updateProperty: vi.fn(), deleteProperty: vi.fn(),
    uploadAttachment: vi.fn(), deleteAttachment: vi.fn(), reload: vi.fn(),
  };
}

function makeLocationsStore() {
  return { locations: [] };
}

describe("PropertiesPage — external selection", () => {
  it("opens the edit modal for the property matching selectedItemId and clears selection", () => {
    const store = makeStore([makeProperty()]);
    const onclearselection = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(PropertiesPage, {
      target,
      props: { store, locationsStore: makeLocationsStore(), selectedItemId: "p1", onclearselection },
    });
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("Edit property");
    expect(onclearselection).toHaveBeenCalledOnce();

    unmount(comp);
  });
});

describe("PropertiesPage — filters", () => {
  it("filters the table by status", () => {
    const store = makeStore([
      makeProperty({ id: "p1", name: "Casa Sul", status: "watching" }),
      makeProperty({ id: "p2", name: "Casa Norte", status: "purchased" }),
    ]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(PropertiesPage, { target, props: { store, locationsStore: makeLocationsStore() } });
    flushSync();

    const statusSelect = target.querySelectorAll("select.filter-sel")[0] as HTMLSelectElement;
    statusSelect.value = "purchased";
    statusSelect.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    expect(target.textContent).toContain("Casa Norte");
    expect(target.textContent).not.toContain("Casa Sul");

    unmount(comp);
  });
});

describe("PropertiesPage — add property", () => {
  it("opens the create modal when the add button is clicked", () => {
    const store = makeStore([]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(PropertiesPage, { target, props: { store, locationsStore: makeLocationsStore() } });
    flushSync();

    const addBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Add property"))!;
    addBtn.click();
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("＋ New property");

    unmount(comp);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/PropertiesPage.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/PropertiesPage.svelte`

- [ ] **Step 3: Write minimal implementation**

Create `packages/editor/src/lib/components/PropertiesPage.svelte`:

```svelte
<script lang="ts">
  import type { createPropertiesStore, Property } from "../propertiesStore.svelte";
  import type { createLocationsStore } from "../locationsStore.svelte";
  import PropertyModal from "./PropertyModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";
  import Card from "./ui/Card.svelte";

  type PropertiesStore = ReturnType<typeof createPropertiesStore>;
  type LocationsStore = ReturnType<typeof createLocationsStore>;

  interface Props {
    store: PropertiesStore;
    locationsStore: LocationsStore;
    selectedItemId?: string | null;
    onclearselection?: () => void;
  }

  let { store, locationsStore, selectedItemId = null, onclearselection }: Props = $props();

  let modalProperty = $state<Property | "create" | null>(null);

  $effect(() => {
    if (selectedItemId) {
      const found = store.properties.find((p) => p.id === selectedItemId);
      if (found) {
        modalProperty = found;
        onclearselection?.();
      }
    }
  });

  let searchQuery = $state("");
  let statusFilter = $state("");
  let typeFilter = $state("");

  const locationMap = $derived(new Map(locationsStore.locations.map((l) => [l.id, l])));

  const filteredProperties = $derived(store.properties.filter((p) => {
    if (statusFilter && p.status !== statusFilter) return false;
    if (typeFilter && p.type !== typeFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!p.name.toLowerCase().includes(q) && !p.address.toLowerCase().includes(q)) return false;
    }
    return true;
  }));

  function countByStatus(status: Property["status"]): number {
    return store.properties.filter((p) => p.status === status).length;
  }

  function statusLabel(status: Property["status"]): string {
    if (status === "proposal_made") return "Proposal made";
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  function statusColor(status: Property["status"]): string {
    if (status === "purchased") return "#33aa66";
    if (status === "rejected") return "#cc3333";
    if (status === "proposal_made") return "#cc8833";
    if (status === "visited") return "#3388cc";
    return "#888888";
  }

  function typeLabel(type: Property["type"]): string {
    if (type === "land") return "Land";
    if (type === "new_build") return "New build";
    return "House";
  }

  function fmt(n: number): string {
    return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }

  function sizeLabel(p: Property): string {
    const parts: string[] = [];
    if (p.builtSize != null) parts.push(`${fmt(p.builtSize)} m² built`);
    if (p.landSize != null) parts.push(`${fmt(p.landSize)} m² land`);
    return parts.length ? parts.join(" · ") : "—";
  }
</script>

<div class="page">

  {#if store.properties.length === 0}
    <div class="empty-charts">
      <span class="empty-icon">🏘</span>
      <p>No properties yet — click ＋ Add property to get started.</p>
    </div>
  {:else}
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-label">Search pipeline</div>
        <div class="stat-chips-row">
          <div class="stat-chip">
            <div class="stat-title">Watching</div>
            <div class="stat-value">{countByStatus("watching")}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">Visited</div>
            <div class="stat-value">{countByStatus("visited")}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">Proposal made</div>
            <div class="stat-value">{countByStatus("proposal_made")}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">Purchased</div>
            <div class="stat-value">{countByStatus("purchased")}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">Rejected</div>
            <div class="stat-value">{countByStatus("rejected")}</div>
          </div>
          <div class="stat-chip">
            <div class="stat-title">Total</div>
            <div class="stat-value">{store.properties.length}</div>
          </div>
        </div>
      </Card>
    </div>
  {/if}

  <div class="table-card-wrap">
    <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
    <div class="toolbar">
      <Input placeholder="🔍 Search…" bind:value={searchQuery} />
      <select class="native-input filter-sel" bind:value={statusFilter}>
        <option value="">All statuses</option>
        <option value="watching">Watching</option>
        <option value="visited">Visited</option>
        <option value="proposal_made">Proposal made</option>
        <option value="purchased">Purchased</option>
        <option value="rejected">Rejected</option>
      </select>
      <select class="native-input filter-sel" bind:value={typeFilter}>
        <option value="">All types</option>
        <option value="land">Land</option>
        <option value="house">House</option>
        <option value="new_build">New build</option>
      </select>
      <Button onclick={() => { modalProperty = "create"; }}>＋ Add property</Button>
    </div>

    <div class="table-wrapper">
      {#snippet emojiCell(p: Property)}
        {p.emoji}
      {/snippet}
      {#snippet nameCell(p: Property)}
        {p.name}
        {#if p.address}<span class="desc">{p.address}</span>{/if}
      {/snippet}
      {#snippet typeCell(p: Property)}
        {typeLabel(p.type)}
      {/snippet}
      {#snippet locationCell(p: Property)}
        {p.locationId ? (locationMap.get(p.locationId)?.name ?? "—") : "—"}
      {/snippet}
      {#snippet priceCell(p: Property)}
        {p.price != null ? fmt(p.price) + " €" : "—"}
      {/snippet}
      {#snippet sizeCell(p: Property)}
        {sizeLabel(p)}
      {/snippet}
      {#snippet statusCell(p: Property)}
        <span
          class="status-chip"
          style="background:{statusColor(p.status)}22;color:{statusColor(p.status)};border:1px solid {statusColor(p.status)}44"
        >{statusLabel(p.status)}</span>
      {/snippet}

      <SortableTable
        columns={[
          { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
          { key: "name", label: "Name", sortValue: (p) => p.name, cellClass: "name-cell", cell: nameCell },
          { key: "type", label: "Type", sortValue: (p) => typeLabel(p.type), cell: typeCell },
          { key: "location", label: "Location", sortValue: (p) => (p.locationId ? locationMap.get(p.locationId)?.name ?? null : null), cell: locationCell },
          { key: "price", label: "Price", sortValue: (p) => p.price, cell: priceCell },
          { key: "size", label: "Size", sortValue: (p) => p.builtSize ?? p.landSize, cell: sizeCell },
          { key: "status", label: "Status", sortValue: (p) => p.status, cell: statusCell },
        ] as Column<Property>[]}
        rows={filteredProperties}
        rowKey={(p) => p.id}
        rowClick={(p) => { modalProperty = p; }}
        emptyMessage={store.properties.length === 0 ? "No properties yet — click ＋ Add property to get started." : "No properties match your filters."}
      />
    </div>

    <div class="footer">{filteredProperties.length} properties</div>
    </Card>
  </div>
</div>

{#if modalProperty !== null}
  <PropertyModal
    property={modalProperty === "create" ? null : modalProperty}
    {store}
    {locationsStore}
    onclose={() => { modalProperty = null; }}
  />
{/if}

<style>
  .page { display: flex; flex-direction: column; height: 100%; background: var(--bg); font-family: var(--font-sans); }

  .empty-charts {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 32px; gap: 10px; color: var(--text-faint); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .empty-icon { font-size: 36px; }
  .empty-charts p { margin: 0; font-size: 13px; }

  .chart-card-wrap { padding: var(--space-4); flex-shrink: 0; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }
  .stat-chips-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
  .stat-chip {
    flex: 1; min-width: 100px; background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 6px 10px;
  }
  .stat-title { font-size: 8px; color: var(--text-faint); text-transform: uppercase; margin-bottom: 2px; }
  .stat-value { font-size: 13px; color: var(--text); font-weight: 600; }

  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }

  .toolbar {
    display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3);
    background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .toolbar :global(.ui-input) { flex: 1; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); box-sizing: border-box; cursor: pointer;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  .filter-sel { cursor: pointer; }

  .table-wrapper { flex: 1; overflow-y: auto; }
  :global(.emoji-cell) { font-size: 16px; width: 32px; text-align: center; }
  :global(.name-cell) { color: var(--text); font-weight: 600; }
  .desc { font-size: 11px; color: var(--text-faint); font-weight: 400; margin-left: 6px; }
  .status-chip { padding: 2px 7px; border-radius: var(--radius-sm); font-size: 10px; font-weight: 500; }

  .footer { padding: var(--space-2) var(--space-4); border-top: 1px solid var(--border); font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/PropertiesPage.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/PropertiesPage.svelte packages/editor/test/PropertiesPage.test.ts
git commit -m "feat(properties): add PropertiesPage with summary stats and sortable table"
```

---

### Task 8: Frontend HomePropertiesWidget

**Files:**
- Create: `packages/editor/src/lib/components/HomePropertiesWidget.svelte`
- Test: `packages/editor/test/HomePropertiesWidget.test.ts`

**Interfaces:**
- Consumes: `createPropertiesStore`, `Property` from `propertiesStore.svelte.ts` (Task 5); shared `Card` (existing).
- Produces: `HomePropertiesWidget` component with props `{ propertiesStore: PropertiesStore; onnavigate: () => void }`. Consumed by Task 9 (`HomePage.svelte`).

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/HomePropertiesWidget.test.ts`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import HomePropertiesWidget from "../src/lib/components/HomePropertiesWidget.svelte";
import type { Property } from "../src/lib/propertiesStore.svelte";

function makeProperty(overrides: Partial<Property> = {}): Property {
  return {
    id: "p1", name: "Casa da Rua das Flores", emoji: "🏠", type: "house", status: "watching",
    locationId: null, address: "", price: null, landSize: null, builtSize: null,
    bedrooms: null, bathrooms: null, listingUrl: null, contact: "",
    pros: [], cons: [], notes: "", attachments: [],
    ...overrides,
  };
}

function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

describe("HomePropertiesWidget", () => {
  it("renders nothing when there are no properties", () => {
    const store = { properties: [] };
    const el = target();
    const comp = mount(HomePropertiesWidget, { target: el, props: { propertiesStore: store, onnavigate: vi.fn() } });
    flushSync();
    expect(el.querySelector(".widget")).toBeNull();
    unmount(comp);
    el.remove();
  });

  it("shows status counts and the most recently added properties", () => {
    const store = {
      properties: [
        makeProperty({ id: "p1", name: "Casa Sul", status: "watching", price: 250000 }),
        makeProperty({ id: "p2", name: "Terreno Norte", status: "purchased", price: 90000 }),
      ],
    };
    const el = target();
    const comp = mount(HomePropertiesWidget, { target: el, props: { propertiesStore: store, onnavigate: vi.fn() } });
    flushSync();
    expect(el.querySelector(".widget")).not.toBeNull();
    expect(el.textContent).toContain("Terreno Norte");
    expect(el.textContent).toContain("Casa Sul");
    unmount(comp);
    el.remove();
  });

  it("calls onnavigate when clicked", () => {
    const store = { properties: [makeProperty()] };
    const el = target();
    const onnavigate = vi.fn();
    const comp = mount(HomePropertiesWidget, { target: el, props: { propertiesStore: store, onnavigate } });
    flushSync();
    (el.querySelector(".widget") as HTMLElement).click();
    expect(onnavigate).toHaveBeenCalled();
    unmount(comp);
    el.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/HomePropertiesWidget.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/HomePropertiesWidget.svelte`

- [ ] **Step 3: Write minimal implementation**

Create `packages/editor/src/lib/components/HomePropertiesWidget.svelte`:

```svelte
<script lang="ts">
  import type { createPropertiesStore } from "../propertiesStore.svelte";
  import Card from "./ui/Card.svelte";

  type PropertiesStore = ReturnType<typeof createPropertiesStore>;

  interface Props {
    propertiesStore: PropertiesStore;
    onnavigate: () => void;
  }
  let { propertiesStore, onnavigate }: Props = $props();

  const STATUSES = ["watching", "visited", "proposal_made", "purchased", "rejected"] as const;

  function countByStatus(status: string): number {
    return propertiesStore.properties.filter((p) => p.status === status).length;
  }

  function statusLabel(status: string): string {
    if (status === "proposal_made") return "Proposal";
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  function statusColor(status: string): string {
    if (status === "purchased") return "#33aa66";
    if (status === "rejected") return "#cc3333";
    if (status === "proposal_made") return "#cc8833";
    if (status === "visited") return "#3388cc";
    return "#888888";
  }

  function fmt(n: number): string {
    return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }

  const recent = $derived(propertiesStore.properties.slice(-3).reverse());
</script>

{#if propertiesStore.properties.length > 0}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
  <div
    class="widget"
    role="button"
    tabindex="0"
    onclick={onnavigate}
    onkeydown={(e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onnavigate();
      }
    }}
  >
    <Card>
      <div class="header"><h3>🏘 Properties</h3></div>
      <div class="status-counts">
        {#each STATUSES as s}
          <span class="status-count" style="color:{statusColor(s)}">{statusLabel(s)} {countByStatus(s)}</span>
        {/each}
      </div>
      <ul class="recent-list">
        {#each recent as p (p.id)}
          <li>
            <span class="emoji">{p.emoji}</span>
            <span class="name">{p.name}</span>
            <span class="price">{p.price != null ? fmt(p.price) + " €" : "—"}</span>
          </li>
        {/each}
      </ul>
    </Card>
  </div>
{/if}

<style>
  .widget { cursor: pointer; }
  .header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--space-2); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .status-counts { display: flex; flex-wrap: wrap; gap: 8px; font-size: 11px; font-weight: 600; margin-bottom: 8px; }
  .recent-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .recent-list li { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-muted); }
  .recent-list .name { flex: 1; color: var(--text); font-weight: 500; }
  .recent-list .price { font-weight: 600; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/HomePropertiesWidget.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/HomePropertiesWidget.svelte packages/editor/test/HomePropertiesWidget.test.ts
git commit -m "feat(properties): add home dashboard widget"
```

---

### Task 9: Wire store, routing, nav entry, and activity-log filter into the app shell

**Files:**
- Modify: `packages/editor/src/App.svelte` (store creation, reload effect, route swap, `HomePage` prop)
- Modify: `packages/editor/src/lib/components/HomePage.svelte` (accept and render `propertiesStore`)
- Modify: `packages/editor/src/lib/components/NavMenu.svelte` (drop `placeholder: true` on `properties`)
- Modify: `packages/editor/src/lib/components/settings/SettingsActivityLog.svelte` (add "Properties" to the module filter dropdown)

**Interfaces:**
- Consumes: `createPropertiesStore` (Task 5), `PropertiesPage` (Task 7), `HomePropertiesWidget` (Task 8).

- [ ] **Step 1: Wire the store into App.svelte**

In `packages/editor/src/App.svelte`, add the import and store creation next to `locationsStore` (around line 80):

```svelte
  import { createPropertiesStore } from "./lib/propertiesStore.svelte";
```

```svelte
  const locationsStore = createLocationsStore(getHomeId);
  const propertiesStore = createPropertiesStore(getHomeId);
```

Add the reload call inside the home-switch `$effect` (around line 93-104), next to `locationsStore.reload()`:

```svelte
    locationsStore.reload();
    propertiesStore.reload();
```

- [ ] **Step 2: Wire the route and HomePage prop**

Replace the placeholder route:

```svelte
      {:else if currentRoute === "#/properties"}
        <PlaceholderPage icon="🏘" label="Properties" description="Track property listings, prices, and details." />
```

with:

```svelte
      {:else if currentRoute === "#/properties"}
        <PropertiesPage store={propertiesStore} {locationsStore} />
```

Add the `PropertiesPage` import next to the other page imports:

```svelte
  import PropertiesPage from "./lib/components/PropertiesPage.svelte";
```

Add `propertiesStore` to the `<HomePage ... />` invocation:

```svelte
        <HomePage
          {floorStore}
          {choreStore}
          {inventoryStore}
          {settingsStore}
          {costsStore}
          {worksStore}
          {consumableStore}
          {locationsStore}
          {propertiesStore}
        />
```

- [ ] **Step 3: Render the widget in HomePage.svelte**

In `packages/editor/src/lib/components/HomePage.svelte`, add the import:

```svelte
  import type { createPropertiesStore } from "../propertiesStore.svelte";
  import HomePropertiesWidget from "./HomePropertiesWidget.svelte";
```

Add the type alias next to `LocationsStore`:

```svelte
  type PropertiesStore = ReturnType<typeof createPropertiesStore>;
```

Add `propertiesStore` to `Props` and the destructure:

```svelte
  interface Props {
    floorStore: HouseStore;
    choreStore: ChoreStore;
    inventoryStore: InventoryStore;
    settingsStore: SettingsStore;
    costsStore: CostsStore;
    worksStore: WorksStore;
    consumableStore: ConsumableStore;
    locationsStore: LocationsStore;
    propertiesStore: PropertiesStore;
  }
  let { floorStore, choreStore, inventoryStore, settingsStore, costsStore, worksStore, consumableStore, locationsStore, propertiesStore }: Props = $props();
```

Add the widget to the side column, after `HomeLocationsWidget`:

```svelte
    <HomeLocationsWidget {locationsStore} onnavigate={() => navigate("#/locations")} />
    <HomePropertiesWidget {propertiesStore} onnavigate={() => navigate("#/properties")} />
```

- [ ] **Step 4: Drop the placeholder flag in NavMenu**

In `packages/editor/src/lib/components/NavMenu.svelte`, change:

```typescript
    { id: "properties",  href: "#/properties",  icon: "🏘", label: "Properties",  placeholder: true },
```

to:

```typescript
    { id: "properties",  href: "#/properties",  icon: "🏘", label: "Properties"   },
```

- [ ] **Step 5: Add Properties to the Activity Log module filter**

In `packages/editor/src/lib/components/settings/SettingsActivityLog.svelte`, add an option after `Knowledge Base` in the `<select class="activity-module-filter ...">`:

```svelte
          <option value="kb">Knowledge Base</option>
          <option value="locations">Locations</option>
          <option value="properties">Properties</option>
```

(This also adds the pre-existing missing "Locations" option, consistent with the `MODULE_NOUNS` fix in Task 2 — both were gaps from when the Locations module shipped.)

- [ ] **Step 6: Run the full frontend test suite to verify nothing broke**

Run: `cd packages/editor && npx vitest run`
Expected: PASS (all existing tests plus the 16 new tests from Tasks 5–8)

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/src/lib/components/HomePage.svelte packages/editor/src/lib/components/NavMenu.svelte packages/editor/src/lib/components/settings/SettingsActivityLog.svelte
git commit -m "feat(properties): wire store, routing, nav entry, and activity-log filter into the app shell"
```

---

### Task 10: Manual verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend and frontend test suites one more time**

```bash
cd packages/backend && python -m pytest -q
cd packages/editor && npx vitest run
```
Expected: All PASS.

- [ ] **Step 2: Launch the app and drive the feature end-to-end**

Use the `webapp-testing` skill (Playwright) or the project's `run` skill to start the dev server, then:
1. Create (or reuse) a home; go to Settings → Home and enable the "Properties" module (it's off by default).
2. Navigate to Properties via the nav — confirm it's no longer "Coming soon" and shows the empty state.
3. Also enable "Locations" and add 1-2 candidate locations, so the Property modal's location dropdown has options.
4. Add a property of each type: Land only, Existing house, New-build — set price, sizes, bedrooms/bathrooms (house/new-build), listing URL, contact, and link one to a Location.
5. On the Pros/Cons tab, add 2+ pros and 1+ cons; confirm add/remove works and persists on save.
6. Upload a photo attachment to a saved property; confirm the thumbnail renders correctly (not broken) — this specifically verifies the attachment-URL fix from this plan's Global Constraints.
7. Move a property through several statuses (Watching → Visited → Proposal made → Purchased) and confirm the summary stat chips and status filter update correctly.
8. Confirm the table search (by name/address) and type filter work, and that sorting by Price/Size/Status via column headers works.
9. Delete a location that a property references; confirm the property's Location column falls back to "—" instead of erroring.
10. Go to the Home dashboard and confirm the new Properties widget shows status counts and the most recently added properties, and that clicking it navigates to `#/properties`.
11. Go to Settings → Activity Log; confirm entries for Properties actions appear with readable descriptions (e.g. "added property 'Casa Sul'"), and that filtering by module includes "Properties" (and "Locations", confirming the drive-by fix).
12. Check both light and dark theme for the new page and modal (status chip colors, pros/cons list, table) — no unreadable contrast.

- [ ] **Step 3: Report results**

Summarize pass/fail for each item above. Fix any issues found before considering the module complete.

---

## Self-Review Notes

- **Spec coverage:** all 4 spec sections (data model, backend, frontend, testing) are covered — Task 1 = data model + persistence, Tasks 2-3 = backend REST, Task 4 = MCP, Tasks 5-8 = frontend, Task 9 = wiring, Task 10 = the spec's "manual verification" requirement. The spec's two explicit out-of-scope items (floor-plan pins, reorder) are correctly absent from every task.
- **Placeholder scan:** no TBD/TODO; every step has complete, runnable code.
- **Type consistency:** `Property`'s field set (`type`, `status`, `locationId`, `pros`/`cons`, etc.) is defined once in Task 1 (backend Pydantic model + SQL columns) and once in Task 5 (frontend TypeScript interface), and referenced identically by name in every later task — route paths from Task 2/3 are consumed verbatim by the store in Task 5; the store's method names (`createProperty`, `updateProperty`, `deleteProperty`, `uploadAttachment`, `deleteAttachment`) match what `PropertyModal` (Task 6) and `PropertiesPage` (Task 7) call.
- **Bug fixes carried in-scope:** the `MODULE_NOUNS`/`ActivityEntry.module` gap (Task 2) and the WorkModal-style broken attachment URL (avoided in Task 6, not fixed elsewhere) were both discovered while researching this module's own activity-log and attachment wiring, are directly on the code paths this plan already touches, and were confirmed with the user before inclusion.

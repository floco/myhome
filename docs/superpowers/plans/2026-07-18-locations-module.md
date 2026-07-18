# Locations Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `#/locations` placeholder with a real tool for comparing 3+ candidate locations (countries, cities, regions) against a customizable, weighted set of criteria, visually surfacing both the best location per criterion and the best overall.

**Architecture:** A standalone module following the existing Consumables/Works/Costs pattern — new backend files (models, persistence, routes, MCP tools) plus new frontend files (store, page, and supporting components), wired into the existing multi-home / nav / routing infrastructure. No floor-plan integration (candidate locations are not the user's own home).

**Tech Stack:** FastAPI + Pydantic + SQLAlchemy (SQLite) on the backend; Svelte 5 (runes) + Vitest on the frontend. No new dependencies.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-18-locations-module-design.md` — read it before starting; every task below implements a piece of it.
- One comparison per Project home (no separate "comparison sets").
- 1–5 integer score per (location, criterion) cell, plus a free-text note. `null` score = unrated.
- Criterion weight is `"low" | "medium" | "high"`, multiplier 1 / 2 / 3. Overall weighted score = `Σ(score × weight) / Σ(weight)` over that location's *rated* criteria only.
- New Project homes are seeded with 11 default criteria (see Task 1). Existing/demo homes never get seeded.
- Follow existing module conventions exactly: SQLAlchemy `Table` in `schema.py` (no Alembic — `metadata.create_all` handles it), `load_x`/`save_x` truncate-and-reinsert persistence functions, FastAPI routes returning the raw Pydantic doc/model, MCP tools as thin wrappers around `_impl` functions, Svelte stores as `create_XStore(getHomeId)` factories with `$state` arrays and a `reload()` method.
- Per this repo's known Svelte 5 + jsdom testing gotcha: components under test must be mounted to a node attached to `document.body`, and any manually-dispatched DOM events need `bubbles: true`, or handlers silently never fire.

---

### Task 1: Backend data layer — schema, models, persistence, default-criteria seed

**Files:**
- Modify: `packages/backend/src/myhome/schema.py` (append 3 tables at end of file, after `house_documents`)
- Create: `packages/backend/src/myhome/models_locations.py`
- Create: `packages/backend/src/myhome/persistence_locations.py`
- Test: `packages/backend/tests/test_locations_persistence.py`

**Interfaces:**
- Produces: `LocationCriterion(id, name, description="", weight="low"|"medium"|"high"="medium")`, `Location(id, name, emoji="📍")`, `LocationRating(locationId, criterionId, score: int|None=None, note="")`, `LocationsDocument(version=1, criteria=[], locations=[], ratings=[])`, `LocationCriterionCreate/Update`, `LocationCreate/Update`, `ReorderRequest(orderedIds: list[str])`, `RatingUpdate(score, note)` — all in `models_locations.py`.
- Produces: `load_locations(home_id: str) -> LocationsDocument`, `save_locations(home_id: str, doc: LocationsDocument) -> None`, `seed_default_criteria(home_id: str) -> None`, `DEFAULT_CRITERIA: list[tuple[str, str]]` — all in `persistence_locations.py`. Consumed by Tasks 2, 3, 4.

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_locations_persistence.py`:

```python
import pytest
from myhome.models_locations import Location, LocationCriterion, LocationRating, LocationsDocument
from myhome.persistence_locations import DEFAULT_CRITERIA, load_locations, save_locations, seed_default_criteria


def make_doc() -> LocationsDocument:
    return LocationsDocument(
        criteria=[LocationCriterion(id="crit1", name="Cost of Living", description="How expensive", weight="high")],
        locations=[Location(id="loc1", name="Ljubljana", emoji="🇸🇮")],
        ratings=[LocationRating(locationId="loc1", criterionId="crit1", score=4, note="Cheap enough")],
    )


def test_load_locations_empty(client, home_id):
    doc = load_locations(home_id)
    assert doc.criteria == []
    assert doc.locations == []
    assert doc.ratings == []


def test_save_and_load_round_trip(client, home_id):
    save_locations(home_id, make_doc())
    doc = load_locations(home_id)
    assert doc.criteria[0].name == "Cost of Living"
    assert doc.criteria[0].weight == "high"
    assert doc.locations[0].name == "Ljubljana"
    assert doc.locations[0].emoji == "🇸🇮"
    assert doc.ratings[0].score == 4
    assert doc.ratings[0].note == "Cheap enough"


def test_save_deletes_ratings_for_removed_criterion(client, home_id):
    save_locations(home_id, make_doc())
    doc = load_locations(home_id)
    doc.criteria = []
    save_locations(home_id, doc)
    reloaded = load_locations(home_id)
    assert reloaded.ratings == []


def test_save_deletes_ratings_for_removed_location(client, home_id):
    save_locations(home_id, make_doc())
    doc = load_locations(home_id)
    doc.locations = []
    save_locations(home_id, doc)
    reloaded = load_locations(home_id)
    assert reloaded.ratings == []


def test_seed_default_criteria(client, home_id):
    seed_default_criteria(home_id)
    doc = load_locations(home_id)
    assert len(doc.criteria) == len(DEFAULT_CRITERIA) == 11
    assert doc.locations == []
    names = [c.name for c in doc.criteria]
    assert "Cost of Living" in names
    assert "Healthcare" in names
    assert all(c.weight == "medium" for c in doc.criteria)
    assert all(c.description != "" for c in doc.criteria)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_locations_persistence.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.models_locations'`

- [ ] **Step 3: Write minimal implementation**

Append to `packages/backend/src/myhome/schema.py` (after the `house_documents` table at the end of the file):

```python
location_criteria = Table(
    "location_criteria", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("description", String, nullable=False),
    Column("weight", String, nullable=False),
)

locations = Table(
    "locations", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
)

location_ratings = Table(
    "location_ratings", metadata,
    Column("location_id", String, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True),
    Column("criterion_id", String, ForeignKey("location_criteria.id", ondelete="CASCADE"), primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("score", Integer),
    Column("note", String, nullable=False),
)
```

Create `packages/backend/src/myhome/models_locations.py`:

```python
# packages/backend/src/myhome/models_locations.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

Weight = Literal["low", "medium", "high"]


class LocationCriterion(BaseModel):
    id: str
    name: str
    description: str = ""
    weight: Weight = "medium"


class Location(BaseModel):
    id: str
    name: str
    emoji: str = "📍"


class LocationRating(BaseModel):
    locationId: str
    criterionId: str
    score: int | None = None
    note: str = ""


class LocationsDocument(BaseModel):
    version: int = 1
    criteria: list[LocationCriterion] = []
    locations: list[Location] = []
    ratings: list[LocationRating] = []


class LocationCriterionCreate(BaseModel):
    name: str
    description: str = ""
    weight: Weight = "medium"


class LocationCriterionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    weight: Weight | None = None


class LocationCreate(BaseModel):
    name: str
    emoji: str = "📍"


class LocationUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None


class ReorderRequest(BaseModel):
    orderedIds: list[str]


class RatingUpdate(BaseModel):
    score: int | None = None
    note: str = ""
```

Create `packages/backend/src/myhome/persistence_locations.py`:

```python
# packages/backend/src/myhome/persistence_locations.py
from __future__ import annotations

import uuid

from sqlalchemy import select

from .db import get_engine
from .models_locations import Location, LocationCriterion, LocationRating, LocationsDocument
from .schema import (
    location_criteria as location_criteria_table,
    location_ratings as location_ratings_table,
    locations as locations_table,
)

DEFAULT_CRITERIA: list[tuple[str, str]] = [
    ("Geography & Climate", "Geographic location, climate patterns, seasonal temperatures."),
    ("Cost of Living", "Cost of land, construction, everyday goods and services relative to your budget."),
    ("Healthcare", "Quality and accessibility of the healthcare system, especially for retirement."),
    ("Taxation", "Tax rules and residency implications for foreign residents."),
    ("Language & Culture", "Local language and your comfort with it; familiarity and appeal of the local culture."),
    ("Social Network & Community", "Presence of an existing community/family nearby and opportunities for social integration."),
    ("Safety", "Personal and property safety in the area."),
    ("Access to Services", "Proximity to essential services: hospitals, shops, etc."),
    ("Mobility & Transport", "Airports, roads, and public transport connections."),
    ("Real Estate Regulations", "Building and zoning regulations that would apply."),
    ("Quality of Life", "Overall subjective quality of life in the area."),
]


def load_locations(home_id: str) -> LocationsDocument:
    engine = get_engine()
    with engine.connect() as conn:
        criterion_rows = conn.execute(
            select(location_criteria_table).where(location_criteria_table.c.home_id == home_id)
            .order_by(location_criteria_table.c.order_index)
        ).mappings().all()
        location_rows = conn.execute(
            select(locations_table).where(locations_table.c.home_id == home_id)
            .order_by(locations_table.c.order_index)
        ).mappings().all()
        rating_rows = conn.execute(
            select(location_ratings_table).where(location_ratings_table.c.home_id == home_id)
        ).mappings().all()

    criteria = [
        LocationCriterion(id=r["id"], name=r["name"], description=r["description"], weight=r["weight"])
        for r in criterion_rows
    ]
    locations = [Location(id=r["id"], name=r["name"], emoji=r["emoji"]) for r in location_rows]
    ratings = [
        LocationRating(locationId=r["location_id"], criterionId=r["criterion_id"], score=r["score"], note=r["note"])
        for r in rating_rows
    ]
    return LocationsDocument(criteria=criteria, locations=locations, ratings=ratings)


def save_locations(home_id: str, doc: LocationsDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(location_ratings_table.delete().where(location_ratings_table.c.home_id == home_id))
        conn.execute(locations_table.delete().where(locations_table.c.home_id == home_id))
        conn.execute(location_criteria_table.delete().where(location_criteria_table.c.home_id == home_id))
        if doc.criteria:
            conn.execute(location_criteria_table.insert(), [
                {
                    "id": c.id, "home_id": home_id, "order_index": i,
                    "name": c.name, "description": c.description, "weight": c.weight,
                }
                for i, c in enumerate(doc.criteria)
            ])
        if doc.locations:
            conn.execute(locations_table.insert(), [
                {"id": l.id, "home_id": home_id, "order_index": i, "name": l.name, "emoji": l.emoji}
                for i, l in enumerate(doc.locations)
            ])
        if doc.ratings:
            conn.execute(location_ratings_table.insert(), [
                {
                    "location_id": r.locationId, "criterion_id": r.criterionId, "home_id": home_id,
                    "score": r.score, "note": r.note,
                }
                for r in doc.ratings
            ])


def seed_default_criteria(home_id: str) -> None:
    doc = LocationsDocument(
        criteria=[
            LocationCriterion(id=str(uuid.uuid4()), name=name, description=description)
            for name, description in DEFAULT_CRITERIA
        ],
    )
    save_locations(home_id, doc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_locations_persistence.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/models_locations.py packages/backend/src/myhome/persistence_locations.py packages/backend/tests/test_locations_persistence.py
git commit -m "feat(locations): add data layer — schema, models, persistence, default criteria seed"
```

---

### Task 2: Backend REST routes

**Files:**
- Create: `packages/backend/src/myhome/routes/locations.py`
- Modify: `packages/backend/src/myhome/main.py:19` (add `locations` to the routes import) and add `app.include_router(locations.router)` near the other `include_router` calls
- Test: `packages/backend/tests/test_locations.py`

**Interfaces:**
- Consumes: `load_locations`, `save_locations` from `persistence_locations.py` (Task 1); `LocationCriterion`, `LocationCriterionCreate`, `LocationCriterionUpdate`, `Location`, `LocationCreate`, `LocationUpdate`, `LocationRating`, `RatingUpdate`, `ReorderRequest` from `models_locations.py` (Task 1); `log_activity` from `persistence_activity.py` (existing); `get_current_user_id` from `deps.py` (existing).
- Produces: REST endpoints under `/api/homes/{home_id}/locations...` (full list below). Consumed by Task 5 (frontend store).

```
GET    /api/homes/{home_id}/locations
POST   /api/homes/{home_id}/locations/criteria
PUT    /api/homes/{home_id}/locations/criteria/{id}
DELETE /api/homes/{home_id}/locations/criteria/{id}
PUT    /api/homes/{home_id}/locations/criteria/reorder
POST   /api/homes/{home_id}/locations/locations
PUT    /api/homes/{home_id}/locations/locations/{id}
DELETE /api/homes/{home_id}/locations/locations/{id}
PUT    /api/homes/{home_id}/locations/locations/reorder
PUT    /api/homes/{home_id}/locations/ratings/{location_id}/{criterion_id}
DELETE /api/homes/{home_id}/locations/ratings/{location_id}/{criterion_id}
```

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_locations.py`:

```python
import pytest
from myhome.models_locations import Location, LocationCriterion, LocationRating, LocationsDocument
from myhome.persistence_locations import save_locations


def make_doc() -> LocationsDocument:
    return LocationsDocument(
        criteria=[LocationCriterion(id="crit1", name="Safety", description="", weight="medium")],
        locations=[Location(id="loc1", name="Nantes", emoji="🇫🇷")],
    )


# --- GET ---

def test_get_locations_empty(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["criteria"] == []
    assert data["locations"] == []
    assert data["ratings"] == []


# --- criteria CRUD ---

def test_create_criterion(client, home_id):
    resp = client.post(
        f"/api/homes/{home_id}/locations/criteria",
        json={"name": "Healthcare", "description": "Quality of care", "weight": "high"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Healthcare"
    assert data["weight"] == "high"
    assert "id" in data


def test_create_criterion_defaults(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/locations/criteria", json={"name": "Safety"})
    assert resp.status_code == 201
    assert resp.json()["weight"] == "medium"


def test_update_criterion(client, home_id):
    save_locations(home_id, make_doc())
    resp = client.put(f"/api/homes/{home_id}/locations/criteria/crit1", json={"weight": "low"})
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert data["criteria"][0]["weight"] == "low"


def test_update_criterion_not_found(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/locations/criteria/nope", json={"name": "X"})
    assert resp.status_code == 404


def test_delete_criterion_cascades_ratings(client, home_id):
    doc = make_doc()
    doc.ratings.append(LocationRating(locationId="loc1", criterionId="crit1", score=3, note=""))
    save_locations(home_id, doc)
    resp = client.delete(f"/api/homes/{home_id}/locations/criteria/crit1")
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert data["criteria"] == []
    assert data["ratings"] == []


def test_delete_criterion_not_found(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/locations/criteria/nope")
    assert resp.status_code == 404


def test_reorder_criteria(client, home_id):
    save_locations(home_id, LocationsDocument(criteria=[
        LocationCriterion(id="c1", name="A"), LocationCriterion(id="c2", name="B"),
    ]))
    resp = client.put(f"/api/homes/{home_id}/locations/criteria/reorder", json={"orderedIds": ["c2", "c1"]})
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert [c["id"] for c in data["criteria"]] == ["c2", "c1"]


def test_reorder_criteria_mismatched_ids(client, home_id):
    save_locations(home_id, LocationsDocument(criteria=[LocationCriterion(id="c1", name="A")]))
    resp = client.put(f"/api/homes/{home_id}/locations/criteria/reorder", json={"orderedIds": ["c1", "nope"]})
    assert resp.status_code == 400


# --- locations CRUD ---

def test_create_location(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/locations/locations", json={"name": "Zagreb", "emoji": "🇭🇷"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Zagreb"
    assert data["emoji"] == "🇭🇷"


def test_create_location_default_emoji(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/locations/locations", json={"name": "Nice"})
    assert resp.status_code == 201
    assert resp.json()["emoji"] == "📍"


def test_update_location(client, home_id):
    save_locations(home_id, make_doc())
    resp = client.put(f"/api/homes/{home_id}/locations/locations/loc1", json={"name": "Nantes Metro"})
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert data["locations"][0]["name"] == "Nantes Metro"


def test_update_location_not_found(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/locations/locations/nope", json={"name": "X"})
    assert resp.status_code == 404


def test_delete_location_cascades_ratings(client, home_id):
    save_locations(home_id, make_doc())
    client.put(f"/api/homes/{home_id}/locations/ratings/loc1/crit1", json={"score": 3, "note": "ok"})
    resp = client.delete(f"/api/homes/{home_id}/locations/locations/loc1")
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert data["locations"] == []
    assert data["ratings"] == []


def test_delete_location_not_found(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/locations/locations/nope")
    assert resp.status_code == 404


def test_reorder_locations(client, home_id):
    save_locations(home_id, LocationsDocument(locations=[Location(id="l1", name="A"), Location(id="l2", name="B")]))
    resp = client.put(f"/api/homes/{home_id}/locations/locations/reorder", json={"orderedIds": ["l2", "l1"]})
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert [l["id"] for l in data["locations"]] == ["l2", "l1"]


# --- ratings ---

def test_upsert_rating(client, home_id):
    save_locations(home_id, make_doc())
    resp = client.put(f"/api/homes/{home_id}/locations/ratings/loc1/crit1", json={"score": 5, "note": "Great"})
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert data["ratings"][0]["score"] == 5
    assert data["ratings"][0]["note"] == "Great"


def test_upsert_rating_replaces_existing(client, home_id):
    save_locations(home_id, make_doc())
    client.put(f"/api/homes/{home_id}/locations/ratings/loc1/crit1", json={"score": 2, "note": "meh"})
    client.put(f"/api/homes/{home_id}/locations/ratings/loc1/crit1", json={"score": 5, "note": "great"})
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert len(data["ratings"]) == 1
    assert data["ratings"][0]["score"] == 5


def test_upsert_rating_unknown_location(client, home_id):
    save_locations(home_id, LocationsDocument(criteria=[LocationCriterion(id="crit1", name="Safety")]))
    resp = client.put(f"/api/homes/{home_id}/locations/ratings/nope/crit1", json={"score": 3})
    assert resp.status_code == 404


def test_upsert_rating_unknown_criterion(client, home_id):
    save_locations(home_id, LocationsDocument(locations=[Location(id="loc1", name="X")]))
    resp = client.put(f"/api/homes/{home_id}/locations/ratings/loc1/nope", json={"score": 3})
    assert resp.status_code == 404


def test_clear_rating(client, home_id):
    save_locations(home_id, make_doc())
    client.put(f"/api/homes/{home_id}/locations/ratings/loc1/crit1", json={"score": 4, "note": "x"})
    resp = client.delete(f"/api/homes/{home_id}/locations/ratings/loc1/crit1")
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert data["ratings"] == []


def test_clear_rating_not_found(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/locations/ratings/loc1/crit1")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_locations.py -v`
Expected: FAIL with 404s (no route registered) on every request

- [ ] **Step 3: Write minimal implementation**

Create `packages/backend/src/myhome/routes/locations.py`:

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user_id
from ..models_locations import (
    Location,
    LocationCreate,
    LocationCriterion,
    LocationCriterionCreate,
    LocationCriterionUpdate,
    LocationRating,
    LocationUpdate,
    RatingUpdate,
    ReorderRequest,
)
from ..persistence_activity import log_activity
from ..persistence_locations import load_locations, save_locations

router = APIRouter()


@router.get("/api/homes/{home_id}/locations")
def get_locations(home_id: str):
    return load_locations(home_id)


# --- criteria ---

@router.post("/api/homes/{home_id}/locations/criteria", response_model=LocationCriterion, status_code=201)
def create_criterion(
    home_id: str, body: LocationCriterionCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> LocationCriterion:
    doc = load_locations(home_id)
    item = LocationCriterion(id=str(uuid.uuid4()), **body.model_dump())
    doc.criteria.append(item)
    save_locations(home_id, doc)
    log_activity(home_id, current_user_id, "locations", "create", item.name, item.id)
    return item


@router.put("/api/homes/{home_id}/locations/criteria/{id}", status_code=204)
def update_criterion(home_id: str, id: str, body: LocationCriterionUpdate) -> None:
    doc = load_locations(home_id)
    item = next((c for c in doc.criteria if c.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    save_locations(home_id, doc)


@router.delete("/api/homes/{home_id}/locations/criteria/{id}", status_code=204)
def delete_criterion(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_locations(home_id)
    item = next((c for c in doc.criteria if c.id == id), None)
    if item is None:
        raise HTTPException(status_code=404)
    doc.criteria = [c for c in doc.criteria if c.id != id]
    doc.ratings = [r for r in doc.ratings if r.criterionId != id]
    save_locations(home_id, doc)
    log_activity(home_id, current_user_id, "locations", "delete", item.name, id)


@router.put("/api/homes/{home_id}/locations/criteria/reorder", status_code=204)
def reorder_criteria(home_id: str, body: ReorderRequest) -> None:
    doc = load_locations(home_id)
    by_id = {c.id: c for c in doc.criteria}
    if set(body.orderedIds) != set(by_id.keys()):
        raise HTTPException(status_code=400, detail="orderedIds must match existing criterion ids")
    doc.criteria = [by_id[i] for i in body.orderedIds]
    save_locations(home_id, doc)


# --- locations ---

@router.post("/api/homes/{home_id}/locations/locations", response_model=Location, status_code=201)
def create_location(
    home_id: str, body: LocationCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Location:
    doc = load_locations(home_id)
    item = Location(id=str(uuid.uuid4()), **body.model_dump())
    doc.locations.append(item)
    save_locations(home_id, doc)
    log_activity(home_id, current_user_id, "locations", "create", item.name, item.id)
    return item


@router.put("/api/homes/{home_id}/locations/locations/{id}", status_code=204)
def update_location(home_id: str, id: str, body: LocationUpdate) -> None:
    doc = load_locations(home_id)
    item = next((l for l in doc.locations if l.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    save_locations(home_id, doc)


@router.delete("/api/homes/{home_id}/locations/locations/{id}", status_code=204)
def delete_location(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_locations(home_id)
    item = next((l for l in doc.locations if l.id == id), None)
    if item is None:
        raise HTTPException(status_code=404)
    doc.locations = [l for l in doc.locations if l.id != id]
    doc.ratings = [r for r in doc.ratings if r.locationId != id]
    save_locations(home_id, doc)
    log_activity(home_id, current_user_id, "locations", "delete", item.name, id)


@router.put("/api/homes/{home_id}/locations/locations/reorder", status_code=204)
def reorder_locations(home_id: str, body: ReorderRequest) -> None:
    doc = load_locations(home_id)
    by_id = {l.id: l for l in doc.locations}
    if set(body.orderedIds) != set(by_id.keys()):
        raise HTTPException(status_code=400, detail="orderedIds must match existing location ids")
    doc.locations = [by_id[i] for i in body.orderedIds]
    save_locations(home_id, doc)


# --- ratings ---

@router.put("/api/homes/{home_id}/locations/ratings/{location_id}/{criterion_id}", status_code=204)
def upsert_rating(home_id: str, location_id: str, criterion_id: str, body: RatingUpdate) -> None:
    doc = load_locations(home_id)
    if not any(l.id == location_id for l in doc.locations):
        raise HTTPException(status_code=404, detail="Unknown location_id")
    if not any(c.id == criterion_id for c in doc.criteria):
        raise HTTPException(status_code=404, detail="Unknown criterion_id")
    doc.ratings = [r for r in doc.ratings if not (r.locationId == location_id and r.criterionId == criterion_id)]
    doc.ratings.append(LocationRating(locationId=location_id, criterionId=criterion_id, score=body.score, note=body.note))
    save_locations(home_id, doc)


@router.delete("/api/homes/{home_id}/locations/ratings/{location_id}/{criterion_id}", status_code=204)
def clear_rating(home_id: str, location_id: str, criterion_id: str) -> None:
    doc = load_locations(home_id)
    before = len(doc.ratings)
    doc.ratings = [r for r in doc.ratings if not (r.locationId == location_id and r.criterionId == criterion_id)]
    if len(doc.ratings) == before:
        raise HTTPException(status_code=404)
    save_locations(home_id, doc)
```

Modify `packages/backend/src/myhome/main.py:19` — add `locations` to the import list (keep alphabetical):

```python
from .routes import activity, auth, backup, chores, consumables, costs, ha, homes, house, inventory, kb, locations, mcp_config, notifications, settings, svg, works
```

Add a new `include_router` call next to `app.include_router(consumables.router)` (around line 155):

```python
app.include_router(locations.router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_locations.py -v`
Expected: PASS (20 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/locations.py packages/backend/src/myhome/main.py packages/backend/tests/test_locations.py
git commit -m "feat(locations): add REST routes for criteria, locations, and ratings"
```

---

### Task 3: Seed default criteria on Project home creation

**Files:**
- Modify: `packages/backend/src/myhome/persistence_homes.py` (import + one call in `create_home`)
- Modify: `packages/backend/tests/test_homes.py` (add 2 tests near `test_create_home_project`)

**Interfaces:**
- Consumes: `seed_default_criteria` from `persistence_locations.py` (Task 1).

- [ ] **Step 1: Write the failing test**

In `packages/backend/tests/test_homes.py`, add these two tests directly after `test_create_home_project` (line 38):

```python
def test_create_home_project_seeds_default_location_criteria(client):
    resp = client.post("/api/homes", json={"name": "Retirement Search", "type": "project"})
    home_id = resp.json()["id"]
    locations_resp = client.get(f"/api/homes/{home_id}/locations")
    assert locations_resp.status_code == 200
    data = locations_resp.json()
    assert len(data["criteria"]) == 11
    assert data["locations"] == []


def test_create_home_existing_does_not_seed_location_criteria(client):
    resp = client.post("/api/homes", json={"name": "My House", "type": "existing"})
    home_id = resp.json()["id"]
    locations_resp = client.get(f"/api/homes/{home_id}/locations")
    assert locations_resp.json()["criteria"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_homes.py -k location_criteria -v`
Expected: FAIL — `test_create_home_project_seeds_default_location_criteria` gets 0 criteria instead of 11

- [ ] **Step 3: Write minimal implementation**

In `packages/backend/src/myhome/persistence_homes.py`, add the import next to the existing `from .demo_data import seed_demo_home` (line 14):

```python
from .demo_data import seed_demo_home
from .persistence_locations import seed_default_criteria
```

In `create_home` (currently lines 103–133), add the seeding call right after `save_homes(doc)` and before the `if home_type == "demo":` block:

```python
    _home_dir(home.id).mkdir(parents=True, exist_ok=True)
    doc = load_homes()
    doc.homes.append(home)
    save_homes(doc)

    if home_type == "project":
        seed_default_criteria(home.id)

    if home_type == "demo":
        try:
            seed_demo_home(home.id)
        except Exception:
            doc.homes = [h for h in doc.homes if h.id != home.id]
            save_homes(doc)
            home_dir = _home_dir(home.id)
            if home_dir.exists():
                shutil.rmtree(home_dir)
            raise

    return home
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_homes.py -v`
Expected: PASS (all tests in the file, including the 2 new ones)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/persistence_homes.py packages/backend/tests/test_homes.py
git commit -m "feat(locations): seed default comparison criteria when a Project home is created"
```

---

### Task 4: Backend MCP tools

**Files:**
- Create: `packages/backend/src/myhome/mcp_tools_locations.py`
- Modify: `packages/backend/src/myhome/mcp_app.py` (add to the registration import tuple)
- Test: `packages/backend/tests/test_mcp_tools_locations.py`

**Interfaces:**
- Consumes: `load_locations`, `save_locations` from `persistence_locations.py` (Task 1); `Location`, `LocationCriterion`, `LocationRating` from `models_locations.py` (Task 1); `_require_role`, `_resolve_home_id`, `mcp` from `mcp_server.py` (existing, same pattern as `mcp_tools_consumables.py`).
- Produces: MCP tools `list_locations`, `create_location_criterion`, `update_location_criterion`, `delete_location_criterion`, `create_location`, `update_location`, `delete_location`, `set_location_rating`.

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_mcp_tools_locations.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "project").id


def test_list_locations_returns_seeded_defaults(home_id):
    from myhome.mcp_tools_locations import _list_locations_impl
    doc = _list_locations_impl(home_id)
    assert len(doc["criteria"]) == 11
    assert doc["locations"] == []


def test_create_and_list_location(home_id):
    from myhome.mcp_tools_locations import _create_location_impl, _list_locations_impl
    item = _create_location_impl(home_id, "Ljubljana", emoji="🇸🇮")
    doc = _list_locations_impl(home_id)
    assert doc["locations"][0]["id"] == item["id"]
    assert doc["locations"][0]["emoji"] == "🇸🇮"


def test_update_location(home_id):
    from myhome.mcp_tools_locations import _create_location_impl, _update_location_impl
    item = _create_location_impl(home_id, "Ljubljana")
    updated = _update_location_impl(home_id, item["id"], name="Ljubljana Region")
    assert updated["name"] == "Ljubljana Region"


def test_delete_location(home_id):
    from myhome.mcp_tools_locations import _create_location_impl, _delete_location_impl, _list_locations_impl
    item = _create_location_impl(home_id, "Old Place")
    _delete_location_impl(home_id, item["id"])
    assert _list_locations_impl(home_id)["locations"] == []


def test_delete_location_unknown_id_raises(home_id):
    from myhome.mcp_tools_locations import _delete_location_impl
    with pytest.raises(ValueError):
        _delete_location_impl(home_id, "nonexistent")


def test_create_update_delete_criterion(home_id):
    from myhome.mcp_tools_locations import (
        _create_location_criterion_impl, _update_location_criterion_impl,
        _delete_location_criterion_impl, _list_locations_impl,
    )
    item = _create_location_criterion_impl(home_id, "Internet Speed", weight="high")
    assert item["weight"] == "high"
    updated = _update_location_criterion_impl(home_id, item["id"], weight="low")
    assert updated["weight"] == "low"
    _delete_location_criterion_impl(home_id, item["id"])
    doc = _list_locations_impl(home_id)
    assert all(c["id"] != item["id"] for c in doc["criteria"])


def test_set_location_rating_and_clear(home_id):
    from myhome.mcp_tools_locations import _create_location_impl, _list_locations_impl, _set_location_rating_impl
    location = _create_location_impl(home_id, "Zagreb")
    doc = _list_locations_impl(home_id)
    criterion_id = doc["criteria"][0]["id"]
    rating = _set_location_rating_impl(home_id, location["id"], criterion_id, score=4, note="Nice city")
    assert rating["score"] == 4
    cleared = _set_location_rating_impl(home_id, location["id"], criterion_id, score=None, note="")
    assert cleared["score"] is None


def test_set_location_rating_unknown_location_raises(home_id):
    from myhome.mcp_tools_locations import _list_locations_impl, _set_location_rating_impl
    doc = _list_locations_impl(home_id)
    criterion_id = doc["criteria"][0]["id"]
    with pytest.raises(ValueError):
        _set_location_rating_impl(home_id, "nonexistent", criterion_id, score=3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_mcp_tools_locations.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.mcp_tools_locations'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/backend/src/myhome/mcp_tools_locations.py`:

```python
from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_locations import Location, LocationCriterion, LocationRating
from .persistence_locations import load_locations, save_locations


def _list_locations_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_locations(resolved).model_dump()


def _create_location_criterion_impl(
    home_id: str | None, name: str, description: str = "", weight: str = "medium",
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_locations(resolved)
    item = LocationCriterion(id=str(uuid.uuid4()), name=name, description=description, weight=weight)
    doc.criteria.append(item)
    save_locations(resolved, doc)
    return item.model_dump()


def _update_location_criterion_impl(home_id: str | None, criterion_id: str, **fields) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_locations(resolved)
    item = next((c for c in doc.criteria if c.id == criterion_id), None)
    if item is None:
        raise ValueError(f"Unknown criterion_id {criterion_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(item, field, value)
    save_locations(resolved, doc)
    return item.model_dump()


def _delete_location_criterion_impl(home_id: str | None, criterion_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_locations(resolved)
    before = len(doc.criteria)
    doc.criteria = [c for c in doc.criteria if c.id != criterion_id]
    if len(doc.criteria) == before:
        raise ValueError(f"Unknown criterion_id {criterion_id!r}")
    doc.ratings = [r for r in doc.ratings if r.criterionId != criterion_id]
    save_locations(resolved, doc)
    return {"deleted": criterion_id}


def _create_location_impl(home_id: str | None, name: str, emoji: str = "📍") -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_locations(resolved)
    item = Location(id=str(uuid.uuid4()), name=name, emoji=emoji)
    doc.locations.append(item)
    save_locations(resolved, doc)
    return item.model_dump()


def _update_location_impl(home_id: str | None, location_id: str, **fields) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_locations(resolved)
    item = next((l for l in doc.locations if l.id == location_id), None)
    if item is None:
        raise ValueError(f"Unknown location_id {location_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(item, field, value)
    save_locations(resolved, doc)
    return item.model_dump()


def _delete_location_impl(home_id: str | None, location_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_locations(resolved)
    before = len(doc.locations)
    doc.locations = [l for l in doc.locations if l.id != location_id]
    if len(doc.locations) == before:
        raise ValueError(f"Unknown location_id {location_id!r}")
    doc.ratings = [r for r in doc.ratings if r.locationId != location_id]
    save_locations(resolved, doc)
    return {"deleted": location_id}


def _set_location_rating_impl(
    home_id: str | None, location_id: str, criterion_id: str, score: int | None = None, note: str = "",
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_locations(resolved)
    if not any(l.id == location_id for l in doc.locations):
        raise ValueError(f"Unknown location_id {location_id!r}")
    if not any(c.id == criterion_id for c in doc.criteria):
        raise ValueError(f"Unknown criterion_id {criterion_id!r}")
    doc.ratings = [r for r in doc.ratings if not (r.locationId == location_id and r.criterionId == criterion_id)]
    rating = LocationRating(locationId=location_id, criterionId=criterion_id, score=score, note=note)
    doc.ratings.append(rating)
    save_locations(resolved, doc)
    return rating.model_dump()


@mcp.tool()
async def list_locations(ctx: Context, home_id: str | None = None) -> dict:
    """List candidate locations, comparison criteria, and ratings for a Project home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_locations_impl(home_id)


@mcp.tool()
async def create_location_criterion(
    ctx: Context, name: str, home_id: str | None = None, description: str = "", weight: str = "medium",
) -> dict:
    """Add a comparison criterion (e.g. "Healthcare", "Cost of Living"). weight is
    one of "low", "medium", "high" and controls how much it counts toward the
    overall weighted score."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_location_criterion_impl(home_id, name, description, weight)


@mcp.tool()
async def update_location_criterion(
    ctx: Context, criterion_id: str, home_id: str | None = None,
    name: str | None = None, description: str | None = None, weight: str | None = None,
) -> dict:
    """Update a comparison criterion's name, description, or weight."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_location_criterion_impl(home_id, criterion_id, name=name, description=description, weight=weight)


@mcp.tool()
async def delete_location_criterion(ctx: Context, criterion_id: str, home_id: str | None = None) -> dict:
    """Delete a comparison criterion and its ratings across all locations."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_location_criterion_impl(home_id, criterion_id)


@mcp.tool()
async def create_location(ctx: Context, name: str, home_id: str | None = None, emoji: str = "📍") -> dict:
    """Add a candidate location (country, city, region) to compare."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_location_impl(home_id, name, emoji)


@mcp.tool()
async def update_location(
    ctx: Context, location_id: str, home_id: str | None = None, name: str | None = None, emoji: str | None = None,
) -> dict:
    """Update a candidate location's name or emoji."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_location_impl(home_id, location_id, name=name, emoji=emoji)


@mcp.tool()
async def delete_location(ctx: Context, location_id: str, home_id: str | None = None) -> dict:
    """Delete a candidate location and its ratings across all criteria."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_location_impl(home_id, location_id)


@mcp.tool()
async def set_location_rating(
    ctx: Context, location_id: str, criterion_id: str, home_id: str | None = None,
    score: int | None = None, note: str = "",
) -> dict:
    """Rate a location against a criterion. score is 1-5 (best), or omit/null to
    clear the score while keeping the note."""
    await _require_role(ctx.request_context.request, "normal")
    return _set_location_rating_impl(home_id, location_id, criterion_id, score, note)
```

Modify `packages/backend/src/myhome/mcp_app.py` — add `mcp_tools_locations` to the import tuple (keep alphabetical):

```python
from . import (  # noqa: F401 - imported for the side effect of registering tools
    mcp_tools_chores,
    mcp_tools_consumables,
    mcp_tools_costs,
    mcp_tools_homes,
    mcp_tools_inventory,
    mcp_tools_kb,
    mcp_tools_locations,
    mcp_tools_settings,
    mcp_tools_works,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_mcp_tools_locations.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_locations.py packages/backend/src/myhome/mcp_app.py packages/backend/tests/test_mcp_tools_locations.py
git commit -m "feat(locations): add MCP tools for criteria, locations, and ratings"
```

---

### Task 5: Frontend store

**Files:**
- Create: `packages/editor/src/lib/locationsStore.svelte.ts`
- Test: `packages/editor/test/locationsStore.test.ts`

**Interfaces:**
- Produces: types `LocationCriterion`, `Location`, `LocationRating`, `LocationsDocument`; constant `WEIGHT_MULTIPLIER: Record<"low"|"medium"|"high", number>`; pure functions `ratingFor(ratings, locationId, criterionId)`, `weightedScore(criteria, ratings, locationId)`, `bestScoreForCriterion(locations, ratings, criterionId)`; factory `createLocationsStore(getHomeId)` returning `{ criteria, locations, ratings, loaded, loadError, createCriterion, updateCriterion, deleteCriterion, reorderCriteria, createLocation, updateLocation, deleteLocation, reorderLocations, setRating, clearRating, reload }`. Consumed by Tasks 6–10.

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/locationsStore.test.ts`:

```typescript
import { describe, it, expect, afterEach, vi } from "vitest";
import {
  createLocationsStore, ratingFor, weightedScore, bestScoreForCriterion, WEIGHT_MULTIPLIER,
} from "../src/lib/locationsStore.svelte";

const HOME = "home-123";
const getHomeId = () => HOME;

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

const emptyDoc = { version: 1, criteria: [], locations: [], ratings: [] };

const sampleDoc = {
  version: 1,
  criteria: [
    { id: "c1", name: "Cost of Living", description: "", weight: "high" },
    { id: "c2", name: "Safety", description: "", weight: "medium" },
  ],
  locations: [
    { id: "l1", name: "Nantes", emoji: "🇫🇷" },
    { id: "l2", name: "Ljubljana", emoji: "🇸🇮" },
  ],
  ratings: [
    { locationId: "l1", criterionId: "c1", score: 2, note: "pricier" },
    { locationId: "l1", criterionId: "c2", score: 4, note: "" },
    { locationId: "l2", criterionId: "c1", score: 5, note: "cheap" },
  ],
};

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

describe("locationsStore — init", () => {
  it("loads criteria, locations, and ratings from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createLocationsStore(getHomeId);
    await tick();
    expect(store.criteria.length).toBe(2);
    expect(store.locations.length).toBe(2);
    expect(store.ratings.length).toBe(3);
    expect(store.loaded).toBe(true);
  });

  it("marks loaded on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network")));
    const store = createLocationsStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("Network");
  });

  it("does not fetch when no homeId provided", async () => {
    const fetchFn = vi.fn();
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(() => null);
    await tick();
    expect(fetchFn).not.toHaveBeenCalled();
    expect(store.loaded).toBe(true);
  });
});

describe("locationsStore — criteria CRUD", () => {
  it("createCriterion POSTs to /criteria and reloads", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({}) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(getHomeId);
    await tick();
    await store.createCriterion({ name: "Healthcare", description: "", weight: "high" });
    expect(fetchFn).toHaveBeenCalledWith(
      `/api/homes/${HOME}/locations/criteria`,
      expect.objectContaining({ method: "POST" }),
    );
    expect(store.criteria.length).toBe(2);
  });

  it("deleteCriterion DELETEs /criteria/{id}", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => undefined })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(getHomeId);
    await tick();
    await store.deleteCriterion("c1");
    expect(fetchFn).toHaveBeenCalledWith(
      `/api/homes/${HOME}/locations/criteria/c1`,
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("reorderCriteria PUTs ordered ids to /criteria/reorder", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => undefined })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(getHomeId);
    await tick();
    await store.reorderCriteria(["c2", "c1"]);
    expect(fetchFn).toHaveBeenCalledWith(
      `/api/homes/${HOME}/locations/criteria/reorder`,
      expect.objectContaining({ method: "PUT", body: JSON.stringify({ orderedIds: ["c2", "c1"] }) }),
    );
  });
});

describe("locationsStore — locations CRUD", () => {
  it("createLocation POSTs to /locations/locations", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({}) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(getHomeId);
    await tick();
    await store.createLocation({ name: "Zagreb", emoji: "🇭🇷" });
    expect(fetchFn).toHaveBeenCalledWith(
      `/api/homes/${HOME}/locations/locations`,
      expect.objectContaining({ method: "POST" }),
    );
  });
});

describe("locationsStore — ratings", () => {
  it("setRating PUTs score+note to /ratings/{locationId}/{criterionId}", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => undefined })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(getHomeId);
    await tick();
    await store.setRating("l1", "c1", 3, "revised");
    expect(fetchFn).toHaveBeenCalledWith(
      `/api/homes/${HOME}/locations/ratings/l1/c1`,
      expect.objectContaining({ method: "PUT", body: JSON.stringify({ score: 3, note: "revised" }) }),
    );
  });

  it("clearRating DELETEs /ratings/{locationId}/{criterionId}", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => undefined })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(getHomeId);
    await tick();
    await store.clearRating("l1", "c1");
    expect(fetchFn).toHaveBeenCalledWith(
      `/api/homes/${HOME}/locations/ratings/l1/c1`,
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});

describe("locationsStore — pure helpers", () => {
  it("ratingFor finds the matching rating", () => {
    const r = ratingFor(sampleDoc.ratings as any, "l1", "c1");
    expect(r?.score).toBe(2);
  });

  it("ratingFor returns null when no match", () => {
    expect(ratingFor(sampleDoc.ratings as any, "l2", "c2")).toBeNull();
  });

  it("weightedScore averages rated criteria by weight, ignoring unrated ones", () => {
    // l1: c1 score=2 weight=high(3), c2 score=4 weight=medium(2) => (2*3+4*2)/(3+2) = 2.8
    const score = weightedScore(sampleDoc.criteria as any, sampleDoc.ratings as any, "l1");
    expect(score).toBeCloseTo(2.8);
  });

  it("weightedScore returns null when the location has no ratings", () => {
    const score = weightedScore(sampleDoc.criteria as any, [], "l1");
    expect(score).toBeNull();
  });

  it("bestScoreForCriterion returns the highest rated score for a criterion", () => {
    const best = bestScoreForCriterion(sampleDoc.locations as any, sampleDoc.ratings as any, "c1");
    expect(best).toBe(5);
  });

  it("bestScoreForCriterion returns null when no location has been rated", () => {
    expect(bestScoreForCriterion(sampleDoc.locations as any, [], "c1")).toBeNull();
  });

  it("WEIGHT_MULTIPLIER maps low/medium/high to 1/2/3", () => {
    expect(WEIGHT_MULTIPLIER).toEqual({ low: 1, medium: 2, high: 3 });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/locationsStore.test.ts`
Expected: FAIL with `Cannot find module '../src/lib/locationsStore.svelte'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/editor/src/lib/locationsStore.svelte.ts`:

```typescript
export type Weight = "low" | "medium" | "high";

export interface LocationCriterion {
  id: string;
  name: string;
  description: string;
  weight: Weight;
}

export interface Location {
  id: string;
  name: string;
  emoji: string;
}

export interface LocationRating {
  locationId: string;
  criterionId: string;
  score: number | null;
  note: string;
}

export interface LocationsDocument {
  version: number;
  criteria: LocationCriterion[];
  locations: Location[];
  ratings: LocationRating[];
}

export const WEIGHT_MULTIPLIER: Record<Weight, number> = { low: 1, medium: 2, high: 3 };

export function ratingFor(
  ratings: LocationRating[],
  locationId: string,
  criterionId: string,
): LocationRating | null {
  return ratings.find((r) => r.locationId === locationId && r.criterionId === criterionId) ?? null;
}

export function weightedScore(
  criteria: LocationCriterion[],
  ratings: LocationRating[],
  locationId: string,
): number | null {
  let sum = 0;
  let weightTotal = 0;
  for (const c of criteria) {
    const r = ratingFor(ratings, locationId, c.id);
    if (r?.score == null) continue;
    const w = WEIGHT_MULTIPLIER[c.weight];
    sum += r.score * w;
    weightTotal += w;
  }
  return weightTotal === 0 ? null : sum / weightTotal;
}

export function bestScoreForCriterion(
  locations: Location[],
  ratings: LocationRating[],
  criterionId: string,
): number | null {
  let best: number | null = null;
  for (const loc of locations) {
    const r = ratingFor(ratings, loc.id, criterionId);
    if (r?.score == null) continue;
    if (best === null || r.score > best) best = r.score;
  }
  return best;
}

export function createLocationsStore(getHomeId: () => string | null = () => null) {
  const criteria = $state<LocationCriterion[]>([]);
  const locations = $state<Location[]>([]);
  const ratings = $state<LocationRating[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/locations`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: LocationsDocument = await resp.json();
      criteria.length = 0;
      for (const c of doc.criteria) criteria.push(c);
      locations.length = 0;
      for (const l of doc.locations) locations.push(l);
      ratings.length = 0;
      for (const r of doc.ratings) ratings.push(r);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createCriterion(data: Omit<LocationCriterion, "id">): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/criteria`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateCriterion(id: string, patch: Partial<Omit<LocationCriterion, "id">>): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/criteria/${id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteCriterion(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/criteria/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function reorderCriteria(orderedIds: string[]): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/criteria/reorder`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ orderedIds }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function createLocation(data: Omit<Location, "id">): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/locations`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateLocation(id: string, patch: Partial<Omit<Location, "id">>): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/locations/${id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteLocation(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/locations/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function reorderLocations(orderedIds: string[]): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/locations/reorder`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ orderedIds }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function setRating(locationId: string, criterionId: string, score: number | null, note: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/ratings/${locationId}/${criterionId}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ score, note }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function clearRating(locationId: string, criterionId: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/ratings/${locationId}/${criterionId}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  init();

  return {
    get criteria() { return criteria as LocationCriterion[]; },
    get locations() { return locations as Location[]; },
    get ratings() { return ratings as LocationRating[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createCriterion,
    updateCriterion,
    deleteCriterion,
    reorderCriteria,
    createLocation,
    updateLocation,
    deleteLocation,
    reorderLocations,
    setRating,
    clearRating,
    reload: init,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/locationsStore.test.ts`
Expected: PASS (14 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/locationsStore.svelte.ts packages/editor/test/locationsStore.test.ts
git commit -m "feat(locations): add frontend store with weighted-score and best-cell helpers"
```

---

### Task 6: `LocationRankingChart.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/LocationRankingChart.svelte`
- Test: `packages/editor/test/LocationRankingChart.test.ts`

**Interfaces:**
- Consumes: `Location`, `LocationCriterion`, `LocationRating`, `weightedScore` from `locationsStore.svelte.ts` (Task 5).
- Produces: `<LocationRankingChart locations criteria ratings />` — renders `.row` elements in descending weighted-score order, with `.crown` on the top (tied) score(s). Consumed by Task 9.

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/LocationRankingChart.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import LocationRankingChart from "../src/lib/components/LocationRankingChart.svelte";

const criteria = [{ id: "c1", name: "Cost", description: "", weight: "high" as const }];

function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

describe("LocationRankingChart", () => {
  it("sorts locations by weighted score descending and crowns the top one", () => {
    const el = target();
    const comp = mount(LocationRankingChart, {
      target: el,
      props: {
        locations: [
          { id: "l1", name: "Nantes", emoji: "🇫🇷" },
          { id: "l2", name: "Ljubljana", emoji: "🇸🇮" },
        ],
        criteria,
        ratings: [
          { locationId: "l1", criterionId: "c1", score: 2, note: "" },
          { locationId: "l2", criterionId: "c1", score: 5, note: "" },
        ],
      },
    });
    flushSync();
    const rows = Array.from(el.querySelectorAll(".row"));
    expect(rows[0].querySelector(".name")?.textContent).toBe("Ljubljana");
    expect(rows[0].querySelector(".crown")).not.toBeNull();
    expect(rows[1].querySelector(".crown")).toBeNull();
    unmount(comp);
    el.remove();
  });

  it("shows unrated locations last with a dash", () => {
    const el = target();
    const comp = mount(LocationRankingChart, {
      target: el,
      props: {
        locations: [
          { id: "l1", name: "Rated", emoji: "📍" },
          { id: "l2", name: "Unrated", emoji: "📍" },
        ],
        criteria,
        ratings: [{ locationId: "l1", criterionId: "c1", score: 3, note: "" }],
      },
    });
    flushSync();
    const rows = Array.from(el.querySelectorAll(".row"));
    expect(rows[1].querySelector(".name")?.textContent).toBe("Unrated");
    expect(rows[1].querySelector(".score")?.textContent).toBe("—");
    unmount(comp);
    el.remove();
  });

  it("crowns tied top locations", () => {
    const el = target();
    const comp = mount(LocationRankingChart, {
      target: el,
      props: {
        locations: [
          { id: "l1", name: "A", emoji: "📍" },
          { id: "l2", name: "B", emoji: "📍" },
        ],
        criteria,
        ratings: [
          { locationId: "l1", criterionId: "c1", score: 4, note: "" },
          { locationId: "l2", criterionId: "c1", score: 4, note: "" },
        ],
      },
    });
    flushSync();
    expect(el.querySelectorAll(".crown").length).toBe(2);
    unmount(comp);
    el.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/LocationRankingChart.test.ts`
Expected: FAIL with `Cannot find module '../src/lib/components/LocationRankingChart.svelte'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/editor/src/lib/components/LocationRankingChart.svelte`:

```svelte
<script lang="ts">
  import type { Location, LocationCriterion, LocationRating } from "../locationsStore.svelte";
  import { weightedScore } from "../locationsStore.svelte";

  interface Props {
    locations: Location[];
    criteria: LocationCriterion[];
    ratings: LocationRating[];
  }
  let { locations, criteria, ratings }: Props = $props();

  const ranked = $derived(
    locations
      .map((loc) => ({ loc, score: weightedScore(criteria, ratings, loc.id) }))
      .sort((a, b) => {
        if (a.score === null && b.score === null) return 0;
        if (a.score === null) return 1;
        if (b.score === null) return -1;
        return b.score - a.score;
      }),
  );

  const topScore = $derived(ranked.find((r) => r.score !== null)?.score ?? null);

  function isWinner(score: number | null): boolean {
    return score !== null && topScore !== null && score === topScore;
  }
</script>

<div class="ranking">
  {#each ranked as { loc, score } (loc.id)}
    <div class="row">
      <div class="label">
        {#if isWinner(score)}<span class="crown">👑</span>{/if}
        <span class="emoji">{loc.emoji}</span>
        <span class="name">{loc.name}</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill" style="width:{score !== null ? (score / 5) * 100 : 0}%"></div>
      </div>
      <div class="score">{score !== null ? score.toFixed(1) : "—"}</div>
    </div>
  {/each}
</div>

<style>
  .ranking { display: flex; flex-direction: column; gap: 8px; }
  .row { display: flex; align-items: center; gap: 10px; }
  .label { display: flex; align-items: center; gap: 4px; width: 160px; flex-shrink: 0; font-size: 12px; color: var(--text); }
  .crown { font-size: 12px; }
  .emoji { font-size: 14px; }
  .name { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bar-track { flex: 1; height: 10px; background: var(--surface-alt); border-radius: 5px; overflow: hidden; }
  .bar-fill { height: 100%; background: var(--accent); border-radius: 5px; transition: width 0.2s; }
  .score { width: 32px; text-align: right; font-size: 12px; font-weight: 600; color: var(--text-muted); flex-shrink: 0; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/LocationRankingChart.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/LocationRankingChart.svelte packages/editor/test/LocationRankingChart.test.ts
git commit -m "feat(locations): add ranking chart component"
```

---

### Task 7: `LocationRatingPopup.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/LocationRatingPopup.svelte`
- Test: `packages/editor/test/LocationRatingPopup.test.ts`

**Interfaces:**
- Consumes: `Location`, `LocationCriterion`, `LocationRating` types from `locationsStore.svelte.ts` (Task 5).
- Produces: `<LocationRatingPopup location criterion rating anchorX anchorY onsave onclose />` where `onsave: (score: number | null, note: string) => void`. Consumed by Task 8. Portals its DOM to `document.body`, same pattern as `EmojiPicker.svelte`.

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/LocationRatingPopup.test.ts`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import LocationRatingPopup from "../src/lib/components/LocationRatingPopup.svelte";

const location = { id: "l1", name: "Nantes", emoji: "🇫🇷" };
const criterion = { id: "c1", name: "Cost of Living", description: "", weight: "medium" as const };

function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

describe("LocationRatingPopup", () => {
  it("pre-fills score and note from the existing rating", () => {
    const el = target();
    const comp = mount(LocationRatingPopup, {
      target: el,
      props: {
        location, criterion,
        rating: { locationId: "l1", criterionId: "c1", score: 3, note: "decent" },
        anchorX: 10, anchorY: 10,
        onsave: vi.fn(), onclose: vi.fn(),
      },
    });
    flushSync();
    expect(document.querySelector(".score-btn.selected")?.textContent).toBe("3");
    expect((document.querySelector(".note-textarea") as HTMLTextAreaElement).value).toBe("decent");
    unmount(comp);
    el.remove();
  });

  it("selecting a score and saving calls onsave with the score and note", () => {
    const el = target();
    const onsave = vi.fn();
    const comp = mount(LocationRatingPopup, {
      target: el,
      props: { location, criterion, rating: null, anchorX: 0, anchorY: 0, onsave, onclose: vi.fn() },
    });
    flushSync();
    const buttons = Array.from(document.querySelectorAll(".score-btn"));
    (buttons[3] as HTMLButtonElement).click(); // score 4
    const textarea = document.querySelector(".note-textarea") as HTMLTextAreaElement;
    textarea.value = "Great fit";
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    (document.querySelector(".save-btn") as HTMLButtonElement).click();
    expect(onsave).toHaveBeenCalledWith(4, "Great fit");
    unmount(comp);
    el.remove();
  });

  it("clear calls onsave with null score and empty note", () => {
    const el = target();
    const onsave = vi.fn();
    const comp = mount(LocationRatingPopup, {
      target: el,
      props: {
        location, criterion,
        rating: { locationId: "l1", criterionId: "c1", score: 5, note: "x" },
        anchorX: 0, anchorY: 0, onsave, onclose: vi.fn(),
      },
    });
    flushSync();
    (document.querySelector(".clear-btn") as HTMLButtonElement).click();
    expect(onsave).toHaveBeenCalledWith(null, "");
    unmount(comp);
    el.remove();
  });

  it("Escape key closes the popup", () => {
    const el = target();
    const onclose = vi.fn();
    const comp = mount(LocationRatingPopup, {
      target: el,
      props: { location, criterion, rating: null, anchorX: 0, anchorY: 0, onsave: vi.fn(), onclose },
    });
    flushSync();
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(onclose).toHaveBeenCalled();
    unmount(comp);
    el.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/LocationRatingPopup.test.ts`
Expected: FAIL with `Cannot find module '../src/lib/components/LocationRatingPopup.svelte'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/editor/src/lib/components/LocationRatingPopup.svelte`:

```svelte
<script lang="ts">
  import type { Location, LocationCriterion, LocationRating } from "../locationsStore.svelte";

  interface Props {
    location: Location;
    criterion: LocationCriterion;
    rating: LocationRating | null;
    anchorX: number;
    anchorY: number;
    onsave: (score: number | null, note: string) => void;
    onclose: () => void;
  }
  let { location, criterion, rating, anchorX, anchorY, onsave, onclose }: Props = $props();

  let score = $state<number | null>(rating?.score ?? null);
  let note = $state(rating?.note ?? "");

  function portal(node: HTMLElement): { destroy(): void } {
    document.body.appendChild(node);
    return {
      destroy() {
        if (document.body.contains(node)) document.body.removeChild(node);
      },
    };
  }

  function selectScore(v: number): void {
    score = score === v ? null : v;
  }

  function handleSave(): void {
    onsave(score, note);
  }

  function handleClear(): void {
    onsave(null, "");
  }

  function handleWindowKeydown(e: KeyboardEvent): void {
    if (e.key === "Escape") onclose();
  }
</script>

<svelte:window onkeydown={handleWindowKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="popup-backdrop" role="presentation" onclick={onclose} use:portal></div>
<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="popup" style="left:{anchorX}px;top:{anchorY}px" onclick={(e) => e.stopPropagation()} use:portal>
  <div class="popup-title">{location.emoji} {location.name} — {criterion.name}</div>
  <div class="score-picker">
    {#each [1, 2, 3, 4, 5] as v}
      <button type="button" class="score-btn" class:selected={score === v} onclick={() => selectScore(v)}>{v}</button>
    {/each}
  </div>
  <textarea class="note-textarea" placeholder="Note…" bind:value={note}></textarea>
  <div class="popup-actions">
    <button type="button" class="save-btn" onclick={handleSave}>Save</button>
    <button type="button" class="clear-btn" onclick={handleClear}>Clear</button>
    <button type="button" class="close-btn" onclick={onclose}>Close</button>
  </div>
</div>

<style>
  .popup-backdrop { position: fixed; inset: 0; z-index: 998; background: transparent; }
  .popup {
    position: fixed; z-index: 999;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); box-shadow: var(--shadow-md);
    padding: 12px; width: 240px;
  }
  .popup-title { font-size: 12px; font-weight: 600; color: var(--text); margin-bottom: 8px; }
  .score-picker { display: flex; gap: 4px; margin-bottom: 8px; }
  .score-btn {
    flex: 1; padding: 6px 0; border: 1px solid var(--border); background: var(--surface-alt);
    color: var(--text-muted); border-radius: var(--radius-sm); cursor: pointer; font-size: 12px; font-weight: 600;
  }
  .score-btn.selected { background: var(--accent); color: var(--accent-contrast); border-color: var(--accent); }
  .note-textarea {
    width: 100%; min-height: 50px; background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); color: var(--text); padding: 6px 8px; font-size: 12px;
    font-family: var(--font-sans); box-sizing: border-box; resize: vertical; margin-bottom: 8px;
  }
  .popup-actions { display: flex; gap: 6px; }
  .save-btn {
    flex: 1; background: var(--accent); color: var(--accent-contrast); border: none;
    border-radius: var(--radius-sm); padding: 6px 0; cursor: pointer; font-size: 12px; font-weight: 600;
  }
  .clear-btn, .close-btn {
    background: var(--surface-alt); color: var(--text-muted); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 6px 10px; cursor: pointer; font-size: 12px;
  }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/LocationRatingPopup.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/LocationRatingPopup.svelte packages/editor/test/LocationRatingPopup.test.ts
git commit -m "feat(locations): add rating cell popup component"
```

---

### Task 8: `LocationsMatrix.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/LocationsMatrix.svelte`
- Test: `packages/editor/test/LocationsMatrix.test.ts`

**Interfaces:**
- Consumes: `createLocationsStore` return type, `ratingFor`, `bestScoreForCriterion` from `locationsStore.svelte.ts` (Task 5); `LocationRatingPopup` (Task 7); `EmojiPicker` from `ui/EmojiPicker.svelte` (existing).
- Produces: `<LocationsMatrix store />` — renders the criteria × locations comparison table with inline add/edit/delete/reorder for both axes and cell rating via popup. Consumed by Task 9.

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/LocationsMatrix.test.ts`:

```typescript
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import LocationsMatrix from "../src/lib/components/LocationsMatrix.svelte";
import { createLocationsStore } from "../src/lib/locationsStore.svelte";

const HOME = "home-123";
const getHomeId = () => HOME;

const sampleDoc = {
  version: 1,
  criteria: [
    { id: "c1", name: "Cost of Living", description: "Land, construction, everyday costs", weight: "high" },
    { id: "c2", name: "Safety", description: "", weight: "medium" },
  ],
  locations: [
    { id: "l1", name: "Nantes", emoji: "🇫🇷" },
    { id: "l2", name: "Ljubljana", emoji: "🇸🇮" },
  ],
  ratings: [
    { locationId: "l1", criterionId: "c1", score: 2, note: "pricier" },
    { locationId: "l2", criterionId: "c1", score: 5, note: "cheap" },
  ],
};

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({ ok: status >= 200 && status < 300, status, json: async () => body });
}

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

afterEach(() => vi.unstubAllGlobals());

describe("LocationsMatrix", () => {
  it("renders one column per location and one row per criterion", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsMatrix, { target: el, props: { store } });
    flushSync();
    expect(el.querySelectorAll(".location-header").length).toBe(2);
    expect(el.querySelectorAll("tbody tr").length).toBe(3); // 2 criteria + add-criterion row
    unmount(comp);
    el.remove();
  });

  it("highlights the best-rated cell in each criterion row", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsMatrix, { target: el, props: { store } });
    flushSync();
    const costRow = Array.from(el.querySelectorAll("tbody tr"))[0];
    const bestCells = costRow.querySelectorAll("td.rating-cell.best");
    expect(bestCells.length).toBe(1);
    expect(bestCells[0].textContent).toContain("5");
    unmount(comp);
    el.remove();
  });

  it("clicking a cell opens the rating popup", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsMatrix, { target: el, props: { store } });
    flushSync();
    const safetyRow = Array.from(el.querySelectorAll("tbody tr"))[1];
    const cell = safetyRow.querySelector("td.rating-cell") as HTMLElement;
    cell.click();
    flushSync();
    expect(document.querySelector(".popup-title")).not.toBeNull();
    unmount(comp);
    el.remove();
  });

  it("adding a location POSTs to the locations endpoint", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({}) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsMatrix, { target: el, props: { store } });
    flushSync();
    const input = el.querySelector(".add-header input") as HTMLInputElement;
    input.value = "Zagreb";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    (el.querySelector(".add-header .add-btn") as HTMLButtonElement).click();
    await tick();
    expect(fetchFn).toHaveBeenCalledWith(
      `/api/homes/${HOME}/locations/locations`,
      expect.objectContaining({ method: "POST" }),
    );
    unmount(comp);
    el.remove();
  });

  it("deleting a criterion requires a confirm click", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsMatrix, { target: el, props: { store } });
    flushSync();
    const costRow = Array.from(el.querySelectorAll("tbody tr"))[0];
    const deleteBtn = costRow.querySelector(".criterion-cell button[title='Delete']") as HTMLButtonElement;
    deleteBtn.click();
    flushSync();
    expect(costRow.querySelector(".confirm-text")).not.toBeNull();
    unmount(comp);
    el.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/LocationsMatrix.test.ts`
Expected: FAIL with `Cannot find module '../src/lib/components/LocationsMatrix.svelte'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/editor/src/lib/components/LocationsMatrix.svelte`:

```svelte
<script lang="ts">
  import type { createLocationsStore, Location, LocationCriterion, Weight } from "../locationsStore.svelte";
  import { ratingFor, bestScoreForCriterion } from "../locationsStore.svelte";
  import EmojiPicker from "./ui/EmojiPicker.svelte";
  import LocationRatingPopup from "./LocationRatingPopup.svelte";

  type LocationsStore = ReturnType<typeof createLocationsStore>;
  interface Props { store: LocationsStore; }
  let { store }: Props = $props();

  const SCORE_COLOR: Record<number, string> = {
    1: "var(--danger)", 2: "#ff9800", 3: "#ffc107", 4: "#8bc34a", 5: "var(--success)",
  };
  const WEIGHT_LABEL: Record<Weight, string> = { low: "Low", medium: "Med", high: "High" };

  let newCriterionName = $state("");
  let newLocationName = $state("");
  let newLocationEmoji = $state("📍");

  let editingCriterionId = $state<string | null>(null);
  let editCriterionName = $state("");
  let editCriterionDescription = $state("");
  let editCriterionWeight = $state<Weight>("medium");
  let confirmDeleteCriterionId = $state<string | null>(null);

  let editingLocationId = $state<string | null>(null);
  let editLocationName = $state("");
  let editLocationEmoji = $state("📍");
  let confirmDeleteLocationId = $state<string | null>(null);

  let openCell = $state<{ locationId: string; criterionId: string; anchorX: number; anchorY: number } | null>(null);

  function startEditCriterion(c: LocationCriterion): void {
    editingCriterionId = c.id;
    editCriterionName = c.name;
    editCriterionDescription = c.description;
    editCriterionWeight = c.weight;
  }

  async function saveCriterion(): Promise<void> {
    if (!editingCriterionId) return;
    await store.updateCriterion(editingCriterionId, {
      name: editCriterionName, description: editCriterionDescription, weight: editCriterionWeight,
    });
    editingCriterionId = null;
  }

  async function addCriterion(): Promise<void> {
    const name = newCriterionName.trim();
    if (!name) return;
    await store.createCriterion({ name, description: "", weight: "medium" });
    newCriterionName = "";
  }

  async function moveCriterion(id: string, dir: -1 | 1): Promise<void> {
    const ids = store.criteria.map((c) => c.id);
    const idx = ids.indexOf(id);
    const swapWith = idx + dir;
    if (swapWith < 0 || swapWith >= ids.length) return;
    [ids[idx], ids[swapWith]] = [ids[swapWith], ids[idx]];
    await store.reorderCriteria(ids);
  }

  function startEditLocation(l: Location): void {
    editingLocationId = l.id;
    editLocationName = l.name;
    editLocationEmoji = l.emoji;
  }

  async function saveLocation(): Promise<void> {
    if (!editingLocationId) return;
    await store.updateLocation(editingLocationId, { name: editLocationName, emoji: editLocationEmoji });
    editingLocationId = null;
  }

  async function addLocation(): Promise<void> {
    const name = newLocationName.trim();
    if (!name) return;
    await store.createLocation({ name, emoji: newLocationEmoji });
    newLocationName = "";
    newLocationEmoji = "📍";
  }

  async function moveLocation(id: string, dir: -1 | 1): Promise<void> {
    const ids = store.locations.map((l) => l.id);
    const idx = ids.indexOf(id);
    const swapWith = idx + dir;
    if (swapWith < 0 || swapWith >= ids.length) return;
    [ids[idx], ids[swapWith]] = [ids[swapWith], ids[idx]];
    await store.reorderLocations(ids);
  }

  function openRatingPopup(locationId: string, criterionId: string, e: MouseEvent): void {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    openCell = { locationId, criterionId, anchorX: rect.left, anchorY: rect.bottom };
  }

  async function handleSaveRating(score: number | null, note: string): Promise<void> {
    if (!openCell) return;
    if (score === null && note.trim() === "") {
      await store.clearRating(openCell.locationId, openCell.criterionId);
    } else {
      await store.setRating(openCell.locationId, openCell.criterionId, score, note);
    }
    openCell = null;
  }
</script>

<div class="matrix-wrapper">
  <table class="matrix">
    <thead>
      <tr>
        <th class="corner">Criteria</th>
        {#each store.locations as loc (loc.id)}
          <th class="location-header">
            {#if editingLocationId === loc.id}
              <div class="edit-form">
                <EmojiPicker bind:value={editLocationEmoji} />
                <input class="edit-input" bind:value={editLocationName} />
                <button class="icon-btn" onclick={saveLocation} title="Save">✓</button>
                <button class="icon-btn" onclick={() => { editingLocationId = null; }} title="Cancel">✕</button>
              </div>
            {:else if confirmDeleteLocationId === loc.id}
              <div class="header-content">
                <span class="confirm-text">Delete {loc.name}?</span>
                <div class="header-actions">
                  <button class="icon-btn" onclick={() => { store.deleteLocation(loc.id); confirmDeleteLocationId = null; }} title="Confirm delete">✓</button>
                  <button class="icon-btn" onclick={() => { confirmDeleteLocationId = null; }} title="Cancel">✕</button>
                </div>
              </div>
            {:else}
              <div class="header-content">
                <span class="loc-emoji">{loc.emoji}</span>
                <span class="loc-name">{loc.name}</span>
                <div class="header-actions">
                  <button class="icon-btn" onclick={() => moveLocation(loc.id, -1)} title="Move left">◀</button>
                  <button class="icon-btn" onclick={() => moveLocation(loc.id, 1)} title="Move right">▶</button>
                  <button class="icon-btn" onclick={() => startEditLocation(loc)} title="Edit">✏️</button>
                  <button class="icon-btn" onclick={() => { confirmDeleteLocationId = loc.id; }} title="Delete">🗑</button>
                </div>
              </div>
            {/if}
          </th>
        {/each}
        <th class="add-header">
          <div class="add-form">
            <EmojiPicker bind:value={newLocationEmoji} />
            <input
              class="edit-input"
              placeholder="New location…"
              bind:value={newLocationName}
              onkeydown={(e) => { if (e.key === "Enter") addLocation(); }}
            />
            <button class="add-btn" onclick={addLocation} title="Add location">＋</button>
          </div>
        </th>
      </tr>
    </thead>
    <tbody>
      {#each store.criteria as criterion (criterion.id)}
        {@const best = bestScoreForCriterion(store.locations, store.ratings, criterion.id)}
        <tr>
          <td class="criterion-cell">
            {#if editingCriterionId === criterion.id}
              <div class="edit-form-col">
                <input class="edit-input" bind:value={editCriterionName} />
                <textarea class="edit-textarea" bind:value={editCriterionDescription}></textarea>
                <select class="native-select" bind:value={editCriterionWeight}>
                  <option value="low">Low weight</option>
                  <option value="medium">Medium weight</option>
                  <option value="high">High weight</option>
                </select>
                <div class="row-actions">
                  <button class="icon-btn" onclick={saveCriterion} title="Save">✓</button>
                  <button class="icon-btn" onclick={() => { editingCriterionId = null; }} title="Cancel">✕</button>
                </div>
              </div>
            {:else if confirmDeleteCriterionId === criterion.id}
              <div class="criterion-content">
                <span class="confirm-text">Delete {criterion.name}?</span>
                <div class="row-actions">
                  <button class="icon-btn" onclick={() => { store.deleteCriterion(criterion.id); confirmDeleteCriterionId = null; }} title="Confirm delete">✓</button>
                  <button class="icon-btn" onclick={() => { confirmDeleteCriterionId = null; }} title="Cancel">✕</button>
                </div>
              </div>
            {:else}
              <div class="criterion-content">
                <div class="criterion-title-row">
                  <span class="criterion-name">{criterion.name}</span>
                  <span class="weight-tag weight-{criterion.weight}">{WEIGHT_LABEL[criterion.weight]}</span>
                </div>
                {#if criterion.description}<p class="criterion-desc">{criterion.description}</p>{/if}
                <div class="row-actions">
                  <button class="icon-btn" onclick={() => moveCriterion(criterion.id, -1)} title="Move up">▲</button>
                  <button class="icon-btn" onclick={() => moveCriterion(criterion.id, 1)} title="Move down">▼</button>
                  <button class="icon-btn" onclick={() => startEditCriterion(criterion)} title="Edit">✏️</button>
                  <button class="icon-btn" onclick={() => { confirmDeleteCriterionId = criterion.id; }} title="Delete">🗑</button>
                </div>
              </div>
            {/if}
          </td>
          {#each store.locations as loc (loc.id)}
            {@const rating = ratingFor(store.ratings, loc.id, criterion.id)}
            {@const isBest = rating?.score != null && best !== null && rating.score === best}
            <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
            <td
              class="rating-cell"
              class:best={isBest}
              role="button"
              tabindex="0"
              onclick={(e) => openRatingPopup(loc.id, criterion.id, e)}
            >
              {#if rating?.score != null}
                <span class="score-badge" style="background:{SCORE_COLOR[rating.score]}">{rating.score}</span>
                {#if rating.note}<span class="note-preview">{rating.note}</span>{/if}
              {:else}
                <span class="score-empty">—</span>
              {/if}
            </td>
          {/each}
        </tr>
      {/each}
      <tr>
        <td class="add-criterion-cell">
          <input
            class="edit-input"
            placeholder="New criterion…"
            bind:value={newCriterionName}
            onkeydown={(e) => { if (e.key === "Enter") addCriterion(); }}
          />
          <button class="add-btn" onclick={addCriterion} title="Add criterion">＋</button>
        </td>
        {#each store.locations as loc (loc.id)}
          <td class="add-criterion-filler"></td>
        {/each}
      </tr>
    </tbody>
  </table>
</div>

{#if openCell}
  {@const cellLocation = store.locations.find((l) => l.id === openCell!.locationId)}
  {@const cellCriterion = store.criteria.find((c) => c.id === openCell!.criterionId)}
  {#if cellLocation && cellCriterion}
    <LocationRatingPopup
      location={cellLocation}
      criterion={cellCriterion}
      rating={ratingFor(store.ratings, openCell.locationId, openCell.criterionId)}
      anchorX={openCell.anchorX}
      anchorY={openCell.anchorY}
      onsave={handleSaveRating}
      onclose={() => { openCell = null; }}
    />
  {/if}
{/if}

<style>
  .matrix-wrapper { overflow-x: auto; }
  .matrix { width: 100%; border-collapse: collapse; font-size: 12px; }
  .matrix th, .matrix td { border-bottom: 1px solid var(--border); padding: 8px 10px; vertical-align: top; text-align: left; }
  .corner { min-width: 220px; color: var(--text-faint); font-weight: 600; text-transform: uppercase; font-size: 10px; letter-spacing: 0.05em; }
  .location-header, .add-header { min-width: 160px; }
  .header-content { display: flex; flex-direction: column; gap: 4px; }
  .loc-emoji { font-size: 18px; }
  .loc-name { font-weight: 600; color: var(--text); }
  .header-actions, .row-actions { display: flex; gap: 4px; }
  .icon-btn { border: none; background: var(--surface-alt); color: var(--text-muted); border-radius: var(--radius-sm); padding: 2px 6px; cursor: pointer; font-size: 11px; }
  .icon-btn:hover { background: var(--surface-hover); color: var(--text); }
  .add-btn { border: none; background: var(--accent); color: var(--accent-contrast); border-radius: var(--radius-sm); padding: 4px 10px; cursor: pointer; font-size: 13px; flex-shrink: 0; }
  .edit-form, .add-form { display: flex; align-items: center; gap: 4px; }
  .edit-form-col { display: flex; flex-direction: column; gap: 4px; }
  .edit-input { flex: 1; background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text); padding: 4px 6px; font-size: 12px; font-family: var(--font-sans); box-sizing: border-box; }
  .edit-textarea { background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text); padding: 4px 6px; font-size: 12px; font-family: var(--font-sans); resize: vertical; min-height: 40px; }
  .native-select { background: var(--surface-alt); border: 1px solid var(--border); color: var(--text); border-radius: var(--radius-sm); padding: 4px 6px; font-size: 12px; font-family: var(--font-sans); }
  .confirm-text { font-size: 11px; color: var(--danger); }

  .criterion-cell { min-width: 240px; }
  .criterion-title-row { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
  .criterion-name { font-weight: 600; color: var(--text); }
  .criterion-desc { margin: 2px 0 6px; color: var(--text-muted); font-size: 11px; }
  .weight-tag { font-size: 9px; font-weight: 700; text-transform: uppercase; padding: 1px 6px; border-radius: var(--radius-pill); background: var(--surface-alt); color: var(--text-muted); }
  .weight-high { background: color-mix(in srgb, var(--danger) 15%, var(--surface)); color: var(--danger); }
  .weight-medium { background: color-mix(in srgb, #ff9800 15%, var(--surface)); color: #ff9800; }
  .weight-low { background: var(--surface-alt); color: var(--text-faint); }

  .rating-cell { cursor: pointer; text-align: center; }
  .rating-cell:hover { background: var(--surface-hover); }
  .rating-cell.best { background: color-mix(in srgb, var(--success) 12%, transparent); outline: 1px solid var(--success); outline-offset: -1px; }
  .score-badge { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; color: #fff; font-weight: 700; font-size: 11px; }
  .score-empty { color: var(--text-faint); }
  .note-preview { display: block; margin-top: 4px; color: var(--text-muted); font-size: 10px; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .add-criterion-cell { display: flex; align-items: center; gap: 4px; }
  .add-criterion-filler { background: transparent; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/LocationsMatrix.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/LocationsMatrix.svelte packages/editor/test/LocationsMatrix.test.ts
git commit -m "feat(locations): add comparison matrix component"
```

---

### Task 9: `LocationsPage.svelte`

**Files:**
- Create: `packages/editor/src/lib/components/LocationsPage.svelte`
- Test: `packages/editor/test/LocationsPage.test.ts`

**Interfaces:**
- Consumes: `LocationRankingChart` (Task 6), `LocationsMatrix` (Task 8), `Card` from `ui/Card.svelte` (existing), `createLocationsStore` type (Task 5).
- Produces: `<LocationsPage store />`. Consumed by Task 11 (App.svelte routing).

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/LocationsPage.test.ts`:

```typescript
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import LocationsPage from "../src/lib/components/LocationsPage.svelte";
import { createLocationsStore } from "../src/lib/locationsStore.svelte";

const HOME = "home-123";
const getHomeId = () => HOME;

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({ ok: status >= 200 && status < 300, status, json: async () => body });
}
async function tick(): Promise<void> { await new Promise((r) => setTimeout(r, 0)); }
function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

afterEach(() => vi.unstubAllGlobals());

describe("LocationsPage", () => {
  it("shows an empty state when there are no locations yet, but still shows the matrix to add one", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, criteria: [], locations: [], ratings: [] }));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsPage, { target: el, props: { store } });
    flushSync();
    expect(el.querySelector(".empty-state")).not.toBeNull();
    expect(el.querySelector(".matrix-card-wrap")).not.toBeNull();
    unmount(comp);
    el.remove();
  });

  it("shows the ranking chart once at least one location exists", async () => {
    vi.stubGlobal("fetch", makeFetch(200, {
      version: 1,
      criteria: [{ id: "c1", name: "Cost", description: "", weight: "medium" }],
      locations: [{ id: "l1", name: "Nantes", emoji: "🇫🇷" }],
      ratings: [],
    }));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsPage, { target: el, props: { store } });
    flushSync();
    expect(el.querySelector(".empty-state")).toBeNull();
    expect(el.querySelector(".ranking")).not.toBeNull();
    unmount(comp);
    el.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/LocationsPage.test.ts`
Expected: FAIL with `Cannot find module '../src/lib/components/LocationsPage.svelte'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/editor/src/lib/components/LocationsPage.svelte`:

```svelte
<script lang="ts">
  import type { createLocationsStore } from "../locationsStore.svelte";
  import Card from "./ui/Card.svelte";
  import LocationRankingChart from "./LocationRankingChart.svelte";
  import LocationsMatrix from "./LocationsMatrix.svelte";

  type LocationsStore = ReturnType<typeof createLocationsStore>;
  interface Props { store: LocationsStore; }
  let { store }: Props = $props();
</script>

<div class="page">
  {#if store.locations.length === 0}
    <div class="empty-state">
      <span class="empty-icon">🌍</span>
      <p>No locations yet — add candidates below to start comparing.</p>
    </div>
  {:else}
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-label">Ranking — weighted overall score</div>
        <LocationRankingChart locations={store.locations} criteria={store.criteria} ratings={store.ratings} />
      </Card>
    </div>
  {/if}

  <div class="matrix-card-wrap">
    <Card style="padding:0; overflow:hidden;">
      <LocationsMatrix {store} />
    </Card>
  </div>
</div>

<style>
  .page {
    display: flex; flex-direction: column; height: 100%; background: var(--bg);
    font-family: var(--font-sans); gap: var(--space-4); padding: var(--space-4);
    box-sizing: border-box; overflow-y: auto;
  }
  .empty-state {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 32px; gap: 10px; color: var(--text-faint);
  }
  .empty-icon { font-size: 36px; }
  .empty-state p { margin: 0; font-size: 13px; }
  .chart-card-wrap { flex-shrink: 0; }
  .chart-label { font-size: 10px; color: var(--text-faint); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 10px; }
  .matrix-card-wrap { flex: 1; min-height: 0; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/LocationsPage.test.ts`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/LocationsPage.svelte packages/editor/test/LocationsPage.test.ts
git commit -m "feat(locations): add page composing ranking chart and comparison matrix"
```

---

### Task 10: `HomeLocationsWidget.svelte` + `HomePage.svelte` wiring

**Files:**
- Create: `packages/editor/src/lib/components/HomeLocationsWidget.svelte`
- Test: `packages/editor/test/HomeLocationsWidget.test.ts`
- Modify: `packages/editor/src/lib/components/HomePage.svelte`

**Interfaces:**
- Consumes: `weightedScore` from `locationsStore.svelte.ts` (Task 5); `Card` from `ui/Card.svelte` (existing).
- Produces: `<HomeLocationsWidget locationsStore onnavigate />`, rendered inside `HomePage.svelte`'s `.col-side`.

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/HomeLocationsWidget.test.ts`:

```typescript
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import HomeLocationsWidget from "../src/lib/components/HomeLocationsWidget.svelte";
import { createLocationsStore } from "../src/lib/locationsStore.svelte";

const HOME = "home-123";
const getHomeId = () => HOME;

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({ ok: status >= 200 && status < 300, status, json: async () => body });
}
async function tick(): Promise<void> { await new Promise((r) => setTimeout(r, 0)); }
function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

afterEach(() => vi.unstubAllGlobals());

describe("HomeLocationsWidget", () => {
  it("renders nothing when there are no locations", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, criteria: [], locations: [], ratings: [] }));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(HomeLocationsWidget, { target: el, props: { locationsStore: store, onnavigate: vi.fn() } });
    flushSync();
    expect(el.querySelector(".widget")).toBeNull();
    unmount(comp);
    el.remove();
  });

  it("shows the top-ranked location", async () => {
    vi.stubGlobal("fetch", makeFetch(200, {
      version: 1,
      criteria: [{ id: "c1", name: "Cost", description: "", weight: "medium" }],
      locations: [
        { id: "l1", name: "Nantes", emoji: "🇫🇷" },
        { id: "l2", name: "Ljubljana", emoji: "🇸🇮" },
      ],
      ratings: [
        { locationId: "l1", criterionId: "c1", score: 2, note: "" },
        { locationId: "l2", criterionId: "c1", score: 5, note: "" },
      ],
    }));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(HomeLocationsWidget, { target: el, props: { locationsStore: store, onnavigate: vi.fn() } });
    flushSync();
    expect(el.querySelector(".top-pick .name")?.textContent).toBe("Ljubljana");
    unmount(comp);
    el.remove();
  });

  it("calls onnavigate when clicked", async () => {
    vi.stubGlobal("fetch", makeFetch(200, {
      version: 1, criteria: [], locations: [{ id: "l1", name: "Nantes", emoji: "🇫🇷" }], ratings: [],
    }));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const onnavigate = vi.fn();
    const comp = mount(HomeLocationsWidget, { target: el, props: { locationsStore: store, onnavigate } });
    flushSync();
    (el.querySelector(".widget") as HTMLElement).click();
    expect(onnavigate).toHaveBeenCalled();
    unmount(comp);
    el.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/HomeLocationsWidget.test.ts`
Expected: FAIL with `Cannot find module '../src/lib/components/HomeLocationsWidget.svelte'`

- [ ] **Step 3: Write minimal implementation**

Create `packages/editor/src/lib/components/HomeLocationsWidget.svelte`:

```svelte
<script lang="ts">
  import type { createLocationsStore } from "../locationsStore.svelte";
  import { weightedScore } from "../locationsStore.svelte";
  import Card from "./ui/Card.svelte";

  type LocationsStore = ReturnType<typeof createLocationsStore>;

  interface Props {
    locationsStore: LocationsStore;
    onnavigate: () => void;
  }
  let { locationsStore, onnavigate }: Props = $props();

  const ranked = $derived(
    locationsStore.locations
      .map((loc) => ({ loc, score: weightedScore(locationsStore.criteria, locationsStore.ratings, loc.id) }))
      .sort((a, b) => (b.score ?? -1) - (a.score ?? -1)),
  );
  const top = $derived(ranked[0] ?? null);
  const rest = $derived(ranked.slice(1, 4));
</script>

{#if locationsStore.locations.length > 0}
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
      <div class="header"><h3>🌍 Locations</h3></div>
      {#if top}
        <div class="top-pick">
          <span class="crown">👑</span>
          <span class="emoji">{top.loc.emoji}</span>
          <span class="name">{top.loc.name}</span>
          <span class="score">{top.score !== null ? top.score.toFixed(1) : "—"}</span>
        </div>
      {/if}
      {#if rest.length > 0}
        <ul class="rest-list">
          {#each rest as { loc, score } (loc.id)}
            <li>
              <span class="emoji">{loc.emoji}</span>
              <span class="name">{loc.name}</span>
              <span class="score">{score !== null ? score.toFixed(1) : "—"}</span>
            </li>
          {/each}
        </ul>
      {/if}
    </Card>
  </div>
{/if}

<style>
  .widget { cursor: pointer; }
  .header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--space-2); }
  .header h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
  .top-pick { display: flex; align-items: center; gap: 6px; font-size: 13px; margin-bottom: 6px; }
  .top-pick .name { font-weight: 700; color: var(--text); flex: 1; }
  .top-pick .score { font-weight: 600; color: var(--success); }
  .rest-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .rest-list li { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-muted); }
  .rest-list .name { flex: 1; }
  .rest-list .score { font-weight: 600; }
</style>
```

Modify `packages/editor/src/lib/components/HomePage.svelte`: add the import (near line 14, after `HomeConsumablesWidget`), add `locationsStore` to `Props`/destructure, and render the widget in `.col-side` (after `HomeConsumablesWidget`):

```svelte
  import HomeConsumablesWidget from "./HomeConsumablesWidget.svelte";
  import HomeLocationsWidget from "./HomeLocationsWidget.svelte";
```

```svelte
  import type { createConsumableStore } from "../consumableStore.svelte";
  import type { createLocationsStore } from "../locationsStore.svelte";
```

```svelte
  type ConsumableStore = ReturnType<typeof createConsumableStore>;
  type LocationsStore = ReturnType<typeof createLocationsStore>;
```

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
  }
  let { floorStore, choreStore, inventoryStore, settingsStore, costsStore, worksStore, consumableStore, locationsStore }: Props = $props();
```

```svelte
    <HomeConsumablesWidget {consumableStore} onnavigate={() => navigate("#/consumables")} />
    <HomeLocationsWidget {locationsStore} onnavigate={() => navigate("#/locations")} />
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/HomeLocationsWidget.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/HomeLocationsWidget.svelte packages/editor/test/HomeLocationsWidget.test.ts packages/editor/src/lib/components/HomePage.svelte
git commit -m "feat(locations): add home dashboard widget"
```

---

### Task 11: Wire into `App.svelte` and `NavMenu.svelte`

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Modify: `packages/editor/src/lib/components/NavMenu.svelte`

**Interfaces:**
- Consumes: `createLocationsStore` (Task 5), `LocationsPage` (Task 9), `homesStore.activeHomeId`/`getHomeId` (existing).

No new test file for this task — the `App.svelte` routing test file (`App.routing.test.ts`) only covers the floor-plan/home-dashboard special cases, not every module route (consistent with how Chores/Works/Costs/KB routing is untested at the `App` level; each page is unit-tested standalone, which Tasks 6–10 already cover). This task is verified by the full existing frontend test suite still passing plus the manual check in Task 12.

- [ ] **Step 1: Add store creation and reload wiring**

In `packages/editor/src/App.svelte`, add the import next to `ConsumablesPage`/`createConsumableStore` (around line 25-27):

```svelte
  import LocationsPage from "./lib/components/LocationsPage.svelte";
  import { createLocationsStore } from "./lib/locationsStore.svelte";
```

Add store creation next to `consumableStore` (line 77):

```svelte
  const consumableStore = createConsumableStore(getHomeId);
  const locationsStore = createLocationsStore(getHomeId);
```

Add reload call inside the home-switch `$effect` (line 89-100), next to `consumableStore.reload()`:

```svelte
    consumableStore.reload();
    locationsStore.reload();
```

- [ ] **Step 2: Wire the route and HomePage prop**

Replace the placeholder route (originally `{:else if currentRoute === "#/locations"} <PlaceholderPage icon="🌍" label="Locations" description="Pin and compare candidate locations on a map." />`) with:

```svelte
      {:else if currentRoute === "#/locations"}
        <LocationsPage store={locationsStore} />
```

Add `locationsStore` to the `<HomePage ... />` invocation (the block that currently passes `floorStore choreStore inventoryStore settingsStore costsStore worksStore consumableStore`):

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
        />
```

- [ ] **Step 3: Drop the placeholder flag in NavMenu**

In `packages/editor/src/lib/components/NavMenu.svelte`, change line 20 from:

```typescript
    { id: "locations",   href: "#/locations",   icon: "🌍", label: "Locations",   placeholder: true },
```

to:

```typescript
    { id: "locations",   href: "#/locations",   icon: "🌍", label: "Locations"   },
```

- [ ] **Step 4: Run the full frontend test suite to verify nothing broke**

Run: `cd packages/editor && npx vitest run`
Expected: PASS (all existing tests plus the ~26 new tests from Tasks 5–10)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/src/lib/components/NavMenu.svelte
git commit -m "feat(locations): wire store, routing, and nav entry into the app shell"
```

---

### Task 12: Manual verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend and frontend test suites one more time**

```bash
cd packages/backend && python -m pytest -q
cd packages/editor && npx vitest run
```
Expected: All PASS.

- [ ] **Step 2: Launch the app and drive the feature end-to-end**

Use the `webapp-testing` skill (Playwright) or the project's `run` skill to start the dev server, then:
1. Create a new home with type "Project" (e.g. name "Retirement Search").
2. In Settings → Home, enable the "Locations" module (it's off by default for Project homes).
3. Navigate to Locations via the nav — confirm it's no longer "Coming soon" and shows the empty state with the matrix visible for adding criteria/locations.
4. Add 3 candidate locations (e.g. "Nantes 🇫🇷", "Ljubljana 🇸🇮", "Zagreb 🇭🇷").
5. Confirm the 11 default criteria are present, each editable.
6. Rate several cells across all 3 locations for several criteria, including at least one 3-way tie and one criterion left fully unrated.
7. Confirm: the ranking chart at the top updates live, sorts descending, crowns the correct (possibly tied) leader; the matrix highlights the best cell per row (or none, for the unrated row).
8. Edit a criterion's weight and confirm the ranking re-sorts accordingly.
9. Delete a location and confirm its column and ratings disappear from both the matrix and the chart.
10. Go to the Home dashboard and confirm the new Locations widget shows the current top pick and links back to `#/locations`.
11. Check both light and dark theme for the new page (score badge colors, best-cell highlight, popup) — no unreadable contrast.

- [ ] **Step 3: Report results**

Summarize pass/fail for each item above. Fix any issues found before considering the module complete.

---

## Self-Review Notes

- **Spec coverage:** all 4 spec sections (data model, backend, frontend, testing) are covered — Tasks 1–4 = backend, Tasks 5–10 = frontend, Task 11 = wiring, Task 12 = the spec's "manual verification" requirement.
- **Placeholder scan:** no TBD/TODO; every step has complete, runnable code.
- **Type consistency:** `Weight = "low"|"medium"|"high"` and `WEIGHT_MULTIPLIER` are defined once in Task 5 (frontend) and once in Task 1 (backend, as a `Literal`) and referenced identically by name in every later task (`weightedScore`, `bestScoreForCriterion`, `ratingFor`, `LocationCriterion.weight`, `RatingUpdate.score`). Route paths introduced in Task 2 are consumed verbatim by the store in Task 5.

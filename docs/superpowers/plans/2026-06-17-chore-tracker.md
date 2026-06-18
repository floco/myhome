# Chore Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a chore/maintenance tracker to the existing myhome HA add-on: circular progress-ring badges on the floor plan, one-time Donetick import, full CRUD inside the add-on.

**Architecture:** New `/data/chores.json` file (chore definitions + room assignments). New FastAPI routes in `packages/backend` (chore CRUD, assignment CRUD, Donetick import, mark-done). New Svelte components in `packages/editor` (ChoreOverlay always-visible badge layer, ChorePanel slide-over, BadgePopup click menu), wired into `App.svelte` via a `choreMode` toggle.

**Tech Stack:** Python 3.12 / FastAPI / Pydantic v2 / httpx (backend); Svelte 5 runes / TypeScript / Vitest (frontend); SVG stroke-dasharray rings for badges.

---

## File Map

**New backend files:**
- `packages/backend/src/myhome/models_chores.py` — Pydantic models: Chore, Assignment, ChoreDocument, request bodies
- `packages/backend/src/myhome/persistence_chores.py` — `load_chores()` / `save_chores()` (atomic write)
- `packages/backend/src/myhome/routes/chores.py` — all chore + assignment routes (CRUD, import, complete)
- `packages/backend/tests/test_chore_persistence.py` — persistence unit tests
- `packages/backend/tests/test_chores.py` — route integration tests

**Modified backend files:**
- `packages/backend/src/myhome/main.py` — register chores router

**New frontend files:**
- `packages/editor/src/lib/choreStore.svelte.ts` — reactive chore/assignment store
- `packages/editor/src/lib/components/ChoreOverlay.svelte` — always-visible badge SVG layer
- `packages/editor/src/lib/components/ChorePanel.svelte` — right slide-over panel
- `packages/editor/src/lib/components/BadgePopup.svelte` — badge click popup
- `packages/editor/test/choreStore.test.ts` — store unit tests

**Modified frontend files:**
- `packages/editor/src/App.svelte` — choreMode state, ChoreOverlay + ChorePanel wired in

---

## Task 1: Backend chore models

**Files:**
- Create: `packages/backend/src/myhome/models_chores.py`

- [ ] **Step 1: Create `models_chores.py`**

```python
from __future__ import annotations
from pydantic import BaseModel


class Position(BaseModel):
    x: float
    y: float


class Chore(BaseModel):
    id: str
    donetickId: int | None = None
    name: str
    emoji: str
    periodDays: float
    nextDueDate: str   # ISO 8601
    description: str = ""


class Assignment(BaseModel):
    id: str
    choreId: str
    roomId: str | None = None
    position: Position | None = None


class ChoreDocument(BaseModel):
    version: int = 1
    chores: list[Chore] = []
    assignments: list[Assignment] = []


class ChoreCreate(BaseModel):
    name: str
    emoji: str
    periodDays: float
    nextDueDate: str
    description: str = ""
    donetickId: int | None = None


class ChoreUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None
    periodDays: float | None = None
    nextDueDate: str | None = None
    description: str | None = None


class AssignmentCreate(BaseModel):
    choreId: str
    roomId: str | None = None
    position: Position | None = None


class AssignmentUpdate(BaseModel):
    position: Position | None = None


class ImportRequest(BaseModel):
    token: str


class ImportResponse(BaseModel):
    imported: int
```

- [ ] **Step 2: Verify the file imports cleanly**

```bash
cd /projects/myhome/packages/backend
python -c "from myhome.models_chores import ChoreDocument, Chore, Assignment; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add packages/backend/src/myhome/models_chores.py
git commit -m "feat: chore Pydantic models"
```

---

## Task 2: Backend chore persistence

**Files:**
- Create: `packages/backend/src/myhome/persistence_chores.py`
- Create: `packages/backend/tests/test_chore_persistence.py`

- [ ] **Step 1: Write failing persistence tests**

```python
# packages/backend/tests/test_chore_persistence.py
import pytest
from myhome.models_chores import ChoreDocument, Chore, Assignment
from myhome.persistence_chores import load_chores, save_chores


def make_doc() -> ChoreDocument:
    return ChoreDocument(
        version=1,
        chores=[
            Chore(
                id="c1",
                name="🧹 Sweep",
                emoji="🧹",
                periodDays=14,
                nextDueDate="2027-01-01T00:00:00Z",
            )
        ],
        assignments=[
            Assignment(id="a1", choreId="c1", roomId="r1", position={"x": 1.0, "y": 2.0})
        ],
    )


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = load_chores()
    assert doc.chores == []
    assert doc.assignments == []


def test_save_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_doc())
    assert (tmp_path / "chores.json").exists()


def test_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_doc())
    loaded = load_chores()
    assert loaded.chores[0].id == "c1"
    assert loaded.chores[0].emoji == "🧹"
    assert loaded.assignments[0].roomId == "r1"
    assert loaded.assignments[0].position.x == 1.0


def test_save_creates_data_dir_if_missing(tmp_path, monkeypatch):
    nested = tmp_path / "nested" / "data"
    monkeypatch.setenv("DATA_DIR", str(nested))
    save_chores(make_doc())
    assert (nested / "chores.json").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /projects/myhome/packages/backend
pytest tests/test_chore_persistence.py -v
```

Expected: ImportError or ModuleNotFoundError (persistence_chores doesn't exist yet)

- [ ] **Step 3: Implement `persistence_chores.py`**

```python
# packages/backend/src/myhome/persistence_chores.py
import json
import os
from pathlib import Path

from .models_chores import ChoreDocument


def _chores_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "chores.json"


def load_chores() -> ChoreDocument:
    path = _chores_file()
    if not path.exists():
        return ChoreDocument()
    with path.open() as f:
        return ChoreDocument.model_validate(json.load(f))


def save_chores(doc: ChoreDocument) -> None:
    path = _chores_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /projects/myhome/packages/backend
pytest tests/test_chore_persistence.py -v
```

Expected: 4 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/persistence_chores.py packages/backend/tests/test_chore_persistence.py
git commit -m "feat: chore persistence (load/save chores.json)"
```

---

## Task 3: Backend chore CRUD + complete routes

**Files:**
- Create: `packages/backend/src/myhome/routes/chores.py`
- Create: `packages/backend/tests/test_chores.py`
- Modify: `packages/backend/src/myhome/main.py`

- [ ] **Step 1: Write failing route tests (CRUD + complete)**

```python
# packages/backend/tests/test_chores.py
import pytest
from fastapi.testclient import TestClient
from myhome.main import app
from myhome.models_chores import ChoreDocument, Chore
from myhome.persistence_chores import save_chores


def make_chore_doc() -> ChoreDocument:
    return ChoreDocument(
        chores=[
            Chore(
                id="c1",
                name="🧹 Sweep",
                emoji="🧹",
                periodDays=14,
                nextDueDate="2027-06-01T00:00:00Z",
            )
        ],
        assignments=[],
    )


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)


# --- GET /api/chores ---

def test_get_chores_empty_when_no_file(client):
    resp = client.get("/api/chores")
    assert resp.status_code == 200
    data = resp.json()
    assert data["chores"] == []
    assert data["assignments"] == []


def test_get_chores_returns_saved_data(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    resp = c.get("/api/chores")
    assert resp.status_code == 200
    assert resp.json()["chores"][0]["id"] == "c1"


# --- POST /api/chores ---

def test_create_chore(client):
    payload = {
        "name": "🪟 Clean windows",
        "emoji": "🪟",
        "periodDays": 365,
        "nextDueDate": "2027-01-01T00:00:00Z",
        "description": "",
    }
    resp = client.post("/api/chores", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "🪟 Clean windows"
    assert data["emoji"] == "🪟"
    assert "id" in data

    # Verify persisted
    get_resp = client.get("/api/chores")
    assert any(c["name"] == "🪟 Clean windows" for c in get_resp.json()["chores"])


# --- PUT /api/chores/{id} ---

def test_update_chore(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    resp = c.put("/api/chores/c1", json={"name": "🧹 Sweep floors", "periodDays": 21})
    assert resp.status_code == 204
    get_resp = c.get("/api/chores")
    chore = next(ch for ch in get_resp.json()["chores"] if ch["id"] == "c1")
    assert chore["name"] == "🧹 Sweep floors"
    assert chore["periodDays"] == 21
    assert chore["emoji"] == "🧹"  # unchanged


def test_update_chore_404(client):
    resp = client.put("/api/chores/nonexistent", json={"name": "X"})
    assert resp.status_code == 404


# --- DELETE /api/chores/{id} ---

def test_delete_chore(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    resp = c.delete("/api/chores/c1")
    assert resp.status_code == 204
    get_resp = c.get("/api/chores")
    assert get_resp.json()["chores"] == []


def test_delete_chore_404(client):
    resp = client.delete("/api/chores/nonexistent")
    assert resp.status_code == 404


# --- POST /api/chores/{id}/complete ---

def test_complete_chore_advances_next_due(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    resp = c.post("/api/chores/c1/complete")
    assert resp.status_code == 200
    data = resp.json()
    # nextDueDate should now be ~14 days from today, not 2027-06-01
    from datetime import datetime, timezone, timedelta
    new_due = datetime.fromisoformat(data["nextDueDate"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    expected = now + timedelta(days=14)
    assert abs((new_due - expected).total_seconds()) < 5  # within 5 seconds


def test_complete_chore_404(client):
    resp = client.post("/api/chores/nonexistent/complete")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /projects/myhome/packages/backend
pytest tests/test_chores.py -v -k "not import and not assignment"
```

Expected: errors (routes don't exist yet)

- [ ] **Step 3: Create `routes/chores.py` with CRUD + complete**

```python
# packages/backend/src/myhome/routes/chores.py
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from ..models_chores import (
    Assignment,
    AssignmentCreate,
    AssignmentUpdate,
    Chore,
    ChoreCreate,
    ChoreDocument,
    ChoreUpdate,
    ImportRequest,
    ImportResponse,
)
from ..persistence_chores import load_chores, save_chores

router = APIRouter()

UNIT_DAYS: dict[str, float] = {"days": 1, "weeks": 7, "months": 30, "years": 365}


def _period_days(chore: dict) -> float:
    freq: int = chore["frequency"]
    freq_type: str = chore["frequencyType"]
    meta: dict = chore.get("frequencyMetadata") or {}
    unit: str = meta.get("unit", "days")
    if freq_type == "weekly":
        return freq * 7.0
    elif freq_type == "interval":
        return freq * UNIT_DAYS.get(unit, 1)
    elif freq_type == "yearly":
        return freq * 365.0
    elif freq_type == "day_of_the_month":
        return float(freq)
    return float(freq)


def _extract_emoji(name: str) -> str:
    name = name.strip()
    result: list[str] = []
    for ch in name:
        cp = ord(ch)
        if (0x2600 <= cp <= 0x27BF or
                0x1F000 <= cp <= 0x1FFFF or
                cp == 0xFE0F or
                cp == 0x200D):
            result.append(ch)
        elif result:
            break
    return "".join(result).strip() or "📋"


# --- Chore routes ---

@router.get("/api/chores", response_model=ChoreDocument)
def get_chores() -> ChoreDocument:
    return load_chores()


# NOTE: /api/chores/import MUST be defined before /api/chores/{chore_id}
# so FastAPI does not try to match "import" as a chore ID.
@router.post("/api/chores/import", response_model=ImportResponse)
async def import_from_donetick(body: ImportRequest) -> ImportResponse:
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://chores.casa.mutualis.com/api/v1/chores/",
                headers={"secretkey": body.token},
                timeout=10.0,
            )
            resp.raise_for_status()
            raw_chores: list[dict] = resp.json().get("res", [])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Donetick error: {exc}") from exc

    doc = load_chores()
    existing_ids = {c.donetickId for c in doc.chores if c.donetickId is not None}
    imported = 0

    for rc in raw_chores:
        if rc["id"] in existing_ids:
            continue
        doc.chores.append(
            Chore(
                id=str(uuid.uuid4()),
                donetickId=rc["id"],
                name=rc["name"].strip(),
                emoji=_extract_emoji(rc["name"]),
                periodDays=_period_days(rc),
                nextDueDate=rc.get("nextDueDate", ""),
                description="",
            )
        )
        imported += 1

    save_chores(doc)
    return ImportResponse(imported=imported)


@router.post("/api/chores", response_model=Chore, status_code=201)
def create_chore(body: ChoreCreate) -> Chore:
    doc = load_chores()
    chore = Chore(id=str(uuid.uuid4()), **body.model_dump())
    doc.chores.append(chore)
    save_chores(doc)
    return chore


@router.put("/api/chores/{chore_id}", status_code=204)
def update_chore(chore_id: str, body: ChoreUpdate) -> None:
    doc = load_chores()
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(chore, field, value)
    save_chores(doc)


@router.delete("/api/chores/{chore_id}", status_code=204)
def delete_chore(chore_id: str) -> None:
    doc = load_chores()
    if not any(c.id == chore_id for c in doc.chores):
        raise HTTPException(status_code=404, detail="Chore not found")
    doc.chores = [c for c in doc.chores if c.id != chore_id]
    doc.assignments = [a for a in doc.assignments if a.choreId != chore_id]
    save_chores(doc)


@router.post("/api/chores/{chore_id}/complete", response_model=Chore)
def complete_chore(chore_id: str) -> Chore:
    doc = load_chores()
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    next_due = datetime.now(timezone.utc) + timedelta(days=chore.periodDays)
    chore.nextDueDate = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    save_chores(doc)
    return chore


# --- Assignment routes ---

@router.post("/api/assignments", response_model=Assignment, status_code=201)
def create_assignment(body: AssignmentCreate) -> Assignment:
    doc = load_chores()
    if not any(c.id == body.choreId for c in doc.chores):
        raise HTTPException(status_code=404, detail="Chore not found")
    assignment = Assignment(id=str(uuid.uuid4()), **body.model_dump())
    doc.assignments.append(assignment)
    save_chores(doc)
    return assignment


@router.put("/api/assignments/{assignment_id}", status_code=204)
def update_assignment(assignment_id: str, body: AssignmentUpdate) -> None:
    doc = load_chores()
    assignment = next((a for a in doc.assignments if a.id == assignment_id), None)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if body.position is not None:
        assignment.position = body.position
    save_chores(doc)


@router.delete("/api/assignments/{assignment_id}", status_code=204)
def delete_assignment(assignment_id: str) -> None:
    doc = load_chores()
    if not any(a.id == assignment_id for a in doc.assignments):
        raise HTTPException(status_code=404, detail="Assignment not found")
    doc.assignments = [a for a in doc.assignments if a.id != assignment_id]
    save_chores(doc)
```

- [ ] **Step 4: Register chores router in `main.py`**

Replace:
```python
from .routes import house, svg, ha

app = FastAPI(title="MyHome Backend", version="0.1.0")
app.include_router(house.router)
app.include_router(svg.router)
app.include_router(ha.router)
```

With:
```python
from .routes import house, svg, ha, chores

app = FastAPI(title="MyHome Backend", version="0.1.0")
app.include_router(house.router)
app.include_router(svg.router)
app.include_router(ha.router)
app.include_router(chores.router)
```

- [ ] **Step 5: Run CRUD + complete tests**

```bash
cd /projects/myhome/packages/backend
pytest tests/test_chores.py -v -k "not import and not assignment"
```

Expected: 10 tests PASSED

- [ ] **Step 6: Run all backend tests to check nothing broke**

```bash
cd /projects/myhome/packages/backend
pytest -v
```

Expected: all existing tests + new tests PASSED

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/routes/chores.py packages/backend/src/myhome/main.py packages/backend/tests/test_chores.py
git commit -m "feat: chore CRUD + complete routes"
```

---

## Task 4: Backend Donetick import + assignment routes tests

**Files:**
- Modify: `packages/backend/tests/test_chores.py`

The `routes/chores.py` already contains the import and assignment implementations. This task adds the tests.

- [ ] **Step 1: Add import tests to `test_chores.py`**

Append to the end of `packages/backend/tests/test_chores.py`:

```python
# --- POST /api/chores/import ---

def test_import_from_donetick(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import respx
    import httpx

    donetick_response = {
        "res": [
            {
                "id": 42,
                "name": "🪟 Clean windows",
                "frequencyType": "interval",
                "frequency": 6,
                "frequencyMetadata": {"unit": "months"},
                "nextDueDate": "2027-01-01T00:00:00Z",
            },
            {
                "id": 43,
                "name": "🧹 Sweep",
                "frequencyType": "weekly",
                "frequency": 2,
                "frequencyMetadata": {"unit": "weeks"},
                "nextDueDate": "2026-07-01T00:00:00Z",
            },
        ]
    }

    with respx.mock:
        respx.get("https://chores.casa.mutualis.com/api/v1/chores/").mock(
            return_value=httpx.Response(200, json=donetick_response)
        )
        c = TestClient(app)
        resp = c.post("/api/chores/import", json={"token": "test-token"})

    assert resp.status_code == 200
    assert resp.json()["imported"] == 2

    chores_resp = c.get("/api/chores")
    chores = chores_resp.json()["chores"]
    assert len(chores) == 2
    window = next(c for c in chores if c["donetickId"] == 42)
    assert window["emoji"] == "🪟"
    assert window["periodDays"] == 180  # 6 * 30
    sweep = next(c for c in chores if c["donetickId"] == 43)
    assert sweep["periodDays"] == 14  # 2 * 7


def test_import_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from myhome.models_chores import Chore
    from myhome.persistence_chores import save_chores
    import respx
    import httpx

    existing = ChoreDocument(
        chores=[Chore(id="x", donetickId=42, name="🪟 Clean windows", emoji="🪟", periodDays=180, nextDueDate="2027-01-01T00:00:00Z")],
        assignments=[],
    )
    save_chores(existing)

    donetick_response = {"res": [{"id": 42, "name": "🪟 Clean windows", "frequencyType": "interval", "frequency": 6, "frequencyMetadata": {"unit": "months"}, "nextDueDate": "2027-01-01T00:00:00Z"}]}
    with respx.mock:
        respx.get("https://chores.casa.mutualis.com/api/v1/chores/").mock(
            return_value=httpx.Response(200, json=donetick_response)
        )
        c = TestClient(app)
        resp = c.post("/api/chores/import", json={"token": "test-token"})

    assert resp.json()["imported"] == 0
    assert len(c.get("/api/chores").json()["chores"]) == 1


# --- Assignment routes ---

def test_create_assignment(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    resp = c.post("/api/assignments", json={"choreId": "c1", "roomId": "r1", "position": {"x": 3.0, "y": 4.0}})
    assert resp.status_code == 201
    data = resp.json()
    assert data["choreId"] == "c1"
    assert data["roomId"] == "r1"
    assert data["position"]["x"] == 3.0
    assert "id" in data


def test_create_assignment_house_level(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    resp = c.post("/api/assignments", json={"choreId": "c1", "roomId": None, "position": None})
    assert resp.status_code == 201
    assert resp.json()["roomId"] is None
    assert resp.json()["position"] is None


def test_create_assignment_404_unknown_chore(client):
    resp = client.post("/api/assignments", json={"choreId": "nope", "roomId": "r1"})
    assert resp.status_code == 404


def test_update_assignment_position(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    create_resp = c.post("/api/assignments", json={"choreId": "c1", "roomId": "r1", "position": {"x": 1.0, "y": 1.0}})
    aid = create_resp.json()["id"]
    put_resp = c.put(f"/api/assignments/{aid}", json={"position": {"x": 5.0, "y": 6.0}})
    assert put_resp.status_code == 204
    assignments = c.get("/api/chores").json()["assignments"]
    a = next(a for a in assignments if a["id"] == aid)
    assert a["position"]["x"] == 5.0


def test_delete_assignment(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    aid = c.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"}).json()["id"]
    del_resp = c.delete(f"/api/assignments/{aid}")
    assert del_resp.status_code == 204
    assert c.get("/api/chores").json()["assignments"] == []


def test_delete_chore_cascades_assignments(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_chores(make_chore_doc())
    c = TestClient(app)
    c.post("/api/assignments", json={"choreId": "c1", "roomId": "r1"})
    c.delete("/api/chores/c1")
    assert c.get("/api/chores").json()["assignments"] == []
```

- [ ] **Step 2: Add `respx` to dev dependencies**

Edit `packages/backend/pyproject.toml` — add `"respx>=0.21"` to `[project.optional-dependencies] dev`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
    "respx>=0.21",
]
```

Then install:
```bash
cd /projects/myhome/packages/backend
pip install -e ".[dev]"
```

- [ ] **Step 3: Run all test_chores tests**

```bash
cd /projects/myhome/packages/backend
pytest tests/test_chores.py -v
```

Expected: all tests PASSED (including import + assignment tests)

- [ ] **Step 4: Run full backend suite**

```bash
cd /projects/myhome/packages/backend
pytest -v
```

Expected: all tests PASSED

- [ ] **Step 5: Commit**

```bash
git add packages/backend/tests/test_chores.py packages/backend/pyproject.toml
git commit -m "test: import + assignment route tests; add respx dev dependency"
```

---

## Task 5: Frontend chore store

**Files:**
- Create: `packages/editor/src/lib/choreStore.svelte.ts`
- Create: `packages/editor/test/choreStore.test.ts`

- [ ] **Step 1: Write failing store tests**

```typescript
// packages/editor/test/choreStore.test.ts
import { describe, it, expect, afterEach, vi } from "vitest";
import { createChoreStore } from "../src/lib/choreStore.svelte";

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

const emptyDoc = { version: 1, chores: [], assignments: [] };

const sampleDoc = {
  version: 1,
  chores: [
    { id: "c1", donetickId: null, name: "🧹 Sweep", emoji: "🧹", periodDays: 14, nextDueDate: new Date(Date.now() + 7 * 86400000).toISOString(), description: "" },
    { id: "c2", donetickId: null, name: "🪟 Windows", emoji: "🪟", periodDays: 365, nextDueDate: new Date(Date.now() - 5 * 86400000).toISOString(), description: "" },
  ],
  assignments: [
    { id: "a1", choreId: "c1", roomId: "r1", position: { x: 1, y: 2 } },
    { id: "a2", choreId: "c2", roomId: null, position: null },
  ],
};

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

describe("choreStore — init", () => {
  it("starts empty and loads from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createChoreStore();
    await tick();
    expect(store.chores.length).toBe(2);
    expect(store.assignments.length).toBe(2);
    expect(store.loaded).toBe(true);
  });

  it("marks loaded even on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network error")));
    const store = createChoreStore();
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("Network error");
  });

  it("returns empty arrays when API returns empty doc", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore();
    await tick();
    expect(store.chores).toEqual([]);
    expect(store.assignments).toEqual([]);
  });
});

describe("choreStore — getProgress", () => {
  it("returns ~0.5 when half period remains", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore();
    await tick();
    const halfRemaining = new Date(Date.now() + 7 * 86400000).toISOString();
    const pct = store.getProgress({ id: "x", donetickId: null, name: "", emoji: "", periodDays: 14, nextDueDate: halfRemaining, description: "" });
    expect(pct).toBeCloseTo(0.5, 1);
  });

  it("returns 0 when overdue", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore();
    await tick();
    const overdue = new Date(Date.now() - 86400000).toISOString();
    const pct = store.getProgress({ id: "x", donetickId: null, name: "", emoji: "", periodDays: 14, nextDueDate: overdue, description: "" });
    expect(pct).toBe(0);
  });

  it("returns 1 when just scheduled", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore();
    await tick();
    const fullRemaining = new Date(Date.now() + 14 * 86400000).toISOString();
    const pct = store.getProgress({ id: "x", donetickId: null, name: "", emoji: "", periodDays: 14, nextDueDate: fullRemaining, description: "" });
    expect(pct).toBeCloseTo(1, 1);
  });
});

describe("choreStore — getColor", () => {
  it("returns green for >50%", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore();
    await tick();
    expect(store.getColor(0.8)).toBe("#4caf50");
  });

  it("returns orange for 25-50%", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore();
    await tick();
    expect(store.getColor(0.4)).toBe("#ff9800");
  });

  it("returns red for <25% or overdue", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore();
    await tick();
    expect(store.getColor(0.1)).toBe("#f44336");
    expect(store.getColor(0)).toBe("#f44336");
  });
});

describe("choreStore — assignmentsForRoom", () => {
  it("returns only assignments for the specified room", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createChoreStore();
    await tick();
    const forR1 = store.assignmentsForRoom("r1");
    expect(forR1.length).toBe(1);
    expect(forR1[0].id).toBe("a1");
  });

  it("returns empty array for unknown room", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createChoreStore();
    await tick();
    expect(store.assignmentsForRoom("unknown")).toEqual([]);
  });

  it("does not include house-level assignments", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createChoreStore();
    await tick();
    // a2 has roomId: null (house-level) — should not appear in any room query
    const forR1 = store.assignmentsForRoom("r1");
    expect(forR1.every((a) => a.roomId !== null)).toBe(true);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /projects/myhome/packages/editor
npm test -- choreStore
```

Expected: error (module not found)

- [ ] **Step 3: Implement `choreStore.svelte.ts`**

```typescript
// packages/editor/src/lib/choreStore.svelte.ts

export interface Chore {
  id: string;
  donetickId: number | null;
  name: string;
  emoji: string;
  periodDays: number;
  nextDueDate: string;
  description: string;
}

export interface Position {
  x: number;
  y: number;
}

export interface Assignment {
  id: string;
  choreId: string;
  roomId: string | null;
  position: Position | null;
}

export interface ChoreDocument {
  version: number;
  chores: Chore[];
  assignments: Assignment[];
}

export function createChoreStore() {
  const chores = $state<Chore[]>([]);
  const assignments = $state<Assignment[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    try {
      const resp = await fetch("/api/chores");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: ChoreDocument = await resp.json();
      chores.length = 0;
      for (const c of doc.chores) chores.push(c);
      assignments.length = 0;
      for (const a of doc.assignments) assignments.push(a);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  function getProgress(chore: Chore): number {
    const now = Date.now();
    const due = new Date(chore.nextDueDate).getTime();
    const periodMs = chore.periodDays * 86400 * 1000;
    return Math.max(0, Math.min(1, (due - now) / periodMs));
  }

  function getColor(pct: number): string {
    if (pct > 0.5) return "#4caf50";
    if (pct > 0.25) return "#ff9800";
    return "#f44336";
  }

  function assignmentsForRoom(roomId: string): Assignment[] {
    return assignments.filter((a) => a.roomId === roomId);
  }

  function houseAssignments(): Assignment[] {
    return assignments.filter((a) => a.roomId === null);
  }

  async function createChore(data: Omit<Chore, "id">): Promise<void> {
    const resp = await fetch("/api/chores", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateChore(id: string, patch: Partial<Omit<Chore, "id" | "donetickId">>): Promise<void> {
    const resp = await fetch(`/api/chores/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteChore(id: string): Promise<void> {
    const resp = await fetch(`/api/chores/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function completeChore(id: string): Promise<void> {
    const resp = await fetch(`/api/chores/${id}/complete`, { method: "POST" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function importFromDonetick(token: string): Promise<number> {
    const resp = await fetch("/api/chores/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const { imported } = await resp.json();
    await init();
    return imported as number;
  }

  async function createAssignment(data: Omit<Assignment, "id">): Promise<void> {
    const resp = await fetch("/api/assignments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateAssignmentPosition(id: string, position: Position): Promise<void> {
    const resp = await fetch(`/api/assignments/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ position }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteAssignment(id: string): Promise<void> {
    const resp = await fetch(`/api/assignments/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  init();

  return {
    get chores() { return chores as Chore[]; },
    get assignments() { return assignments as Assignment[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    getProgress,
    getColor,
    assignmentsForRoom,
    houseAssignments,
    createChore,
    updateChore,
    deleteChore,
    completeChore,
    importFromDonetick,
    createAssignment,
    updateAssignmentPosition,
    deleteAssignment,
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /projects/myhome/packages/editor
npm test -- choreStore
```

Expected: all tests PASSED

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/choreStore.svelte.ts packages/editor/test/choreStore.test.ts
git commit -m "feat: frontend chore store"
```

---

## Task 6: ChoreOverlay component

**Files:**
- Create: `packages/editor/src/lib/components/ChoreOverlay.svelte`

The overlay renders circular progress-ring badges for all room-assigned assignments directly on the floor plan. It is always in the DOM (badges visible in all modes) but pointer-events are disabled outside chore mode so the drawing tools remain usable.

- [ ] **Step 1: Create `ChoreOverlay.svelte`**

```svelte
<!-- packages/editor/src/lib/components/ChoreOverlay.svelte -->
<script lang="ts">
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";
  import type { Chore, Assignment, Position } from "../choreStore.svelte";

  interface Props {
    chores: Chore[];
    assignments: Assignment[];
    viewport: ViewportState;
    choreMode: boolean;
    width: number;
    height: number;
    onclick: (assignmentId: string) => void;
    ondragend: (assignmentId: string, worldPos: Position) => void;
  }

  let { chores, assignments, viewport, choreMode, width, height, onclick, ondragend }: Props = $props();

  const R = 18;
  const C = 2 * Math.PI * R;

  function findChore(choreId: string): Chore | undefined {
    return chores.find((c) => c.id === choreId);
  }

  function getProgress(chore: Chore): number {
    const now = Date.now();
    const due = new Date(chore.nextDueDate).getTime();
    const periodMs = chore.periodDays * 86400 * 1000;
    return Math.max(0, Math.min(1, (due - now) / periodMs));
  }

  function getColor(pct: number): string {
    if (pct > 0.5) return "#4caf50";
    if (pct > 0.25) return "#ff9800";
    return "#f44336";
  }

  // Drag state
  let dragId = $state<string | null>(null);
  let dragStartScreen = $state<Position>({ x: 0, y: 0 });
  let dragStartWorld = $state<Position>({ x: 0, y: 0 });
  let dragOffsetScreen = $state<Position>({ x: 0, y: 0 });

  function badgeScreen(a: Assignment): Position | null {
    if (!a.position) return null;
    const base = worldToScreen(a.position, viewport);
    if (dragId === a.id) {
      return { x: base.x + dragOffsetScreen.x, y: base.y + dragOffsetScreen.y };
    }
    return base;
  }

  function handlePointerDown(e: PointerEvent, a: Assignment): void {
    if (!choreMode || !a.position) return;
    e.stopPropagation();
    (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
    dragId = a.id;
    dragStartScreen = { x: e.clientX, y: e.clientY };
    dragStartWorld = { x: a.position.x, y: a.position.y };
    dragOffsetScreen = { x: 0, y: 0 };
  }

  function handlePointerMove(e: PointerEvent): void {
    if (!dragId) return;
    dragOffsetScreen = { x: e.clientX - dragStartScreen.x, y: e.clientY - dragStartScreen.y };
  }

  function handlePointerUp(e: PointerEvent, a: Assignment): void {
    if (!dragId || dragId !== a.id) return;
    const dx = e.clientX - dragStartScreen.x;
    const dy = e.clientY - dragStartScreen.y;
    const moved = Math.hypot(dx, dy) > 4;
    if (moved) {
      const worldPos: Position = {
        x: dragStartWorld.x + dx / viewport.zoom,
        y: dragStartWorld.y + dy / viewport.zoom,
      };
      ondragend(a.id, worldPos);
    } else {
      onclick(a.id);
    }
    dragId = null;
    dragOffsetScreen = { x: 0, y: 0 };
  }

  const roomAssignments = $derived(
    assignments.filter((a) => a.roomId !== null && a.position !== null)
  );
</script>

<svg
  {width}
  {height}
  style="position:absolute;top:0;left:0;pointer-events:{choreMode ? 'all' : 'none'};overflow:visible"
  onpointermove={handlePointerMove}
>
  {#each roomAssignments as a (a.id)}
    {@const chore = findChore(a.choreId)}
    {#if chore}
      {@const sp = badgeScreen(a)}
      {#if sp}
        {@const pct = getProgress(chore)}
        {@const color = getColor(pct)}
        {@const dashFill = pct * C}
        <g
          transform="translate({sp.x},{sp.y})"
          style="cursor:{choreMode ? (dragId === a.id ? 'grabbing' : 'grab') : 'default'}"
          onpointerdown={(e) => handlePointerDown(e, a)}
          onpointerup={(e) => handlePointerUp(e, a)}
        >
          <!-- Dark background -->
          <circle r={R + 3} fill="#1a1a2e" opacity="0.75"/>
          <!-- Track ring -->
          <circle r={R} fill="none" stroke="#3a3a3a" stroke-width="5"/>
          <!-- Progress arc -->
          <circle r={R} fill="none" stroke={color} stroke-width="5"
            stroke-dasharray="{dashFill} {C}" stroke-linecap="round"
            transform="rotate(-90 0 0)"/>
          <!-- Emoji -->
          <text
            text-anchor="middle"
            dominant-baseline="central"
            font-size="13"
            style="user-select:none;pointer-events:none"
          >{chore.emoji}</text>
        </g>
      {/if}
    {/if}
  {/each}
</svg>
```

- [ ] **Step 2: Verify TypeScript compiles cleanly**

```bash
cd /projects/myhome/packages/editor
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/ChoreOverlay.svelte
git commit -m "feat: ChoreOverlay SVG badge component"
```

---

## Task 7: ChorePanel and BadgePopup components

**Files:**
- Create: `packages/editor/src/lib/components/BadgePopup.svelte`
- Create: `packages/editor/src/lib/components/ChorePanel.svelte`

- [ ] **Step 1: Create `BadgePopup.svelte`**

This small popup appears when the user clicks a badge. It is absolutely positioned near the badge.

```svelte
<!-- packages/editor/src/lib/components/BadgePopup.svelte -->
<script lang="ts">
  import type { Chore, Assignment } from "../choreStore.svelte";

  interface Props {
    chore: Chore;
    assignment: Assignment;
    screenX: number;
    screenY: number;
    oncomplete: () => void;
    onremove: () => void;
    onclose: () => void;
  }

  let { chore, assignment, screenX, screenY, oncomplete, onremove, onclose }: Props = $props();

  function formatDate(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  const overdue = $derived(new Date(chore.nextDueDate).getTime() < Date.now());
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
  class="popup"
  style="left:{screenX + 26}px;top:{screenY - 20}px"
  onclick={(e) => e.stopPropagation()}
>
  <div class="popup-name">{chore.name}</div>
  <div class="popup-due" class:overdue>
    {overdue ? "Overdue since" : "Due"}: {formatDate(chore.nextDueDate)}
  </div>
  <div class="popup-actions">
    <button onclick={oncomplete}>✓ Mark done</button>
    <button onclick={onremove}>✕ Remove</button>
    <button class="close-btn" onclick={onclose}>✕</button>
  </div>
</div>

<style>
  .popup {
    position: fixed;
    background: #2a2a3e;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 8px 10px;
    min-width: 180px;
    z-index: 100;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    font-size: 12px;
    color: #ccc;
  }
  .popup-name {
    font-weight: 600;
    margin-bottom: 4px;
    color: #eee;
  }
  .popup-due {
    color: #888;
    margin-bottom: 8px;
  }
  .popup-due.overdue {
    color: #f44336;
  }
  .popup-actions {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .popup-actions button {
    padding: 3px 8px;
    border: none;
    border-radius: 3px;
    background: #3a3a5a;
    color: #ccc;
    cursor: pointer;
    font-size: 11px;
  }
  .popup-actions button:hover {
    background: #4a4a6a;
  }
  .close-btn {
    margin-left: auto;
  }
</style>
```

- [ ] **Step 2: Create `ChorePanel.svelte`**

```svelte
<!-- packages/editor/src/lib/components/ChorePanel.svelte -->
<script lang="ts">
  import type { createChoreStore } from "../choreStore.svelte";
  import type { Chore } from "../choreStore.svelte";

  type ChoreStore = ReturnType<typeof createChoreStore>;

  interface Props {
    store: ChoreStore;
    assigningChoreId: string | null;
    onAssignToRoom: (choreId: string) => void;
    onCancelAssign: () => void;
  }

  let { store, assigningChoreId, onAssignToRoom, onCancelAssign }: Props = $props();

  // Import section
  let showImportInput = $state(false);
  let importToken = $state("");
  let importStatus = $state<"idle" | "loading" | "done" | "error">("idle");
  let importCount = $state(0);

  async function handleImport(): Promise<void> {
    importStatus = "loading";
    try {
      importCount = await store.importFromDonetick(importToken.trim());
      importStatus = "done";
      importToken = "";
      showImportInput = false;
    } catch {
      importStatus = "error";
    }
  }

  // New chore form
  let showNewForm = $state(false);
  let newName = $state("");
  let newEmoji = $state("📋");
  let newPeriodDays = $state(30);
  let newNextDue = $state(new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10));

  async function handleCreate(): Promise<void> {
    if (!newName.trim()) return;
    await store.createChore({
      name: newName.trim(),
      emoji: newEmoji.trim() || "📋",
      periodDays: newPeriodDays,
      nextDueDate: new Date(newNextDue).toISOString(),
      description: "",
      donetickId: null,
    });
    showNewForm = false;
    newName = "";
    newEmoji = "📋";
    newPeriodDays = 30;
    newNextDue = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
  }

  // Edit form
  let editingId = $state<string | null>(null);
  let editName = $state("");
  let editEmoji = $state("");
  let editPeriodDays = $state(30);
  let editNextDue = $state("");

  function startEdit(chore: Chore): void {
    editingId = chore.id;
    editName = chore.name;
    editEmoji = chore.emoji;
    editPeriodDays = chore.periodDays;
    editNextDue = chore.nextDueDate.slice(0, 10);
  }

  async function handleUpdate(): Promise<void> {
    if (!editingId) return;
    await store.updateChore(editingId, {
      name: editName.trim(),
      emoji: editEmoji.trim() || "📋",
      periodDays: editPeriodDays,
      nextDueDate: new Date(editNextDue).toISOString(),
    });
    editingId = null;
  }

  const houseChores = $derived(
    store.houseAssignments().map((a) => ({
      assignment: a,
      chore: store.chores.find((c) => c.id === a.choreId),
    })).filter((x): x is { assignment: typeof x.assignment; chore: Chore } => x.chore !== undefined)
  );
</script>

<div class="panel">
  <div class="panel-header">Chores</div>

  {#if assigningChoreId}
    <div class="assign-banner">
      Click a room on the map to assign this chore.
      <button onclick={onCancelAssign}>Cancel</button>
    </div>
  {/if}

  <!-- Import section (shown if no chores yet) -->
  {#if store.chores.length === 0}
    <div class="section">
      <div class="section-title">Import</div>
      {#if !showImportInput}
        <button class="primary-btn" onclick={() => { showImportInput = true; }}>
          Import from Donetick
        </button>
      {:else}
        <input
          type="password"
          placeholder="Donetick API token"
          bind:value={importToken}
          class="token-input"
        />
        <div class="row-btns">
          <button class="primary-btn" disabled={importStatus === "loading"} onclick={handleImport}>
            {importStatus === "loading" ? "Importing…" : "Import"}
          </button>
          <button onclick={() => { showImportInput = false; }}>Cancel</button>
        </div>
        {#if importStatus === "error"}
          <div class="error-msg">Import failed. Check your token.</div>
        {/if}
      {/if}
      {#if importStatus === "done"}
        <div class="success-msg">{importCount} chores imported.</div>
      {/if}
    </div>
  {/if}

  <!-- House-level chores -->
  {#if houseChores.length > 0}
    <div class="section">
      <div class="section-title">🏠 Whole house</div>
      {#each houseChores as { assignment, chore }}
        <div class="chore-row">
          <span class="chore-emoji">{chore.emoji}</span>
          <span class="chore-name">{chore.name}</span>
          <button class="done-btn" onclick={() => store.completeChore(chore.id)}>✓</button>
          <button class="icon-btn" onclick={() => store.deleteAssignment(assignment.id)}>✕</button>
        </div>
      {/each}
    </div>
  {/if}

  <!-- All chores list -->
  <div class="section chores-list">
    <div class="section-title">All chores ({store.chores.length})</div>
    {#each store.chores as chore (chore.id)}
      {@const pct = store.getProgress(chore)}
      {@const color = store.getColor(pct)}
      {#if editingId === chore.id}
        <div class="edit-form">
          <input class="edit-input" bind:value={editName} placeholder="Name"/>
          <input class="edit-input emoji-input" bind:value={editEmoji} placeholder="Emoji" maxlength="4"/>
          <label class="edit-label">Period (days)
            <input type="number" class="edit-input" bind:value={editPeriodDays} min="1"/>
          </label>
          <label class="edit-label">Next due
            <input type="date" class="edit-input" bind:value={editNextDue}/>
          </label>
          <div class="row-btns">
            <button class="primary-btn" onclick={handleUpdate}>Save</button>
            <button onclick={() => { editingId = null; }}>Cancel</button>
          </div>
        </div>
      {:else}
        <div class="chore-row" class:assigning={assigningChoreId === chore.id}>
          <!-- Mini ring badge -->
          <svg width="22" height="22" viewBox="-11 -11 22 22" style="flex-shrink:0">
            <circle r="9" fill="none" stroke="#3a3a3a" stroke-width="3"/>
            <circle r="9" fill="none" stroke={color} stroke-width="3"
              stroke-dasharray="{pct * 56.5} 56.5" stroke-linecap="round"
              transform="rotate(-90 0 0)"/>
            <text text-anchor="middle" dominant-baseline="central" font-size="8">{chore.emoji}</text>
          </svg>
          {@const daysLeft = Math.round((new Date(chore.nextDueDate).getTime() - Date.now()) / 86400000)}
          <div class="chore-info">
            <span class="chore-name">{chore.name}</span>
            <span class="chore-days" style="color:{color}">
              {daysLeft >= 0 ? `+${daysLeft}d` : `${daysLeft}d`}
            </span>
          </div>
          <div class="chore-actions">
            <button
              class="assign-btn"
              title="Assign to room"
              onclick={() => onAssignToRoom(chore.id)}
            >→</button>
            <button
              class="house-btn"
              title="Assign to whole house"
              onclick={() => store.createAssignment({ choreId: chore.id, roomId: null, position: null })}
            >🏠</button>
            <button class="icon-btn" title="Edit" onclick={() => startEdit(chore)}>✏️</button>
            <button class="icon-btn" title="Delete" onclick={() => store.deleteChore(chore.id)}>🗑️</button>
          </div>
        </div>
      {/if}
    {/each}
  </div>

  <!-- New chore form -->
  {#if showNewForm}
    <div class="section">
      <div class="section-title">New chore</div>
      <input class="edit-input" bind:value={newName} placeholder="Name (include emoji)"/>
      <input class="edit-input emoji-input" bind:value={newEmoji} placeholder="Emoji" maxlength="4"/>
      <label class="edit-label">Period (days)
        <input type="number" class="edit-input" bind:value={newPeriodDays} min="1"/>
      </label>
      <label class="edit-label">Next due
        <input type="date" class="edit-input" bind:value={newNextDue}/>
      </label>
      <div class="row-btns">
        <button class="primary-btn" onclick={handleCreate}>Add</button>
        <button onclick={() => { showNewForm = false; }}>Cancel</button>
      </div>
    </div>
  {:else}
    <button class="add-btn" onclick={() => { showNewForm = true; }}>＋ New chore</button>
  {/if}
</div>

<style>
  .panel {
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    width: 300px;
    background: #1e1e2e;
    border-left: 1px solid #333;
    overflow-y: auto;
    z-index: 10;
    display: flex;
    flex-direction: column;
    font-size: 12px;
    color: #ccc;
  }
  .panel-header {
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 600;
    color: #eee;
    border-bottom: 1px solid #333;
    background: #252535;
  }
  .assign-banner {
    background: #2a4a2a;
    padding: 8px 12px;
    color: #8f8;
    font-size: 11px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .section {
    padding: 8px 12px;
    border-bottom: 1px solid #2a2a3a;
  }
  .section-title {
    font-size: 10px;
    text-transform: uppercase;
    color: #666;
    margin-bottom: 6px;
    letter-spacing: 0.05em;
  }
  .chore-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 0;
  }
  .chore-row.assigning {
    background: #2a4a2a;
    border-radius: 4px;
    padding: 4px 4px;
  }
  .chore-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .chore-name {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 11px;
  }
  .chore-days {
    font-size: 10px;
  }
  .chore-emoji {
    font-size: 14px;
  }
  .chore-actions {
    display: flex;
    gap: 2px;
  }
  .chores-list {
    flex: 1;
  }
  button {
    padding: 3px 7px;
    border: none;
    border-radius: 3px;
    background: #3a3a5a;
    color: #ccc;
    cursor: pointer;
    font-size: 11px;
  }
  button:hover { background: #4a4a6a; }
  button:disabled { opacity: 0.5; cursor: default; }
  .primary-btn { background: #2a6; color: #fff; }
  .primary-btn:hover { background: #3b7; }
  .done-btn { color: #8f8; }
  .icon-btn { padding: 2px 4px; font-size: 10px; }
  .assign-btn { font-weight: bold; }
  .add-btn {
    margin: 8px 12px;
    display: block;
    width: calc(100% - 24px);
    padding: 6px;
    text-align: center;
    background: #2a2a4a;
    border: 1px dashed #444;
    color: #888;
    border-radius: 4px;
  }
  .add-btn:hover { background: #3a3a5a; color: #ccc; }
  .token-input, .edit-input {
    width: 100%;
    padding: 4px 6px;
    border: 1px solid #444;
    border-radius: 3px;
    background: #2a2a3a;
    color: #ccc;
    font-size: 11px;
    box-sizing: border-box;
    margin-bottom: 4px;
  }
  .emoji-input { width: 60px; }
  .edit-label {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-bottom: 4px;
    color: #888;
    font-size: 10px;
  }
  .row-btns { display: flex; gap: 6px; }
  .error-msg { color: #f44336; font-size: 11px; margin-top: 4px; }
  .success-msg { color: #4caf50; font-size: 11px; margin-top: 4px; }
</style>
```

- [ ] **Step 3: Verify TypeScript compiles cleanly**

```bash
cd /projects/myhome/packages/editor
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/BadgePopup.svelte packages/editor/src/lib/components/ChorePanel.svelte
git commit -m "feat: ChorePanel and BadgePopup components"
```

---

## Task 8: App.svelte integration

**Files:**
- Modify: `packages/editor/src/App.svelte`

Wire choreStore, ChoreOverlay, ChorePanel, and BadgePopup into `App.svelte`. Add the chore mode toggle button in the topbar.

- [ ] **Step 1: Add imports and new state to the `<script>` section of `App.svelte`**

At the top of `<script lang="ts">` in `packages/editor/src/App.svelte`, add after the existing imports:

```typescript
import { createChoreStore } from "./lib/choreStore.svelte";
import type { Assignment } from "./lib/choreStore.svelte";
import ChoreOverlay from "./lib/components/ChoreOverlay.svelte";
import ChorePanel from "./lib/components/ChorePanel.svelte";
import BadgePopup from "./lib/components/BadgePopup.svelte";

const choreStore = createChoreStore();

let choreMode = $state(false);
let assigningChoreId = $state<string | null>(null);
let selectedBadge = $state<{ assignment: Assignment; screenX: number; screenY: number } | null>(null);
```

- [ ] **Step 2: Add badge popup handler and assignment-mode room handler**

Add these functions inside the `<script>` section, after the existing `handleSelectRoom` function:

```typescript
function handleSelectRoomOrAssign(id: string | null): void {
  if (assigningChoreId && id) {
    // Find room centroid for default badge position
    const room = floorStore.floor.rooms.find((r) => r.id === id);
    let position = { x: 0, y: 0 };
    if (room?.polygon && room.polygon.length > 0) {
      const n = room.polygon.length;
      position = {
        x: room.polygon.reduce((s, p) => s + p.x, 0) / n,
        y: room.polygon.reduce((s, p) => s + p.y, 0) / n,
      };
    }
    choreStore.createAssignment({ choreId: assigningChoreId, roomId: id, position });
    assigningChoreId = null;
  } else {
    toolStore.selectRoom(id);
  }
}

function handleBadgeClick(assignmentId: string, e?: { clientX: number; clientY: number }): void {
  const assignment = choreStore.assignments.find((a) => a.id === assignmentId);
  if (!assignment) return;
  // Compute screen position of the badge from the assignment's world position
  let screenX = 0;
  let screenY = 0;
  if (assignment.position) {
    const sp = viewportStore.worldToScreen(assignment.position);
    screenX = sp.x;
    screenY = sp.y;
  }
  selectedBadge = { assignment, screenX, screenY };
}

function handleBadgeDragEnd(assignmentId: string, worldPos: { x: number; y: number }): void {
  choreStore.updateAssignmentPosition(assignmentId, worldPos);
}
```

Also update the existing `handleSelectRoom` to delegate to the new function:

```typescript
function handleSelectRoom(id: string | null): void {
  handleSelectRoomOrAssign(id);
}
```

And add Escape key handling for chore mode — in the existing `handleKeydown` function, add before the final `if` block:

```typescript
if (event.key === "Escape" && assigningChoreId) {
  assigningChoreId = null;
  return;
}
```

- [ ] **Step 3: Add Chores button to the topbar in the template**

In the `.topbar-actions` div (inside the `<div class="topbar-actions">` block), add the Chores toggle button before the Save button:

```svelte
<button
  class="chore-btn"
  class:chore-active={choreMode}
  onclick={() => { choreMode = !choreMode; if (!choreMode) { assigningChoreId = null; selectedBadge = null; } }}
>Chores</button>
```

- [ ] **Step 4: Add ChoreOverlay inside `.body` after the Canvas, and ChorePanel + BadgePopup conditionally**

The `.body` div has `position:relative` (add it to the CSS if not already present — the overlay uses `position:absolute`). Inside the `{:else}` block (after `{#if !floorStore.loaded}`), after the closing `{/if}` for `selectedRoom`, add:

```svelte
<ChoreOverlay
  chores={choreStore.chores}
  assignments={choreStore.assignments}
  viewport={viewportStore.viewport}
  {choreMode}
  width={canvasWidth}
  height={canvasHeight}
  onclick={(id) => handleBadgeClick(id)}
  ondragend={handleBadgeDragEnd}
/>

{#if choreMode}
  <ChorePanel
    store={choreStore}
    {assigningChoreId}
    onAssignToRoom={(id) => { assigningChoreId = id; selectedBadge = null; }}
    onCancelAssign={() => { assigningChoreId = null; }}
  />
{/if}

{#if selectedBadge}
  {@const chore = choreStore.chores.find((c) => c.id === selectedBadge!.assignment.choreId)}
  {#if chore}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div style="position:absolute;inset:0;z-index:50" onclick={() => { selectedBadge = null; }}>
      <BadgePopup
        {chore}
        assignment={selectedBadge.assignment}
        screenX={selectedBadge.screenX}
        screenY={selectedBadge.screenY}
        oncomplete={async () => { await choreStore.completeChore(chore.id); selectedBadge = null; }}
        onremove={async () => { await choreStore.deleteAssignment(selectedBadge!.assignment.id); selectedBadge = null; }}
        onclose={() => { selectedBadge = null; }}
      />
    </div>
  {/if}
{/if}
```

- [ ] **Step 5: Add chore-btn styles to `<style>` in App.svelte**

Inside the `<style>` block, add (also ensure `.body` has `position: relative`):

```css
.body {
  display: flex;
  flex: 1;
  overflow: hidden;
  position: relative;
}
.chore-btn {
  padding: 4px 10px;
  border: none;
  border-radius: 4px;
  background: #444;
  color: #ccc;
  cursor: pointer;
  font-size: 12px;
}
.chore-btn.chore-active {
  background: #446;
  color: #ccf;
}
```

- [ ] **Step 6: Hide Toolbar in chore mode**

In the template, the `<Toolbar .../>` block is inside the `{:else}` block. Wrap it in a conditional:

Change:
```svelte
<Toolbar
  tool={toolStore.state.tool}
  ...
/>
```

To:
```svelte
{#if !choreMode}
  <Toolbar
    tool={toolStore.state.tool}
    hasSelection={toolStore.state.selectedId !== null || toolStore.state.selectedOpeningId !== null}
    hasUndo={floorStore.hasUndo}
    hasRedo={floorStore.hasRedo}
    onselecttool={(tool) => toolStore.setTool(tool)}
    ondelete={handleDelete}
    onundo={handleUndo}
    onredo={handleRedo}
  />
{/if}
```

- [ ] **Step 7: Verify TypeScript compiles cleanly**

```bash
cd /projects/myhome/packages/editor
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 8: Run all frontend tests**

```bash
cd /projects/myhome/packages/editor
npm test
```

Expected: all tests PASSED (including choreStore tests; no regressions)

- [ ] **Step 9: Run all backend tests**

```bash
cd /projects/myhome/packages/backend
pytest -v
```

Expected: all tests PASSED

- [ ] **Step 10: Commit**

```bash
git add packages/editor/src/App.svelte
git commit -m "feat: wire chore tracker into App.svelte (chore mode, overlay, panel, popup)"
```

---

## Test count target

After all tasks:
- Backend: ≥ 18 existing + ~20 new chore tests ≈ **38+ pytest tests**
- Frontend: ≥ 85 existing + ~13 choreStore tests ≈ **98+ vitest tests**

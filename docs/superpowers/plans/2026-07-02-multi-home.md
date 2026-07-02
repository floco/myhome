# Multi-Home Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to create and switch between multiple homes, each with isolated data and a configurable set of enabled modules.

**Architecture:** Add a homes registry (`/data/homes.json`) and per-home subdirectories (`/data/homes/{id}/`). All backend module routes gain a `/{home_id}/` prefix; all persistence functions gain a `home_id` parameter. A singleton `homesStore` on the frontend drives module reload on home switch via a reactive `$effect` in App.svelte. A `HomesSwitcher` component lives at the top of the nav; module visibility is controlled by `enabledModules` in the active home.

**Tech Stack:** Python/FastAPI (backend), Svelte 5 runes + TypeScript (frontend), Vitest (frontend tests), Pytest (backend tests), JSON file persistence.

---

## File Map

### Backend — new files
- `packages/backend/src/myhome/models_homes.py` — `Home`, `HomeCreate`, `HomePatch`, `HomesDocument` pydantic models
- `packages/backend/src/myhome/persistence_homes.py` — homes CRUD, `migrate_legacy_if_needed()`
- `packages/backend/src/myhome/routes/homes.py` — `GET/POST /api/homes`, `PATCH/DELETE /api/homes/{id}`
- `packages/backend/tests/test_homes_persistence.py`
- `packages/backend/tests/test_homes.py`

### Backend — modified files
- `packages/backend/src/myhome/persistence.py` — `load_house(home_id)`, `save_house(home_id, doc)`
- `packages/backend/src/myhome/persistence_chores.py` — all functions gain `home_id: str`
- `packages/backend/src/myhome/persistence_costs.py` — same
- `packages/backend/src/myhome/persistence_inventory.py` — same
- `packages/backend/src/myhome/persistence_kb.py` — same
- `packages/backend/src/myhome/persistence_works.py` — same
- `packages/backend/src/myhome/persistence_consumables.py` — same
- `packages/backend/src/myhome/persistence_settings.py` — same
- `packages/backend/src/myhome/routes/house.py` — prefix `/api/homes/{home_id}/house`
- `packages/backend/src/myhome/routes/svg.py` — prefix `/api/homes/{home_id}/house/floors/{floor_id}/svg`
- `packages/backend/src/myhome/routes/chores.py` — prefix `/api/homes/{home_id}/...`
- `packages/backend/src/myhome/routes/costs.py` — same
- `packages/backend/src/myhome/routes/inventory.py` — same
- `packages/backend/src/myhome/routes/kb.py` — same
- `packages/backend/src/myhome/routes/works.py` — same
- `packages/backend/src/myhome/routes/consumables.py` — same
- `packages/backend/src/myhome/routes/settings.py` — same
- `packages/backend/src/myhome/main.py` — register homes router + call migration
- `packages/backend/tests/conftest.py` — add `home_id` fixture
- `packages/backend/tests/test_persistence.py` — update calls for home_id
- `packages/backend/tests/test_chores.py` — update URLs + add home_id fixture
- `packages/backend/tests/test_chore_persistence.py` — update calls
- `packages/backend/tests/test_settings.py` — update URLs
- `packages/backend/tests/test_settings_persistence.py` — update calls
- `packages/backend/tests/test_costs.py` — update URLs
- `packages/backend/tests/test_costs_persistence.py` — update calls
- `packages/backend/tests/test_inventory.py` — update URLs
- `packages/backend/tests/test_inventory_persistence.py` — update calls
- `packages/backend/tests/test_kb.py` — update URLs
- `packages/backend/tests/test_kb_persistence.py` — update calls
- `packages/backend/tests/test_works.py` — update URLs
- `packages/backend/tests/test_works_persistence.py` — update calls
- `packages/backend/tests/test_consumables.py` — update URLs
- `packages/backend/tests/test_consumables_persistence.py` — update calls
- `packages/backend/tests/test_routes.py` — update URLs

### Frontend — new files
- `packages/editor/src/lib/homesStore.svelte.ts` — singleton homes state + CRUD
- `packages/editor/src/lib/components/HomesSwitcher.svelte` — nav home picker
- `packages/editor/src/lib/components/NewHomeModal.svelte` — create home form
- `packages/editor/src/lib/components/PlaceholderPage.svelte` — "Coming soon" screen
- `packages/editor/test/homesStore.test.ts`

### Frontend — modified files
- `packages/editor/src/lib/houseStore.svelte.ts` — accept `getHomeId`; use in API calls
- `packages/editor/src/lib/choreStore.svelte.ts` — same
- `packages/editor/src/lib/costsStore.svelte.ts` — same
- `packages/editor/src/lib/inventoryStore.svelte.ts` — same
- `packages/editor/src/lib/kbStore.svelte.ts` — same
- `packages/editor/src/lib/worksStore.svelte.ts` — same
- `packages/editor/src/lib/consumableStore.svelte.ts` — same
- `packages/editor/src/lib/settingsStore.svelte.ts` — same
- `packages/editor/src/lib/components/NavMenu.svelte` — HomesSwitcher at top; filter by enabledModules; placeholder entries
- `packages/editor/src/lib/components/SettingsPage.svelte` — Home section + Modules section
- `packages/editor/src/App.svelte` — init homesStore; pass getHomeId to stores; $effect for reload; zero-homes screen; placeholder routes
- `packages/editor/test/App.test.ts` — stub new API URLs
- `packages/editor/test/App.routing.test.ts` — stub new API URLs
- `packages/editor/test/choreStore.test.ts` — pass getHomeId; update URL stubs
- `packages/editor/test/houseStore.test.ts` — same
- (and all other store tests that stub fetch)

---

## Task 1: Backend — homes models + persistence

**Files:**
- Create: `packages/backend/src/myhome/models_homes.py`
- Create: `packages/backend/src/myhome/persistence_homes.py`
- Create: `packages/backend/tests/test_homes_persistence.py`

- [ ] **Step 1: Write the failing persistence tests**

```python
# packages/backend/tests/test_homes_persistence.py
import shutil
import pytest
from myhome.models_homes import Home, HomesDocument
from myhome.persistence_homes import (
    load_homes,
    save_homes,
    create_home,
    patch_home,
    delete_home,
    migrate_legacy_if_needed,
)


def test_load_returns_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    doc = load_homes()
    assert doc.homes == []


def test_create_home_adds_to_registry_and_creates_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home = create_home("Rue des Lilas", "existing")
    assert home.name == "Rue des Lilas"
    assert home.type == "existing"
    assert "chores" in home.enabledModules
    assert (tmp_path / "homes" / home.id).is_dir()
    doc = load_homes()
    assert len(doc.homes) == 1
    assert doc.homes[0].id == home.id


def test_create_project_home_has_limited_modules(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home = create_home("Dream House", "project")
    assert "chores" not in home.enabledModules
    assert "works" in home.enabledModules
    assert "kb" in home.enabledModules
    assert "plan" in home.enabledModules


def test_patch_home_name(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home = create_home("Old Name", "existing")
    updated = patch_home(home.id, name="New Name", home_type=None, enabled_modules=None)
    assert updated is not None
    assert updated.name == "New Name"
    assert load_homes().homes[0].name == "New Name"


def test_patch_home_enabled_modules(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home = create_home("Test", "existing")
    updated = patch_home(home.id, name=None, home_type=None, enabled_modules=["home", "plan"])
    assert updated.enabledModules == ["home", "plan"]


def test_patch_home_returns_none_for_unknown_id(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    result = patch_home("nonexistent", name="X", home_type=None, enabled_modules=None)
    assert result is None


def test_delete_home_removes_from_registry_and_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home = create_home("Test", "existing")
    home_dir = tmp_path / "homes" / home.id
    assert home_dir.is_dir()
    result = delete_home(home.id)
    assert result is True
    assert not home_dir.exists()
    assert load_homes().homes == []


def test_delete_home_returns_false_for_unknown_id(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert delete_home("nonexistent") is False


def test_migrate_legacy_moves_files_and_creates_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "house.json").write_text('{"version":1,"house":{},"floors":[]}')
    (tmp_path / "chores.json").write_text('{"version":1,"chores":[],"assignments":[]}')
    migrate_legacy_if_needed()
    doc = load_homes()
    assert len(doc.homes) == 1
    assert doc.homes[0].id == "default"
    assert doc.homes[0].type == "existing"
    assert (tmp_path / "homes" / "default" / "house.json").exists()
    assert (tmp_path / "homes" / "default" / "chores.json").exists()
    assert not (tmp_path / "house.json").exists()


def test_migrate_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "house.json").write_text('{}')
    migrate_legacy_if_needed()
    migrate_legacy_if_needed()
    assert len(load_homes().homes) == 1


def test_migrate_does_nothing_when_no_legacy_files(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    migrate_legacy_if_needed()
    assert not (tmp_path / "homes.json").exists()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /projects/myhome && python -m pytest packages/backend/tests/test_homes_persistence.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'myhome.models_homes'`

- [ ] **Step 3: Create `models_homes.py`**

```python
# packages/backend/src/myhome/models_homes.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

ALL_MODULE_IDS: list[str] = [
    "home", "plan", "chores", "inventory", "consumables",
    "works", "kb", "costs",
    "locations", "properties", "budget", "visits", "contacts", "checklist",
]

DEFAULT_EXISTING_MODULES: list[str] = [
    "home", "plan", "chores", "inventory", "consumables", "works", "kb", "costs",
]

DEFAULT_PROJECT_MODULES: list[str] = ["home", "plan", "works", "kb"]


class Home(BaseModel):
    id: str
    name: str
    type: Literal["existing", "project"]
    enabledModules: list[str]
    createdAt: str


class HomeCreate(BaseModel):
    name: str
    type: Literal["existing", "project"]


class HomePatch(BaseModel):
    name: str | None = None
    type: Literal["existing", "project"] | None = None
    enabledModules: list[str] | None = None


class HomesDocument(BaseModel):
    version: int = 1
    homes: list[Home] = []
```

- [ ] **Step 4: Create `persistence_homes.py`**

```python
# packages/backend/src/myhome/persistence_homes.py
from __future__ import annotations

import json
import os
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .models_homes import (
    Home,
    HomesDocument,
    DEFAULT_EXISTING_MODULES,
    DEFAULT_PROJECT_MODULES,
)

_LEGACY_FILES = [
    "house.json", "chores.json", "costs.json", "inventory.json",
    "works.json", "kb.json", "consumables.json", "settings.json",
]
_LEGACY_ATTACHMENT_DIRS = [
    "chores-attachments", "costs-attachments", "inventory-attachments",
    "works-attachments", "kb-attachments",
]


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data"))


def _homes_file() -> Path:
    return _data_dir() / "homes.json"


def _home_dir(home_id: str) -> Path:
    return _data_dir() / "homes" / home_id


def load_homes() -> HomesDocument:
    path = _homes_file()
    if not path.exists():
        return HomesDocument()
    with path.open() as f:
        return HomesDocument.model_validate(json.load(f))


def save_homes(doc: HomesDocument) -> None:
    path = _homes_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def create_home(name: str, home_type: str) -> Home:
    modules = (
        DEFAULT_EXISTING_MODULES[:]
        if home_type == "existing"
        else DEFAULT_PROJECT_MODULES[:]
    )
    home = Home(
        id=secrets.token_hex(8),
        name=name,
        type=home_type,
        enabledModules=modules,
        createdAt=datetime.now(timezone.utc).isoformat(),
    )
    _home_dir(home.id).mkdir(parents=True, exist_ok=True)
    doc = load_homes()
    doc.homes.append(home)
    save_homes(doc)
    return home


def patch_home(
    home_id: str,
    name: str | None,
    home_type: str | None,
    enabled_modules: list[str] | None,
) -> Home | None:
    doc = load_homes()
    home = next((h for h in doc.homes if h.id == home_id), None)
    if home is None:
        return None
    if name is not None:
        home.name = name
    if home_type is not None:
        home.type = home_type
    if enabled_modules is not None:
        home.enabledModules = enabled_modules
    save_homes(doc)
    return home


def delete_home(home_id: str) -> bool:
    doc = load_homes()
    before = len(doc.homes)
    doc.homes = [h for h in doc.homes if h.id != home_id]
    if len(doc.homes) == before:
        return False
    save_homes(doc)
    home_dir = _home_dir(home_id)
    if home_dir.exists():
        shutil.rmtree(home_dir)
    return True


def migrate_legacy_if_needed() -> None:
    data_dir = _data_dir()
    if _homes_file().exists():
        return
    has_legacy = any((data_dir / f).exists() for f in _LEGACY_FILES)
    if not has_legacy:
        return
    default_id = "default"
    home_dir = _home_dir(default_id)
    home_dir.mkdir(parents=True, exist_ok=True)
    for fname in _LEGACY_FILES:
        src = data_dir / fname
        if src.exists():
            shutil.move(str(src), str(home_dir / fname))
    for dir_name in _LEGACY_ATTACHMENT_DIRS:
        src = data_dir / dir_name
        if src.exists():
            shutil.move(str(src), str(home_dir / dir_name))
    home = Home(
        id=default_id,
        name="My Home",
        type="existing",
        enabledModules=DEFAULT_EXISTING_MODULES[:],
        createdAt=datetime.now(timezone.utc).isoformat(),
    )
    save_homes(HomesDocument(homes=[home]))
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
cd /projects/myhome && python -m pytest packages/backend/tests/test_homes_persistence.py -v
```

Expected: all 10 tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/models_homes.py packages/backend/src/myhome/persistence_homes.py packages/backend/tests/test_homes_persistence.py
git commit -m "feat(backend): add homes models and persistence"
```

---

## Task 2: Backend — homes API routes

**Files:**
- Create: `packages/backend/src/myhome/routes/homes.py`
- Modify: `packages/backend/src/myhome/main.py`
- Create: `packages/backend/tests/test_homes.py`

- [ ] **Step 1: Write failing route tests**

```python
# packages/backend/tests/test_homes.py


def test_get_homes_returns_empty_list(client):
    resp = client.get("/api/homes")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_home_existing(client):
    resp = client.post("/api/homes", json={"name": "Rue des Lilas", "type": "existing"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Rue des Lilas"
    assert data["type"] == "existing"
    assert "chores" in data["enabledModules"]
    assert "id" in data
    assert "createdAt" in data


def test_create_home_project(client):
    resp = client.post("/api/homes", json={"name": "Dream Build", "type": "project"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "project"
    assert "chores" not in data["enabledModules"]
    assert "works" in data["enabledModules"]


def test_get_homes_lists_created_homes(client):
    client.post("/api/homes", json={"name": "A", "type": "existing"})
    client.post("/api/homes", json={"name": "B", "type": "project"})
    resp = client.get("/api/homes")
    assert resp.status_code == 200
    names = [h["name"] for h in resp.json()]
    assert "A" in names
    assert "B" in names


def test_patch_home_name(client):
    home_id = client.post("/api/homes", json={"name": "Old", "type": "existing"}).json()["id"]
    resp = client.patch(f"/api/homes/{home_id}", json={"name": "New"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


def test_patch_home_enabled_modules(client):
    home_id = client.post("/api/homes", json={"name": "Test", "type": "existing"}).json()["id"]
    resp = client.patch(f"/api/homes/{home_id}", json={"enabledModules": ["home", "plan"]})
    assert resp.status_code == 200
    assert resp.json()["enabledModules"] == ["home", "plan"]


def test_patch_home_returns_404_for_unknown(client):
    resp = client.patch("/api/homes/nonexistent", json={"name": "X"})
    assert resp.status_code == 404


def test_delete_home(client):
    home_id = client.post("/api/homes", json={"name": "Test", "type": "existing"}).json()["id"]
    resp = client.delete(f"/api/homes/{home_id}")
    assert resp.status_code == 204
    homes = client.get("/api/homes").json()
    assert all(h["id"] != home_id for h in homes)


def test_delete_home_returns_404_for_unknown(client):
    resp = client.delete("/api/homes/nonexistent")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /projects/myhome && python -m pytest packages/backend/tests/test_homes.py -v 2>&1 | head -20
```

Expected: `FAILED — 404 Not Found` (routes don't exist yet)

- [ ] **Step 3: Create `routes/homes.py`**

```python
# packages/backend/src/myhome/routes/homes.py
from fastapi import APIRouter, HTTPException

from ..models_homes import Home, HomeCreate, HomePatch
from ..persistence_homes import (
    load_homes,
    create_home,
    patch_home,
    delete_home,
)

router = APIRouter()


@router.get("/api/homes", response_model=list[Home])
def get_homes() -> list[Home]:
    return load_homes().homes


@router.post("/api/homes", response_model=Home, status_code=201)
def post_homes(body: HomeCreate) -> Home:
    return create_home(body.name, body.type)


@router.patch("/api/homes/{home_id}", response_model=Home)
def patch_home_route(home_id: str, body: HomePatch) -> Home:
    home = patch_home(home_id, body.name, body.type, body.enabledModules)
    if home is None:
        raise HTTPException(status_code=404)
    return home


@router.delete("/api/homes/{home_id}", status_code=204)
def delete_home_route(home_id: str) -> None:
    if not delete_home(home_id):
        raise HTTPException(status_code=404)
```

- [ ] **Step 4: Register homes router and call migration in `main.py`**

In `main.py`, add the import and router registration. Add the migration call after `_first_boot()`:

```python
# At the top, add to the existing imports line:
from .routes import auth, backup, chores, consumables, costs, ha, homes, house, inventory, kb, settings, svg, works

# After _first_boot() call (around line 44), add:
from .persistence_homes import migrate_legacy_if_needed
migrate_legacy_if_needed()

# In the Routers section, add:
app.include_router(homes.router)
```

- [ ] **Step 5: Run homes tests**

```bash
cd /projects/myhome && python -m pytest packages/backend/tests/test_homes.py -v
```

Expected: all 9 tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/routes/homes.py packages/backend/src/myhome/main.py packages/backend/tests/test_homes.py
git commit -m "feat(backend): add homes API routes and startup migration"
```

---

## Task 3: Backend — refactor persistence layer for home_id

All 8 persistence modules replace their `_data_dir()` path helper with a `_home_dir(home_id)` helper and add `home_id: str` to all public functions.

**Pattern (shown in full for `persistence.py`; apply identically to others):**

**Files:**
- Modify: `packages/backend/src/myhome/persistence.py`
- Modify: `packages/backend/src/myhome/persistence_chores.py`
- Modify: `packages/backend/src/myhome/persistence_costs.py`
- Modify: `packages/backend/src/myhome/persistence_inventory.py`
- Modify: `packages/backend/src/myhome/persistence_kb.py`
- Modify: `packages/backend/src/myhome/persistence_works.py`
- Modify: `packages/backend/src/myhome/persistence_consumables.py`
- Modify: `packages/backend/src/myhome/persistence_settings.py`
- Modify: `packages/backend/tests/conftest.py`
- Modify: `packages/backend/tests/test_persistence.py`
- Modify: `packages/backend/tests/test_settings_persistence.py`
- Modify: `packages/backend/tests/test_chore_persistence.py`
- Modify: `packages/backend/tests/test_costs_persistence.py`
- Modify: `packages/backend/tests/test_inventory_persistence.py`
- Modify: `packages/backend/tests/test_kb_persistence.py`
- Modify: `packages/backend/tests/test_works_persistence.py`
- Modify: `packages/backend/tests/test_consumables_persistence.py`

- [ ] **Step 1: Refactor `persistence.py`**

Replace the entire file:

```python
# packages/backend/src/myhome/persistence.py
import json
import os
from pathlib import Path

from .models import HouseDocument


def _home_dir(home_id: str) -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "homes" / home_id


def _house_file(home_id: str) -> Path:
    return _home_dir(home_id) / "house.json"


def load_house(home_id: str) -> HouseDocument | None:
    path = _house_file(home_id)
    if not path.exists():
        return None
    with path.open() as f:
        return HouseDocument.model_validate(json.load(f))


def save_house(home_id: str, doc: HouseDocument) -> None:
    path = _house_file(home_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)
```

- [ ] **Step 2: Refactor `persistence_settings.py`**

Replace the path helper and all function signatures:

```python
# packages/backend/src/myhome/persistence_settings.py
import json
import os
from pathlib import Path

from .models_settings import (
    SettingsDocument,
    _default_cost_categories,
    _default_consumable_units,
    _default_inventory_categories,
    _default_work_categories,
)


def _home_dir(home_id: str) -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "homes" / home_id


def _settings_file(home_id: str) -> Path:
    return _home_dir(home_id) / "settings.json"


def load_settings(home_id: str) -> SettingsDocument:
    path = _settings_file(home_id)
    if not path.exists():
        return SettingsDocument(
            costCategories=_default_cost_categories(),
            inventoryCategories=_default_inventory_categories(),
            workCategories=_default_work_categories(),
            consumableUnits=_default_consumable_units(),
        )
    with path.open() as f:
        doc = SettingsDocument.model_validate(json.load(f))
    if not doc.consumableUnits:
        doc.consumableUnits = _default_consumable_units()
    return doc


def save_settings(home_id: str, doc: SettingsDocument) -> None:
    path = _settings_file(home_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)
```

- [ ] **Step 3: Apply the same pattern to the remaining 6 persistence files**

For each file below, replace the `_data_dir()` helper with `_home_dir(home_id: str) -> Path` and add `home_id: str` as the first parameter to every public function. File paths change from `data_dir / "chores.json"` to `_home_dir(home_id) / "chores.json"`, and attachment dirs similarly move inside the home dir.

Files to update and their key data paths:
- `persistence_chores.py`: `_chores_file(home_id)` → `_home_dir(home_id) / "chores.json"` ; `_attachments_dir(home_id, chore_id)` → `_home_dir(home_id) / "chores-attachments" / chore_id` ; add `home_id: str` to `load_chores`, `save_chores`, `save_attachment`, `delete_attachment`, `delete_all_attachments`, `generate_pdf_thumbnail`
- `persistence_costs.py`: same pattern, file `"costs.json"`, attachments `"costs-attachments/{entry_id}"`
- `persistence_inventory.py`: file `"inventory.json"`, attachments `"inventory-attachments/{item_id}"`
- `persistence_kb.py`: file `"kb.json"`, attachments `"kb-attachments/{article_id}"`
- `persistence_works.py`: file `"works.json"`, attachments `"works-attachments/{work_id}"`
- `persistence_consumables.py`: file `"consumables.json"` (no attachments)

For each function that previously called `path.parent.mkdir(parents=True, exist_ok=True)`, keep that call — it still creates the home subdirectory on first write.

- [ ] **Step 4: Update `conftest.py` to add `home_id` fixture**

Add after the `client` fixture (around line 30):

```python
@pytest.fixture()
def home_id(client) -> str:
    resp = client.post("/api/homes", json={"name": "Test Home", "type": "existing"})
    assert resp.status_code == 201
    return resp.json()["id"]
```

- [ ] **Step 5: Update `test_persistence.py`**

Every call to `load_house()` / `save_house(doc)` gains a `home_id` string. The test must create the home directory first. Since these are direct persistence function tests (no HTTP client), create the dir manually:

```python
# test_persistence.py — show the updated pattern for every test
from myhome.persistence import load_house, save_house
from myhome.models import HouseDocument, House

HOME_ID = "test-home"


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)


def test_load_house_returns_none_when_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert load_house(HOME_ID) is None


def test_save_and_load_house(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = HouseDocument(house=House(name="Test"), floors=[])
    save_house(HOME_ID, doc)
    loaded = load_house(HOME_ID)
    assert loaded is not None
    assert loaded.house.name == "Test"
```

Apply the same `HOME_ID = "test-home"` + `_setup()` helper pattern to all persistence test files (`test_settings_persistence.py`, `test_chore_persistence.py`, `test_costs_persistence.py`, `test_inventory_persistence.py`, `test_kb_persistence.py`, `test_works_persistence.py`, `test_consumables_persistence.py`). In each, pass `HOME_ID` as the first argument to all persistence function calls.

- [ ] **Step 6: Run all backend persistence tests**

```bash
cd /projects/myhome && python -m pytest packages/backend/tests/ -k "persistence" -v
```

Expected: all persistence tests PASS (route tests will still fail — that's Task 4)

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/persistence.py \
        packages/backend/src/myhome/persistence_settings.py \
        packages/backend/src/myhome/persistence_chores.py \
        packages/backend/src/myhome/persistence_costs.py \
        packages/backend/src/myhome/persistence_inventory.py \
        packages/backend/src/myhome/persistence_kb.py \
        packages/backend/src/myhome/persistence_works.py \
        packages/backend/src/myhome/persistence_consumables.py \
        packages/backend/tests/conftest.py \
        packages/backend/tests/test_persistence.py \
        packages/backend/tests/test_settings_persistence.py \
        packages/backend/tests/test_chore_persistence.py \
        packages/backend/tests/test_costs_persistence.py \
        packages/backend/tests/test_inventory_persistence.py \
        packages/backend/tests/test_kb_persistence.py \
        packages/backend/tests/test_works_persistence.py \
        packages/backend/tests/test_consumables_persistence.py
git commit -m "refactor(backend): add home_id to all persistence functions"
```

---

## Task 4: Backend — refactor module routes for home_id prefix

All module routes get a `home_id: str` path parameter and the `/api/homes/{home_id}/` prefix. They pass `home_id` through to persistence calls.

**Files:**
- Modify: `packages/backend/src/myhome/routes/house.py`
- Modify: `packages/backend/src/myhome/routes/svg.py`
- Modify: `packages/backend/src/myhome/routes/chores.py`
- Modify: `packages/backend/src/myhome/routes/costs.py`
- Modify: `packages/backend/src/myhome/routes/inventory.py`
- Modify: `packages/backend/src/myhome/routes/kb.py`
- Modify: `packages/backend/src/myhome/routes/works.py`
- Modify: `packages/backend/src/myhome/routes/consumables.py`
- Modify: `packages/backend/src/myhome/routes/settings.py`
- Modify: `packages/backend/tests/test_routes.py`
- Modify: `packages/backend/tests/test_chores.py`
- Modify: `packages/backend/tests/test_settings.py`
- Modify: `packages/backend/tests/test_costs.py`
- Modify: `packages/backend/tests/test_inventory.py`
- Modify: `packages/backend/tests/test_kb.py`
- Modify: `packages/backend/tests/test_works.py`
- Modify: `packages/backend/tests/test_consumables.py`

- [ ] **Step 1: Refactor `routes/house.py`**

```python
# packages/backend/src/myhome/routes/house.py
from fastapi import APIRouter, HTTPException
from ..models import HouseDocument
from ..persistence import load_house, save_house

router = APIRouter()


@router.get("/api/homes/{home_id}/house", response_model=HouseDocument)
def get_house(home_id: str) -> HouseDocument:
    doc = load_house(home_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="No house document found")
    return doc


@router.put("/api/homes/{home_id}/house", status_code=204)
def put_house(home_id: str, doc: HouseDocument) -> None:
    save_house(home_id, doc)
```

- [ ] **Step 2: Refactor `routes/svg.py`**

```python
# packages/backend/src/myhome/routes/svg.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from ..persistence import load_house
from ..svg_render import render_floor_svg

router = APIRouter()


@router.get("/api/homes/{home_id}/house/floors/{floor_id}/svg")
def get_floor_svg(home_id: str, floor_id: str) -> Response:
    doc = load_house(home_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="No house document found")
    floor = next((f for f in doc.floors if f.id == floor_id), None)
    if floor is None:
        raise HTTPException(status_code=404, detail="Floor not found")
    return Response(content=render_floor_svg(floor), media_type="image/svg+xml")
```

- [ ] **Step 3: Refactor `routes/settings.py`**

Add `home_id: str` path parameter to all routes and prefix them with `/api/homes/{home_id}`. Pass `home_id` to all `load_settings(home_id)` and `save_settings(home_id, doc)` calls.

The route prefix changes from `/api/settings` to `/api/homes/{home_id}/settings`. Every route handler adds `home_id: str` as first parameter. Example for the first two handlers:

```python
@router.get("/api/homes/{home_id}/settings", response_model=SettingsDocument)
def get_settings(home_id: str) -> SettingsDocument:
    return load_settings(home_id)


@router.put("/api/homes/{home_id}/settings/cost-categories", status_code=204)
def put_cost_categories(home_id: str, body: list[CostCategory]) -> None:
    doc = load_settings(home_id)
    doc.costCategories = body
    save_settings(home_id, doc)
```

Apply the same `home_id: str` parameter + path prefix + persistence call update to every handler in `settings.py`. The full list of routes in the file: `GET /settings`, `PUT /settings/cost-categories`, `PUT /settings/inventory-categories`, `PUT /settings/cost-categories/{id}/placement`, `DELETE /settings/cost-categories/{id}/placement`, `PUT /settings/work-categories`, `PUT /settings/suppliers`, `PUT /settings/consumable-units`, `PUT /settings/consumable-categories`.

- [ ] **Step 4: Refactor `routes/chores.py`, `routes/costs.py`, `routes/inventory.py`, `routes/kb.py`, `routes/works.py`, `routes/consumables.py`**

Apply the same transformation to all remaining route files:
1. Change every route path from `/api/<module>/...` to `/api/homes/{home_id}/<module>/...`
2. Add `home_id: str` as the first parameter of every route handler
3. Pass `home_id` as first arg to every persistence call (e.g., `load_chores(home_id)`, `save_chores(home_id, doc)`, `_attachments_dir(home_id, chore_id)`)

- [ ] **Step 5: Update route tests — add `home_id` fixture and update URLs**

In every route test file, add `home_id` to the fixture list of tests that hit module endpoints, and prefix all URLs with `/api/homes/{home_id}`.

Pattern shown for `test_settings.py`:

```python
# Before:
def test_get_settings_returns_defaults_when_no_file(client):
    resp = client.get("/api/settings")

# After:
def test_get_settings_returns_defaults_when_no_file(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/settings")
```

Apply this transformation to every test function in:
- `test_settings.py` — change `/api/settings` → `/api/homes/{home_id}/settings`
- `test_chores.py` — change `/api/chores` → `/api/homes/{home_id}/chores`, `/api/assignments` → `/api/homes/{home_id}/assignments`, `/api/completions` → `/api/homes/{home_id}/completions`
- `test_costs.py` — change `/api/costs` → `/api/homes/{home_id}/costs`
- `test_inventory.py` — change `/api/inventory` → `/api/homes/{home_id}/inventory`
- `test_kb.py` — change `/api/kb` → `/api/homes/{home_id}/kb`
- `test_works.py` — change `/api/works` → `/api/homes/{home_id}/works`
- `test_consumables.py` — change `/api/consumables` → `/api/homes/{home_id}/consumables`
- `test_routes.py` — update any module URLs present

Also add the helper to the chores file since it has an internal helper that builds URLs:

```python
# test_chores.py — update _chore_id helper
def _chore_id(client, home_id: str) -> str:
    resp = client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep", "emoji": "🧹", "periodDays": 7, "nextDueDate": "2027-01-01T00:00:00Z",
    })
    return resp.json()["id"]
```

- [ ] **Step 6: Run all backend tests**

```bash
cd /projects/myhome && python -m pytest packages/backend/tests/ -v --tb=short 2>&1 | tail -30
```

Expected: all tests PASS (backup, auth, HA, svg render tests are not affected)

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/routes/ packages/backend/tests/
git commit -m "refactor(backend): prefix all module routes with /api/homes/{home_id}"
```

---

## Task 5: Frontend — homesStore singleton

**Files:**
- Create: `packages/editor/src/lib/homesStore.svelte.ts`
- Create: `packages/editor/test/homesStore.test.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// packages/editor/test/homesStore.test.ts
import { describe, it, expect, afterEach, vi } from "vitest";
import { homesStore } from "../src/lib/homesStore.svelte";

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

afterEach(() => {
  vi.unstubAllGlobals();
  // Reset singleton state between tests
  homesStore._reset();
});

describe("homesStore — loadHomes", () => {
  it("starts with empty homes and null activeHomeId", () => {
    expect(homesStore.homes).toEqual([]);
    expect(homesStore.activeHomeId).toBeNull();
    expect(homesStore.loaded).toBe(false);
  });

  it("loads homes and sets activeHomeId to first home", async () => {
    const homes = [
      { id: "h1", name: "Rue des Lilas", type: "existing", enabledModules: ["home", "plan"], createdAt: "2026-01-01T00:00:00Z" },
      { id: "h2", name: "Dream Build", type: "project", enabledModules: ["home", "plan", "works"], createdAt: "2026-01-02T00:00:00Z" },
    ];
    vi.stubGlobal("fetch", makeFetch(200, homes));
    await homesStore.loadHomes();
    expect(homesStore.homes.length).toBe(2);
    expect(homesStore.activeHomeId).toBe("h1");
    expect(homesStore.loaded).toBe(true);
  });

  it("sets loaded=true and empty homes on empty list", async () => {
    vi.stubGlobal("fetch", makeFetch(200, []));
    await homesStore.loadHomes();
    expect(homesStore.homes).toEqual([]);
    expect(homesStore.activeHomeId).toBeNull();
    expect(homesStore.loaded).toBe(true);
  });
});

describe("homesStore — setActiveHomeId", () => {
  it("switches active home", async () => {
    const homes = [
      { id: "h1", name: "A", type: "existing", enabledModules: [], createdAt: "" },
      { id: "h2", name: "B", type: "existing", enabledModules: [], createdAt: "" },
    ];
    vi.stubGlobal("fetch", makeFetch(200, homes));
    await homesStore.loadHomes();
    homesStore.setActiveHomeId("h2");
    expect(homesStore.activeHomeId).toBe("h2");
  });
});

describe("homesStore — createHome", () => {
  it("posts to /api/homes and adds home to list", async () => {
    const newHome = { id: "h-new", name: "Villa", type: "existing", enabledModules: ["home"], createdAt: "" };
    vi.stubGlobal("fetch", makeFetch(201, newHome));
    await homesStore.createHome("Villa", "existing");
    expect(homesStore.homes.length).toBe(1);
    expect(homesStore.activeHomeId).toBe("h-new");
  });
});

describe("homesStore — patchHome", () => {
  it("patches and updates local homes list", async () => {
    const home = { id: "h1", name: "Old", type: "existing", enabledModules: ["home"], createdAt: "" };
    vi.stubGlobal("fetch", makeFetch(200, { ...home, name: "New" }));
    homesStore.homes.push(home);
    await homesStore.patchHome("h1", { name: "New" });
    expect(homesStore.homes[0].name).toBe("New");
  });
});

describe("homesStore — deleteHome", () => {
  it("deletes home and switches to first remaining", async () => {
    vi.stubGlobal("fetch", makeFetch(204));
    const h1 = { id: "h1", name: "A", type: "existing" as const, enabledModules: [], createdAt: "" };
    const h2 = { id: "h2", name: "B", type: "existing" as const, enabledModules: [], createdAt: "" };
    homesStore.homes.push(h1, h2);
    homesStore.setActiveHomeId("h1");
    await homesStore.deleteHome("h1");
    expect(homesStore.homes.length).toBe(1);
    expect(homesStore.activeHomeId).toBe("h2");
  });
});

describe("homesStore — activeHome", () => {
  it("returns the active home object", async () => {
    const home = { id: "h1", name: "Test", type: "existing" as const, enabledModules: ["home"], createdAt: "" };
    vi.stubGlobal("fetch", makeFetch(200, [home]));
    await homesStore.loadHomes();
    expect(homesStore.activeHome?.name).toBe("Test");
  });
});
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /projects/myhome && npx vitest run packages/editor/test/homesStore.test.ts 2>&1 | head -20
```

Expected: `Cannot find module '../src/lib/homesStore.svelte'`

- [ ] **Step 3: Create `homesStore.svelte.ts`**

```typescript
// packages/editor/src/lib/homesStore.svelte.ts

export interface Home {
  id: string;
  name: string;
  type: "existing" | "project";
  enabledModules: string[];
  createdAt: string;
}

const homes = $state<Home[]>([]);
let activeHomeId = $state<string | null>(null);
let loaded = $state(false);

async function loadHomes(): Promise<void> {
  const resp = await fetch("/api/homes");
  if (!resp.ok) return;
  const data: Home[] = await resp.json();
  homes.length = 0;
  for (const h of data) homes.push(h);
  loaded = true;
  if (activeHomeId === null && homes.length > 0) {
    activeHomeId = homes[0].id;
  }
}

async function createHome(name: string, type: "existing" | "project"): Promise<Home> {
  const resp = await fetch("/api/homes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, type }),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const home: Home = await resp.json();
  homes.push(home);
  activeHomeId = home.id;
  return home;
}

async function patchHome(
  id: string,
  patch: { name?: string; type?: "existing" | "project"; enabledModules?: string[] },
): Promise<void> {
  const resp = await fetch(`/api/homes/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const updated: Home = await resp.json();
  const idx = homes.findIndex((h) => h.id === id);
  if (idx >= 0) homes[idx] = updated;
}

async function deleteHome(id: string): Promise<void> {
  const resp = await fetch(`/api/homes/${id}`, { method: "DELETE" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const idx = homes.findIndex((h) => h.id === id);
  if (idx >= 0) homes.splice(idx, 1);
  if (activeHomeId === id) {
    activeHomeId = homes[0]?.id ?? null;
  }
}

function setActiveHomeId(id: string): void {
  activeHomeId = id;
}

function _reset(): void {
  homes.length = 0;
  activeHomeId = null;
  loaded = false;
}

export const homesStore = {
  get homes() { return homes; },
  get activeHomeId() { return activeHomeId; },
  get activeHome() { return homes.find((h) => h.id === activeHomeId) ?? null; },
  get loaded() { return loaded; },
  loadHomes,
  createHome,
  patchHome,
  deleteHome,
  setActiveHomeId,
  _reset,
};
```

- [ ] **Step 4: Run tests**

```bash
cd /projects/myhome && npx vitest run packages/editor/test/homesStore.test.ts
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/homesStore.svelte.ts packages/editor/test/homesStore.test.ts
git commit -m "feat(frontend): add homesStore singleton"
```

---

## Task 6: Frontend — HomesSwitcher, NewHomeModal, PlaceholderPage components

**Files:**
- Create: `packages/editor/src/lib/components/HomesSwitcher.svelte`
- Create: `packages/editor/src/lib/components/NewHomeModal.svelte`
- Create: `packages/editor/src/lib/components/PlaceholderPage.svelte`

- [ ] **Step 1: Create `PlaceholderPage.svelte`**

```svelte
<!-- packages/editor/src/lib/components/PlaceholderPage.svelte -->
<script lang="ts">
  interface Props {
    icon: string;
    label: string;
    description: string;
  }
  let { icon, label, description }: Props = $props();
</script>

<div class="placeholder">
  <div class="icon">{icon}</div>
  <h2 class="label">{label}</h2>
  <p class="desc">{description}</p>
  <span class="badge">Coming soon</span>
</div>

<style>
  .placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 12px;
    color: var(--text-muted);
    padding: 40px;
    text-align: center;
  }
  .icon { font-size: 48px; line-height: 1; }
  .label { font-size: 20px; font-weight: 600; color: var(--text); margin: 0; }
  .desc { font-size: 14px; max-width: 360px; margin: 0; }
  .badge {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 3px 10px;
    border-radius: var(--radius-pill);
    background: var(--surface-hover);
    color: var(--text-muted);
  }
</style>
```

- [ ] **Step 2: Create `NewHomeModal.svelte`**

```svelte
<!-- packages/editor/src/lib/components/NewHomeModal.svelte -->
<script lang="ts">
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";
  import { homesStore } from "../homesStore.svelte";

  interface Props {
    open: boolean;
    onclose: () => void;
    /** If true, hides the cancel button (zero-homes first-time flow) */
    required?: boolean;
  }
  let { open, onclose, required = false }: Props = $props();

  let name = $state("");
  let type = $state<"existing" | "project">("existing");
  let saving = $state(false);
  let error = $state<string | null>(null);

  async function submit(): Promise<void> {
    if (!name.trim()) { error = "Name is required"; return; }
    saving = true;
    error = null;
    try {
      await homesStore.createHome(name.trim(), type);
      name = "";
      type = "existing";
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to create home";
    } finally {
      saving = false;
    }
  }
</script>

<Modal {open} title="New home" onclose={required ? undefined : onclose}>
  <div class="form">
    <Input label="Name" bind:value={name} placeholder="Rue des Lilas" />

    <fieldset class="type-group">
      <legend>Type</legend>
      <label class="type-option" class:selected={type === "existing"}>
        <input type="radio" bind:group={type} value="existing" />
        <span class="type-icon">🏠</span>
        <span class="type-body">
          <strong>Existing home</strong>
          <small>A property you already own or live in — full module set.</small>
        </span>
      </label>
      <label class="type-option" class:selected={type === "project"}>
        <input type="radio" bind:group={type} value="project" />
        <span class="type-icon">🏗</span>
        <span class="type-body">
          <strong>Project home</strong>
          <small>Scouting locations, searching for land, or managing a build.</small>
        </span>
      </label>
    </fieldset>

    {#if error}
      <p class="error">{error}</p>
    {/if}
  </div>

  {#snippet actions()}
    {#if !required}
      <Button variant="ghost" onclick={onclose} disabled={saving}>Cancel</Button>
    {/if}
    <Button onclick={submit} disabled={saving || !name.trim()}>
      {saving ? "Creating…" : "Create home"}
    </Button>
  {/snippet}
</Modal>

<style>
  .form { display: flex; flex-direction: column; gap: 16px; }

  .type-group {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 4px 8px 8px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .type-group legend { font-size: 12px; color: var(--text-muted); padding: 0 4px; }

  .type-option {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 10px;
    border-radius: var(--radius);
    cursor: pointer;
    border: 1px solid transparent;
  }
  .type-option:hover { background: var(--surface-hover); }
  .type-option.selected { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 10%, transparent); }
  .type-option input[type="radio"] { position: absolute; opacity: 0; }

  .type-icon { font-size: 20px; flex-shrink: 0; margin-top: 2px; }
  .type-body { display: flex; flex-direction: column; gap: 2px; }
  .type-body strong { font-size: 13px; font-weight: 600; color: var(--text); }
  .type-body small { font-size: 12px; color: var(--text-muted); }

  .error { color: var(--danger, #c0392b); font-size: 13px; margin: 0; }
</style>
```

- [ ] **Step 3: Create `HomesSwitcher.svelte`**

```svelte
<!-- packages/editor/src/lib/components/HomesSwitcher.svelte -->
<script lang="ts">
  import { homesStore } from "../homesStore.svelte";
  import NewHomeModal from "./NewHomeModal.svelte";

  interface Props {
    expanded: boolean;
  }
  let { expanded }: Props = $props();

  let dropdownOpen = $state(false);
  let showNewModal = $state(false);

  function selectHome(id: string): void {
    homesStore.setActiveHomeId(id);
    dropdownOpen = false;
  }

  function typeIcon(type: string): string {
    return type === "project" ? "🏗" : "🏠";
  }
</script>

<div class="switcher" class:expanded>
  <button
    class="current"
    onclick={() => { dropdownOpen = !dropdownOpen; }}
    title={homesStore.activeHome?.name ?? "Select home"}
  >
    <span class="icon">{typeIcon(homesStore.activeHome?.type ?? "existing")}</span>
    {#if expanded}
      <span class="name">{homesStore.activeHome?.name ?? "—"}</span>
      <span class="chevron">{dropdownOpen ? "▲" : "▼"}</span>
    {/if}
  </button>

  {#if dropdownOpen && expanded}
    <div class="dropdown">
      {#each homesStore.homes as home (home.id)}
        <button
          class="home-item"
          class:active={home.id === homesStore.activeHomeId}
          onclick={() => selectHome(home.id)}
        >
          <span class="icon">{typeIcon(home.type)}</span>
          <span class="home-name">{home.name}</span>
        </button>
      {/each}
      <hr class="separator" />
      <button class="home-item add" onclick={() => { dropdownOpen = false; showNewModal = true; }}>
        <span class="icon">＋</span>
        <span class="home-name">New home</span>
      </button>
    </div>
  {/if}
</div>

<NewHomeModal open={showNewModal} onclose={() => { showNewModal = false; }} />

<style>
  .switcher { position: relative; padding: 6px 6px 4px; border-bottom: 1px solid var(--border); }

  .current {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 6px 8px;
    border: none;
    background: none;
    border-radius: var(--radius);
    cursor: pointer;
    color: var(--text);
    min-width: 0;
  }
  .current:hover { background: var(--surface-hover); }

  .icon { font-size: 16px; width: 20px; text-align: center; flex-shrink: 0; }
  .name { font-size: 12px; font-weight: 600; flex: 1; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .chevron { font-size: 10px; color: var(--text-muted); flex-shrink: 0; }

  .dropdown {
    position: absolute;
    top: calc(100% + 2px);
    left: 6px;
    right: 6px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 100;
    padding: 4px;
  }

  .home-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 8px 10px;
    border: none;
    background: none;
    border-radius: var(--radius);
    cursor: pointer;
    color: var(--text);
    font-size: 13px;
    text-align: left;
  }
  .home-item:hover { background: var(--surface-hover); }
  .home-item.active { background: var(--accent); color: var(--accent-contrast); }
  .home-item.add { color: var(--text-muted); }

  .separator { border: none; border-top: 1px solid var(--border); margin: 4px 0; }
</style>
```

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/PlaceholderPage.svelte \
        packages/editor/src/lib/components/NewHomeModal.svelte \
        packages/editor/src/lib/components/HomesSwitcher.svelte
git commit -m "feat(frontend): add HomesSwitcher, NewHomeModal, PlaceholderPage components"
```

---

## Task 7: Frontend — refactor all module stores for homeId

Each store factory gains a `getHomeId: () => string | null` parameter. The `init()` function reads `getHomeId()` and bails if null. All API URLs use `getHomeId()`. A public `reload()` method re-runs `init()`. The auto-call at the bottom of the factory remains — it will bail out when `getHomeId()` returns null (which it does until App.svelte's effect fires).

**Files:**
- Modify: `packages/editor/src/lib/houseStore.svelte.ts`
- Modify: `packages/editor/src/lib/choreStore.svelte.ts`
- Modify: `packages/editor/src/lib/costsStore.svelte.ts`
- Modify: `packages/editor/src/lib/inventoryStore.svelte.ts`
- Modify: `packages/editor/src/lib/kbStore.svelte.ts`
- Modify: `packages/editor/src/lib/worksStore.svelte.ts`
- Modify: `packages/editor/src/lib/consumableStore.svelte.ts`
- Modify: `packages/editor/src/lib/settingsStore.svelte.ts`
- Modify: `packages/editor/test/choreStore.test.ts`
- Modify: `packages/editor/test/houseStore.test.ts`
- (and any other store tests that currently stub `/api/...` URLs)

- [ ] **Step 1: Refactor `houseStore.svelte.ts`**

Change the factory signature and `init()` to use `getHomeId`:

```typescript
// In houseStore.svelte.ts — change factory signature:
export function createHouseStore(getHomeId: () => string | null = () => null) {
  // ... existing state ...

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) return;
    try {
      const resp = await fetch(`/api/homes/${homeId}/house`);
      // ... rest of init unchanged, except any other /api/house → /api/homes/${homeId}/house
    }
  }

  async function save(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) return;
    const resp = await fetch(`/api/homes/${homeId}/house`, {
      method: "PUT",
      // ...
    });
  }

  // At the bottom of the factory, keep: init();
  // Add to return object:
  return {
    // ... existing exports ...
    reload: init,
  };
}
```

Change the only two `fetch` calls in `houseStore.svelte.ts`:
- `fetch("/api/house")` → `` fetch(`/api/homes/${homeId}/house`) ``
- `fetch("/api/house", { method: "PUT", ... })` → `` fetch(`/api/homes/${homeId}/house`, ...) ``

- [ ] **Step 2: Refactor `choreStore.svelte.ts`**

```typescript
export function createChoreStore(getHomeId: () => string | null = () => null) {
  // ... existing state ...

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) return;
    try {
      const resp = await fetch(`/api/homes/${homeId}/chores`);
      // ...
    }
  }
  // ... all other fetch calls gain the homeId prefix ...
  // e.g.:
  //   /api/chores      → /api/homes/${homeId}/chores
  //   /api/chores/${id} → /api/homes/${homeId}/chores/${id}
  //   /api/assignments  → /api/homes/${homeId}/assignments
  //   /api/completions/${id} → /api/homes/${homeId}/completions/${id}
  // All these functions need to get homeId at the top: const homeId = getHomeId(); if (!homeId) return;

  return { /* existing exports */ reload: init };
}
```

- [ ] **Step 3: Apply same pattern to the remaining 6 stores**

For each store, make these changes:
1. Change factory signature: `export function createXxxStore(getHomeId: () => string | null = () => null)`
2. In `init()`: add `const homeId = getHomeId(); if (!homeId) return;` at the top
3. In every other async function that calls `fetch`: add the same `homeId` guard and prefix all `/api/<module>` URLs with `/api/homes/${homeId}`
4. Add `reload: init` to the return object

Stores and their URL prefixes:
- `costsStore.svelte.ts`: `/api/costs` → `/api/homes/${homeId}/costs`
- `inventoryStore.svelte.ts`: `/api/inventory` → `/api/homes/${homeId}/inventory`
- `kbStore.svelte.ts`: `/api/kb` → `/api/homes/${homeId}/kb`
- `worksStore.svelte.ts`: `/api/works` → `/api/homes/${homeId}/works`
- `consumableStore.svelte.ts`: `/api/consumables` → `/api/homes/${homeId}/consumables`
- `settingsStore.svelte.ts`: `/api/settings` → `/api/homes/${homeId}/settings`

- [ ] **Step 4: Update store tests**

All store tests that stub `fetch` need:
1. Pass `() => "home-123"` to the store factory
2. Update stubbed URL keys from `/api/chores` to `/api/homes/home-123/chores`

Pattern for `choreStore.test.ts`:

```typescript
// Before:
const store = createChoreStore();

// After:
const HOME_ID = "home-123";
const store = createChoreStore(() => HOME_ID);

// Before stub key:
"/api/chores": sampleDoc,

// After stub key:
[`/api/homes/${HOME_ID}/chores`]: sampleDoc,
```

Apply the same pattern to `houseStore.test.ts` and any other store tests.

Also update `App.test.ts` and `App.routing.test.ts` — these use `stubFetch` with a `handlers` object. Add stubs for `/api/homes` (returns empty array initially) and the module endpoints:

```typescript
// In stubFetch default handlers, add:
"/api/homes": [],
```

Note: module endpoint stubs in App tests use the new URL format e.g. `/api/homes/h1/house`.

- [ ] **Step 5: Run all frontend store tests**

```bash
cd /projects/myhome && npx vitest run packages/editor/test/ 2>&1 | tail -30
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/houseStore.svelte.ts \
        packages/editor/src/lib/choreStore.svelte.ts \
        packages/editor/src/lib/costsStore.svelte.ts \
        packages/editor/src/lib/inventoryStore.svelte.ts \
        packages/editor/src/lib/kbStore.svelte.ts \
        packages/editor/src/lib/worksStore.svelte.ts \
        packages/editor/src/lib/consumableStore.svelte.ts \
        packages/editor/src/lib/settingsStore.svelte.ts \
        packages/editor/test/
git commit -m "refactor(frontend): add getHomeId param to all module stores"
```

---

## Task 8: Frontend — wire App.svelte (homesStore init, home switch, zero-homes screen)

**Files:**
- Modify: `packages/editor/src/App.svelte`

- [ ] **Step 1: Import homesStore and pass getHomeId to all store factories**

In `App.svelte`, at the top of the `<script>` block add:

```typescript
import { homesStore } from "./lib/homesStore.svelte";
```

Then change all store factory calls to pass the `getHomeId` function:

```typescript
const floorStore = createHouseStore(() => homesStore.activeHomeId);
const choreStore = createChoreStore(() => homesStore.activeHomeId);
const inventoryStore = createInventoryStore(() => homesStore.activeHomeId);
const settingsStore = createSettingsStore(() => homesStore.activeHomeId);
const costsStore = createCostsStore(() => homesStore.activeHomeId);
const worksStore = createWorksStore(() => homesStore.activeHomeId);
const kbStore = createKBStore(() => homesStore.activeHomeId);
const consumableStore = createConsumableStore(() => homesStore.activeHomeId);
```

- [ ] **Step 2: Initialize homesStore on app load**

Find where the existing stores' `init()` is called (they auto-call, so nothing explicit needed). Add the homesStore load call. Place it after all store declarations:

```typescript
// Load homes on startup — this sets activeHomeId, which triggers the $effect below
homesStore.loadHomes();
```

- [ ] **Step 3: Add $effect for home switching + route redirect**

After the `homesStore.loadHomes()` call, add:

```typescript
// All enabled module IDs for the current route — used to guard redirect
const ROUTE_TO_MODULE: Record<string, string> = {
  "#/plan": "plan", "#/chores": "chores", "#/inventory": "inventory",
  "#/consumables": "consumables", "#/works": "works", "#/kb": "kb",
  "#/costs": "costs", "#/locations": "locations", "#/properties": "properties",
  "#/budget": "budget", "#/visits": "visits", "#/contacts": "contacts",
  "#/checklist": "checklist",
};

$effect(() => {
  const id = homesStore.activeHomeId;
  if (id) {
    floorStore.reload();
    choreStore.reload();
    inventoryStore.reload();
    settingsStore.reload();
    costsStore.reload();
    worksStore.reload();
    kbStore.reload();
    consumableStore.reload();
    // Redirect to home if current route's module is not enabled in new home
    const moduleId = ROUTE_TO_MODULE[currentRoute];
    if (moduleId && !homesStore.activeHome?.enabledModules.includes(moduleId)) {
      window.location.hash = "#/";
    }
  }
});
```

- [ ] **Step 4: Add zero-homes screen**

Wrap the entire main app layout in a conditional that checks `homesStore.loaded`. Find the top-level auth check in the template (the `{#if authStore.user === null}` block) and add a zero-homes branch:

```svelte
{#if authStore.user === null}
  <LoginPage ... />
{:else if homesStore.loaded && homesStore.homes.length === 0}
  <!-- Zero-homes: first-time setup -->
  <div class="zero-homes">
    <div class="zero-homes-inner">
      <h1>Welcome to My Home</h1>
      <p>Create your first home to get started.</p>
      <NewHomeModal open={true} onclose={() => {}} required={true} />
    </div>
  </div>
{:else}
  <!-- Normal app layout — existing content -->
  ...
{/if}
```

Add the import for `NewHomeModal` in the `<script>` block:
```typescript
import NewHomeModal from "./lib/components/NewHomeModal.svelte";
```

Add styles for `.zero-homes` and `.zero-homes-inner` in the `<style>` block:
```css
.zero-homes {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: var(--bg);
}
.zero-homes-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
  padding: 40px;
}
.zero-homes-inner h1 { font-size: 24px; font-weight: 700; margin: 0; color: var(--text); }
.zero-homes-inner p { color: var(--text-muted); margin: 0; }
```

- [ ] **Step 5: Add placeholder module routes**

In the route switching section of App.svelte (the `{:else if currentRoute === "#/chores"}` chain), add entries for each placeholder module:

```svelte
{:else if currentRoute === "#/locations"}
  <PlaceholderPage icon="🌍" label="Locations" description="Compare countries, cities, and neighborhoods with notes and ratings." />
{:else if currentRoute === "#/properties"}
  <PlaceholderPage icon="🏘" label="Properties" description="Track candidate plots and homes with specs, price, and pros/cons." />
{:else if currentRoute === "#/budget"}
  <PlaceholderPage icon="💰" label="Budget" description="Model purchase and construction cost scenarios with financing options." />
{:else if currentRoute === "#/visits"}
  <PlaceholderPage icon="📅" label="Visits" description="Log property and site viewings with notes, photos, and ratings." />
{:else if currentRoute === "#/contacts"}
  <PlaceholderPage icon="👤" label="Contacts" description="Keep track of agents, notaries, architects, and contractors." />
{:else if currentRoute === "#/checklist"}
  <PlaceholderPage icon="✅" label="Checklist" description="Track due diligence items, permits, and legal steps." />
```

Add the import:
```typescript
import PlaceholderPage from "./lib/components/PlaceholderPage.svelte";
```

- [ ] **Step 6: Run frontend tests**

```bash
cd /projects/myhome && npx vitest run packages/editor/test/ 2>&1 | tail -20
```

Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/App.svelte
git commit -m "feat(frontend): wire homesStore into App, add home switch effect and zero-homes screen"
```

---

## Task 9: Frontend — update NavMenu (HomesSwitcher + module filtering)

**Files:**
- Modify: `packages/editor/src/lib/components/NavMenu.svelte`

- [ ] **Step 1: Import HomesSwitcher and homesStore**

Add to the `<script>` block of `NavMenu.svelte`:

```typescript
import HomesSwitcher from "./HomesSwitcher.svelte";
import { homesStore } from "../homesStore.svelte";
```

- [ ] **Step 2: Add placeholder modules and enabledModules filtering**

Replace the static `modules` array with the full list including placeholders, and add the derived filtered list:

```typescript
const ALL_MODULES = [
  { id: "home",        href: "#/",            icon: "🏡", label: "Home"             },
  { id: "plan",        href: "#/plan",        icon: "📐", label: "Floor Plan"       },
  { id: "chores",      href: "#/chores",      icon: "✅", label: "Chores"           },
  { id: "inventory",   href: "#/inventory",   icon: "📦", label: "Inventory"        },
  { id: "consumables", href: "#/consumables", icon: "🛒", label: "Consumables"      },
  { id: "works",       href: "#/works",       icon: "🔧", label: "Works"            },
  { id: "kb",          href: "#/kb",          icon: "📖", label: "Knowledge Base"   },
  { id: "costs",       href: "#/costs",       icon: "💶", label: "Costs"            },
  { id: "locations",   href: "#/locations",   icon: "🌍", label: "Locations",   placeholder: true },
  { id: "properties",  href: "#/properties",  icon: "🏘", label: "Properties",  placeholder: true },
  { id: "budget",      href: "#/budget",      icon: "💰", label: "Budget",      placeholder: true },
  { id: "visits",      href: "#/visits",      icon: "📅", label: "Visits",      placeholder: true },
  { id: "contacts",    href: "#/contacts",    icon: "👤", label: "Contacts",    placeholder: true },
  { id: "checklist",   href: "#/checklist",   icon: "✅", label: "Checklist",   placeholder: true },
];

const visibleModules = $derived(
  ALL_MODULES.filter((m) => homesStore.activeHome?.enabledModules.includes(m.id) ?? true)
);
```

- [ ] **Step 3: Replace the template to use HomesSwitcher and filtered modules**

Replace the entire `<nav>` content in the template:

```svelte
<nav class="nav" class:expanded>
  <div class="nav-body">
    <HomesSwitcher {expanded} />
    {#each visibleModules as mod (mod.id)}
      <a
        href={mod.href}
        class="nav-item"
        class:active={isActive(mod.href)}
        class:soon={mod.placeholder}
        title={mod.placeholder ? `${mod.label} — coming soon` : mod.label}
        onclick={onclose}
      >
        <span class="nav-icon">{mod.icon}</span>
        <span class="nav-label">
          {mod.label}
          {#if mod.placeholder && expanded}<span class="soon-badge">Soon</span>{/if}
        </span>
      </a>
    {/each}
    <hr class="nav-separator" />
    <a href={settingsLink.href} class="nav-item" class:active={isActive(settingsLink.href)} title={settingsLink.label} onclick={onclose}>
      <span class="nav-icon">{settingsLink.icon}</span>
      <span class="nav-label">{settingsLink.label}</span>
    </a>
  </div>
</nav>
```

- [ ] **Step 4: Add `.soon` and `.soon-badge` styles**

```css
.nav-item.soon { opacity: 0.55; }
.soon-badge {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: var(--surface-hover);
  color: var(--text-muted);
  border-radius: var(--radius-pill);
  padding: 1px 5px;
  margin-left: 4px;
}
```

- [ ] **Step 5: Run frontend tests**

```bash
cd /projects/myhome && npx vitest run packages/editor/test/ 2>&1 | tail -20
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/NavMenu.svelte
git commit -m "feat(frontend): add HomesSwitcher to nav and filter modules by enabledModules"
```

---

## Task 10: Frontend — SettingsPage Home section + Modules section

**Files:**
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte`

- [ ] **Step 1: Add homesStore import and Home section state**

Add to the existing `<script lang="ts">` block:

```typescript
import { homesStore } from "../homesStore.svelte";

// --- Home metadata ---
let editingHomeName = $state(false);
let homeNameDraft = $state("");
let showDeleteConfirm = $state(false);
let deleteError = $state<string | null>(null);
let homeNameError = $state<string | null>(null);

function startEditHomeName(): void {
  homeNameDraft = homesStore.activeHome?.name ?? "";
  editingHomeName = true;
  homeNameError = null;
}

async function saveHomeName(): Promise<void> {
  if (!homeNameDraft.trim()) { homeNameError = "Name required"; return; }
  const id = homesStore.activeHomeId;
  if (!id) return;
  await homesStore.patchHome(id, { name: homeNameDraft.trim() });
  editingHomeName = false;
}

async function toggleHomeType(): Promise<void> {
  const home = homesStore.activeHome;
  if (!home) return;
  const next = home.type === "existing" ? "project" : "existing";
  await homesStore.patchHome(home.id, { type: next });
}

let moduleToggleWarning = $state<string | null>(null);

async function toggleModule(moduleId: string): Promise<void> {
  const home = homesStore.activeHome;
  if (!home) return;
  const current = home.enabledModules;
  const isDisabling = current.includes(moduleId);
  if (isDisabling) {
    moduleToggleWarning = `This hides ${CORE_MODULES.concat(PROJECT_MODULES).find(m => m.id === moduleId)?.label ?? moduleId} but does not delete your data.`;
  }
  const next = isDisabling
    ? current.filter((m) => m !== moduleId)
    : [...current, moduleId];
  await homesStore.patchHome(home.id, { enabledModules: next });
}

async function confirmDeleteHome(): Promise<void> {
  const id = homesStore.activeHomeId;
  if (!id) return;
  try {
    await homesStore.deleteHome(id);
    showDeleteConfirm = false;
  } catch (e) {
    deleteError = e instanceof Error ? e.message : "Failed to delete home";
  }
}

const CORE_MODULES = [
  { id: "home",        icon: "🏡", label: "Home"           },
  { id: "plan",        icon: "📐", label: "Floor Plan"     },
  { id: "chores",      icon: "✅", label: "Chores"         },
  { id: "inventory",   icon: "📦", label: "Inventory"      },
  { id: "consumables", icon: "🛒", label: "Consumables"    },
  { id: "works",       icon: "🔧", label: "Works"          },
  { id: "kb",          icon: "📖", label: "Knowledge Base" },
  { id: "costs",       icon: "💶", label: "Costs"          },
];

const PROJECT_MODULES = [
  { id: "locations",  icon: "🌍", label: "Locations"  },
  { id: "properties", icon: "🏘", label: "Properties" },
  { id: "budget",     icon: "💰", label: "Budget"     },
  { id: "visits",     icon: "📅", label: "Visits"     },
  { id: "contacts",   icon: "👤", label: "Contacts"   },
  { id: "checklist",  icon: "✅", label: "Checklist"  },
];
```

- [ ] **Step 2: Add Home section and Modules section to the template**

Insert these two Card blocks at the very top of the template, before the existing cost categories Card:

```svelte
<!-- Home metadata -->
<Card>
  <h2 class="section-title">Home</h2>

  <div class="home-row">
    <span class="home-label">Name</span>
    {#if editingHomeName}
      <div class="home-edit-row">
        <Input bind:value={homeNameDraft} placeholder="Home name" />
        <Button onclick={saveHomeName}>Save</Button>
        <Button variant="ghost" onclick={() => { editingHomeName = false; }}>Cancel</Button>
      </div>
      {#if homeNameError}<p class="field-error">{homeNameError}</p>{/if}
    {:else}
      <span class="home-value">{homesStore.activeHome?.name ?? "—"}</span>
      <Button variant="ghost" onclick={startEditHomeName}>Edit</Button>
    {/if}
  </div>

  <div class="home-row">
    <span class="home-label">Type</span>
    <span class="home-value">
      {homesStore.activeHome?.type === "project" ? "🏗 Project home" : "🏠 Existing home"}
    </span>
    <Button variant="ghost" onclick={toggleHomeType}>Change</Button>
  </div>

  <div class="home-row danger-row">
    <Button
      variant="danger"
      disabled={homesStore.homes.length <= 1}
      onclick={() => { showDeleteConfirm = true; }}
      title={homesStore.homes.length <= 1 ? "Cannot delete the only home" : undefined}
    >
      Delete this home
    </Button>
  </div>
</Card>

<!-- Module toggles -->
<Card>
  <h2 class="section-title">Modules</h2>
  <p class="section-desc">Choose which modules are visible in the nav for this home.</p>

  {#if moduleToggleWarning}
    <p class="module-warning">{moduleToggleWarning}</p>
  {/if}

  <div class="module-group">
    <h3 class="group-label">Core modules</h3>
    {#each CORE_MODULES as mod (mod.id)}
      <label class="module-row">
        <input
          type="checkbox"
          checked={homesStore.activeHome?.enabledModules.includes(mod.id) ?? false}
          onchange={() => toggleModule(mod.id)}
        />
        <span class="mod-icon">{mod.icon}</span>
        <span class="mod-label">{mod.label}</span>
      </label>
    {/each}
  </div>

  <div class="module-group">
    <h3 class="group-label">Project modules <span class="soon-tag">Placeholder</span></h3>
    {#each PROJECT_MODULES as mod (mod.id)}
      <label class="module-row">
        <input
          type="checkbox"
          checked={homesStore.activeHome?.enabledModules.includes(mod.id) ?? false}
          onchange={() => toggleModule(mod.id)}
        />
        <span class="mod-icon">{mod.icon}</span>
        <span class="mod-label">{mod.label}</span>
      </label>
    {/each}
  </div>
</Card>

<!-- Delete confirmation modal -->
<Modal open={showDeleteConfirm} title="Delete home" onclose={() => { showDeleteConfirm = false; }}>
  <p>Delete <strong>{homesStore.activeHome?.name}</strong>? This permanently removes all data for this home and cannot be undone.</p>
  {#if deleteError}<p class="field-error">{deleteError}</p>{/if}
  {#snippet actions()}
    <Button variant="ghost" onclick={() => { showDeleteConfirm = false; }}>Cancel</Button>
    <Button variant="danger" onclick={confirmDeleteHome}>Delete</Button>
  {/snippet}
</Modal>
```

- [ ] **Step 3: Add styles for new sections**

```css
.home-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; }
.home-label { font-size: 13px; color: var(--text-muted); width: 60px; flex-shrink: 0; }
.home-value { font-size: 13px; font-weight: 500; color: var(--text); flex: 1; }
.home-edit-row { display: flex; gap: 8px; flex: 1; align-items: center; }
.danger-row { padding-top: 12px; margin-top: 4px; border-top: 1px solid var(--border); }

.section-desc { font-size: 13px; color: var(--text-muted); margin: 0 0 12px; }
.module-group { margin-bottom: 16px; }
.group-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin: 0 0 8px; display: flex; align-items: center; gap: 8px; }
.module-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; cursor: pointer; }
.module-row input[type="checkbox"] { accent-color: var(--accent); width: 15px; height: 15px; }
.mod-icon { font-size: 16px; width: 20px; text-align: center; }
.mod-label { font-size: 13px; color: var(--text); }
.soon-tag {
  font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
  background: var(--surface-hover); color: var(--text-muted);
  border-radius: var(--radius-pill); padding: 1px 5px;
}
.field-error { color: var(--danger, #c0392b); font-size: 12px; margin: 4px 0 0; }
.module-warning { font-size: 12px; color: var(--text-muted); background: var(--surface-hover); border-radius: var(--radius); padding: 8px 10px; margin: 0 0 8px; }
```

- [ ] **Step 4: Run all frontend tests**

```bash
cd /projects/myhome && npx vitest run packages/editor/test/ 2>&1 | tail -20
```

Expected: all tests PASS

- [ ] **Step 5: Run all backend tests too**

```bash
cd /projects/myhome && python -m pytest packages/backend/tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/SettingsPage.svelte
git commit -m "feat(frontend): add Home and Modules sections to SettingsPage"
```

---

## Self-Review Checklist

Before declaring done, verify:

- [ ] `GET /api/homes` returns `[]` on a fresh install with no legacy data (migration not triggered)
- [ ] `GET /api/homes` returns one `"default"` home when legacy flat files existed (migration triggered)
- [ ] Creating a home of type `"existing"` enables all 8 core modules; `"project"` enables only `home/plan/works/kb`
- [ ] Switching homes in the nav causes all pages to reload data from the new home's endpoints
- [ ] Zero-homes screen appears on fresh install and disappears after creating the first home
- [ ] Disabling a module in Settings removes its nav entry immediately; the route still renders `PlaceholderPage` if the URL is visited directly (acceptable — no guard required)
- [ ] Deleting the only home is blocked (button disabled)
- [ ] `PATCH /api/homes/{id}` with `{enabledModules: [...]}` persists immediately and nav updates

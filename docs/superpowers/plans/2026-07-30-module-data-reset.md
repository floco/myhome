# Module Data Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an admin wipe one module's data for the currently selected home (records + attachments) from Settings, without touching that module's shared config or any other module.

**Architecture:** A new admin-gated `POST /api/homes/{home_id}/modules/{module_id}/reset` endpoint dispatches to a small `reset_*(home_id)` function added to each of the 11 resettable modules' persistence files (8 are `save_X(home_id, EmptyDocument())` + `rmtree` of the attachments dir; KB and Locations are bespoke; Build reuses the existing `delete_build_project`). The route logs one activity entry per reset. The frontend adds a "Reset" button next to each module row in `SettingsGeneral.svelte`, gated behind a confirmation modal, wired through a new `homesStore.resetModuleData()`.

**Tech Stack:** FastAPI + SQLAlchemy Core (SQLite) backend, Svelte 5 (runes) + svelte-i18n frontend, pytest, vitest.

## Global Constraints

- Reset is restricted to the 11 modules: chores, inventory, consumables, works, kb, costs, locations, properties, build, contacts, insurance. `home` and `plan` are never resettable via this endpoint (400).
- Reset always preserves shared config: cost categories, suppliers, inventory categories, work categories, consumable categories, insurance categories, contact types, and (for locations specifically) evaluation criteria. Only records/entries/attachments are deleted.
- The endpoint is admin-gated (`require_auth("admin")`), matching Delete Home and the Donetick import.
- One activity log entry is written per reset (`action="reset"`); no other module's activity history is touched or deleted.
- No cross-module cascade cleanup of loose references (e.g. a Build task's `contractor_id` pointing at a deleted Contact) — accepted limitation, not handled here.

---

### Task 1: Activity log "reset" action

**Files:**
- Modify: `packages/backend/src/myhome/models_activity.py:12`
- Modify: `packages/backend/src/myhome/persistence_activity.py:81-82`
- Test: `packages/backend/tests/test_activity.py`

**Interfaces:**
- Produces: `describe(entry: ActivityEntry) -> str` now also handles `entry.action == "reset"`, returning `f"reset {MODULE_NOUNS[entry.module]} data"` instead of the normal `"{verb} {noun} '{label}'"` shape (a module-wide reset has no single entity label).
- Produces: `ActivityEntry.action` `Literal` now includes `"reset"`, so `log_activity(home_id, user_id, module_id, "reset", entity_label)` (existing signature, unchanged) can be called with `action="reset"` without a pydantic validation error.

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_activity.py`:

```python
def test_describe_module_reset():
    entry = ActivityEntry(
        id="e1", timestamp="2026-01-01T00:00:00+00:00", userId="u1", username="admin",
        module="chores", action="reset", entityLabel="chores", refId=None,
    )
    assert describe(entry) == "reset chore data"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_activity.py::test_describe_module_reset -v`
Expected: FAIL — pydantic `ValidationError` because `"reset"` is not a valid value for the `action` `Literal`.

- [ ] **Step 3: Add `"reset"` to the `action` Literal**

In `packages/backend/src/myhome/models_activity.py`, change line 12 from:

```python
    action: Literal["create", "update", "delete", "complete", "restore", "delete_forever", "empty_trash"]
```

to:

```python
    action: Literal["create", "update", "delete", "complete", "restore", "delete_forever", "empty_trash", "reset"]
```

- [ ] **Step 4: Special-case `describe()` for the reset action**

In `packages/backend/src/myhome/persistence_activity.py`, replace the `describe` function (lines 81-82):

```python
def describe(entry: ActivityEntry) -> str:
    return f"{ACTION_VERBS[entry.action]} {MODULE_NOUNS[entry.module]} '{entry.entityLabel}'"
```

with:

```python
def describe(entry: ActivityEntry) -> str:
    if entry.action == "reset":
        return f"reset {MODULE_NOUNS[entry.module]} data"
    return f"{ACTION_VERBS[entry.action]} {MODULE_NOUNS[entry.module]} '{entry.entityLabel}'"
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_activity.py -v`
Expected: PASS (all tests in the file, including the new one).

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/models_activity.py packages/backend/src/myhome/persistence_activity.py packages/backend/tests/test_activity.py
git commit -m "feat(activity): add reset action for module-wide data resets"
```

---

### Task 2: Persistence reset for the 6 document-with-attachments modules

**Files:**
- Modify: `packages/backend/src/myhome/persistence_chores.py:178` (insert after `delete_all_attachments`, before `generate_pdf_thumbnail`)
- Modify: `packages/backend/src/myhome/persistence_inventory.py:125`
- Modify: `packages/backend/src/myhome/persistence_works.py:118`
- Modify: `packages/backend/src/myhome/persistence_costs.py:114`
- Modify: `packages/backend/src/myhome/persistence_properties.py:113`
- Modify: `packages/backend/src/myhome/persistence_insurance.py:120`
- Test: `packages/backend/tests/test_chores.py`, `test_inventory.py`, `test_works.py`, `test_costs.py`, `test_properties.py`, `test_insurance.py`

**Interfaces:**
- Consumes: each file's existing `save_X(home_id, XDocument())`, `_home_dir(home_id) -> Path`, and the document classes already imported in that file (`ChoreDocument`, `InventoryDocument`, `WorksDocument`, `CostsDocument`, `PropertiesDocument`, `InsuranceDocument`).
- Produces: `reset_chores(home_id)`, `reset_inventory(home_id)`, `reset_works(home_id)`, `reset_costs(home_id)`, `reset_properties(home_id)`, `reset_insurance(home_id)` — each clears that module's SQL rows for the home and removes its `<module>-attachments/` directory. All are `(home_id: str) -> None`.

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_chores.py`:

```python
def test_reset_chores_clears_data_and_attachments(client, tmp_path, home_id):
    cid = _chore_id(client, home_id)
    client.post(f"/api/homes/{home_id}/chores/{cid}/attachments",
                files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 10, "image/jpeg")})
    att_dir = tmp_path / "homes" / home_id / "chores-attachments" / cid
    assert att_dir.exists()

    from myhome.persistence_chores import reset_chores
    reset_chores(home_id)

    assert client.get(f"/api/homes/{home_id}/chores").json()["chores"] == []
    assert not att_dir.exists()
```

Add to `packages/backend/tests/test_inventory.py`:

```python
def test_reset_inventory_clears_data(client, home_id):
    client.post(f"/api/homes/{home_id}/inventory/items", json={"name": "Washing machine"})
    from myhome.persistence_inventory import reset_inventory
    reset_inventory(home_id)
    assert client.get(f"/api/homes/{home_id}/inventory").json()["items"] == []
```

Add to `packages/backend/tests/test_works.py`:

```python
def test_reset_works_clears_data(client, home_id):
    client.post(f"/api/homes/{home_id}/works", json={"title": "Roof repair", "status": "planned", "date": "2026-04-01"})
    from myhome.persistence_works import reset_works
    reset_works(home_id)
    assert client.get(f"/api/homes/{home_id}/works").json()["works"] == []
```

Add to `packages/backend/tests/test_costs.py`:

```python
def test_reset_costs_clears_data(client, home_id):
    client.post(f"/api/homes/{home_id}/costs", json={
        "categoryId": "cat-fuel", "date": "2026-01-01", "totalAmount": 100.0,
    })
    from myhome.persistence_costs import reset_costs
    reset_costs(home_id)
    assert client.get(f"/api/homes/{home_id}/costs").json()["entries"] == []
```

Add to `packages/backend/tests/test_properties.py`:

```python
def test_reset_properties_clears_data(client, home_id):
    client.post(f"/api/homes/{home_id}/properties", json={"name": "Terreno Norte", "type": "land"})
    from myhome.persistence_properties import reset_properties
    reset_properties(home_id)
    assert client.get(f"/api/homes/{home_id}/properties").json()["properties"] == []
```

Add to `packages/backend/tests/test_insurance.py`:

```python
def test_reset_insurance_clears_data(client, home_id):
    client.post(f"/api/homes/{home_id}/insurance", json={
        "name": "Travel Insurance", "categoryId": "icat-travel", "premiumFrequency": "annual",
    })
    from myhome.persistence_insurance import reset_insurance
    reset_insurance(home_id)
    assert client.get(f"/api/homes/{home_id}/insurance").json()["policies"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && pytest tests/test_chores.py::test_reset_chores_clears_data_and_attachments tests/test_inventory.py::test_reset_inventory_clears_data tests/test_works.py::test_reset_works_clears_data tests/test_costs.py::test_reset_costs_clears_data tests/test_properties.py::test_reset_properties_clears_data tests/test_insurance.py::test_reset_insurance_clears_data -v`
Expected: FAIL with `ImportError: cannot import name 'reset_chores'` (and equivalents) for each.

- [ ] **Step 3: Implement `reset_chores`**

In `packages/backend/src/myhome/persistence_chores.py`, insert after line 178 (the end of `delete_all_attachments`, before `generate_pdf_thumbnail`):

```python
def reset_chores(home_id: str) -> None:
    save_chores(home_id, ChoreDocument())
    attachments_root = _home_dir(home_id) / "chores-attachments"
    if attachments_root.exists():
        shutil.rmtree(attachments_root)
```

- [ ] **Step 4: Implement `reset_inventory`**

In `packages/backend/src/myhome/persistence_inventory.py`, insert after line 125 (end of `delete_all_attachments`):

```python
def reset_inventory(home_id: str) -> None:
    save_inventory(home_id, InventoryDocument())
    attachments_root = _home_dir(home_id) / "inventory-attachments"
    if attachments_root.exists():
        shutil.rmtree(attachments_root)
```

- [ ] **Step 5: Implement `reset_works`**

In `packages/backend/src/myhome/persistence_works.py`, insert after line 118:

```python
def reset_works(home_id: str) -> None:
    save_works(home_id, WorksDocument())
    attachments_root = _home_dir(home_id) / "works-attachments"
    if attachments_root.exists():
        shutil.rmtree(attachments_root)
```

- [ ] **Step 6: Implement `reset_costs`**

In `packages/backend/src/myhome/persistence_costs.py`, insert after line 114:

```python
def reset_costs(home_id: str) -> None:
    save_costs(home_id, CostsDocument())
    attachments_root = _home_dir(home_id) / "costs-attachments"
    if attachments_root.exists():
        shutil.rmtree(attachments_root)
```

- [ ] **Step 7: Implement `reset_properties`**

In `packages/backend/src/myhome/persistence_properties.py`, insert after line 113:

```python
def reset_properties(home_id: str) -> None:
    save_properties(home_id, PropertiesDocument())
    attachments_root = _home_dir(home_id) / "properties-attachments"
    if attachments_root.exists():
        shutil.rmtree(attachments_root)
```

- [ ] **Step 8: Implement `reset_insurance`**

In `packages/backend/src/myhome/persistence_insurance.py`, insert after line 120:

```python
def reset_insurance(home_id: str) -> None:
    save_insurance(home_id, InsuranceDocument())
    attachments_root = _home_dir(home_id) / "insurance-attachments"
    if attachments_root.exists():
        shutil.rmtree(attachments_root)
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `cd packages/backend && pytest tests/test_chores.py tests/test_inventory.py tests/test_works.py tests/test_costs.py tests/test_properties.py tests/test_insurance.py -v`
Expected: PASS (full files, no regressions).

- [ ] **Step 10: Commit**

```bash
git add packages/backend/src/myhome/persistence_chores.py packages/backend/src/myhome/persistence_inventory.py packages/backend/src/myhome/persistence_works.py packages/backend/src/myhome/persistence_costs.py packages/backend/src/myhome/persistence_properties.py packages/backend/src/myhome/persistence_insurance.py packages/backend/tests/test_chores.py packages/backend/tests/test_inventory.py packages/backend/tests/test_works.py packages/backend/tests/test_costs.py packages/backend/tests/test_properties.py packages/backend/tests/test_insurance.py
git commit -m "feat(reset): add reset_* persistence functions for attachment-bearing modules"
```

---

### Task 3: Persistence reset for Consumables and Contacts

**Files:**
- Modify: `packages/backend/src/myhome/persistence_consumables.py` (append at end of file, after line 78)
- Modify: `packages/backend/src/myhome/persistence_contacts.py` (append at end of file, after line 81)
- Test: `packages/backend/tests/test_consumables.py`, `packages/backend/tests/test_contacts.py`

**Interfaces:**
- Consumes: `save_consumables(home_id, ConsumableDocument())`, `save_contacts(home_id, ContactsDocument())` (existing, already imported in each file).
- Produces: `reset_consumables(home_id: str) -> None`, `reset_contacts(home_id: str) -> None`. Neither module has an attachments directory, so these are pure data clears.

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_consumables.py`:

```python
def test_reset_consumables_clears_data(client, home_id):
    client.post(f"/api/homes/{home_id}/consumables", json={
        "name": "Dish soap", "emoji": "🧴", "unit": "mL", "quantity": 500.0, "minQuantity": 100.0,
    })
    from myhome.persistence_consumables import reset_consumables
    reset_consumables(home_id)
    assert client.get(f"/api/homes/{home_id}/consumables").json()["consumables"] == []
```

Add to `packages/backend/tests/test_contacts.py`:

```python
def test_reset_contacts_clears_data(client, home_id):
    client.post(f"/api/homes/{home_id}/contacts", json={"name": "Metro Plumbing", "typeId": "ctype-supplier"})
    from myhome.persistence_contacts import reset_contacts
    reset_contacts(home_id)
    assert client.get(f"/api/homes/{home_id}/contacts").json()["contacts"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && pytest tests/test_consumables.py::test_reset_consumables_clears_data tests/test_contacts.py::test_reset_contacts_clears_data -v`
Expected: FAIL with `ImportError: cannot import name 'reset_consumables'` / `'reset_contacts'`.

- [ ] **Step 3: Implement `reset_consumables`**

Append to the end of `packages/backend/src/myhome/persistence_consumables.py`:

```python


def reset_consumables(home_id: str) -> None:
    save_consumables(home_id, ConsumableDocument())
```

- [ ] **Step 4: Implement `reset_contacts`**

Append to the end of `packages/backend/src/myhome/persistence_contacts.py`:

```python


def reset_contacts(home_id: str) -> None:
    save_contacts(home_id, ContactsDocument())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/backend && pytest tests/test_consumables.py tests/test_contacts.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/persistence_consumables.py packages/backend/src/myhome/persistence_contacts.py packages/backend/tests/test_consumables.py packages/backend/tests/test_contacts.py
git commit -m "feat(reset): add reset_consumables and reset_contacts"
```

---

### Task 4: Persistence reset for KB

**Files:**
- Modify: `packages/backend/src/myhome/persistence_kb.py:301` (insert after `delete_attachment`, before `generate_pdf_thumbnail`)
- Test: `packages/backend/tests/test_kb.py`

**Interfaces:**
- Consumes: `_kb_dir(home_id) -> Path` (entries directory), `_home_dir(home_id) -> Path` (existing helpers already in the file).
- Produces: `reset_kb(home_id: str) -> None` — KB stores each page as a markdown file under `<home>/kb/` and attachments under `<home>/kb-attachments/<entry_id>/`, not as a SQL document, so reset removes both directories wholesale rather than calling a `save_kb`.

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_kb.py`:

```python
def test_reset_kb_clears_entries_and_attachments(client, tmp_path, home_id):
    eid = client.post(f"/api/homes/{home_id}/kb", json={"title": "How to paint", "content": "# Painting"}).json()["id"]
    client.post(
        f"/api/homes/{home_id}/kb/{eid}/attachments",
        files={"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")},
    )
    kb_dir = tmp_path / "homes" / home_id / "kb"
    att_dir = tmp_path / "homes" / home_id / "kb-attachments"
    assert kb_dir.exists()
    assert att_dir.exists()

    from myhome.persistence_kb import reset_kb
    reset_kb(home_id)

    assert client.get(f"/api/homes/{home_id}/kb").json()["entries"] == []
    assert not kb_dir.exists()
    assert not att_dir.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_kb.py::test_reset_kb_clears_entries_and_attachments -v`
Expected: FAIL with `ImportError: cannot import name 'reset_kb'`.

- [ ] **Step 3: Implement `reset_kb`**

In `packages/backend/src/myhome/persistence_kb.py`, insert after line 301 (end of `delete_attachment`, before `generate_pdf_thumbnail`):

```python
def reset_kb(home_id: str) -> None:
    kb_dir = _kb_dir(home_id)
    if kb_dir.exists():
        shutil.rmtree(kb_dir)
    attachments_root = _home_dir(home_id) / "kb-attachments"
    if attachments_root.exists():
        shutil.rmtree(attachments_root)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_kb.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/persistence_kb.py packages/backend/tests/test_kb.py
git commit -m "feat(reset): add reset_kb"
```

---

### Task 5: Persistence reset for Locations (preserves criteria)

**Files:**
- Modify: `packages/backend/src/myhome/persistence_locations.py` (append at end of file, after line 94)
- Test: `packages/backend/tests/test_locations.py`

**Interfaces:**
- Consumes: `get_engine()`, `location_ratings_table`, `locations_table` (already imported).
- Produces: `reset_locations(home_id: str) -> None`. Unlike the other modules, this does **not** call `save_locations` with an empty document — that would also wipe `location_criteria`, which is this module's config-equivalent and must be preserved. It deletes only `location_ratings` and `locations` rows directly.

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_locations.py`:

```python
def test_reset_locations_preserves_criteria(client, home_id):
    client.post(f"/api/homes/{home_id}/locations/criteria", json={"name": "Safety"})
    client.post(f"/api/homes/{home_id}/locations/locations", json={"name": "Zagreb"})

    from myhome.persistence_locations import reset_locations
    reset_locations(home_id)

    data = client.get(f"/api/homes/{home_id}/locations").json()
    assert data["locations"] == []
    assert data["ratings"] == []
    assert len(data["criteria"]) == 1
    assert data["criteria"][0]["name"] == "Safety"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && pytest tests/test_locations.py::test_reset_locations_preserves_criteria -v`
Expected: FAIL with `ImportError: cannot import name 'reset_locations'`.

- [ ] **Step 3: Implement `reset_locations`**

Append to the end of `packages/backend/src/myhome/persistence_locations.py`:

```python


def reset_locations(home_id: str) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(location_ratings_table.delete().where(location_ratings_table.c.home_id == home_id))
        conn.execute(locations_table.delete().where(locations_table.c.home_id == home_id))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && pytest tests/test_locations.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/persistence_locations.py packages/backend/tests/test_locations.py
git commit -m "feat(reset): add reset_locations, preserving evaluation criteria"
```

---

### Task 6: Reset endpoint and dispatcher

**Files:**
- Create: `packages/backend/src/myhome/routes/modules.py`
- Modify: `packages/backend/src/myhome/main.py:20` (import) and the `include_router` block (~line 159)
- Test: Create `packages/backend/tests/test_modules_reset.py`

**Interfaces:**
- Consumes: `reset_chores`, `reset_inventory`, `reset_works`, `reset_costs`, `reset_properties`, `reset_insurance` (Task 2), `reset_consumables`, `reset_contacts` (Task 3), `reset_kb` (Task 4), `reset_locations` (Task 5) — all `(home_id: str) -> None`. Also consumes the existing `delete_build_project(home_id: str) -> None` from `persistence_build.py`, `require_auth` from `deps.py`, `log_activity` from `persistence_activity.py`, and `load_homes` from `persistence_homes.py`.
- Produces: `POST /api/homes/{home_id}/modules/{module_id}/reset` — 204 on success, 400 for an unknown/non-resettable `module_id` (including `home`/`plan`), 404 for an unknown `home_id`, 403 for a non-admin caller.

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_modules_reset.py`:

```python
def test_reset_requires_admin(ro_client, home_id):
    resp = ro_client.post(f"/api/homes/{home_id}/modules/chores/reset")
    assert resp.status_code == 403


def test_reset_rejects_unknown_module(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/modules/bogus/reset")
    assert resp.status_code == 400


def test_reset_rejects_home_module(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/modules/home/reset")
    assert resp.status_code == 400


def test_reset_rejects_plan_module(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/modules/plan/reset")
    assert resp.status_code == 400


def test_reset_returns_404_for_unknown_home(client):
    resp = client.post("/api/homes/nonexistent/modules/chores/reset")
    assert resp.status_code == 404


def test_reset_clears_chores_and_logs_activity(client, home_id):
    client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep", "emoji": "🧹", "periodDays": 7, "nextDueDate": "2027-01-01T00:00:00Z",
    })
    resp = client.post(f"/api/homes/{home_id}/modules/chores/reset")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/chores").json()["chores"] == []

    log = client.get(f"/api/homes/{home_id}/activity").json()
    reset_entries = [e for e in log["entries"] if e["module"] == "chores" and e["action"] == "reset"]
    assert len(reset_entries) == 1
    assert reset_entries[0]["description"] == "reset chore data"


def test_reset_does_not_touch_other_modules(client, home_id):
    client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Sweep", "emoji": "🧹", "periodDays": 7, "nextDueDate": "2027-01-01T00:00:00Z",
    })
    client.post(f"/api/homes/{home_id}/works", json={"title": "Roof repair", "status": "planned", "date": "2026-04-01"})

    client.post(f"/api/homes/{home_id}/modules/chores/reset")

    assert client.get(f"/api/homes/{home_id}/chores").json()["chores"] == []
    works = client.get(f"/api/homes/{home_id}/works").json()["works"]
    assert len(works) == 1
    assert works[0]["title"] == "Roof repair"


def test_reset_all_resettable_module_ids_succeed(client, home_id):
    resettable = [
        "chores", "inventory", "consumables", "works", "kb", "costs",
        "locations", "properties", "build", "contacts", "insurance",
    ]
    for module_id in resettable:
        resp = client.post(f"/api/homes/{home_id}/modules/{module_id}/reset")
        assert resp.status_code == 204, f"{module_id} reset failed: {resp.text}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && pytest tests/test_modules_reset.py -v`
Expected: FAIL with 404 on every request (route doesn't exist yet).

- [ ] **Step 3: Implement the route**

Create `packages/backend/src/myhome/routes/modules.py`:

```python
# packages/backend/src/myhome/routes/modules.py
from fastapi import APIRouter, HTTPException

from ..deps import require_auth
from ..persistence_activity import log_activity
from ..persistence_build import delete_build_project
from ..persistence_chores import reset_chores
from ..persistence_consumables import reset_consumables
from ..persistence_contacts import reset_contacts
from ..persistence_costs import reset_costs
from ..persistence_homes import load_homes
from ..persistence_insurance import reset_insurance
from ..persistence_inventory import reset_inventory
from ..persistence_kb import reset_kb
from ..persistence_locations import reset_locations
from ..persistence_properties import reset_properties
from ..persistence_works import reset_works

router = APIRouter()

RESET_HANDLERS = {
    "chores": reset_chores,
    "inventory": reset_inventory,
    "consumables": reset_consumables,
    "works": reset_works,
    "kb": reset_kb,
    "costs": reset_costs,
    "locations": reset_locations,
    "properties": reset_properties,
    "build": delete_build_project,
    "contacts": reset_contacts,
    "insurance": reset_insurance,
}


@router.post("/api/homes/{home_id}/modules/{module_id}/reset", status_code=204)
def reset_module_route(
    home_id: str, module_id: str,
    current_user: tuple[str, str] = require_auth("admin"),
) -> None:
    handler = RESET_HANDLERS.get(module_id)
    if handler is None:
        raise HTTPException(status_code=400, detail=f"Unknown or non-resettable module: {module_id!r}")
    home = next((h for h in load_homes().homes if h.id == home_id), None)
    if home is None:
        raise HTTPException(status_code=404)
    handler(home_id)
    log_activity(home_id, current_user[0], module_id, "reset", module_id)
```

- [ ] **Step 4: Register the router**

In `packages/backend/src/myhome/main.py`, change line 20 from:

```python
from .routes import activity, auth, backup, build, chores, consumables, contacts, costs, ha, homes, house, insurance, inventory, kb, locations, mcp_config, notifications, properties, settings, svg, system, works
```

to:

```python
from .routes import activity, auth, backup, build, chores, consumables, contacts, costs, ha, homes, house, insurance, inventory, kb, locations, mcp_config, modules, notifications, properties, settings, svg, system, works
```

Then add `app.include_router(modules.router)` immediately after `app.include_router(settings.router)` in the `include_router` block.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/backend && pytest tests/test_modules_reset.py -v`
Expected: PASS.

Then run the full backend suite to check for regressions:

Run: `cd packages/backend && pytest tests -v`
Expected: PASS (all tests, no regressions).

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/routes/modules.py packages/backend/src/myhome/main.py packages/backend/tests/test_modules_reset.py
git commit -m "feat(reset): add POST /api/homes/{home_id}/modules/{module_id}/reset endpoint"
```

---

### Task 7: Frontend i18n keys

**Files:**
- Modify: `packages/editor/src/lib/locales/en.json:165` and `:892`
- Modify: `packages/editor/src/lib/locales/fr.json:165` and `:892`

**Interfaces:**
- Produces: `common.reset`, `settings.general.resetModuleTitle`, `settings.general.resetModuleBody`, `settings.general.resetModuleSuccess`, `settings.general.resetModuleFailed` — all take a `{label}` interpolation value except `common.reset`, consumed by Task 9's `SettingsGeneral.svelte` changes.

- [ ] **Step 1: Add `common.reset` to `en.json`**

In `packages/editor/src/lib/locales/en.json`, change line 165 from:

```json
    "delete": "Delete",
```

to:

```json
    "delete": "Delete",
    "reset": "Reset",
```

- [ ] **Step 2: Add `common.reset` to `fr.json`**

In `packages/editor/src/lib/locales/fr.json`, change line 165 from:

```json
    "delete": "Supprimer",
```

to:

```json
    "delete": "Supprimer",
    "reset": "Réinitialiser",
```

- [ ] **Step 3: Add `settings.general.resetModule*` keys to `en.json`**

In `packages/editor/src/lib/locales/en.json`, change (now shifted one line down, at line 893) from:

```json
      "moduleHideWarning": "This hides {label} but does not delete your data."
```

to:

```json
      "moduleHideWarning": "This hides {label} but does not delete your data.",
      "resetModuleTitle": "Reset {label} data",
      "resetModuleBody": "This permanently deletes all {label} data and attachments. Any shared configuration for this module (categories, etc.) is kept. This cannot be undone.",
      "resetModuleSuccess": "{label} data has been reset.",
      "resetModuleFailed": "Failed to reset {label} data"
```

- [ ] **Step 4: Add `settings.general.resetModule*` keys to `fr.json`**

In `packages/editor/src/lib/locales/fr.json`, change (now shifted one line down, at line 893) from:

```json
      "moduleHideWarning": "Cela masque {label} mais ne supprime pas vos données."
```

to:

```json
      "moduleHideWarning": "Cela masque {label} mais ne supprime pas vos données.",
      "resetModuleTitle": "Réinitialiser les données de {label}",
      "resetModuleBody": "Cela supprime définitivement toutes les données et pièces jointes de {label}. La configuration partagée de ce module (catégories, etc.) est conservée. Cette action est irréversible.",
      "resetModuleSuccess": "Les données de {label} ont été réinitialisées.",
      "resetModuleFailed": "Échec de la réinitialisation des données de {label}"
```

- [ ] **Step 5: Verify the JSON is valid**

Run: `cd packages/editor && node -e "JSON.parse(require('fs').readFileSync('src/lib/locales/en.json')); JSON.parse(require('fs').readFileSync('src/lib/locales/fr.json')); console.log('OK')"`
Expected: prints `OK` with no errors.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json
git commit -m "i18n: add module data reset copy (en/fr)"
```

---

### Task 8: `homesStore.resetModuleData()`

**Files:**
- Modify: `packages/editor/src/lib/homesStore.svelte.ts` (insert after `deleteHome`, before `setActiveHomeId`)
- Test: `packages/editor/test/homesStore.test.ts`

**Interfaces:**
- Produces: `resetModuleData(homeId: string, moduleId: string): Promise<void>` — `POST`s to `/api/homes/{homeId}/modules/{moduleId}/reset`, throws `Error("HTTP <status>")` on a non-2xx response, otherwise resolves with no return value (the store does not mutate any local module data). Exported on the `homesStore` object, consumed by Task 9.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/homesStore.test.ts`:

```ts
describe("homesStore — resetModuleData", () => {
  it("posts to the module reset endpoint", async () => {
    const fetchMock = makeFetch(204);
    vi.stubGlobal("fetch", fetchMock);
    await homesStore.resetModuleData("h1", "chores");
    expect(fetchMock).toHaveBeenCalledWith("/api/homes/h1/modules/chores/reset", { method: "POST" });
  });

  it("throws on a non-ok response", async () => {
    vi.stubGlobal("fetch", makeFetch(403));
    await expect(homesStore.resetModuleData("h1", "chores")).rejects.toThrow("HTTP 403");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/homesStore.test.ts`
Expected: FAIL — `homesStore.resetModuleData is not a function`.

- [ ] **Step 3: Implement `resetModuleData`**

In `packages/editor/src/lib/homesStore.svelte.ts`, insert after the `deleteHome` function (after line 61, before `setActiveHomeId`):

```ts
async function resetModuleData(homeId: string, moduleId: string): Promise<void> {
  const resp = await fetch(`/api/homes/${homeId}/modules/${moduleId}/reset`, { method: "POST" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
}
```

Then add `resetModuleData,` to the exported `homesStore` object, right after `deleteHome,`:

```ts
export const homesStore = {
  get homes() { return homes; },
  get activeHomeId() { return activeHomeId; },
  get activeHome() { return homes.find((h) => h.id === activeHomeId) ?? null; },
  get loaded() { return loaded; },
  loadHomes,
  createHome,
  patchHome,
  deleteHome,
  resetModuleData,
  setActiveHomeId,
  _reset,
};
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/homesStore.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/homesStore.svelte.ts packages/editor/test/homesStore.test.ts
git commit -m "feat(reset): add homesStore.resetModuleData()"
```

---

### Task 9: `SettingsGeneral.svelte` reset button and confirm modal

**Files:**
- Modify: `packages/editor/src/lib/components/settings/SettingsGeneral.svelte`
- Test: `packages/editor/test/SettingsGeneral.test.ts`

**Interfaces:**
- Consumes: `homesStore.resetModuleData(homeId, moduleId): Promise<void>` (Task 8); i18n keys `common.reset`, `settings.general.resetModuleTitle`, `settings.general.resetModuleBody`, `settings.general.resetModuleSuccess`, `settings.general.resetModuleFailed` (Task 7); existing `Modal`, `Button` components (`open: boolean`, `title: string`, `onclose: () => void`, `footer?: Snippet`; `variant?: "primary" | "secondary" | "ghost" | "danger"`).
- Produces: no new exports — this is a leaf UI change. A "Reset" button appears on every module row except `home` and `plan`; clicking it opens a confirm modal; confirming calls `resetModuleData` and shows an inline success/error message in the Modules card.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/SettingsGeneral.test.ts`:

```ts
  it("shows a Reset button for data modules but not for Home or Plan", () => {
    seedHome({ enabledModules: ["home", "plan", "chores"] });
    const app = mount(SettingsGeneral, { target, props: {} });
    flushSync();
    const choresRow = [...target.querySelectorAll(".module-row")].find((r) => r.textContent?.includes("Chores"))!;
    expect([...choresRow.querySelectorAll("button")].some((b) => b.textContent?.trim() === "Reset")).toBe(true);
    const homeRow = [...target.querySelectorAll(".module-row")].find((r) => r.textContent?.trim().startsWith("Home"))!;
    expect([...homeRow.querySelectorAll("button")].some((b) => b.textContent?.trim() === "Reset")).toBe(false);
    unmount(app);
  });

  it("resetting a module shows a confirm modal and calls resetModuleData on confirm", async () => {
    seedHome({ enabledModules: ["home", "plan", "chores"] });
    vi.stubGlobal("fetch", makeFetch(204));
    const app = mount(SettingsGeneral, { target, props: {} });
    flushSync();
    const choresRow = [...target.querySelectorAll(".module-row")].find((r) => r.textContent?.includes("Chores"))!;
    const resetBtn = [...choresRow.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Reset")!;
    resetBtn.click();
    flushSync();
    const modal = target.querySelector(".ui-modal")!;
    expect(modal.textContent).toContain("Reset Chores data");
    const confirmBtn = [...modal.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Reset")!;
    confirmBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(fetch).toHaveBeenCalledWith("/api/homes/h1/modules/chores/reset", { method: "POST" });
    flushSync();
    expect(target.querySelector(".ui-modal")).toBeNull();
    expect(target.textContent).toContain("Chores data has been reset.");
    unmount(app);
  });

  it("shows an error inline and keeps the modal open when reset fails", async () => {
    seedHome({ enabledModules: ["home", "plan", "chores"] });
    vi.stubGlobal("fetch", makeFetch(403));
    const app = mount(SettingsGeneral, { target, props: {} });
    flushSync();
    const choresRow = [...target.querySelectorAll(".module-row")].find((r) => r.textContent?.includes("Chores"))!;
    const resetBtn = [...choresRow.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Reset")!;
    resetBtn.click();
    flushSync();
    const confirmBtn = [...target.querySelectorAll(".ui-modal button")].find((b) => b.textContent?.trim() === "Reset")!;
    confirmBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.querySelector(".ui-modal")).not.toBeNull();
    expect(target.textContent).toContain("Failed to reset Chores data");
    unmount(app);
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/SettingsGeneral.test.ts`
Expected: FAIL — no "Reset" button exists yet on module rows.

- [ ] **Step 3: Restructure the module row and add reset state/handlers**

In `packages/editor/src/lib/components/settings/SettingsGeneral.svelte`, add new state and handler functions after the existing `moduleToggleWarning` block (after line 70, before `confirmDeleteHome`):

```ts
  let resetModuleId = $state<string | null>(null);
  let resetError = $state<string | null>(null);
  let resetSuccessMessage = $state<string | null>(null);

  function startReset(moduleId: string): void {
    resetModuleId = moduleId;
    resetError = null;
  }

  async function confirmReset(): Promise<void> {
    const home = homesStore.activeHome;
    if (!home || !resetModuleId) return;
    const label = $_(`common.modules.${resetModuleId}`);
    try {
      await homesStore.resetModuleData(home.id, resetModuleId);
      resetSuccessMessage = $_('settings.general.resetModuleSuccess', { values: { label } });
      resetModuleId = null;
    } catch {
      resetError = $_('settings.general.resetModuleFailed', { values: { label } });
    }
  }
```

- [ ] **Step 4: Restructure the module row markup**

Replace the `module-group` block (lines 158-171):

```svelte
  <div class="module-group">
    {#each MODULES as mod (mod.id)}
      <label class="module-row">
        <input
          type="checkbox"
          checked={homesStore.activeHome?.enabledModules.includes(mod.id) ?? false}
          onchange={() => toggleModule(mod.id)}
        />
        <span class="mod-icon">{mod.icon}</span>
        <span class="mod-label">{$_(`common.modules.${mod.id}`)}</span>
        {#if mod.placeholder}<span class="soon-tag">{$_('settings.general.placeholderTag')}</span>{/if}
      </label>
    {/each}
  </div>
```

with:

```svelte
  <div class="module-group">
    {#each MODULES as mod (mod.id)}
      <div class="module-row">
        <label class="module-row-label">
          <input
            type="checkbox"
            checked={homesStore.activeHome?.enabledModules.includes(mod.id) ?? false}
            onchange={() => toggleModule(mod.id)}
          />
          <span class="mod-icon">{mod.icon}</span>
          <span class="mod-label">{$_(`common.modules.${mod.id}`)}</span>
          {#if mod.placeholder}<span class="soon-tag">{$_('settings.general.placeholderTag')}</span>{/if}
        </label>
        {#if mod.id !== "home" && mod.id !== "plan"}
          <Button variant="ghost" onclick={() => startReset(mod.id)}>{$_('common.reset')}</Button>
        {/if}
      </div>
    {/each}
  </div>

  {#if resetSuccessMessage}
    <p class="module-success">{resetSuccessMessage}</p>
  {/if}
```

- [ ] **Step 5: Add the confirm modal**

After the existing delete-home `<Modal>` block (after line 181, before the `<style>` block), add:

```svelte
<Modal
  open={resetModuleId !== null}
  title={resetModuleId ? $_('settings.general.resetModuleTitle', { values: { label: $_(`common.modules.${resetModuleId}`) } }) : ''}
  onclose={() => { resetModuleId = null; }}
>
  <p>{resetModuleId ? $_('settings.general.resetModuleBody', { values: { label: $_(`common.modules.${resetModuleId}`) } }) : ''}</p>
  {#if resetError}<p class="field-error">{resetError}</p>{/if}
  {#snippet footer()}
    <Button variant="ghost" onclick={() => { resetModuleId = null; }}>{$_('common.cancel')}</Button>
    <Button variant="danger" onclick={confirmReset}>{$_('common.reset')}</Button>
  {/snippet}
</Modal>
```

- [ ] **Step 6: Update the CSS**

Replace the `.module-row` rule in the `<style>` block:

```css
  .module-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; cursor: pointer; }
```

with:

```css
  .module-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 6px 0; }
  .module-row-label { display: flex; align-items: center; gap: 10px; cursor: pointer; flex: 1; }
```

And add, next to the existing `.module-warning` rule:

```css
  .module-success { font-size: 12px; color: var(--text-muted); background: var(--surface-hover); border-radius: var(--radius); padding: 8px 10px; margin: 8px 0 0; }
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/SettingsGeneral.test.ts`
Expected: PASS (all tests in the file, including the pre-existing ones — the `.module-row` restructure must not break `renders core module checkboxes reflecting enabledModules` or `toggling a module checkbox calls patchHome`).

- [ ] **Step 8: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsGeneral.svelte packages/editor/test/SettingsGeneral.test.ts
git commit -m "feat(settings): add per-module data reset button and confirm modal"
```

---

### Task 10: Full verification pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend suite**

Run: `cd packages/backend && pytest tests -v`
Expected: PASS, no regressions.

- [ ] **Step 2: Run the full frontend suite**

Run: `cd packages/editor && npx vitest run`
Expected: PASS, no regressions.

- [ ] **Step 3: Typecheck the frontend**

Run: `cd packages/editor && npm run check`
Expected: no new type errors.

- [ ] **Step 4: Manual smoke test**

Use the `run` skill (or start the dev server manually) to open Settings > General for a home with some Chores data, click Reset next to Chores, confirm in the modal, and verify: the success message appears, the Chores page shows no chores after navigating to it, and other modules (e.g. Works) still show their data untouched.

# Contacts Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a central Contacts module (contractors/suppliers/providers) that absorbs the existing minimal Suppliers list and becomes the real target for Build Tracking's `contractorId` and Works/Costs' supplier field.

**Architecture:** New SQLite-backed `contacts` CRUD module (models/persistence/routes/MCP tools, mirroring the existing Works module) plus a per-home editable "Contact Types" list in Settings (mirroring the existing category-list pattern). `works.supplier_id` and `cost_entries.supplier_id` are renamed to `contact_id` and repointed at Contacts; `build_tasks.contractor_id` keeps its name but becomes a real Contact reference instead of free text. The old `suppliers` table/model/endpoint is removed (fresh start, no data migration of existing supplier rows).

**Tech Stack:** FastAPI + SQLAlchemy Core (SQLite) backend, Svelte 5 (runes) + TypeScript frontend, pytest, vitest.

## Global Constraints

- Every home-scoped table added or touched uses `(id, home_id)` composite primary keys where ids can repeat across homes (seed/demo data), or a bare UUID `id` where ids are always randomly generated per-record (see `schema.py:95-99` for the existing rule and the bug it fixed in `feedback_category_table_home_scoping_bug`).
- `category_id`/`supplier_id`/`contact_id`-style cross-module reference columns stay plain unvalidated string columns — no hard `ForeignKey` — per the existing rule documented at `schema.py:202-204`.
- Migrations in `migrations.py` must never assume the shape of a table changes retroactively; once a migration function is written for a given `MIGRATIONS` version, later work must not edit that function's *behavior* — only append new versions.
- No new frontend dependencies. Reuse existing shared UI components (`Card`, `Button`, `Input`, `Modal`, `SortableTable`, `Tabs`) and existing patterns (`WorksPage.svelte` / `WorkModal.svelte` / `SettingsCategories.svelte`).
- Every backend module change that adds/removes a locale-facing string must update both `packages/editor/src/lib/locales/en.json` and `fr.json` (mirrored line-for-line structure) in the same task.

---

## Task 1: Backend — Contacts schema, Contact Types (absorb Suppliers), migration v5

**Files:**
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/migrations.py`
- Modify: `packages/backend/src/myhome/models_settings.py`
- Modify: `packages/backend/src/myhome/persistence_settings.py`
- Modify: `packages/backend/src/myhome/routes/settings.py`
- Test: `packages/backend/tests/test_settings.py`
- Test: `packages/backend/tests/test_settings_persistence.py`
- Test: `packages/backend/tests/test_migrations.py`

**Interfaces:**
- Produces: `contacts` table in `schema.py` (used by Task 3's `persistence_contacts.py`); `ContactType` pydantic model + `SettingsDocument.contactTypes: list[ContactType]` (used by Task 8/9 frontend and Task 3's Contact modal type dropdown).

### Step 1: Add the `contacts` table and retain (but stop actively using) `suppliers` in `schema.py`

Open `packages/backend/src/myhome/schema.py`. Add a comment above the existing `suppliers` table (around line 131) explaining it must stay for migration compatibility, and add the new `contacts` and `contact_types` tables after `consumable_categories` (after line ~146, before whatever table follows it):

```python
# suppliers is superseded by contacts + contact_types (see migration
# version 5, _absorb_suppliers_into_contacts) and is no longer read or
# written by any persistence_*.py module. The Table object stays defined
# here ONLY because migration version 4 (_scope_category_tables_by_home,
# already shipped) references it by name to recreate the table with a
# composite primary key -- removing the object would break that migration
# for any database still below schema version 4. Do not remove this until
# migration version 4 itself is retired.
suppliers = Table(
    "suppliers", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
)

contact_types = Table(
    "contact_types", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
)

contacts = Table(
    "contacts", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("company_name", String),
    Column("type_id", String, nullable=False),
    Column("phone", String),
    Column("email", String),
    Column("address", String),
    Column("website", String),
    Column("notes", String, nullable=False),
)
```

(Keep the existing `suppliers = Table(...)` block exactly as-is other than adding the comment — do not change its columns.)

### Step 2: Add migration version 5

Open `packages/backend/src/myhome/migrations.py`. Change `CURRENT_VERSION = 4` to `CURRENT_VERSION = 5`. Add this function before the `MIGRATIONS` list:

```python
_DEFAULT_CONTACT_TYPES = [
    ("ctype-contractor", "Contractor"),
    ("ctype-supplier", "Supplier"),
    ("ctype-service", "Service Provider"),
    ("ctype-agent", "Agent"),
    ("ctype-notary", "Notary"),
    ("ctype-other", "Other"),
]


def _absorb_suppliers_into_contacts(conn: Connection) -> None:
    # cost_entries.supplier_id / works.supplier_id become contact_id, and
    # the standalone suppliers list is replaced by the new Contacts module
    # + a per-home editable Contact Types list. contact_types is a
    # brand-new table, so unlike cost_categories/work_categories/etc.
    # (whose rows already existed for any home that had ever saved
    # settings before this migration), every existing home's contact_types
    # starts genuinely empty -- it will never hit the lazy "row is None"
    # default-seed path in load_settings() again once that home already
    # has a settings row. Seed the defaults directly here so upgraded
    # homes get the same starting list a fresh home gets.
    conn.execute(text("ALTER TABLE cost_entries RENAME COLUMN supplier_id TO contact_id"))
    conn.execute(text("ALTER TABLE works RENAME COLUMN supplier_id TO contact_id"))
    conn.execute(text("DROP TABLE IF EXISTS suppliers"))
    home_ids = [r[0] for r in conn.execute(text("SELECT id FROM homes")).all()]
    for home_id in home_ids:
        for i, (type_id, name) in enumerate(_DEFAULT_CONTACT_TYPES):
            conn.execute(
                text(
                    "INSERT INTO contact_types (id, home_id, order_index, name) "
                    "VALUES (:id, :home_id, :i, :name)"
                ),
                {"id": type_id, "home_id": home_id, "i": i, "name": name},
            )
```

Add `(5, _absorb_suppliers_into_contacts)` to the `MIGRATIONS` list, after the existing `(4, _scope_category_tables_by_home)` entry.

### Step 3: Write the migration test

Add to `packages/backend/tests/test_migrations.py`:

```python
def test_run_migrations_absorbs_suppliers_into_contacts(tmp_path):
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE homes (id VARCHAR PRIMARY KEY, name VARCHAR, type VARCHAR, created_at VARCHAR)"
        ))
        conn.execute(text("INSERT INTO homes (id, name, type, created_at) VALUES ('h1', 'Home 1', 'existing', '2026-01-01')"))
        conn.execute(text("INSERT INTO homes (id, name, type, created_at) VALUES ('h2', 'Home 2', 'existing', '2026-01-01')"))
        _create_legacy_category_tables(conn)
        conn.execute(text(
            "CREATE TABLE cost_entries (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, category_id VARCHAR NOT NULL, date VARCHAR NOT NULL, "
            "total_amount FLOAT NOT NULL, quantity FLOAT, unit_price FLOAT, supplier_id VARCHAR, "
            "notes VARCHAR NOT NULL, room_id VARCHAR, attachments TEXT NOT NULL)"
        ))
        conn.execute(text(
            "INSERT INTO cost_entries (id, home_id, order_index, category_id, date, total_amount, "
            "supplier_id, notes, attachments) VALUES "
            "('c1', 'h1', 0, 'cat-fuel', '2026-01-01', 100.0, 'sup-1', '', '[]')"
        ))
        conn.execute(text(
            "CREATE TABLE works (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, title VARCHAR NOT NULL, description VARCHAR NOT NULL, "
            "status VARCHAR NOT NULL, category_id VARCHAR, date VARCHAR NOT NULL, total_cost FLOAT, "
            "supplier_id VARCHAR, notes VARCHAR NOT NULL, attachments TEXT NOT NULL, "
            "placement_floor_id VARCHAR, placement_x FLOAT, placement_y FLOAT)"
        ))
        conn.execute(text(
            "INSERT INTO works (id, home_id, order_index, title, description, status, date, "
            "supplier_id, notes, attachments) VALUES "
            "('w1', 'h1', 0, 'Roof repair', '', 'done', '2026-01-01', 'sup-1', '', '[]')"
        ))
        conn.execute(text(
            "CREATE TABLE contact_types (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL)"
        ))
        conn.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        conn.execute(text("INSERT INTO schema_version (version) VALUES (4)"))

    run_migrations(engine)

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        cost_row = conn.execute(text("SELECT contact_id FROM cost_entries WHERE id = 'c1'")).mappings().first()
        work_row = conn.execute(text("SELECT contact_id FROM works WHERE id = 'w1'")).mappings().first()
        supplier_table_exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='suppliers'")
        ).first()
        h1_types = conn.execute(
            text("SELECT id, name FROM contact_types WHERE home_id = 'h1' ORDER BY order_index")
        ).mappings().all()
        h2_types = conn.execute(
            text("SELECT id, name FROM contact_types WHERE home_id = 'h2' ORDER BY order_index")
        ).mappings().all()

    assert version == CURRENT_VERSION
    assert cost_row["contact_id"] == "sup-1"
    assert work_row["contact_id"] == "sup-1"
    assert supplier_table_exists is None
    assert [t["id"] for t in h1_types] == [
        "ctype-contractor", "ctype-supplier", "ctype-service", "ctype-agent", "ctype-notary", "ctype-other",
    ]
    assert h1_types[0]["name"] == "Contractor"
    assert len(h2_types) == 6
```

Note this test's `_create_legacy_category_tables(conn)` call (the existing helper at the top of the file) still creates a legacy `suppliers` table with the pre-v4 bare `id` PK shape — that's intentional, it exercises migration v4's rename-recreate dance immediately before v5 drops the resulting table.

### Step 4: Run the migration test to verify it fails

Run: `cd packages/backend && python -m pytest tests/test_migrations.py -v`
Expected: FAIL — `contact_id` column doesn't exist yet (schema.py wasn't touched by migrations.py logic, but the raw-SQL legacy tables in the test also don't have the rename applied since the migration function doesn't exist yet). You'll see an `AttributeError` or `KeyError`-style failure from the new test; the two pre-existing tests in the file should still pass.

### Step 5: Update `models_settings.py`

Open `packages/backend/src/myhome/models_settings.py`. Replace the `Supplier` class:

```python
class Supplier(BaseModel):
    id: str
    name: str
```

with:

```python
class ContactType(BaseModel):
    id: str
    name: str
```

Add this function near the other `_default_*` functions (after `_default_work_categories`):

```python
def _default_contact_types() -> list[ContactType]:
    return [
        ContactType(id="ctype-contractor", name="Contractor"),
        ContactType(id="ctype-supplier", name="Supplier"),
        ContactType(id="ctype-service", name="Service Provider"),
        ContactType(id="ctype-agent", name="Agent"),
        ContactType(id="ctype-notary", name="Notary"),
        ContactType(id="ctype-other", name="Other"),
    ]
```

In `class SettingsDocument`, replace:

```python
    suppliers: list[Supplier] = []
```

with:

```python
    contactTypes: list[ContactType] = []
```

### Step 6: Update `persistence_settings.py`

Open `packages/backend/src/myhome/persistence_settings.py`.

Change the import block:

```python
from .models_settings import (
    ConsumableCategory,
    CostCategory,
    CostCategoryPlacement,
    CostCategoryPosition,
    InventoryCategory,
    NotificationSettings,
    SettingsDocument,
    ContactType,
    WorkCategory,
    _default_cost_categories,
    _default_consumable_units,
    _default_inventory_categories,
    _default_work_categories,
    _default_contact_types,
)
from .schema import (
    consumable_categories as consumable_categories_table,
    cost_categories as cost_categories_table,
    inventory_categories as inventory_categories_table,
    settings as settings_table,
    contact_types as contact_types_table,
    work_categories as work_categories_table,
)
```

(Note `Supplier`/`suppliers_table` are removed entirely — `suppliers` stays defined in `schema.py` per Step 1's comment, but nothing imports it anymore.)

In `load_settings`, replace the early-return default block:

```python
        if row is None:
            return SettingsDocument(
                costCategories=_default_cost_categories(),
                inventoryCategories=_default_inventory_categories(),
                workCategories=_default_work_categories(),
                consumableUnits=_default_consumable_units(),
            )
```

with:

```python
        if row is None:
            return SettingsDocument(
                costCategories=_default_cost_categories(),
                inventoryCategories=_default_inventory_categories(),
                workCategories=_default_work_categories(),
                consumableUnits=_default_consumable_units(),
                contactTypes=_default_contact_types(),
            )
```

Replace the `supplier_rows = conn.execute(...)` query block with:

```python
        contact_type_rows = conn.execute(
            select(contact_types_table).where(contact_types_table.c.home_id == home_id)
            .order_by(contact_types_table.c.order_index)
        ).mappings().all()
```

Replace `suppliers=[Supplier(id=r["id"], name=r["name"]) for r in supplier_rows],` with:

```python
        contactTypes=[ContactType(id=r["id"], name=r["name"]) for r in contact_type_rows],
```

In `save_settings`, replace:

```python
        conn.execute(suppliers_table.delete().where(suppliers_table.c.home_id == home_id))
        if doc.suppliers:
            conn.execute(suppliers_table.insert(), [
                {"id": s.id, "home_id": home_id, "order_index": i, "name": s.name}
                for i, s in enumerate(doc.suppliers)
            ])
```

with:

```python
        conn.execute(contact_types_table.delete().where(contact_types_table.c.home_id == home_id))
        if doc.contactTypes:
            conn.execute(contact_types_table.insert(), [
                {"id": t.id, "home_id": home_id, "order_index": i, "name": t.name}
                for i, t in enumerate(doc.contactTypes)
            ])
```

### Step 7: Update `routes/settings.py`

Open `packages/backend/src/myhome/routes/settings.py`. Replace the import of `Supplier` with `ContactType`:

```python
from ..models_settings import (
    ConsumableCategory,
    CostCategory,
    CostCategoryPlacement,
    InventoryCategory,
    NotificationSettings,
    WorkCategory,
    ContactType,
    SettingsDocument,
)
```

Replace:

```python
@router.put("/api/homes/{home_id}/settings/suppliers", status_code=204)
def put_suppliers(home_id: str, body: list[Supplier]) -> None:
    doc = load_settings(home_id)
    doc.suppliers = body
    save_settings(home_id, doc)
```

with:

```python
@router.put("/api/homes/{home_id}/settings/contact-types", status_code=204)
def put_contact_types(home_id: str, body: list[ContactType]) -> None:
    doc = load_settings(home_id)
    doc.contactTypes = body
    save_settings(home_id, doc)
```

### Step 8: Update `test_settings.py`

Open `packages/backend/tests/test_settings.py`. Replace:

```python
    assert data["suppliers"] == []
```

with:

```python
    assert len(data["contactTypes"]) == 6
    assert data["contactTypes"][0]["name"] == "Contractor"
```

Replace the two supplier tests:

```python
def test_put_suppliers(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/settings/suppliers", json=[{"id": "s1", "name": "Acme Plumbers"}])
    ...


def test_put_suppliers_replaces_all(client, home_id):
    client.put(f"/api/homes/{home_id}/settings/suppliers", json=[{"id": "s1", "name": "A"}, {"id": "s2", "name": "B"}])
    client.put(f"/api/homes/{home_id}/settings/suppliers", json=[{"id": "s3", "name": "C"}])
    ...
```

with:

```python
def test_put_contact_types(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/settings/contact-types", json=[{"id": "t1", "name": "Plumber"}])
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/settings").json()
    assert data["contactTypes"][0]["name"] == "Plumber"


def test_put_contact_types_replaces_all(client, home_id):
    client.put(f"/api/homes/{home_id}/settings/contact-types", json=[{"id": "t1", "name": "A"}, {"id": "t2", "name": "B"}])
    client.put(f"/api/homes/{home_id}/settings/contact-types", json=[{"id": "t3", "name": "C"}])
    data = client.get(f"/api/homes/{home_id}/settings").json()
    assert len(data["contactTypes"]) == 1
    assert data["contactTypes"][0]["name"] == "C"
```

### Step 9: Update `test_settings_persistence.py`

Open `packages/backend/tests/test_settings_persistence.py`. Change the import at line 48 from `Supplier` to `ContactType`, change line 58 from `suppliers=[Supplier(id="s1", name="Acme")],` to `contactTypes=[ContactType(id="t1", name="Plumber")],`, and change line 70 from `assert loaded.suppliers[0].name == "Acme"` to `assert loaded.contactTypes[0].name == "Plumber"`.

### Step 10: Run the full settings + migrations test suite

Run: `cd packages/backend && python -m pytest tests/test_settings.py tests/test_settings_persistence.py tests/test_migrations.py -v`
Expected: All PASS.

### Step 11: Commit

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/migrations.py packages/backend/src/myhome/models_settings.py packages/backend/src/myhome/persistence_settings.py packages/backend/src/myhome/routes/settings.py packages/backend/tests/test_settings.py packages/backend/tests/test_settings_persistence.py packages/backend/tests/test_migrations.py
git commit -m "feat(contacts): add contacts schema, absorb Suppliers into per-home Contact Types"
```

---

## Task 2: Backend — rename `supplier_id` → `contact_id` on Works & Costs

**Files:**
- Modify: `packages/backend/src/myhome/models_works.py`
- Modify: `packages/backend/src/myhome/persistence_works.py`
- Modify: `packages/backend/src/myhome/models_costs.py`
- Modify: `packages/backend/src/myhome/persistence_costs.py`
- Test: `packages/backend/tests/test_works.py`
- Test: `packages/backend/tests/test_works_persistence.py`
- Test: `packages/backend/tests/test_costs.py`
- Test: `packages/backend/tests/test_costs_persistence.py`
- Test: `packages/backend/tests/test_demo_data.py`

**Interfaces:**
- Consumes: `works`/`cost_entries` tables' `contact_id` column from Task 1 Step 1-2 (schema.py already has the column live; the migration handles renaming pre-existing physical rows).
- Produces: `Work.contactId`, `CostEntry.contactId` fields (used by Task 6's demo data, Task 10's frontend rebind).

### Step 1: Rename in `models_works.py`

Open `packages/backend/src/myhome/models_works.py`. In `Work`, `WorkCreate`, and `WorkUpdate`, rename every `supplierId: str | None = None` to `contactId: str | None = None`.

### Step 2: Rename in `persistence_works.py`

Open `packages/backend/src/myhome/persistence_works.py`. In `load_works`, change `supplierId=r["supplier_id"],` to `contactId=r["contact_id"],`. In `save_works`, change `"supplier_id": w.supplierId,` to `"contact_id": w.contactId,`.

### Step 3: Update `test_works.py` and `test_works_persistence.py`

In `packages/backend/tests/test_works.py`: rename `"supplierId": "sup-1",` (line 46) to `"contactId": "sup-1",`, and `assert data["supplierId"] == "sup-1"` (line 53) to `assert data["contactId"] == "sup-1"`.

`test_works_persistence.py` has no `supplierId` references — no change needed there (confirmed by grep; skip if none found).

### Step 4: Rename in `models_costs.py`

Open `packages/backend/src/myhome/models_costs.py`. In `CostEntry`, `CostEntryCreate`, and `CostEntryUpdate`, rename every `supplierId: str | None = None` to `contactId: str | None = None`.

### Step 5: Rename in `persistence_costs.py`

Open `packages/backend/src/myhome/persistence_costs.py`. In `load_costs`, change `supplierId=r["supplier_id"],` to `contactId=r["contact_id"],`. In `save_costs`, change `"supplier_id": e.supplierId,` to `"contact_id": e.contactId,`.

### Step 6: Update `test_costs.py` and `test_costs_persistence.py`

`test_costs.py`: line 16 `supplierId="sup-butagaz",` → `contactId="sup-butagaz",`; line 42 `"supplierId": "sup-butagaz",` → `"contactId": "sup-butagaz",`; line 50 `assert data["supplierId"] == "sup-butagaz"` → `assert data["contactId"] == "sup-butagaz"`; line 64 `assert data["supplierId"] is None` → `assert data["contactId"] is None`; line 69 `json={"totalAmount": 1800.0, "supplierId": "sup-total"}` → `json={"totalAmount": 1800.0, "contactId": "sup-total"}`; line 73 `assert entry["supplierId"] == "sup-total"` → `assert entry["contactId"] == "sup-total"`.

`test_costs_persistence.py`: line 31 `supplierId="sup-butagaz",` → `contactId="sup-butagaz",`; line 53 `assert e.supplierId == "sup-butagaz"` → `assert e.contactId == "sup-butagaz"`; line 67 `assert e.supplierId is None` → `assert e.contactId is None`.

### Step 7: Update `test_demo_data.py` (temporary — will be replaced fully in Task 6)

Since Task 6 rewrites `generate_demo_costs`/`generate_demo_works` signatures, only rename the field reference here for now so this task's test run stays green in isolation: in `packages/backend/tests/test_demo_data.py` line 112-113, change `if entry.supplierId is not None: assert entry.supplierId in supplier_ids` to `if entry.contactId is not None: assert entry.contactId in supplier_ids`. (The `supplier_ids` variable itself and the test name will be rewritten in Task 6 once `generate_demo_costs` takes a contacts list instead of reading `settings.suppliers` — `settings.suppliers` no longer exists after Task 1, so this specific test will actually fail here and get fixed in Task 6. Run it and confirm it fails for exactly that reason before moving on.)

### Step 8: Run the works & costs test suites

Run: `cd packages/backend && python -m pytest tests/test_works.py tests/test_works_persistence.py tests/test_costs.py tests/test_costs_persistence.py -v`
Expected: All PASS.

Run: `cd packages/backend && python -m pytest tests/test_demo_data.py -v`
Expected: `test_generate_demo_costs_entries_reference_valid_categories_and_suppliers` FAILS with an `AttributeError: 'SettingsDocument' object has no attribute 'suppliers'` (or similar) — this is expected and will be fixed in Task 6. All other tests in the file PASS.

### Step 9: Commit

```bash
git add packages/backend/src/myhome/models_works.py packages/backend/src/myhome/persistence_works.py packages/backend/src/myhome/models_costs.py packages/backend/src/myhome/persistence_costs.py packages/backend/tests/test_works.py packages/backend/tests/test_costs.py packages/backend/tests/test_costs_persistence.py packages/backend/tests/test_demo_data.py
git commit -m "feat(contacts): rename Work/CostEntry supplierId to contactId"
```

---

## Task 3: Backend — Contacts CRUD module

**Files:**
- Create: `packages/backend/src/myhome/models_contacts.py`
- Create: `packages/backend/src/myhome/persistence_contacts.py`
- Create: `packages/backend/src/myhome/routes/contacts.py`
- Modify: `packages/backend/src/myhome/main.py`
- Modify: `packages/backend/src/myhome/persistence_activity.py`
- Test: `packages/backend/tests/test_contacts.py`
- Test: `packages/backend/tests/test_contacts_persistence.py`

**Interfaces:**
- Consumes: `contacts` table from Task 1 Step 1.
- Produces: `Contact`, `ContactCreate`, `ContactUpdate`, `ContactsDocument` (`models_contacts.py`); `load_contacts(home_id)`, `save_contacts(home_id, doc)`, `get_contact_usage(home_id, contact_id) -> list[dict]` (`persistence_contacts.py`, `get_contact_usage` fully implemented in Task 4 — this task adds a stub that always returns `[]` so `routes/contacts.py` can import it); REST routes `GET/POST /api/homes/{id}/contacts`, `PUT/DELETE /api/homes/{id}/contacts/{cid}` (Task 4 adds the usage-based 409 and the `/usage` GET route).

### Step 1: Write `models_contacts.py`

```python
# packages/backend/src/myhome/models_contacts.py
from __future__ import annotations
from pydantic import BaseModel


class Contact(BaseModel):
    id: str
    name: str
    companyName: str | None = None
    typeId: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    website: str | None = None
    notes: str = ""


class ContactsDocument(BaseModel):
    version: int = 1
    contacts: list[Contact] = []


class ContactCreate(BaseModel):
    name: str
    companyName: str | None = None
    typeId: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    website: str | None = None
    notes: str = ""


class ContactUpdate(BaseModel):
    name: str | None = None
    companyName: str | None = None
    typeId: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    website: str | None = None
    notes: str | None = None
```

### Step 2: Write `persistence_contacts.py` (with a stub `get_contact_usage`)

```python
# packages/backend/src/myhome/persistence_contacts.py
from sqlalchemy import select

from .db import get_engine
from .models_contacts import Contact, ContactsDocument
from .schema import contacts as contacts_table


def load_contacts(home_id: str) -> ContactsDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(contacts_table).where(contacts_table.c.home_id == home_id)
            .order_by(contacts_table.c.order_index)
        ).mappings().all()
    return ContactsDocument(contacts=[
        Contact(
            id=r["id"], name=r["name"], companyName=r["company_name"], typeId=r["type_id"],
            phone=r["phone"], email=r["email"], address=r["address"], website=r["website"],
            notes=r["notes"],
        )
        for r in rows
    ])


def save_contacts(home_id: str, doc: ContactsDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(contacts_table.delete().where(contacts_table.c.home_id == home_id))
        if doc.contacts:
            conn.execute(contacts_table.insert(), [
                {
                    "id": c.id, "home_id": home_id, "order_index": i, "name": c.name,
                    "company_name": c.companyName, "type_id": c.typeId, "phone": c.phone,
                    "email": c.email, "address": c.address, "website": c.website,
                    "notes": c.notes,
                }
                for i, c in enumerate(doc.contacts)
            ])


def get_contact_usage(home_id: str, contact_id: str) -> list[dict]:
    # Implemented fully in Task 4 -- returns cross-module references to this
    # contact (build tasks, works, cost entries). Stubbed to [] here so
    # routes/contacts.py has something importable for this task's tests.
    return []
```

### Step 3: Write `routes/contacts.py`

```python
# packages/backend/src/myhome/routes/contacts.py
import uuid

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user_id
from ..models_contacts import Contact, ContactCreate, ContactsDocument, ContactUpdate
from ..persistence_activity import log_activity
from ..persistence_contacts import get_contact_usage, load_contacts, save_contacts

router = APIRouter()


@router.get("/api/homes/{home_id}/contacts", response_model=ContactsDocument)
def get_contacts(home_id: str) -> ContactsDocument:
    return load_contacts(home_id)


@router.post("/api/homes/{home_id}/contacts", response_model=Contact, status_code=201)
def create_contact(
    home_id: str, body: ContactCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Contact:
    doc = load_contacts(home_id)
    contact = Contact(id=str(uuid.uuid4()), **body.model_dump())
    doc.contacts.append(contact)
    save_contacts(home_id, doc)
    log_activity(home_id, current_user_id, "contacts", "create", contact.name, contact.id)
    return contact


@router.put("/api/homes/{home_id}/contacts/{id}", status_code=204)
def update_contact(
    home_id: str, id: str, body: ContactUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_contacts(home_id)
    contact = next((c for c in doc.contacts if c.id == id), None)
    if not contact:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    save_contacts(home_id, doc)
    log_activity(home_id, current_user_id, "contacts", "update", contact.name, id)


@router.get("/api/homes/{home_id}/contacts/{id}/usage")
def get_contact_usage_route(home_id: str, id: str) -> dict:
    return {"references": get_contact_usage(home_id, id)}


@router.delete("/api/homes/{home_id}/contacts/{id}", status_code=204)
def delete_contact(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_contacts(home_id)
    contact = next((c for c in doc.contacts if c.id == id), None)
    if contact is None:
        raise HTTPException(status_code=404)
    usage = get_contact_usage(home_id, id)
    if usage:
        raise HTTPException(status_code=409, detail={"references": usage})
    doc.contacts = [c for c in doc.contacts if c.id != id]
    save_contacts(home_id, doc)
    log_activity(home_id, current_user_id, "contacts", "delete", contact.name, id)
```

### Step 4: Register the router in `main.py`

Open `packages/backend/src/myhome/main.py`. In the `from .routes import ...` line, add `contacts` to the alphabetized import list (after `consumables`, before `costs`):

```python
from .routes import activity, auth, backup, build, chores, consumables, contacts, costs, ha, homes, house, inventory, kb, locations, mcp_config, notifications, properties, settings, svg, works
```

Add `app.include_router(contacts.router)` after `app.include_router(consumables.router)`.

### Step 5: Add `"contacts": "contact"` to `MODULE_NOUNS`

Open `packages/backend/src/myhome/persistence_activity.py`. Change:

```python
MODULE_NOUNS = {
    "chores": "chore", "works": "work", "costs": "cost entry",
    "inventory": "inventory item", "consumables": "consumable", "kb": "KB article",
    "locations": "location", "properties": "property", "build": "build task",
}
```

to:

```python
MODULE_NOUNS = {
    "chores": "chore", "works": "work", "costs": "cost entry",
    "inventory": "inventory item", "consumables": "consumable", "kb": "KB article",
    "locations": "location", "properties": "property", "build": "build task",
    "contacts": "contact",
}
```

### Step 6: Write `test_contacts.py`

```python
# packages/backend/tests/test_contacts.py
def test_get_contacts_empty_when_none(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/contacts")
    assert resp.status_code == 200
    assert resp.json()["contacts"] == []


def test_create_contact(client, home_id):
    payload = {"name": "Metro Plumbing", "typeId": "ctype-supplier"}
    resp = client.post(f"/api/homes/{home_id}/contacts", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Metro Plumbing"
    assert data["typeId"] == "ctype-supplier"
    assert data["companyName"] is None
    assert "id" in data
    assert len(client.get(f"/api/homes/{home_id}/contacts").json()["contacts"]) == 1


def test_create_contact_full_fields(client, home_id):
    payload = {
        "name": "Jane Doe", "companyName": "Acme Roofing", "typeId": "ctype-contractor",
        "phone": "+1 555-1234", "email": "jane@acme.example", "address": "123 Main St",
        "website": "https://acme.example", "notes": "Prefers morning calls",
    }
    resp = client.post(f"/api/homes/{home_id}/contacts", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["companyName"] == "Acme Roofing"
    assert data["email"] == "jane@acme.example"


def test_update_contact_partial(client, home_id):
    created = client.post(f"/api/homes/{home_id}/contacts", json={"name": "Jane", "typeId": "ctype-contractor"}).json()
    resp = client.put(f"/api/homes/{home_id}/contacts/{created['id']}", json={"phone": "555-0000"})
    assert resp.status_code == 204
    contact = client.get(f"/api/homes/{home_id}/contacts").json()["contacts"][0]
    assert contact["phone"] == "555-0000"
    assert contact["name"] == "Jane"  # unchanged


def test_update_contact_404(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/contacts/nope", json={"name": "X"})
    assert resp.status_code == 404


def test_delete_contact(client, home_id):
    created = client.post(f"/api/homes/{home_id}/contacts", json={"name": "Jane", "typeId": "ctype-contractor"}).json()
    resp = client.delete(f"/api/homes/{home_id}/contacts/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/contacts").json()["contacts"] == []


def test_delete_contact_404(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/contacts/nope")
    assert resp.status_code == 404


def test_get_contact_usage_empty(client, home_id):
    created = client.post(f"/api/homes/{home_id}/contacts", json={"name": "Jane", "typeId": "ctype-contractor"}).json()
    resp = client.get(f"/api/homes/{home_id}/contacts/{created['id']}/usage")
    assert resp.status_code == 200
    assert resp.json()["references"] == []
```

(The last test only checks the stubbed-empty shape for now — Task 4 adds real usage-detection tests.)

### Step 7: Write `test_contacts_persistence.py`

```python
# packages/backend/tests/test_contacts_persistence.py
from myhome.models_contacts import Contact, ContactsDocument
from myhome.persistence_contacts import load_contacts, save_contacts

HOME_ID = "test-home"


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "homes" / HOME_ID).mkdir(parents=True)
    from myhome.db import get_engine
    from myhome.schema import homes as homes_table
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(homes_table.insert().values(
            id=HOME_ID, name="Test Home", type="existing", created_at="2026-01-01T00:00:00+00:00",
        ))


def make_doc() -> ContactsDocument:
    return ContactsDocument(contacts=[
        Contact(id="c1", name="Metro Plumbing", typeId="ctype-supplier"),
    ])


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = load_contacts(HOME_ID)
    assert doc.contacts == []


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_contacts(HOME_ID, make_doc())
    loaded = load_contacts(HOME_ID)
    c = loaded.contacts[0]
    assert c.id == "c1"
    assert c.name == "Metro Plumbing"
    assert c.typeId == "ctype-supplier"
    assert c.companyName is None


def test_round_trip_preserves_order(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = ContactsDocument(contacts=[
        Contact(id="c1", name="A", typeId="ctype-supplier"),
        Contact(id="c2", name="B", typeId="ctype-contractor"),
    ])
    save_contacts(HOME_ID, doc)
    loaded = load_contacts(HOME_ID)
    assert [c.id for c in loaded.contacts] == ["c1", "c2"]
```

### Step 8: Run the new test suites

Run: `cd packages/backend && python -m pytest tests/test_contacts.py tests/test_contacts_persistence.py -v`
Expected: All PASS.

### Step 9: Commit

```bash
git add packages/backend/src/myhome/models_contacts.py packages/backend/src/myhome/persistence_contacts.py packages/backend/src/myhome/routes/contacts.py packages/backend/src/myhome/main.py packages/backend/src/myhome/persistence_activity.py packages/backend/tests/test_contacts.py packages/backend/tests/test_contacts_persistence.py
git commit -m "feat(contacts): add Contacts CRUD backend module"
```

---

## Task 4: Backend — contact usage lookup + delete protection

**Files:**
- Modify: `packages/backend/src/myhome/persistence_contacts.py`
- Test: `packages/backend/tests/test_contacts.py`
- Test: `packages/backend/tests/test_contacts_persistence.py`

**Interfaces:**
- Consumes: `build_tasks` (`schema.py`, `contractor_id` column), `works` and `cost_entries` (`contact_id` column from Task 2).
- Produces: real `get_contact_usage(home_id, contact_id) -> list[dict]` (each dict: `{"module": str, "id": str, "label": str}`), consumed by Task 3's routes (already wired) and Task 8's frontend `getUsage`.

### Step 1: Implement `get_contact_usage`

Open `packages/backend/src/myhome/persistence_contacts.py`. Change the import line:

```python
from .schema import contacts as contacts_table
```

to:

```python
from .schema import (
    build_tasks as build_tasks_table,
    contacts as contacts_table,
    cost_entries as cost_entries_table,
    works as works_table,
)
```

Replace the stub:

```python
def get_contact_usage(home_id: str, contact_id: str) -> list[dict]:
    # Implemented fully in Task 4 -- returns cross-module references to this
    # contact (build tasks, works, cost entries). Stubbed to [] here so
    # routes/contacts.py has something importable for this task's tests.
    return []
```

with:

```python
def get_contact_usage(home_id: str, contact_id: str) -> list[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        # build_tasks has no home_id column of its own (only reachable via
        # phase_id -> build_projects.home_id); contact_id values are UUIDs
        # generated per-record and never reused across homes, so matching
        # on contractor_id alone can't cross into another home's data.
        build_rows = conn.execute(
            select(build_tasks_table.c.id, build_tasks_table.c.title_override, build_tasks_table.c.title_key)
            .where(build_tasks_table.c.contractor_id == contact_id)
        ).mappings().all()
        work_rows = conn.execute(
            select(works_table.c.id, works_table.c.title)
            .where(works_table.c.home_id == home_id, works_table.c.contact_id == contact_id)
        ).mappings().all()
        cost_rows = conn.execute(
            select(cost_entries_table.c.id, cost_entries_table.c.notes, cost_entries_table.c.total_amount)
            .where(cost_entries_table.c.home_id == home_id, cost_entries_table.c.contact_id == contact_id)
        ).mappings().all()

    references: list[dict] = []
    for r in build_rows:
        # The backend has no locale awareness (see house-build-tracking
        # design's name_key/title_key mechanics) -- a seeded, never-edited
        # task falls back to its raw title_key string here rather than a
        # translated title. This is a display-only reference list, not
        # something requiring localization.
        label = r["title_override"] or r["title_key"] or "(untitled task)"
        references.append({"module": "build", "id": r["id"], "label": label})
    for r in work_rows:
        references.append({"module": "works", "id": r["id"], "label": r["title"]})
    for r in cost_rows:
        label = r["notes"] or f"{r['total_amount']:g}"
        references.append({"module": "costs", "id": r["id"], "label": label})
    return references
```

### Step 2: Add usage + delete-protection tests to `test_contacts.py`

Append to `packages/backend/tests/test_contacts.py`:

```python
def test_delete_contact_blocked_when_used_by_work(client, home_id):
    contact = client.post(f"/api/homes/{home_id}/contacts", json={"name": "Metro Plumbing", "typeId": "ctype-supplier"}).json()
    client.post(f"/api/homes/{home_id}/works", json={"title": "Fix sink", "status": "done", "date": "2026-01-01", "contactId": contact["id"]})
    resp = client.delete(f"/api/homes/{home_id}/contacts/{contact['id']}")
    assert resp.status_code == 409
    assert resp.json()["detail"]["references"][0]["module"] == "works"
    # contact must still exist
    assert len(client.get(f"/api/homes/{home_id}/contacts").json()["contacts"]) == 1


def test_delete_contact_blocked_when_used_by_cost_entry(client, home_id):
    contact = client.post(f"/api/homes/{home_id}/contacts", json={"name": "Metro Plumbing", "typeId": "ctype-supplier"}).json()
    client.post(f"/api/homes/{home_id}/costs/entries", json={"categoryId": "cat-fuel", "date": "2026-01-01", "totalAmount": 50.0, "contactId": contact["id"]})
    resp = client.delete(f"/api/homes/{home_id}/contacts/{contact['id']}")
    assert resp.status_code == 409
    assert resp.json()["detail"]["references"][0]["module"] == "costs"


def test_get_contact_usage_reflects_work_reference(client, home_id):
    contact = client.post(f"/api/homes/{home_id}/contacts", json={"name": "Metro Plumbing", "typeId": "ctype-supplier"}).json()
    client.post(f"/api/homes/{home_id}/works", json={"title": "Fix sink", "status": "done", "date": "2026-01-01", "contactId": contact["id"]})
    resp = client.get(f"/api/homes/{home_id}/contacts/{contact['id']}/usage")
    refs = resp.json()["references"]
    assert len(refs) == 1
    assert refs[0]["label"] == "Fix sink"


def test_delete_contact_unblocked_after_reference_removed(client, home_id):
    contact = client.post(f"/api/homes/{home_id}/contacts", json={"name": "Metro Plumbing", "typeId": "ctype-supplier"}).json()
    work = client.post(f"/api/homes/{home_id}/works", json={"title": "Fix sink", "status": "done", "date": "2026-01-01", "contactId": contact["id"]}).json()
    client.put(f"/api/homes/{home_id}/works/{work['id']}", json={"contactId": None})
    resp = client.delete(f"/api/homes/{home_id}/contacts/{contact['id']}")
    assert resp.status_code == 204
```

### Step 3: Run test_contacts.py

Run: `cd packages/backend && python -m pytest tests/test_contacts.py tests/test_contacts_persistence.py -v`
Expected: All PASS.

### Step 4: Commit

```bash
git add packages/backend/src/myhome/persistence_contacts.py packages/backend/tests/test_contacts.py
git commit -m "feat(contacts): implement contact usage lookup and delete protection"
```

---

## Task 5: Backend — MCP tools for Contacts + Build docstring update

**Files:**
- Create: `packages/backend/src/myhome/mcp_tools_contacts.py`
- Modify: `packages/backend/src/myhome/mcp_app.py`
- Modify: `packages/backend/src/myhome/mcp_tools_build.py`
- Test: `packages/backend/tests/test_mcp_tools_contacts.py`

**Interfaces:**
- Consumes: `load_contacts`/`save_contacts`/`get_contact_usage` from Task 3/4.
- Produces: MCP tools `list_contacts`, `create_contact`, `update_contact`, `delete_contact`.

### Step 1: Write `mcp_tools_contacts.py`

```python
# packages/backend/src/myhome/mcp_tools_contacts.py
from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_contacts import Contact
from .persistence_contacts import get_contact_usage, load_contacts, save_contacts


def _list_contacts_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_contacts(resolved).model_dump()


def _create_contact_impl(
    home_id: str | None, name: str, type_id: str,
    company_name: str | None = None, phone: str | None = None,
    email: str | None = None, address: str | None = None,
    website: str | None = None, notes: str = "",
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_contacts(resolved)
    contact = Contact(
        id=str(uuid.uuid4()), name=name, typeId=type_id, companyName=company_name,
        phone=phone, email=email, address=address, website=website, notes=notes,
    )
    doc.contacts.append(contact)
    save_contacts(resolved, doc)
    return contact.model_dump()


def _update_contact_impl(home_id: str | None, contact_id: str, **fields) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_contacts(resolved)
    contact = next((c for c in doc.contacts if c.id == contact_id), None)
    if contact is None:
        raise ValueError(f"Unknown contact_id {contact_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(contact, field, value)
    save_contacts(resolved, doc)
    return contact.model_dump()


def _delete_contact_impl(home_id: str | None, contact_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    usage = get_contact_usage(resolved, contact_id)
    if usage:
        raise ValueError(f"Contact {contact_id!r} is still referenced by: {usage}")
    doc = load_contacts(resolved)
    before = len(doc.contacts)
    doc.contacts = [c for c in doc.contacts if c.id != contact_id]
    if len(doc.contacts) == before:
        raise ValueError(f"Unknown contact_id {contact_id!r}")
    save_contacts(resolved, doc)
    return {"deleted": contact_id}


@mcp.tool()
async def list_contacts(ctx: Context, home_id: str | None = None) -> dict:
    """List contacts (contractors, suppliers, service providers, agents, notaries) for a home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_contacts_impl(home_id)


@mcp.tool()
async def create_contact(
    ctx: Context, name: str, type_id: str, home_id: str | None = None,
    company_name: str | None = None, phone: str | None = None,
    email: str | None = None, address: str | None = None,
    website: str | None = None, notes: str = "",
) -> dict:
    """Create a contact. type_id should match an id from get_settings' contactTypes."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_contact_impl(home_id, name, type_id, company_name, phone, email, address, website, notes)


@mcp.tool()
async def update_contact(
    ctx: Context, contact_id: str, home_id: str | None = None,
    name: str | None = None, type_id: str | None = None,
    company_name: str | None = None, phone: str | None = None,
    email: str | None = None, address: str | None = None,
    website: str | None = None, notes: str | None = None,
) -> dict:
    """Update fields on an existing contact."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_contact_impl(
        home_id, contact_id, name=name, typeId=type_id, companyName=company_name,
        phone=phone, email=email, address=address, website=website, notes=notes,
    )


@mcp.tool()
async def delete_contact(ctx: Context, contact_id: str, home_id: str | None = None) -> dict:
    """Delete a contact. Fails if the contact is still referenced by a build task, work, or cost entry."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_contact_impl(home_id, contact_id)
```

### Step 2: Register in `mcp_app.py`

Open `packages/backend/src/myhome/mcp_app.py`. Add `mcp_tools_contacts,` to the import tuple, alphabetized after `mcp_tools_consumables,` and before `mcp_tools_costs,`.

### Step 3: Update `mcp_tools_build.py`'s docstring

Open `packages/backend/src/myhome/mcp_tools_build.py`. Change:

```python
    """Update a build task's status, contractor, dates, cost, or validation status."""
```

to:

```python
    """Update a build task's status, contractor, dates, cost, or validation status.
    contractor_id should be the id of a Contact (ideally one with type Contractor) from list_contacts."""
```

### Step 4: Write `test_mcp_tools_contacts.py`

```python
# packages/backend/tests/test_mcp_tools_contacts.py
import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_contact(home_id):
    from myhome.mcp_tools_contacts import _create_contact_impl, _list_contacts_impl
    contact = _create_contact_impl(home_id, "Metro Plumbing", "ctype-supplier")
    doc = _list_contacts_impl(home_id)
    assert doc["contacts"][0]["id"] == contact["id"]
    assert doc["contacts"][0]["typeId"] == "ctype-supplier"


def test_update_contact(home_id):
    from myhome.mcp_tools_contacts import _create_contact_impl, _update_contact_impl
    contact = _create_contact_impl(home_id, "Metro Plumbing", "ctype-supplier")
    updated = _update_contact_impl(home_id, contact["id"], phone="555-0000")
    assert updated["phone"] == "555-0000"


def test_delete_contact(home_id):
    from myhome.mcp_tools_contacts import _create_contact_impl, _delete_contact_impl, _list_contacts_impl
    contact = _create_contact_impl(home_id, "Old Supplier", "ctype-supplier")
    _delete_contact_impl(home_id, contact["id"])
    assert _list_contacts_impl(home_id)["contacts"] == []


def test_delete_contact_unknown_id_raises(home_id):
    from myhome.mcp_tools_contacts import _delete_contact_impl
    with pytest.raises(ValueError):
        _delete_contact_impl(home_id, "nonexistent")


def test_delete_contact_blocked_when_used(home_id):
    from myhome.mcp_tools_contacts import _create_contact_impl, _delete_contact_impl
    from myhome.mcp_tools_works import _create_work_impl
    contact = _create_contact_impl(home_id, "Metro Plumbing", "ctype-supplier")
    _create_work_impl(home_id, "Fix sink", "2026-01-01", supplier_id=contact["id"])
    with pytest.raises(ValueError, match="still referenced"):
        _delete_contact_impl(home_id, contact["id"])
```

Note: `_create_work_impl`'s `supplier_id` kwarg name did not change in Task 2 (that renamed the pydantic model field `Work.supplierId`→`Work.contactId`, not the MCP tool's `supplier_id` parameter name) — leave `mcp_tools_works.py` and `mcp_tools_costs.py` untouched; they still pass `supplierId=supplier_id` into `Work(...)`/`CostEntry(...)` construction, which now fails because that field no longer exists. Fix this now: open `packages/backend/src/myhome/mcp_tools_works.py` and change `supplierId=supplier_id,` to `contactId=supplier_id,` in `_create_work_impl`, and in `_update_work_impl`'s caller (`update_work`'s `@mcp.tool()` wrapper) change `supplierId=supplier_id,` to `contactId=supplier_id,`. Do the same in `packages/backend/src/myhome/mcp_tools_costs.py` for its analogous `supplier_id` parameter. (The MCP tool parameter name `supplier_id` itself stays as-is — renaming it would be an MCP API break for existing tool callers; only the internal pydantic field name changed.)

### Step 5: Run the MCP tool test suites

Run: `cd packages/backend && python -m pytest tests/test_mcp_tools_contacts.py tests/test_mcp_tools_works.py tests/test_mcp_tools_costs.py tests/test_mcp_tools_build.py -v`
Expected: All PASS.

### Step 6: Commit

```bash
git add packages/backend/src/myhome/mcp_tools_contacts.py packages/backend/src/myhome/mcp_app.py packages/backend/src/myhome/mcp_tools_build.py packages/backend/src/myhome/mcp_tools_works.py packages/backend/src/myhome/mcp_tools_costs.py packages/backend/tests/test_mcp_tools_contacts.py
git commit -m "feat(contacts): add MCP tools for Contacts, fix Works/Costs MCP field rename fallout"
```

---

## Task 6: Backend — demo data + default enabled modules

**Files:**
- Modify: `packages/backend/src/myhome/models_homes.py`
- Modify: `packages/backend/src/myhome/demo_content.py`
- Modify: `packages/backend/src/myhome/demo_data.py`
- Modify: `packages/backend/src/myhome/persistence_contacts.py` (add `save_contacts` import re-use — no, already exported; just imported in demo_data.py)
- Test: `packages/backend/tests/test_homes.py`
- Test: `packages/backend/tests/test_demo_data.py`

**Interfaces:**
- Consumes: `Contact`/`ContactsDocument` (Task 3), `persistence_contacts.save_contacts` (Task 3).
- Produces: `generate_demo_contacts() -> list[Contact]`; updated `generate_demo_costs(settings, contacts, rng)` / `generate_demo_works(house, settings, contacts, rng)` signatures.

### Step 1: Add "contacts" to default module lists

Open `packages/backend/src/myhome/models_homes.py`. Change:

```python
DEFAULT_EXISTING_MODULES: list[str] = [
    "home", "plan", "chores", "inventory", "consumables", "works", "kb", "costs",
]

DEFAULT_PROJECT_MODULES: list[str] = ["home", "plan", "works", "kb", "build"]
```

to:

```python
DEFAULT_EXISTING_MODULES: list[str] = [
    "home", "plan", "chores", "inventory", "consumables", "works", "kb", "costs", "contacts",
]

DEFAULT_PROJECT_MODULES: list[str] = ["home", "plan", "works", "kb", "build", "contacts"]
```

### Step 2: Add coverage in `test_homes.py`

Add near the existing `test_create_home` assertions in `packages/backend/tests/test_homes.py` (wherever `assert "chores" in data["enabledModules"]` and `assert "works" in data["enabledModules"]` already live, one for the "existing" home creation test and one for "project"):

```python
    assert "contacts" in data["enabledModules"]
```

(Add this line immediately after each of the two existing `assert "chores"/"works" in data["enabledModules"]` lines at lines 26 and 37 respectively.)

### Step 3: Replace `_SUPPLIERS` with `_CONTACTS` in `demo_content.py`

Open `packages/backend/src/myhome/demo_content.py`. Change the import block:

```python
from .models_settings import (
    ConsumableCategory,
    CostCategory,
    InventoryCategory,
    Supplier,
    SettingsDocument,
    WorkCategory,
    _default_consumable_units,
)
```

to:

```python
from .models_contacts import Contact
from .models_settings import (
    ConsumableCategory,
    CostCategory,
    InventoryCategory,
    SettingsDocument,
    WorkCategory,
    _default_consumable_units,
    _default_contact_types,
)
```

Replace the `_SUPPLIERS` list:

```python
_SUPPLIERS = [
    Supplier(id="sup-metro-plumbing", name="Metro Plumbing Co."),
    Supplier(id="sup-brightspark-electric", name="BrightSpark Electric"),
    Supplier(id="sup-greenscape-landscaping", name="GreenScape Landscaping"),
    Supplier(id="sup-ace-hardware", name="Ace Hardware"),
    Supplier(id="sup-cleanpro-services", name="CleanPro Services"),
    Supplier(id="sup-valleyview-appliance-repair", name="ValleyView Appliance Repair"),
    Supplier(id="sup-suntrust-roofing", name="SunTrust Roofing"),
    Supplier(id="sup-clearview-window-gutter", name="ClearView Window & Gutter"),
    Supplier(id="sup-home-comfort-hvac", name="Home Comfort HVAC"),
]
```

with:

```python
_CONTACTS = [
    Contact(id="sup-metro-plumbing", name="Metro Plumbing Co.", typeId="ctype-supplier"),
    Contact(id="sup-brightspark-electric", name="BrightSpark Electric", typeId="ctype-supplier"),
    Contact(id="sup-greenscape-landscaping", name="GreenScape Landscaping", typeId="ctype-service"),
    Contact(id="sup-ace-hardware", name="Ace Hardware", typeId="ctype-supplier"),
    Contact(id="sup-cleanpro-services", name="CleanPro Services", typeId="ctype-service"),
    Contact(id="sup-valleyview-appliance-repair", name="ValleyView Appliance Repair", typeId="ctype-service"),
    Contact(id="sup-suntrust-roofing", name="SunTrust Roofing", typeId="ctype-contractor"),
    Contact(id="sup-clearview-window-gutter", name="ClearView Window & Gutter", typeId="ctype-contractor"),
    Contact(id="sup-home-comfort-hvac", name="Home Comfort HVAC", typeId="ctype-service"),
]
```

Replace `generate_demo_settings()`:

```python
def generate_demo_settings() -> SettingsDocument:
    return SettingsDocument(
        costCategories=list(_COST_CATEGORIES),
        workCategories=list(_WORK_CATEGORIES),
        inventoryCategories=list(_INVENTORY_CATEGORIES),
        consumableCategories=list(_CONSUMABLE_CATEGORIES),
        suppliers=list(_SUPPLIERS),
        consumableUnits=_default_consumable_units(),
    )
```

with:

```python
def generate_demo_settings() -> SettingsDocument:
    return SettingsDocument(
        costCategories=list(_COST_CATEGORIES),
        workCategories=list(_WORK_CATEGORIES),
        inventoryCategories=list(_INVENTORY_CATEGORIES),
        consumableCategories=list(_CONSUMABLE_CATEGORIES),
        contactTypes=_default_contact_types(),
        consumableUnits=_default_consumable_units(),
    )


def generate_demo_contacts() -> list[Contact]:
    return list(_CONTACTS)
```

### Step 4: Update `demo_data.py`

Open `packages/backend/src/myhome/demo_data.py`.

Change the import from `demo_content`:

```python
from .demo_content import (
    CHORES,
    CONSUMABLE_CATEGORY_ROOM_HINTS,
    CONSUMABLES,
    INVENTORY_CATEGORY_ROOM_HINTS,
    INVENTORY_ITEMS,
    KB_CLOSERS,
    KB_OPENERS,
    KB_TITLES,
    WORKS,
    generate_demo_settings,
)
```

to:

```python
from .demo_content import (
    CHORES,
    CONSUMABLE_CATEGORY_ROOM_HINTS,
    CONSUMABLES,
    INVENTORY_CATEGORY_ROOM_HINTS,
    INVENTORY_ITEMS,
    KB_CLOSERS,
    KB_OPENERS,
    KB_TITLES,
    WORKS,
    generate_demo_contacts,
    generate_demo_settings,
)
```

Add `persistence_contacts,` to the `from . import (...)` block (alphabetized, after `persistence_consumables,` and before `persistence_costs,`), and add `from .models_contacts import Contact, ContactsDocument` after the `from .models_costs import ...` line.

Change `generate_demo_costs`'s signature and body:

```python
def generate_demo_costs(settings: SettingsDocument, rng: random.Random) -> CostsDocument:
    today = date.today()
    entries: list[CostEntry] = []
    supplier_ids = [s.id for s in settings.suppliers]
```

to:

```python
def generate_demo_costs(settings: SettingsDocument, contacts: list[Contact], rng: random.Random) -> CostsDocument:
    today = date.today()
    entries: list[CostEntry] = []
    supplier_ids = [c.id for c in contacts if c.typeId in ("ctype-supplier", "ctype-service")]
```

Within the same function, change `supplierId=rng.choice(supplier_ids),` to `contactId=rng.choice(supplier_ids),` (this appears once, in the maintenance-entries loop).

Change `generate_demo_works`'s signature and body:

```python
def generate_demo_works(house: HouseDocument, settings: SettingsDocument, rng: random.Random) -> WorksDocument:
    today = date.today()
    supplier_ids = [s.id for s in settings.suppliers]
```

to:

```python
def generate_demo_works(house: HouseDocument, settings: SettingsDocument, contacts: list[Contact], rng: random.Random) -> WorksDocument:
    today = date.today()
    supplier_ids = [c.id for c in contacts if c.typeId in ("ctype-supplier", "ctype-service")]
```

Within the same function, change both `supplier_id = rng.choice(supplier_ids)` occurrences to stay as-is (local variable name is fine to keep), but change the `Work(...)` construction's `supplierId=supplier_id,` to `contactId=supplier_id,`.

In `seed_demo_home`, change:

```python
def seed_demo_home(home_id: str) -> None:
    rng = random.Random()

    house = generate_demo_house()
    settings = generate_demo_settings()
    chores_doc = generate_demo_chores(house, rng)
    inventory_doc = generate_demo_inventory(house, settings, rng)
    costs_doc = generate_demo_costs(settings, rng)
    works_doc = generate_demo_works(house, settings, rng)
    kb_doc = generate_demo_kb(rng)
    consumables_doc = generate_demo_consumables(house, settings, rng)

    persistence_settings.save_settings(home_id, settings)
    persistence.save_house(home_id, house)
    persistence_chores.save_chores(home_id, chores_doc)
    persistence_inventory.save_inventory(home_id, inventory_doc)
    persistence_costs.save_costs(home_id, costs_doc)
    persistence_works.save_works(home_id, works_doc)
    for entry in kb_doc.entries:
        persistence_kb.save_entry(home_id, entry)
    persistence_consumables.save_consumables(home_id, consumables_doc)
```

to:

```python
def seed_demo_home(home_id: str) -> None:
    rng = random.Random()

    house = generate_demo_house()
    settings = generate_demo_settings()
    contacts = generate_demo_contacts()
    chores_doc = generate_demo_chores(house, rng)
    inventory_doc = generate_demo_inventory(house, settings, rng)
    costs_doc = generate_demo_costs(settings, contacts, rng)
    works_doc = generate_demo_works(house, settings, contacts, rng)
    kb_doc = generate_demo_kb(rng)
    consumables_doc = generate_demo_consumables(house, settings, rng)

    persistence_settings.save_settings(home_id, settings)
    persistence_contacts.save_contacts(home_id, ContactsDocument(contacts=contacts))
    persistence.save_house(home_id, house)
    persistence_chores.save_chores(home_id, chores_doc)
    persistence_inventory.save_inventory(home_id, inventory_doc)
    persistence_costs.save_costs(home_id, costs_doc)
    persistence_works.save_works(home_id, works_doc)
    for entry in kb_doc.entries:
        persistence_kb.save_entry(home_id, entry)
    persistence_consumables.save_consumables(home_id, consumables_doc)
```

(Leave the rest of `seed_demo_home`, including the `attach_demo_files` call and the second round of `save_*` calls after it, unchanged.)

### Step 5: Fix `test_demo_data.py`

Replace the costs-related demo tests (the ones touched in Task 2 Step 7 plus their siblings). Change:

```python
def test_generate_demo_costs_has_at_least_32_entries():
    settings = generate_demo_settings()
    doc = generate_demo_costs(settings, random.Random(42))
    assert len(doc.entries) >= 32


def test_generate_demo_costs_entries_reference_valid_categories_and_suppliers():
    settings = generate_demo_settings()
    doc = generate_demo_costs(settings, random.Random(42))
    category_ids = {c.id for c in settings.costCategories}
    supplier_ids = {s.id for s in settings.suppliers}
    for entry in doc.entries:
        assert entry.categoryId in category_ids
        assert entry.totalAmount > 0
        if entry.supplierId is not None:
            assert entry.supplierId in supplier_ids
```

to:

```python
def test_generate_demo_costs_has_at_least_32_entries():
    settings = generate_demo_settings()
    contacts = generate_demo_contacts()
    doc = generate_demo_costs(settings, contacts, random.Random(42))
    assert len(doc.entries) >= 32


def test_generate_demo_costs_entries_reference_valid_categories_and_contacts():
    settings = generate_demo_settings()
    contacts = generate_demo_contacts()
    doc = generate_demo_costs(settings, contacts, random.Random(42))
    category_ids = {c.id for c in settings.costCategories}
    contact_ids = {c.id for c in contacts}
    for entry in doc.entries:
        assert entry.categoryId in category_ids
        assert entry.totalAmount > 0
        if entry.contactId is not None:
            assert entry.contactId in contact_ids
```

Add `generate_demo_contacts` to the `from myhome.demo_content import generate_demo_settings` line (making it `from myhome.demo_content import generate_demo_contacts, generate_demo_settings`).

Find the remaining call to `generate_demo_costs(settings, random.Random(...))` later in the same file (`test_generate_demo_costs_spread_across_last_12_months` and any others — grep the file for `generate_demo_costs(` to find every call site) and update each to `generate_demo_costs(settings, generate_demo_contacts(), random.Random(...))`.

If `test_demo_data.py` or another test file calls `generate_demo_works(...)`, update those call sites the same way (add `generate_demo_contacts()` as the third positional argument, before `rng`). Search with `grep -n "generate_demo_works(" packages/backend/tests/*.py packages/backend/src/myhome/*.py`.

### Step 6: Run the full demo + homes test suites

Run: `cd packages/backend && python -m pytest tests/test_demo_data.py tests/test_homes.py -v`
Expected: All PASS.

Run the full backend suite to catch any other `generate_demo_works`/`generate_demo_costs` call sites this plan's grep missed:

Run: `cd packages/backend && python -m pytest -x -q`
Expected: All PASS. If a call-site is found broken, fix its arguments per Step 5's pattern and re-run.

### Step 7: Commit

```bash
git add packages/backend/src/myhome/models_homes.py packages/backend/src/myhome/demo_content.py packages/backend/src/myhome/demo_data.py packages/backend/tests/test_homes.py packages/backend/tests/test_demo_data.py
git commit -m "feat(contacts): seed demo contacts, default-enable contacts module for new homes"
```

---

## Task 7: Frontend — `contactsStore.svelte.ts`

**Files:**
- Create: `packages/editor/src/lib/contactsStore.svelte.ts`
- Test: `packages/editor/test/contactsStore.test.ts`

**Interfaces:**
- Produces: `Contact`, `ContactsDocument`, `ContactUsageRef` types and `createContactsStore(getHomeId)` — consumed by Task 8/9/10/11.

### Step 1: Write `contactsStore.svelte.ts`

```typescript
// packages/editor/src/lib/contactsStore.svelte.ts

export interface Contact {
  id: string;
  name: string;
  companyName: string | null;
  typeId: string;
  phone: string | null;
  email: string | null;
  address: string | null;
  website: string | null;
  notes: string;
}

export interface ContactsDocument {
  version: number;
  contacts: Contact[];
}

export interface ContactUsageRef {
  module: string;
  id: string;
  label: string;
}

export function createContactsStore(getHomeId: () => string | null = () => null) {
  const contacts = $state<Contact[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/contacts`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: ContactsDocument = await resp.json();
      contacts.length = 0;
      for (const c of doc.contacts) contacts.push(c);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createContact(data: Omit<Contact, "id">): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/contacts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateContact(id: string, patch: Partial<Omit<Contact, "id">>): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/contacts/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteContact(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/contacts/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function getUsage(id: string): Promise<ContactUsageRef[]> {
    const homeId = getHomeId();
    if (!homeId) return [];
    const resp = await fetch(`/api/homes/${homeId}/contacts/${id}/usage`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    return data.references as ContactUsageRef[];
  }

  init();

  return {
    get contacts() { return contacts as Contact[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createContact,
    updateContact,
    deleteContact,
    getUsage,
    reload: init,
  };
}
```

### Step 2: Write `contactsStore.test.ts`

```typescript
// packages/editor/test/contactsStore.test.ts
import { describe, it, expect, afterEach, vi } from "vitest";
import { createContactsStore } from "../src/lib/contactsStore.svelte";
import type { Contact } from "../src/lib/contactsStore.svelte";

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

function makeContact(overrides: Partial<Contact> = {}): Contact {
  return {
    id: "c1", name: "Metro Plumbing", companyName: null, typeId: "ctype-supplier",
    phone: null, email: null, address: null, website: null, notes: "",
    ...overrides,
  };
}

const emptyDoc = { version: 1, contacts: [] };

describe("contactsStore — init", () => {
  it("loads contacts from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, contacts: [makeContact()] }));
    const store = createContactsStore(getHomeId);
    await tick();
    expect(store.contacts.length).toBe(1);
    expect(store.contacts[0].id).toBe("c1");
    expect(store.loaded).toBe(true);
  });

  it("marks loaded on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("net fail")));
    const store = createContactsStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("net fail");
  });

  it("does not fetch when no homeId provided", async () => {
    const fetchFn = vi.fn();
    vi.stubGlobal("fetch", fetchFn);
    const store = createContactsStore();
    await tick();
    expect(fetchFn).not.toHaveBeenCalled();
    expect(store.loaded).toBe(true);
  });
});

describe("contactsStore — createContact", () => {
  it("posts to /api/homes/{homeId}/contacts and refreshes", async () => {
    const created = makeContact({ id: "c2", name: "New Contact" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, contacts: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createContactsStore(getHomeId);
    await tick();
    await store.createContact({ name: "New Contact", companyName: null, typeId: "ctype-supplier", phone: null, email: null, address: null, website: null, notes: "" });
    await tick();
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/contacts`);
    expect(fetchFn.mock.calls[1][1].method).toBe("POST");
    expect(store.contacts.length).toBe(1);
  });
});

describe("contactsStore — deleteContact", () => {
  it("calls DELETE /api/homes/{homeId}/contacts/{id}", async () => {
    const fetchFn = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createContactsStore(getHomeId);
    await tick();
    await store.deleteContact("c1");
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/contacts/c1`);
    expect(fetchFn.mock.calls[1][1].method).toBe("DELETE");
  });
});

describe("contactsStore — getUsage", () => {
  it("fetches usage references for a contact", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ references: [{ module: "works", id: "w1", label: "Fix sink" }] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createContactsStore(getHomeId);
    await tick();
    const refs = await store.getUsage("c1");
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/contacts/c1/usage`);
    expect(refs).toEqual([{ module: "works", id: "w1", label: "Fix sink" }]);
  });
});
```

### Step 3: Run the test

Run: `cd packages/editor && npx vitest run test/contactsStore.test.ts`
Expected: All PASS.

### Step 4: Commit

```bash
git add packages/editor/src/lib/contactsStore.svelte.ts packages/editor/test/contactsStore.test.ts
git commit -m "feat(contacts): add contactsStore"
```

---

## Task 8: Frontend — ContactsPage, ContactModal, routing, locale

**Files:**
- Create: `packages/editor/src/lib/components/ContactsPage.svelte`
- Create: `packages/editor/src/lib/components/ContactModal.svelte`
- Modify: `packages/editor/src/lib/components/NavMenu.svelte`
- Modify: `packages/editor/src/App.svelte`
- Modify: `packages/editor/src/lib/settingsStore.svelte.ts`
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`
- Test: `packages/editor/test/ContactsPage.test.ts`
- Test: `packages/editor/test/ContactModal.test.ts`

**Interfaces:**
- Consumes: `createContactsStore` (Task 7); `settingsStore.contactTypes` (added in this task's Step 3, backed by Task 1's backend).
- Produces: working `#/contacts` route.

### Step 1: Add `contactTypes` to `settingsStore.svelte.ts`

Open `packages/editor/src/lib/settingsStore.svelte.ts`. Replace the `Supplier` interface:

```typescript
export interface Supplier {
  id: string;
  name: string;
}
```

with:

```typescript
export interface ContactType {
  id: string;
  name: string;
}
```

In `SettingsDocument`, replace `suppliers: Supplier[];` with `contactTypes: ContactType[];`.

In `createSettingsStore`, replace `const suppliers = $state<Supplier[]>([]);` with `const contactTypes = $state<ContactType[]>([]);`.

In `init()`, replace:

```typescript
      suppliers.length = 0;
      for (const s of (doc.suppliers ?? [])) suppliers.push(s);
```

with:

```typescript
      contactTypes.length = 0;
      for (const t of (doc.contactTypes ?? [])) contactTypes.push(t);
```

Replace the `updateSuppliers` function:

```typescript
  async function updateSuppliers(list: Supplier[]): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/settings/suppliers`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(list),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }
```

with:

```typescript
  async function updateContactTypes(list: ContactType[]): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/settings/contact-types`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(list),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }
```

In the returned object, replace `get suppliers() { return suppliers as Supplier[]; },` with `get contactTypes() { return contactTypes as ContactType[]; },`, and `updateSuppliers,` with `updateContactTypes,`.

### Step 2: Write `ContactModal.svelte`

```svelte
<!-- packages/editor/src/lib/components/ContactModal.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createContactsStore, Contact, ContactUsageRef } from "../contactsStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";

  type ContactsStore = ReturnType<typeof createContactsStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    contact: Contact | null;
    store: ContactsStore;
    settingsStore: SettingsStore;
    onclose: () => void;
  }
  let { contact, store, settingsStore, onclose }: Props = $props();

  const isCreate = contact === null;

  let name = $state(contact?.name ?? "");
  let companyName = $state(contact?.companyName ?? "");
  let typeId = $state(contact?.typeId ?? settingsStore.contactTypes[0]?.id ?? "");
  let phone = $state(contact?.phone ?? "");
  let email = $state(contact?.email ?? "");
  let address = $state(contact?.address ?? "");
  let website = $state(contact?.website ?? "");
  let notes = $state(contact?.notes ?? "");

  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let usage = $state<ContactUsageRef[]>([]);
  let usageLoaded = $state(isCreate);

  $effect(() => {
    if (contact) {
      store.getUsage(contact.id).then((refs) => { usage = refs; usageLoaded = true; });
    }
  });

  async function handleSave(): Promise<void> {
    if (!name.trim()) { error = $_('contacts.modal.nameRequired'); return; }
    saving = true; error = null;
    const patch = {
      name: name.trim(),
      companyName: companyName.trim() || null,
      typeId,
      phone: phone.trim() || null,
      email: email.trim() || null,
      address: address.trim() || null,
      website: website.trim() || null,
      notes: notes.trim(),
    };
    try {
      if (isCreate) {
        await store.createContact(patch);
      } else {
        await store.updateContact(contact!.id, patch);
      }
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('contacts.modal.saveFailed');
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!contact) return;
    deleting = true;
    try {
      await store.deleteContact(contact.id);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('contacts.modal.deleteFailed');
      deleting = false;
    }
  }
</script>

<Modal open={true} title={isCreate ? `＋ ${$_('contacts.modal.newContact')}` : $_('contacts.modal.editContact')} {onclose} width="520px">
  <div class="row">
    <label>{$_('contacts.modal.name')} *</label>
    <Input bind:value={name} placeholder={$_('contacts.modal.namePlaceholder')} />
  </div>
  <div class="row">
    <label>{$_('contacts.modal.companyName')}</label>
    <Input bind:value={companyName} placeholder={$_('contacts.modal.companyNamePlaceholder')} />
  </div>
  <div class="row">
    <label>{$_('contacts.modal.type')}</label>
    <select class="native-input" bind:value={typeId}>
      {#each settingsStore.contactTypes as t}
        <option value={t.id}>{t.name}</option>
      {/each}
    </select>
  </div>
  <div class="row-pair">
    <div class="row">
      <label>{$_('contacts.modal.phone')}</label>
      <Input bind:value={phone} />
    </div>
    <div class="row">
      <label>{$_('contacts.modal.email')}</label>
      <Input bind:value={email} />
    </div>
  </div>
  <div class="row">
    <label>{$_('contacts.modal.address')}</label>
    <Input bind:value={address} />
  </div>
  <div class="row">
    <label>{$_('contacts.modal.website')}</label>
    <Input bind:value={website} />
  </div>
  <div class="row">
    <label>{$_('contacts.modal.notes')}</label>
    <textarea class="native-input notes-area" bind:value={notes} rows="3" placeholder={$_('contacts.modal.notesPlaceholder')}></textarea>
  </div>

  {#if !isCreate}
    <div class="row">
      <label>{$_('contacts.modal.usedIn')}</label>
      {#if !usageLoaded}
        <span class="usage-loading">…</span>
      {:else if usage.length === 0}
        <span class="usage-empty">{$_('contacts.modal.notUsed')}</span>
      {:else}
        <ul class="usage-list">
          {#each usage as ref}
            <li>{ref.label} <span class="usage-module">({ref.module})</span></li>
          {/each}
        </ul>
      {/if}
    </div>
  {/if}

  {#if error}<div class="modal-error">{error}</div>{/if}

  {#snippet footer()}
    {#if !isCreate}
      {#if confirmDelete}
        <span class="confirm-text">{$_('contacts.modal.confirm')}?</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>✓ {$_('contacts.modal.confirm')}</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>✕</Button>
      {:else}
        <Button
          variant="danger"
          disabled={usage.length > 0}
          title={usage.length > 0 ? $_('contacts.modal.deleteBlockedByUsage') : undefined}
          onclick={() => { confirmDelete = true; }}
        >🗑 {$_('common.delete')}</Button>
      {/if}
    {/if}
    <span class="spacer"></span>
    <Button variant="primary" disabled={saving} onclick={handleSave}>
      {saving ? $_('settings.security.saving') : isCreate ? $_('settings.security.create') : $_('common.save')}
    </Button>
  {/snippet}
</Modal>

<style>
  .row { display: flex; flex-direction: column; gap: 4px; margin-bottom: var(--space-3); }
  .row-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: var(--space-3); }
  .row-pair .row { margin-bottom: 0; }
  label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans);
    width: 100%; box-sizing: border-box;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  select.native-input { cursor: pointer; }
  .notes-area { resize: vertical; }
  .usage-list { margin: 0; padding-left: 18px; font-size: 12px; color: var(--text-muted); }
  .usage-module { color: var(--text-faint); }
  .usage-empty, .usage-loading { font-size: 12px; color: var(--text-faint); }
  .modal-error { padding: 8px 0 0; font-size: 11px; color: var(--danger); }
  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
</style>
```

### Step 3: Write `ContactsPage.svelte`

```svelte
<!-- packages/editor/src/lib/components/ContactsPage.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createContactsStore, Contact } from "../contactsStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import ContactModal from "./ContactModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";
  import Card from "./ui/Card.svelte";

  type ContactsStore = ReturnType<typeof createContactsStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;

  interface Props {
    store: ContactsStore;
    settingsStore: SettingsStore;
  }
  let { store, settingsStore }: Props = $props();

  let modalContact = $state<Contact | "create" | null>(null);
  let searchQuery = $state("");
  let typeFilter = $state("");

  const typeMap = $derived(new Map(settingsStore.contactTypes.map(t => [t.id, t])));

  const typeCounts = $derived((() => {
    const counts = new Map<string, number>();
    for (const c of store.contacts) counts.set(c.typeId, (counts.get(c.typeId) ?? 0) + 1);
    return counts;
  })());

  const filteredContacts = $derived(store.contacts.filter(c => {
    if (typeFilter && c.typeId !== typeFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!c.name.toLowerCase().includes(q) && !(c.companyName ?? "").toLowerCase().includes(q)) return false;
    }
    return true;
  }));
</script>

<div class="page">
  {#if store.contacts.length === 0}
    <div class="empty-charts">
      <span class="empty-icon">👤</span>
      <p>{$_('contacts.page.emptyCharts')}</p>
    </div>
  {:else}
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-label">{$_('contacts.page.countByType')}</div>
        <div class="stat-chips-row">
          {#each settingsStore.contactTypes as t}
            <div class="stat-chip">
              <div class="stat-title">{t.name}</div>
              <div class="stat-value">{typeCounts.get(t.id) ?? 0}</div>
            </div>
          {/each}
        </div>
      </Card>
    </div>
  {/if}

  <div class="table-card-wrap">
    <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
    <div class="toolbar">
      <Input placeholder={$_('chores.page.search')} bind:value={searchQuery} />
      <select class="native-input filter-sel" bind:value={typeFilter}>
        <option value="">{$_('contacts.page.allTypes')}</option>
        {#each settingsStore.contactTypes as t}
          <option value={t.id}>{t.name}</option>
        {/each}
      </select>
      <Button onclick={() => { modalContact = "create"; }}>＋ {$_('contacts.page.addContact')}</Button>
    </div>

    <div class="table-wrapper">
      {#snippet nameCell(c: Contact)}
        {c.name}
        {#if c.companyName}<span class="desc">{c.companyName}</span>{/if}
      {/snippet}
      {#snippet typeCell(c: Contact)}
        {typeMap.get(c.typeId)?.name ?? "—"}
      {/snippet}
      {#snippet phoneCell(c: Contact)}
        {c.phone ?? "—"}
      {/snippet}
      {#snippet emailCell(c: Contact)}
        {c.email ?? "—"}
      {/snippet}

      <SortableTable
        columns={[
          { key: "name", label: $_('contacts.page.name'), sortValue: (c) => c.name, cellClass: "name-cell", cell: nameCell },
          { key: "type", label: $_('contacts.page.type'), sortValue: (c) => typeMap.get(c.typeId)?.name ?? null, cell: typeCell },
          { key: "phone", label: $_('contacts.page.phone'), sortValue: (c) => c.phone, cell: phoneCell },
          { key: "email", label: $_('contacts.page.email'), sortValue: (c) => c.email, cell: emailCell },
        ] as Column<Contact>[]}
        rows={filteredContacts}
        rowKey={(c) => c.id}
        rowClick={(c) => { modalContact = c; }}
        emptyMessage={store.contacts.length === 0 ? $_('contacts.page.emptyNoContacts') : $_('contacts.page.emptyNoMatch')}
      />
    </div>

    <div class="footer">{$_('contacts.page.footer', { values: { n: filteredContacts.length } })}</div>
    </Card>
  </div>
</div>

{#if modalContact !== null}
  <ContactModal
    contact={modalContact === "create" ? null : modalContact}
    {store}
    {settingsStore}
    onclose={() => { modalContact = null; }}
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
  .chart-label { font-size: 10px; color: var(--text-faint); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
  .stat-chips-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .stat-chip { flex: 1; min-width: 100px; background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 6px 10px; }
  .stat-title { font-size: 8px; color: var(--text-faint); text-transform: uppercase; margin-bottom: 2px; }
  .stat-value { font-size: 13px; color: var(--text); font-weight: 600; }
  .table-card-wrap { flex: 1; min-height: 0; display: flex; padding: 0 var(--space-4) var(--space-4); }
  .toolbar { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3); background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0; }
  .toolbar :global(.ui-input) { flex: 1; }
  .native-input {
    background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); box-sizing: border-box; cursor: pointer;
  }
  .native-input:focus { outline: none; border-color: var(--accent); }
  .filter-sel { cursor: pointer; }
  .table-wrapper { flex: 1; overflow-y: auto; }
  :global(.name-cell) { color: var(--text); font-weight: 600; }
  .desc { font-size: 11px; color: var(--text-faint); font-weight: 400; margin-left: 6px; }
  .footer { padding: var(--space-2) var(--space-4); border-top: 1px solid var(--border); font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
</style>
```

### Step 4: Wire routing in `NavMenu.svelte` and `App.svelte`

Open `packages/editor/src/lib/components/NavMenu.svelte`. Change:

```javascript
    { id: "contacts",    href: "#/contacts",    icon: "👤", placeholder: true },
```

to:

```javascript
    { id: "contacts",    href: "#/contacts",    icon: "👤" },
```

Open `packages/editor/src/App.svelte`. Add near the other store imports (after `import { createBuildStore } from "./lib/buildStore.svelte";`):

```javascript
  import ContactsPage from "./lib/components/ContactsPage.svelte";
  import { createContactsStore } from "./lib/contactsStore.svelte";
```

Add `const contactsStore = createContactsStore(getHomeId);` after `const buildStore = createBuildStore(getHomeId);`.

Add `contactsStore.reload();` to the `$effect` block, after `buildStore.reload();`.

Replace:

```svelte
      {:else if currentRoute === "#/contacts"}
        <PlaceholderPage icon="👤" label={$_('common.modules.contacts')} description={$_('app.placeholder.contactsDescription')} />
```

with:

```svelte
      {:else if currentRoute === "#/contacts"}
        <ContactsPage store={contactsStore} {settingsStore} />
```

### Step 5: Add and remove locale keys

Open `packages/editor/src/lib/locales/en.json`. Remove the `"contactsDescription"` line from the `app.placeholder` block (around line 1075):

```json
    "placeholder": {
      "budgetDescription": "Plan and track your acquisition or build budget.",
      "visitsDescription": "Schedule and log site visits and viewings.",
      "contactsDescription": "Manage agents, notaries, builders, and other contacts.",
      "checklistDescription": "Track tasks and due diligence items for your project."
    },
```

becomes:

```json
    "placeholder": {
      "budgetDescription": "Plan and track your acquisition or build budget.",
      "visitsDescription": "Schedule and log site visits and viewings.",
      "checklistDescription": "Track tasks and due diligence items for your project."
    },
```

Add a new top-level `"contacts"` key. Insert it after the closing `},` of the `"works"` block (after line 491, before `"inventory": {`):

```json
  "contacts": {
    "page": {
      "emptyCharts": "No contacts yet — click ＋ Add contact to get started.",
      "countByType": "Contacts by type",
      "allTypes": "All types",
      "addContact": "Add contact",
      "name": "Name",
      "type": "Type",
      "phone": "Phone",
      "email": "Email",
      "emptyNoContacts": "No contacts yet — click ＋ Add contact to get started.",
      "emptyNoMatch": "No contacts match your filters.",
      "footer": "{n, plural, one {# contact} other {# contacts}}"
    },
    "modal": {
      "newContact": "New contact",
      "editContact": "Edit contact",
      "name": "Name",
      "namePlaceholder": "Contact name",
      "companyName": "Company",
      "companyNamePlaceholder": "Company name",
      "type": "Type",
      "phone": "Phone",
      "email": "Email",
      "address": "Address",
      "website": "Website",
      "notes": "Notes",
      "notesPlaceholder": "Additional notes…",
      "usedIn": "Used in",
      "notUsed": "Not used anywhere yet.",
      "deleteBlockedByUsage": "This contact is used elsewhere and can't be deleted until those references are removed.",
      "nameRequired": "Name is required",
      "saveFailed": "Save failed",
      "deleteFailed": "Delete failed",
      "confirm": "Confirm"
    }
  },
```

Make the identical structural addition (French text) to `packages/editor/src/lib/locales/fr.json` at the same position, and remove `"contactsDescription"` from its `app.placeholder` block too:

```json
  "contacts": {
    "page": {
      "emptyCharts": "Aucun contact pour l'instant — cliquez sur ＋ Ajouter un contact pour commencer.",
      "countByType": "Contacts par type",
      "allTypes": "Tous les types",
      "addContact": "Ajouter un contact",
      "name": "Nom",
      "type": "Type",
      "phone": "Téléphone",
      "email": "E-mail",
      "emptyNoContacts": "Aucun contact pour l'instant — cliquez sur ＋ Ajouter un contact pour commencer.",
      "emptyNoMatch": "Aucun contact ne correspond à vos filtres.",
      "footer": "{n, plural, one {# contact} other {# contacts}}"
    },
    "modal": {
      "newContact": "Nouveau contact",
      "editContact": "Modifier le contact",
      "name": "Nom",
      "namePlaceholder": "Nom du contact",
      "companyName": "Entreprise",
      "companyNamePlaceholder": "Nom de l'entreprise",
      "type": "Type",
      "phone": "Téléphone",
      "email": "E-mail",
      "address": "Adresse",
      "website": "Site web",
      "notes": "Notes",
      "notesPlaceholder": "Notes complémentaires…",
      "usedIn": "Utilisé dans",
      "notUsed": "Pas encore utilisé.",
      "deleteBlockedByUsage": "Ce contact est utilisé ailleurs et ne peut pas être supprimé tant que ces références ne sont pas retirées.",
      "nameRequired": "Le nom est requis",
      "saveFailed": "Échec de l'enregistrement",
      "deleteFailed": "Échec de la suppression",
      "confirm": "Confirmer"
    }
  },
```

### Step 6: Write `ContactsPage.test.ts` and `ContactModal.test.ts`

```typescript
// packages/editor/test/ContactsPage.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import ContactsPage from "../src/lib/components/ContactsPage.svelte";
import { createContactsStore } from "../src/lib/contactsStore.svelte";
import { createSettingsStore } from "../src/lib/settingsStore.svelte";

const HOME = "home-1";

function stubFetch(contacts: unknown[], contactTypes: unknown[]) {
  vi.stubGlobal("fetch", vi.fn((url: string) => {
    if (url.includes("/contacts")) {
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ version: 1, contacts }) });
    }
    if (url.includes("/settings")) {
      return Promise.resolve({
        ok: true, status: 200,
        json: async () => ({
          version: 1, costCategories: [], inventoryCategories: [], workCategories: [],
          contactTypes, consumableUnits: [], consumableCategories: [],
          notifications: { enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30, haPushEnabled: false, haNotifyService: null, haPushTime: "08:00" },
        }),
      });
    }
    return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
  }));
}

afterEach(() => vi.unstubAllGlobals());

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

describe("ContactsPage", () => {
  it("shows empty state with no contacts", async () => {
    stubFetch([], [{ id: "ctype-supplier", name: "Supplier" }]);
    const store = createContactsStore(() => HOME);
    const settingsStore = createSettingsStore(() => HOME);
    await tick();
    render(ContactsPage, { store, settingsStore });
    expect(screen.getByText(/No contacts yet/)).toBeTruthy();
  });

  it("renders a contact row and opens the modal on click", async () => {
    stubFetch(
      [{ id: "c1", name: "Metro Plumbing", companyName: null, typeId: "ctype-supplier", phone: null, email: null, address: null, website: null, notes: "" }],
      [{ id: "ctype-supplier", name: "Supplier" }],
    );
    const store = createContactsStore(() => HOME);
    const settingsStore = createSettingsStore(() => HOME);
    await tick();
    render(ContactsPage, { store, settingsStore });
    await tick();
    const row = screen.getByText("Metro Plumbing");
    await fireEvent.click(row);
    expect(screen.getByText("Edit contact")).toBeTruthy();
  });
});
```

```typescript
// packages/editor/test/ContactModal.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import ContactModal from "../src/lib/components/ContactModal.svelte";
import { createContactsStore } from "../src/lib/contactsStore.svelte";
import { createSettingsStore } from "../src/lib/settingsStore.svelte";

const HOME = "home-1";

afterEach(() => vi.unstubAllGlobals());

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

describe("ContactModal", () => {
  it("disables delete when the contact is in use", async () => {
    vi.stubGlobal("fetch", vi.fn((url: string) => {
      if (url.endsWith("/usage")) {
        return Promise.resolve({ ok: true, status: 200, json: async () => ({ references: [{ module: "works", id: "w1", label: "Fix sink" }] }) });
      }
      if (url.includes("/settings")) {
        return Promise.resolve({
          ok: true, status: 200,
          json: async () => ({
            version: 1, costCategories: [], inventoryCategories: [], workCategories: [],
            contactTypes: [{ id: "ctype-supplier", name: "Supplier" }], consumableUnits: [], consumableCategories: [],
            notifications: { enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30, haPushEnabled: false, haNotifyService: null, haPushTime: "08:00" },
          }),
        });
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ version: 1, contacts: [] }) });
    }));
    const store = createContactsStore(() => HOME);
    const settingsStore = createSettingsStore(() => HOME);
    await tick();
    const contact = { id: "c1", name: "Metro Plumbing", companyName: null, typeId: "ctype-supplier", phone: null, email: null, address: null, website: null, notes: "" };
    render(ContactModal, { contact, store, settingsStore, onclose: () => {} });
    await tick();
    const deleteButton = screen.getByText(/Delete/) as HTMLButtonElement;
    expect(deleteButton.disabled).toBe(true);
    expect(screen.getByText("Fix sink")).toBeTruthy();
  });
});
```

### Step 7: Run the frontend tests

Run: `cd packages/editor && npx vitest run test/ContactsPage.test.ts test/ContactModal.test.ts`
Expected: All PASS.

### Step 8: Commit

```bash
git add packages/editor/src/lib/components/ContactsPage.svelte packages/editor/src/lib/components/ContactModal.svelte packages/editor/src/lib/components/NavMenu.svelte packages/editor/src/App.svelte packages/editor/src/lib/settingsStore.svelte.ts packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/ContactsPage.test.ts packages/editor/test/ContactModal.test.ts
git commit -m "feat(contacts): add ContactsPage, ContactModal, wire routing and locale"
```

---

## Task 9: Frontend — Settings "Contact Types" tab (replace Suppliers)

**Files:**
- Modify: `packages/editor/src/lib/components/settings/SettingsCategories.svelte`
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`
- Test: `packages/editor/test/SettingsCategories.test.ts`

**Interfaces:**
- Consumes: `settingsStore.contactTypes` / `updateContactTypes` (Task 8 Step 1).

### Step 1: Update the locale tab label

Open `packages/editor/src/lib/locales/en.json`. In `settings.categories.tabs` (around line 876), change `"suppliers": "Suppliers",` to `"contactTypes": "Contact Types",`.

Make the same change in `packages/editor/src/lib/locales/fr.json` (around line 876): change `"suppliers": "Fournisseurs",` to `"contactTypes": "Types de contact",`.

### Step 2: Update the import and tab type in `SettingsCategories.svelte`

Open `packages/editor/src/lib/components/settings/SettingsCategories.svelte`. Change:

```typescript
  import type { createSettingsStore, CostCategory, ConsumableCategory, InventoryCategory, WorkCategory, Supplier } from "../../settingsStore.svelte";
```

to:

```typescript
  import type { createSettingsStore, CostCategory, ConsumableCategory, InventoryCategory, WorkCategory, ContactType } from "../../settingsStore.svelte";
```

Change:

```typescript
  type CategoryTab = "cost" | "inventory" | "work" | "suppliers" | "consumables";
```

to:

```typescript
  type CategoryTab = "cost" | "inventory" | "work" | "contactTypes" | "consumables";
```

### Step 3: Replace the Suppliers script block

Replace the entire `// --- Suppliers ---` block:

```typescript
  // --- Suppliers ---
  let editingSupplierId = $state<string | null>(null);
  let supplierDraft = $state<Supplier>({ id: "", name: "" });
  let showNewSupplierForm = $state(false);
  let newSupplierDraft = $state({ name: "" });
  let confirmDeleteSupplierId = $state<string | null>(null);
  let supplierError = $state<string | null>(null);

  function startEditSupplier(s: Supplier): void {
    editingSupplierId = s.id;
    supplierDraft = { ...s };
    supplierError = null;
  }

  function cancelEditSupplier(): void { editingSupplierId = null; supplierError = null; }

  async function saveEditSupplier(): Promise<void> {
    if (!supplierDraft.name.trim()) { supplierError = $_('settings.general.nameRequired'); return; }
    const updated = store.suppliers.map(s =>
      s.id === editingSupplierId ? { ...supplierDraft, name: supplierDraft.name.trim() } : s
    );
    await store.updateSuppliers(updated);
    editingSupplierId = null; supplierError = null;
  }

  async function deleteSupplier(id: string): Promise<void> {
    await store.updateSuppliers(store.suppliers.filter(s => s.id !== id));
    confirmDeleteSupplierId = null;
  }

  async function addSupplier(): Promise<void> {
    if (!newSupplierDraft.name.trim()) { supplierError = $_('settings.general.nameRequired'); return; }
    const newS: Supplier = {
      id: crypto.randomUUID(),
      name: newSupplierDraft.name.trim(),
    };
    await store.updateSuppliers([...store.suppliers, newS]);
    newSupplierDraft = { name: "" };
    showNewSupplierForm = false;
    supplierError = null;
  }
```

with:

```typescript
  // --- Contact types ---
  let editingContactTypeId = $state<string | null>(null);
  let contactTypeDraft = $state<ContactType>({ id: "", name: "" });
  let showNewContactTypeForm = $state(false);
  let newContactTypeDraft = $state({ name: "" });
  let confirmDeleteContactTypeId = $state<string | null>(null);
  let contactTypeError = $state<string | null>(null);

  function startEditContactType(t: ContactType): void {
    editingContactTypeId = t.id;
    contactTypeDraft = { ...t };
    contactTypeError = null;
  }

  function cancelEditContactType(): void { editingContactTypeId = null; contactTypeError = null; }

  async function saveEditContactType(): Promise<void> {
    if (!contactTypeDraft.name.trim()) { contactTypeError = $_('settings.general.nameRequired'); return; }
    const updated = store.contactTypes.map(t =>
      t.id === editingContactTypeId ? { ...contactTypeDraft, name: contactTypeDraft.name.trim() } : t
    );
    await store.updateContactTypes(updated);
    editingContactTypeId = null; contactTypeError = null;
  }

  async function deleteContactType(id: string): Promise<void> {
    await store.updateContactTypes(store.contactTypes.filter(t => t.id !== id));
    confirmDeleteContactTypeId = null;
  }

  async function addContactType(): Promise<void> {
    if (!newContactTypeDraft.name.trim()) { contactTypeError = $_('settings.general.nameRequired'); return; }
    const newT: ContactType = {
      id: crypto.randomUUID(),
      name: newContactTypeDraft.name.trim(),
    };
    await store.updateContactTypes([...store.contactTypes, newT]);
    newContactTypeDraft = { name: "" };
    showNewContactTypeForm = false;
    contactTypeError = null;
  }
```

### Step 4: Replace the Tabs config entry

Change:

```svelte
    { id: "suppliers", label: $_('settings.categories.tabs.suppliers') },
```

to:

```svelte
    { id: "contactTypes", label: $_('settings.categories.tabs.contactTypes') },
```

(in the `<Tabs tabs={[...]}>` array in the template.)

### Step 5: Replace the Suppliers template block

Replace the entire `{#if activeTab === "suppliers"} ... {/if}` block with:

```svelte
{#if activeTab === "contactTypes"}
  <Card>
    <div class="section-header">
      <h2>{$_('settings.categories.tabs.contactTypes')}</h2>
      <Button onclick={() => { showNewContactTypeForm = true; contactTypeError = null; }}>＋ {$_('common.add')}</Button>
    </div>
    <div class="table-wrapper">
      {#snippet contactTypeNameCell(t: ContactType)}
        {#if editingContactTypeId === t.id}
          <Input bind:value={contactTypeDraft.name} placeholder={$_('settings.categories.name')} />
        {:else}
          {t.name}
        {/if}
      {/snippet}
      {#snippet contactTypeActionsCell(t: ContactType)}
        {#if editingContactTypeId === t.id}
          <button class="icon-action ok" onclick={saveEditContactType} title={$_('common.save')}>✓</button>
          <button class="icon-action" onclick={cancelEditContactType} title={$_('common.cancel')}>✕</button>
        {:else if confirmDeleteContactTypeId === t.id}
          <span class="confirm-text">{$_('settings.categories.deleteConfirm')}</span>
          <button class="icon-action danger" onclick={() => deleteContactType(t.id)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteContactTypeId = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => startEditContactType(t)} title={$_('common.edit')}>✏</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteContactTypeId = t.id; }} title={$_('common.delete')}>🗑</button>
        {/if}
      {/snippet}
      {#snippet contactTypeNewRow()}
        <td class="name-cell-input wide"><Input bind:value={newContactTypeDraft.name} placeholder={$_('settings.categories.nameRequiredPlaceholder')} /></td>
        <td class="actions">
          <button class="icon-action ok" onclick={addContactType} title={$_('common.add')}>✓</button>
          <button class="icon-action" onclick={() => { showNewContactTypeForm = false; contactTypeError = null; }} title={$_('common.cancel')}>✕</button>
        </td>
      {/snippet}
      <SortableTable
        columns={[
          { key: "name", label: $_('settings.categories.name'), sortValue: (t) => t.name, cellClass: (t) => editingContactTypeId === t.id ? "name-cell-input wide" : "", cell: contactTypeNameCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: contactTypeActionsCell },
        ] as Column<ContactType>[]}
        rows={store.contactTypes}
        rowKey={(t) => t.id}
        rowClass={(t) => editingContactTypeId === t.id ? "editing-row" : ""}
        extraRow={showNewContactTypeForm ? contactTypeNewRow : undefined}
      />
    </div>
    {#if contactTypeError}<div class="error">{contactTypeError}</div>{/if}
  </Card>
{/if}
```

### Step 6: Update `SettingsCategories.test.ts`

Open `packages/editor/test/SettingsCategories.test.ts`. Find any test referencing the `suppliers` tab or `store.suppliers`/`updateSuppliers` mock data and rename to `contactTypes`/`store.contactTypes`/`updateContactTypes`, following the same rename pattern as the component (e.g. a mock settings store fixture with `suppliers: []` becomes `contactTypes: []`; a test clicking the "Suppliers" tab label becomes "Contact Types"). Read the file first to find exact line numbers before editing — its structure exactly mirrors the component's five tabs, so apply the same substitution used in Steps 2-5 above wherever the test exercises the suppliers tab specifically. If the file only tests the cost/inventory/work tabs and never touches suppliers, no change is needed (verify with `grep -n "supplier" packages/editor/test/SettingsCategories.test.ts` before assuming skip).

### Step 7: Run the test

Run: `cd packages/editor && npx vitest run test/SettingsCategories.test.ts`
Expected: All PASS.

### Step 8: Commit

```bash
git add packages/editor/src/lib/components/settings/SettingsCategories.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/SettingsCategories.test.ts
git commit -m "feat(contacts): replace Suppliers settings tab with Contact Types"
```

---

## Task 10: Frontend — WorkModal & CostsEntryModal → contactId select

**Files:**
- Modify: `packages/editor/src/lib/worksStore.svelte.ts`
- Modify: `packages/editor/src/lib/costsStore.svelte.ts`
- Modify: `packages/editor/src/lib/components/WorkModal.svelte`
- Modify: `packages/editor/src/lib/components/WorksPage.svelte`
- Modify: `packages/editor/src/lib/components/CostsEntryModal.svelte`
- Modify: `packages/editor/src/lib/components/CostsPage.svelte`
- Modify: `packages/editor/src/App.svelte`
- Test: `packages/editor/test/worksStore.test.ts`
- Test: `packages/editor/test/WorksPage.test.ts`
- Test: `packages/editor/test/WorkModal.test.ts`
- Test: `packages/editor/test/CostsPage.test.ts`
- Test: `packages/editor/test/CostsEntryModal.test.ts`
- Test: `packages/editor/test/searchIndex.test.ts`
- Test: `packages/editor/test/HomeWorksWidget.test.ts`
- Test: `packages/editor/test/HomeCostsWidget.test.ts`
- Test: `packages/editor/test/WorksTimeline.test.ts`

**Interfaces:**
- Consumes: `Work.contactId`/`CostEntry.contactId` from Task 2 (backend); `createContactsStore`, `Contact` from Task 7.

### Step 1: Rename `supplierId` → `contactId` in the TS interfaces

Open `packages/editor/src/lib/worksStore.svelte.ts`. Change `supplierId: string | null;` to `contactId: string | null;` in the `Work` interface.

Open `packages/editor/src/lib/costsStore.svelte.ts`. Change `supplierId: string | null;` to `contactId: string | null;` in the `CostEntry` interface.

### Step 2: Rename every `supplierId` reference across test/mock fixtures

Run `grep -n "supplierId" packages/editor/test/*.ts` from `packages/editor/`. For each hit in `worksStore.test.ts`, `WorksPage.test.ts`, `WorkModal.test.ts`, `CostsPage.test.ts`, `CostsEntryModal.test.ts`, `searchIndex.test.ts`, `HomeWorksWidget.test.ts`, `HomeCostsWidget.test.ts`, `WorksTimeline.test.ts` — mechanically rename `supplierId` to `contactId` (both the object-literal key in mock `Work`/`CostEntry` fixtures, e.g. `makeWork({ ..., supplierId: null })` → `makeWork({ ..., contactId: null })`, and any assertion referencing `.supplierId`). This is a pure rename with no logic change — every one of these fixtures is constructing a `Work`/`CostEntry`-shaped object that must match the renamed interface field or TypeScript will fail to compile the test.

### Step 3: Rebind `WorkModal.svelte` to `contactsStore`

Open `packages/editor/src/lib/components/WorkModal.svelte`. Add an import and prop:

```typescript
  import type { createContactsStore } from "../contactsStore.svelte";
```

Add `type ContactsStore = ReturnType<typeof createContactsStore>;` next to the other type aliases, and add `contactsStore: ContactsStore;` to the `Props` interface, and `contactsStore` to the destructured props.

Change `let supplierId = $state(work?.supplierId ?? "");` to `let contactId = $state(work?.contactId ?? "");`.

In `handleSave`, change `supplierId: supplierId || null,` to `contactId: contactId || null,`.

Replace the supplier `<select>` block:

```svelte
    <div class="row">
      <label>{$_('costs.entryModal.supplier')}</label>
      <select class="native-input" bind:value={supplierId}>
        <option value="">{$_('works.modal.noneOption')}</option>
        {#each settingsStore.suppliers as s}
          <option value={s.id}>{s.name}</option>
        {/each}
      </select>
    </div>
```

with:

```svelte
    <div class="row">
      <label>{$_('costs.entryModal.supplier')}</label>
      <select class="native-input" bind:value={contactId}>
        <option value="">{$_('works.modal.noneOption')}</option>
        {#each contactsStore.contacts.filter(c => c.typeId === "ctype-supplier" || c.typeId === "ctype-service") as c}
          <option value={c.id}>{c.name}</option>
        {/each}
      </select>
    </div>
```

### Step 4: Thread `contactsStore` through `WorksPage.svelte` and `App.svelte`

Open `packages/editor/src/lib/components/WorksPage.svelte`. Add `import type { createContactsStore } from "../contactsStore.svelte";`, `type ContactsStore = ReturnType<typeof createContactsStore>;`, add `contactsStore: ContactsStore;` to `Props`, and `contactsStore` to the destructured props.

Replace `supplierMap`:

```typescript
  const supplierMap = $derived(
    new Map(settingsStore.suppliers.map(s => [s.id, s]))
  );
```

with:

```typescript
  const supplierMap = $derived(
    new Map(contactsStore.contacts.map(c => [c.id, c]))
  );
```

(The rest of `WorksPage.svelte` — the `supplierCell` snippet and the `supplier` column's `sortValue`/`cell` — already reads `work.supplierId`/`supplierMap`; update those two remaining `work.supplierId` reads to `work.contactId`, keeping `supplierMap`'s name as-is since it's a local display variable name and not part of any public interface.)

Pass `{contactsStore}` down to the `<WorkModal>` instantiation at the bottom of the file.

Open `packages/editor/src/App.svelte`. Add `{contactsStore}` to the `<WorksPage store={worksStore} {settingsStore} ...>` invocation (around line 1256-1270).

### Step 5: Rebind `CostsEntryModal.svelte` to `contactsStore`

Open `packages/editor/src/lib/components/CostsEntryModal.svelte`. Add the same `contactsStore` prop pattern as Step 3 (import, type alias, `Props` field, destructure).

Change `let supplierId = $state("");` to `let contactId = $state("");`, and the `$effect` block's `supplierId = entry?.supplierId ?? "";` to `contactId = entry?.contactId ?? "";`.

In `handleSave`, change `supplierId: supplierId || null,` to `contactId: contactId || null,`.

Replace:

```svelte
    <div class="row">
      <label>{$_('costs.entryModal.supplier')}</label>
      <select class="native-input flex-grow" bind:value={supplierId}>
        <option value="">{$_('costs.entryModal.noSupplier')}</option>
        {#each settingsStore.suppliers as s}<option value={s.id}>{s.name}</option>{/each}
      </select>
    </div>
```

with:

```svelte
    <div class="row">
      <label>{$_('costs.entryModal.supplier')}</label>
      <select class="native-input flex-grow" bind:value={contactId}>
        <option value="">{$_('costs.entryModal.noSupplier')}</option>
        {#each contactsStore.contacts.filter(c => c.typeId === "ctype-supplier" || c.typeId === "ctype-service") as c}<option value={c.id}>{c.name}</option>{/each}
      </select>
    </div>
```

### Step 6: Thread `contactsStore` through `CostsPage.svelte` and `App.svelte`

Open `packages/editor/src/lib/components/CostsPage.svelte`. Add the `contactsStore` prop (import/type/Props field/destructure), then replace:

```typescript
  const supplierMap = $derived(
    new Map(settingsStore.suppliers.map(s => [s.id, s]))
  );
```

with:

```typescript
  const supplierMap = $derived(
    new Map(contactsStore.contacts.map(c => [c.id, c]))
  );
```

Update the three `e.supplierId` reads (line 99's search filter, line 273-274's `supplierCell` snippet, line 294's column `sortValue`) to `e.contactId`. Pass `{contactsStore}` to the `<CostsEntryModal>` invocation.

Open `packages/editor/src/App.svelte`. Add `{contactsStore}` to the `<CostsPage {costsStore} {settingsStore} {floorStore} ...>` invocation (around line 1276-1290).

### Step 7: Run the full frontend test suite

Run: `cd packages/editor && npx vitest run`
Expected: All PASS. Fix any remaining `supplierId`/`.suppliers` references vitest's TypeScript compilation surfaces that this plan's grep in Step 2 missed (e.g. a `searchIndex.ts` source file itself, not just its test, may reference `w.supplierId` — check `packages/editor/src/lib/searchIndex.ts` with `grep -n supplierId` and rename there too if found).

### Step 8: Commit

```bash
git add packages/editor/src/lib/worksStore.svelte.ts packages/editor/src/lib/costsStore.svelte.ts packages/editor/src/lib/components/WorkModal.svelte packages/editor/src/lib/components/WorksPage.svelte packages/editor/src/lib/components/CostsEntryModal.svelte packages/editor/src/lib/components/CostsPage.svelte packages/editor/src/App.svelte packages/editor/test
git commit -m "feat(contacts): rebind Work/Costs supplier picker to Contacts"
```

---

## Task 11: Frontend — TaskModal contractor dropdown

**Files:**
- Modify: `packages/editor/src/lib/components/TaskModal.svelte`
- Modify: `packages/editor/src/App.svelte`
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`
- Test: `packages/editor/test/TaskModal.test.ts` (create if it doesn't exist, else extend)

**Interfaces:**
- Consumes: `createContactsStore`, `Contact` (Task 7).

### Step 1: Update locale — drop the free-text placeholder key

Open `packages/editor/src/lib/locales/en.json`. In the `build.modal` block, remove the line `"contractorPlaceholder": "Contractor name",` (line 61) — the field becomes a `<select>` and reuses the already-existing `"noneOption": "— None —"` key for its empty option.

Make the identical removal in `packages/editor/src/lib/locales/fr.json` (line 61, `"contractorPlaceholder": "Nom de l'entrepreneur",`).

### Step 2: Rebind `TaskModal.svelte`

Open `packages/editor/src/lib/components/TaskModal.svelte`. Add an import and prop:

```typescript
  import type { createContactsStore } from "../contactsStore.svelte";
```

Add `type ContactsStore = ReturnType<typeof createContactsStore>;`, add `contactsStore: ContactsStore;` to `Props`, and `contactsStore` to the destructured props.

Replace:

```svelte
      <div class="row">
        <label>{$_('build.modal.contractor')}</label>
        <Input bind:value={contractorId} placeholder={$_('build.modal.contractorPlaceholder')} />
      </div>
```

with:

```svelte
      <div class="row">
        <label>{$_('build.modal.contractor')}</label>
        <select class="native-input" bind:value={contractorId}>
          <option value="">{$_('build.modal.noneOption')}</option>
          {#each contactsStore.contacts.filter(c => c.typeId === "ctype-contractor") as c}
            <option value={c.id}>{c.name}</option>
          {/each}
        </select>
      </div>
```

(`contractorId`'s `$state` declaration and its use in `handleSave`'s `patch` object stay unchanged — only the input widget changes.)

The `Input` import at the top of the file may now be unused if nothing else in `TaskModal.svelte` uses `<Input>` — check with `grep -n "<Input" packages/editor/src/lib/components/TaskModal.svelte`; if the only remaining reference was this one, remove the `import Input from "./ui/Input.svelte";` line too (it's currently used for the title field as well — `<input class="task-title-input native-input" bind:value={title} .../>` at line 142 is a plain HTML `<input>`, not the `Input` component, so double-check: if `Input` truly has no remaining usages, remove the import; otherwise leave it).

### Step 3: Wire `contactsStore` in `App.svelte`

Open `packages/editor/src/App.svelte`. Add `{contactsStore}` to the `<TaskModal>` invocation:

```svelte
{#if openBuildTaskId}
  <TaskModal
    task={buildStore.tasks.find((t) => t.id === openBuildTaskId) ?? null}
    store={buildStore}
    onclose={() => { openBuildTaskId = null; }}
  />
{/if}
```

becomes:

```svelte
{#if openBuildTaskId}
  <TaskModal
    task={buildStore.tasks.find((t) => t.id === openBuildTaskId) ?? null}
    store={buildStore}
    {contactsStore}
    onclose={() => { openBuildTaskId = null; }}
  />
{/if}
```

### Step 4: Write/extend `TaskModal.test.ts`

Check whether `packages/editor/test/TaskModal.test.ts` already exists (`ls packages/editor/test/TaskModal.test.ts`). If it exists, read it fully first and add a `contactsStore` prop (with a minimal stub store shaped like `{ contacts: [...] }`) to every existing `render(TaskModal, {...})` call so the tests keep compiling and passing, then add the following new test. If it does not exist, create it fresh:

```typescript
// packages/editor/test/TaskModal.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import TaskModal from "../src/lib/components/TaskModal.svelte";
import { createBuildStore } from "../src/lib/buildStore.svelte";
import { createContactsStore } from "../src/lib/contactsStore.svelte";

const HOME = "home-1";

afterEach(() => vi.unstubAllGlobals());

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

describe("TaskModal — contractor dropdown", () => {
  it("lists only ctype-contractor contacts", async () => {
    vi.stubGlobal("fetch", vi.fn((url: string) => {
      if (url.includes("/contacts")) {
        return Promise.resolve({
          ok: true, status: 200,
          json: async () => ({
            version: 1,
            contacts: [
              { id: "c1", name: "SunTrust Roofing", companyName: null, typeId: "ctype-contractor", phone: null, email: null, address: null, website: null, notes: "" },
              { id: "c2", name: "Metro Plumbing", companyName: null, typeId: "ctype-supplier", phone: null, email: null, address: null, website: null, notes: "" },
            ],
          }),
        });
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ version: 1, project: null, phases: [], tasks: [], dependencies: [] }) });
    }));
    const buildStore = createBuildStore(() => HOME);
    const contactsStore = createContactsStore(() => HOME);
    await tick();
    const task = {
      id: "t1", phaseId: "p1", parentTaskId: null, displayOrder: 0,
      titleKey: null, titleOverride: "Foundation pour", descriptionKey: null, descriptionOverride: "",
      status: "not_started" as const, plannedStartDate: null, plannedDueDate: null, actualCompletionDate: null,
      plannedCost: null, actualCost: null, contractorId: null, validationRequired: false,
      validationStatus: "not_required" as const, notes: "", attachments: [],
    };
    render(TaskModal, { task, store: buildStore, contactsStore, onclose: () => {} });
    await tick();
    expect(screen.getByText("SunTrust Roofing")).toBeTruthy();
    expect(screen.queryByText("Metro Plumbing")).toBeNull();
  });
});
```

### Step 5: Run the test

Run: `cd packages/editor && npx vitest run test/TaskModal.test.ts`
Expected: All PASS.

### Step 6: Run the complete frontend and backend suites once more

Run: `cd packages/editor && npx vitest run`
Run: `cd packages/backend && python -m pytest -q`
Expected: All PASS in both.

### Step 7: Commit

```bash
git add packages/editor/src/lib/components/TaskModal.svelte packages/editor/src/App.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/TaskModal.test.ts
git commit -m "feat(contacts): rebind build task contractor field to Contacts dropdown"
```

---

## Task 12: Manual verification

Use the `webapp-testing` skill to drive the running app in a real browser before calling this feature done.

- [ ] Start the dev server (backend + frontend) per this repo's existing dev-server recipe.
- [ ] Log in, open Settings > Modules, confirm "Contacts" is enabled by default on an existing-type home (or enable it if testing against a home created before this change).
- [ ] Navigate to Settings > the categories/suppliers area, confirm the tab now reads "Contact Types" with the 6 seeded defaults (Contractor, Supplier, Service Provider, Agent, Notary, Other), and that add/edit/delete works there.
- [ ] Navigate to `#/contacts`. Confirm the empty state (if no contacts yet) or the summary-cards-by-type + table layout renders.
- [ ] Add one contact of each default type (at least a Contractor and a Supplier), with full fields (company, phone, email, address, website, notes).
- [ ] Open a contact's edit view and confirm "Used in" shows "Not used anywhere yet."
- [ ] Go to Works, create/edit a work, confirm the "Supplier" dropdown lists the Supplier/Service Provider contacts (not the Contractor) and can be saved.
- [ ] Go to Costs, create/edit a cost entry, confirm the same supplier dropdown behavior.
- [ ] Go to Build (start tracking if not already started), open a task, confirm the "Contractor" field is now a dropdown listing only Contractor-typed contacts, and can be saved.
- [ ] Return to the Contact used by that work/cost/task and confirm its "Used in" panel now lists all three references with sensible labels.
- [ ] Attempt to delete that in-use contact from the Contacts page — confirm the Delete button is disabled with an explanatory tooltip.
- [ ] Unlink the contact from all three records (set each back to "— None —" / empty), then delete it successfully.
- [ ] Spin up (or use an existing) demo home; confirm it seeds contacts (visible on `#/contacts`) and that its Works/Costs demo records display resolved contact names rather than "—".
- [ ] Switch locale to French and spot-check the Contacts page, Contact modal, and the renamed Contact Types settings tab render translated text with no missing-key fallbacks.

If any step fails, return to the relevant task above, fix it, add/adjust a regression test, and re-run the affected test suite before re-verifying manually.

---

## Task 13: Final full-suite verification

- [ ] Run: `cd packages/backend && python -m pytest -q` — expect all pass, no skips due to import errors.
- [ ] Run: `cd packages/editor && npx vitest run` — expect all pass.
- [ ] Run: `cd packages/editor && npx tsc --noEmit` (or this repo's equivalent typecheck command — check `package.json` scripts if the exact invocation differs) — expect no type errors, confirming every `supplierId`→`contactId` rename site across the frontend was caught.
- [ ] `git log --oneline` over this branch's commits to confirm all 11 feature commits plus this task's are present and nothing was left uncommitted (`git status`).

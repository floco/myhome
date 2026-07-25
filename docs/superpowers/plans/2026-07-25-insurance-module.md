# Insurance Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `#/insurance` placeholder with a full policy-tracking module (categories, provider, dates, premium, coverage links/attachments, alternatives) that mirrors the Works module's backend shape, plus a per-record toggle that auto-syncs a policy's premium into the Costs module only when flagged (e.g. home insurance, not travel/life).

**Architecture:** SQLite via SQLAlchemy Core (`schema.py`/`persistence_insurance.py`, whole-document load/save per home, same as Works/Costs). A per-home editable `insurance_categories` list follows the Work/Inventory/Consumable category pattern. Cost sync is implemented in `routes/insurance.py` by directly mutating the Costs document (`load_costs`/`save_costs`) — there is no dedicated cost-entry-creation function anywhere in this codebase to call into, so this follows the same load-modify-save style Costs itself uses. Frontend follows the Works page/modal shape (tabbed modal, `SortableTable` list, `DonutChart` summary) with no floor-plan placement, since policies aren't physical objects.

**Tech Stack:** FastAPI, SQLAlchemy Core, Pydantic (backend); Svelte 5 runes, svelte-i18n, vitest (frontend); pytest (backend tests).

**Design spec:** `docs/superpowers/specs/2026-07-25-insurance-module-design.md`

## Global Constraints

- New backend module files follow the exact Works pattern: `models_insurance.py`, `persistence_insurance.py`, `routes/insurance.py`, `mcp_tools_insurance.py` — no per-row CRUD functions in the persistence layer, only `load_insurance`/`save_insurance` (whole-document replace) plus attachment file helpers.
- `category_id`/`contact_id`-style cross-references are plain unvalidated string columns, never a SQL `ForeignKey` — this project's established rule for references into the independently-managed settings/contacts tables.
- Every new/changed backend field uses camelCase in Pydantic models and snake_case in SQL columns, matching every existing module.
- `models_homes.py` already has `"insurance"` registered in `ALL_MODULE_IDS`, `DEFAULT_EXISTING_MODULES`, `DEFAULT_PROJECT_MODULES` (uncommitted local change present at plan-writing time) — no task in this plan touches that file.
- `NavMenu.svelte` and `SettingsGeneral.svelte` already list the `insurance` module without `placeholder: true` friction beyond what's noted per-task below — check current state before editing, don't blindly re-add.
- All new user-facing strings go in both `packages/editor/src/lib/locales/en.json` and `fr.json` in the same task that introduces them (this project ships English + French).
- Run backend tests with `cd packages/backend && python -m pytest tests/ -x -q` (or a `-k`/path filter for a single file) and frontend tests with `cd packages/editor && npx vitest run <path>` from repo root `/projects/myhome`.

---

## Task 1: Backend — Insurance schema, `cost_entries` source columns, migration v6

**Files:**
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/migrations.py`
- Modify: `packages/backend/tests/test_migrations.py`

**Interfaces:**
- Produces: `schema.insurance_categories` table (`id, home_id, order_index, name, emoji`), `schema.insurance_policies` table (see columns below), `schema.cost_entries` gains `source_module`, `source_id` columns. `migrations.CURRENT_VERSION == 6`.

- [ ] **Step 1: Write the failing migration test**

Add to `packages/backend/tests/test_migrations.py`, after `test_run_migrations_absorbs_suppliers_into_contacts`:

```python
def test_run_migrations_adds_insurance_support(tmp_path):
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE homes (id VARCHAR PRIMARY KEY, name VARCHAR, type VARCHAR, created_at VARCHAR)"
        ))
        conn.execute(text("INSERT INTO homes (id, name, type, created_at) VALUES ('h1', 'Home 1', 'existing', '2026-01-01')"))
        conn.execute(text("INSERT INTO homes (id, name, type, created_at) VALUES ('h2', 'Home 2', 'existing', '2026-01-01')"))
        _create_legacy_category_tables(conn)
        # cost_entries already has contact_id (post-migration-5 shape) but not
        # the new source_module/source_id columns yet.
        conn.execute(text(
            "CREATE TABLE cost_entries (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, category_id VARCHAR NOT NULL, date VARCHAR NOT NULL, "
            "total_amount FLOAT NOT NULL, quantity FLOAT, unit_price FLOAT, contact_id VARCHAR, "
            "notes VARCHAR NOT NULL, room_id VARCHAR, attachments TEXT NOT NULL)"
        ))
        conn.execute(text(
            "INSERT INTO cost_entries (id, home_id, order_index, category_id, date, total_amount, notes, attachments) "
            "VALUES ('c1', 'h1', 0, 'cat-fuel', '2026-01-01', 100.0, '', '[]')"
        ))
        conn.execute(text(
            "INSERT INTO cost_categories (id, home_id, order_index, name, emoji, color) "
            "VALUES ('cat-fuel', 'h1', 0, 'Fuel', '🛢', '#4466cc')"
        ))
        conn.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        conn.execute(text("INSERT INTO schema_version (version) VALUES (5)"))

    run_migrations(engine)

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        cost_row = conn.execute(text("SELECT source_module, source_id FROM cost_entries WHERE id = 'c1'")).mappings().first()
        h1_insurance_cats = conn.execute(
            text("SELECT id, name, emoji FROM insurance_categories WHERE home_id = 'h1' ORDER BY order_index")
        ).mappings().all()
        h2_insurance_cats = conn.execute(
            text("SELECT id FROM insurance_categories WHERE home_id = 'h2'")
        ).mappings().all()
        h1_cost_cats = conn.execute(
            text("SELECT id, name FROM cost_categories WHERE home_id = 'h1' ORDER BY order_index")
        ).mappings().all()

    assert version == CURRENT_VERSION
    assert cost_row["source_module"] is None
    assert cost_row["source_id"] is None
    assert [c["id"] for c in h1_insurance_cats] == [
        "icat-home", "icat-auto", "icat-health", "icat-life", "icat-travel", "icat-liability",
    ]
    assert h1_insurance_cats[0]["name"] == "Home"
    assert h1_insurance_cats[0]["emoji"] == "🏠"
    assert len(h2_insurance_cats) == 6
    assert [c["id"] for c in h1_cost_cats] == ["cat-fuel", "cat-insurance"]
```

Also update `_create_legacy_category_tables` in the same file to create an empty `insurance_categories` table, so this test (and every other migration test that runs through version 6) has it available before migration 6 backfills it:

```python
    for other_table, cols in [
        ("inventory_categories", "id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, order_index INTEGER NOT NULL, name VARCHAR NOT NULL"),
        ("work_categories", "id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL"),
        ("suppliers", "id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, order_index INTEGER NOT NULL, name VARCHAR NOT NULL"),
        ("consumable_categories", "id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL"),
        ("insurance_categories", "id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL"),
    ]:
        conn.execute(text(f"CREATE TABLE {other_table} ({cols})"))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_migrations.py::test_run_migrations_adds_insurance_support -v`
Expected: FAIL — `CURRENT_VERSION` is still 5, `source_module` column doesn't exist, `insurance_categories` stays empty for `h1`.

- [ ] **Step 3: Add the tables to `schema.py`**

Insert after the `consumable_categories` table definition (before `settings`):

```python
insurance_categories = Table(
    "insurance_categories", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
)
```

Insert after the `consumable_transactions` table definition (after `consumables`, before `activity_log_entries` — grouping it with the other per-home record tables like `works`/`consumables`):

```python
insurance_policies = Table(
    "insurance_policies", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("category_id", String, nullable=False),
    Column("contact_id", String),
    Column("policy_number", String),
    Column("coverage_summary", String, nullable=False),
    Column("conditions_url", String),
    Column("start_date", String),
    Column("end_date", String),
    Column("premium_amount", Float),
    Column("premium_frequency", String, nullable=False),
    Column("include_in_costs", Boolean, nullable=False),
    Column("alternatives", String, nullable=False),
    Column("notes", String, nullable=False),
    Column("attachments", Text, nullable=False),
    Column("linked_cost_entry_id", String),
)
```

Modify the `cost_entries` table definition to add the two new columns at the end:

```python
cost_entries = Table(
    "cost_entries", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("category_id", String, nullable=False),
    Column("date", String, nullable=False),
    Column("total_amount", Float, nullable=False),
    Column("quantity", Float),
    Column("unit_price", Float),
    Column("contact_id", String),
    Column("notes", String, nullable=False),
    Column("room_id", String),
    Column("attachments", Text, nullable=False),
    Column("source_module", String),
    Column("source_id", String),
)
```

- [ ] **Step 4: Add migration 6 to `migrations.py`**

Add the default tuples and migration function after `_absorb_suppliers_into_contacts`, and register it in `MIGRATIONS`:

```python
_DEFAULT_INSURANCE_CATEGORIES = [
    ("icat-home", "Home", "🏠"),
    ("icat-auto", "Auto", "🚗"),
    ("icat-health", "Health", "⚕️"),
    ("icat-life", "Life", "❤️"),
    ("icat-travel", "Travel", "✈️"),
    ("icat-liability", "Liability", "🛡️"),
]


def _add_insurance_support(conn: Connection) -> None:
    # insurance_categories is a brand-new table -- create_all() already
    # created it (empty) for every home before this migration runs, same
    # situation contact_types was in for migration 5. Back-fill defaults so
    # upgraded homes start with the same category list a fresh home gets;
    # load_settings()'s lazy "row is None" default-seed path won't fire
    # again for any home whose settings row already exists.
    conn.execute(text("ALTER TABLE cost_entries ADD COLUMN source_module VARCHAR"))
    conn.execute(text("ALTER TABLE cost_entries ADD COLUMN source_id VARCHAR"))
    home_ids = [r[0] for r in conn.execute(text("SELECT id FROM homes")).all()]
    for home_id in home_ids:
        for i, (cat_id, name, emoji) in enumerate(_DEFAULT_INSURANCE_CATEGORIES):
            conn.execute(
                text(
                    "INSERT INTO insurance_categories (id, home_id, order_index, name, emoji) "
                    "VALUES (:id, :home_id, :i, :name, :emoji)"
                ),
                {"id": cat_id, "home_id": home_id, "i": i, "name": name, "emoji": emoji},
            )
        existing = conn.execute(
            text("SELECT 1 FROM cost_categories WHERE home_id = :h AND id = 'cat-insurance'"),
            {"h": home_id},
        ).first()
        if existing is None:
            count = conn.execute(
                text("SELECT COUNT(*) FROM cost_categories WHERE home_id = :h"), {"h": home_id}
            ).scalar()
            conn.execute(
                text(
                    "INSERT INTO cost_categories (id, home_id, order_index, name, emoji, unit, color) "
                    "VALUES ('cat-insurance', :h, :i, 'Insurance', '🛡️', NULL, '#7a5cc4')"
                ),
                {"h": home_id, "i": count},
            )


MIGRATIONS: list[tuple[int, Callable[[Connection], None]]] = [
    (2, _drop_kb_folders_table),
    (3, _add_ha_user_id_column),
    (4, _scope_category_tables_by_home),
    (5, _absorb_suppliers_into_contacts),
    (6, _add_insurance_support),
]
```

And bump `CURRENT_VERSION = 6` (was `5`).

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_migrations.py -v`
Expected: All PASS, including the new `test_run_migrations_adds_insurance_support` and the pre-existing migration tests (which now also run migration 6 as part of their sequence, so they exercise the `insurance_categories` backfill implicitly too).

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/migrations.py packages/backend/tests/test_migrations.py
git commit -m "feat(insurance): add schema tables, cost_entries source columns, migration v6"
```

---

## Task 2: Backend — `models_insurance.py` + `persistence_insurance.py`

**Files:**
- Create: `packages/backend/src/myhome/models_insurance.py`
- Create: `packages/backend/src/myhome/persistence_insurance.py`
- Create: `packages/backend/tests/test_insurance_persistence.py`

**Interfaces:**
- Consumes: `schema.insurance_policies` (Task 1).
- Produces: `InsurancePolicy`, `InsurancePolicyCreate`, `InsurancePolicyUpdate`, `InsuranceDocument` (models); `load_insurance(home_id) -> InsuranceDocument`, `save_insurance(home_id, doc) -> None`, `get_attachment_path`, `save_attachment`, `delete_attachment`, `delete_all_attachments`, `generate_pdf_thumbnail` (persistence) — all consumed by Task 3's routes.

- [ ] **Step 1: Write the failing persistence test**

Create `packages/backend/tests/test_insurance_persistence.py`:

```python
from myhome.models_insurance import InsurancePolicy, InsuranceDocument
from myhome.persistence_insurance import (
    delete_attachment,
    get_attachment_path,
    load_insurance,
    save_attachment,
    save_insurance,
)

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


def make_doc() -> InsuranceDocument:
    return InsuranceDocument(policies=[
        InsurancePolicy(
            id="ins1", name="Home Insurance — AXA", categoryId="icat-home",
            premiumAmount=45.0, premiumFrequency="monthly", includeInCosts=True,
            startDate="2026-01-01", endDate="2027-01-01",
        )
    ])


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = load_insurance(HOME_ID)
    assert doc.policies == []


def test_round_trip(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_insurance(HOME_ID, make_doc())
    loaded = load_insurance(HOME_ID)
    p = loaded.policies[0]
    assert p.id == "ins1"
    assert p.name == "Home Insurance — AXA"
    assert p.categoryId == "icat-home"
    assert p.premiumAmount == 45.0
    assert p.premiumFrequency == "monthly"
    assert p.includeInCosts is True
    assert p.attachments == []
    assert p.linkedCostEntryId is None


def test_round_trip_preserves_order(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = InsuranceDocument(policies=[
        InsurancePolicy(id="ins1", name="A", categoryId="icat-home", premiumFrequency="annual", includeInCosts=False),
        InsurancePolicy(id="ins2", name="B", categoryId="icat-travel", premiumFrequency="annual", includeInCosts=False),
    ])
    save_insurance(HOME_ID, doc)
    loaded = load_insurance(HOME_ID)
    assert [p.id for p in loaded.policies] == ["ins1", "ins2"]


def test_attachment_save_and_delete(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_attachment(HOME_ID, "ins1", "policy.pdf", b"%PDF test")
    path = get_attachment_path(HOME_ID, "ins1", "policy.pdf")
    assert path.exists()
    assert path.read_bytes() == b"%PDF test"
    assert delete_attachment(HOME_ID, "ins1", "policy.pdf") is True
    assert not path.exists()


def test_delete_attachment_missing_returns_false(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert delete_attachment(HOME_ID, "ins1", "nope.pdf") is False
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_insurance_persistence.py -v`
Expected: FAIL — `myhome.models_insurance` doesn't exist yet.

- [ ] **Step 3: Create `models_insurance.py`**

```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class InsurancePolicy(BaseModel):
    id: str
    name: str
    categoryId: str
    contactId: str | None = None
    policyNumber: str | None = None
    coverageSummary: str = ""
    conditionsUrl: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    premiumAmount: float | None = None
    premiumFrequency: Literal["monthly", "quarterly", "annual", "other"] = "annual"
    includeInCosts: bool = False
    alternatives: str = ""
    notes: str = ""
    attachments: list[str] = []
    linkedCostEntryId: str | None = None


class InsuranceDocument(BaseModel):
    version: int = 1
    policies: list[InsurancePolicy] = []


class InsurancePolicyCreate(BaseModel):
    name: str
    categoryId: str
    contactId: str | None = None
    policyNumber: str | None = None
    coverageSummary: str = ""
    conditionsUrl: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    premiumAmount: float | None = None
    premiumFrequency: Literal["monthly", "quarterly", "annual", "other"] = "annual"
    includeInCosts: bool = False
    alternatives: str = ""
    notes: str = ""


class InsurancePolicyUpdate(BaseModel):
    name: str | None = None
    categoryId: str | None = None
    contactId: str | None = None
    policyNumber: str | None = None
    coverageSummary: str | None = None
    conditionsUrl: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    premiumAmount: float | None = None
    premiumFrequency: Literal["monthly", "quarterly", "annual", "other"] | None = None
    includeInCosts: bool | None = None
    alternatives: str | None = None
    notes: str | None = None
```

- [ ] **Step 4: Create `persistence_insurance.py`**

```python
import json
import logging
import os
import shutil
from pathlib import Path

from sqlalchemy import select

from .db import get_engine
from .ids import InvalidIdError
from .models_insurance import InsurancePolicy, InsuranceDocument
from .schema import insurance_policies as insurance_policies_table

_log = logging.getLogger(__name__)


def _home_dir(home_id: str) -> Path:
    homes_root = os.path.normpath(os.path.join(os.environ.get("DATA_DIR", "/data"), "homes"))
    candidate = os.path.normpath(os.path.join(homes_root, home_id))
    if not candidate.startswith(homes_root + os.sep):
        raise InvalidIdError(f"Invalid home_id: {home_id!r}")
    return Path(candidate)


def _attachments_dir(home_id: str, policy_id: str) -> Path:
    base = os.path.normpath(str(_home_dir(home_id) / "insurance-attachments"))
    candidate = os.path.normpath(os.path.join(base, policy_id))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid policy_id: {policy_id!r}")
    return Path(candidate)


def load_insurance(home_id: str) -> InsuranceDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(insurance_policies_table).where(insurance_policies_table.c.home_id == home_id)
            .order_by(insurance_policies_table.c.order_index)
        ).mappings().all()
    return InsuranceDocument(policies=[
        InsurancePolicy(
            id=r["id"], name=r["name"], categoryId=r["category_id"], contactId=r["contact_id"],
            policyNumber=r["policy_number"], coverageSummary=r["coverage_summary"],
            conditionsUrl=r["conditions_url"], startDate=r["start_date"], endDate=r["end_date"],
            premiumAmount=r["premium_amount"], premiumFrequency=r["premium_frequency"],
            includeInCosts=bool(r["include_in_costs"]), alternatives=r["alternatives"],
            notes=r["notes"], attachments=json.loads(r["attachments"]),
            linkedCostEntryId=r["linked_cost_entry_id"],
        )
        for r in rows
    ])


def save_insurance(home_id: str, doc: InsuranceDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(insurance_policies_table.delete().where(insurance_policies_table.c.home_id == home_id))
        if doc.policies:
            conn.execute(insurance_policies_table.insert(), [
                {
                    "id": p.id, "home_id": home_id, "order_index": i, "name": p.name,
                    "category_id": p.categoryId, "contact_id": p.contactId,
                    "policy_number": p.policyNumber, "coverage_summary": p.coverageSummary,
                    "conditions_url": p.conditionsUrl, "start_date": p.startDate, "end_date": p.endDate,
                    "premium_amount": p.premiumAmount, "premium_frequency": p.premiumFrequency,
                    "include_in_costs": p.includeInCosts, "alternatives": p.alternatives,
                    "notes": p.notes, "attachments": json.dumps(p.attachments),
                    "linked_cost_entry_id": p.linkedCostEntryId,
                }
                for i, p in enumerate(doc.policies)
            ])


def get_attachment_path(home_id: str, policy_id: str, filename: str) -> Path:
    base = os.path.normpath(str(_attachments_dir(home_id, policy_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    return Path(candidate)


def save_attachment(home_id: str, policy_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, policy_id)
    base = os.path.normpath(str(path))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path.mkdir(parents=True, exist_ok=True)
    Path(candidate).write_bytes(data)


def delete_attachment(home_id: str, policy_id: str, filename: str) -> bool:
    base = os.path.normpath(str(_attachments_dir(home_id, policy_id)))
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


def delete_all_attachments(home_id: str, policy_id: str) -> None:
    path = _attachments_dir(home_id, policy_id)
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

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_insurance_persistence.py -v`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/models_insurance.py packages/backend/src/myhome/persistence_insurance.py packages/backend/tests/test_insurance_persistence.py
git commit -m "feat(insurance): add InsurancePolicy model and persistence layer"
```

---

## Task 3: Backend — `routes/insurance.py` CRUD + attachments + registration

**Files:**
- Create: `packages/backend/src/myhome/routes/insurance.py`
- Modify: `packages/backend/src/myhome/main.py`
- Modify: `packages/backend/src/myhome/persistence_activity.py`
- Modify: `packages/backend/src/myhome/models_activity.py`
- Create: `packages/backend/tests/test_insurance.py`

**Interfaces:**
- Consumes: `load_insurance`/`save_insurance`/attachment helpers (Task 2), `InsurancePolicy`/`InsurancePolicyCreate`/`InsurancePolicyUpdate`/`InsuranceDocument` (Task 2), `log_activity` (existing `persistence_activity.py`).
- Produces: REST routes under `/api/homes/{home_id}/insurance`, consumed by the frontend store in Task 8. `linkedCostEntryId`/cost-sync logic is added in Task 4, not here — this task's `create_policy`/`update_policy`/`delete_policy` are plain CRUD only.

- [ ] **Step 1: Write the failing route tests**

Create `packages/backend/tests/test_insurance.py` (modeled directly on `test_works.py`, trimmed to the fields that differ):

```python
import pytest
from myhome.models_insurance import InsurancePolicy, InsuranceDocument
from myhome.persistence_insurance import save_insurance


def make_doc() -> InsuranceDocument:
    return InsuranceDocument(policies=[
        InsurancePolicy(
            id="ins1", name="Home Insurance — AXA", categoryId="icat-home",
            premiumAmount=45.0, premiumFrequency="monthly", includeInCosts=False,
        )
    ])


def test_get_insurance_empty_when_no_data(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/insurance")
    assert resp.status_code == 200
    assert resp.json()["policies"] == []


def test_get_insurance_returns_saved_data(client, home_id):
    save_insurance(home_id, make_doc())
    resp = client.get(f"/api/homes/{home_id}/insurance")
    assert resp.status_code == 200
    assert resp.json()["policies"][0]["id"] == "ins1"


def test_create_policy(client, home_id):
    payload = {"name": "Travel Insurance", "categoryId": "icat-travel", "premiumFrequency": "annual"}
    resp = client.post(f"/api/homes/{home_id}/insurance", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Travel Insurance"
    assert data["includeInCosts"] is False
    assert data["attachments"] == []
    assert data["linkedCostEntryId"] is None
    assert "id" in data
    assert len(client.get(f"/api/homes/{home_id}/insurance").json()["policies"]) == 1


def test_create_policy_full_fields(client, home_id):
    payload = {
        "name": "Home Insurance — AXA", "categoryId": "icat-home", "contactId": "con-1",
        "policyNumber": "POL-123", "coverageSummary": "Fire, theft, water damage",
        "conditionsUrl": "https://example.com/policy.pdf", "startDate": "2026-01-01",
        "endDate": "2027-01-01", "premiumAmount": 45.0, "premiumFrequency": "monthly",
        "includeInCosts": True, "alternatives": "Quoted Allianz at 50€/mo", "notes": "Renews automatically",
    }
    resp = client.post(f"/api/homes/{home_id}/insurance", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["premiumAmount"] == 45.0
    assert data["contactId"] == "con-1"
    assert data["includeInCosts"] is True


def test_update_policy_partial(client, home_id):
    save_insurance(home_id, make_doc())
    resp = client.put(f"/api/homes/{home_id}/insurance/ins1", json={"premiumAmount": 50.0})
    assert resp.status_code == 204
    policy = client.get(f"/api/homes/{home_id}/insurance").json()["policies"][0]
    assert policy["premiumAmount"] == 50.0
    assert policy["name"] == "Home Insurance — AXA"  # unchanged


def test_update_policy_404(client, home_id):
    resp = client.put(f"/api/homes/{home_id}/insurance/nope", json={"premiumAmount": 1.0})
    assert resp.status_code == 404


def test_delete_policy(client, home_id):
    save_insurance(home_id, make_doc())
    resp = client.delete(f"/api/homes/{home_id}/insurance/ins1")
    assert resp.status_code == 204
    assert client.get(f"/api/homes/{home_id}/insurance").json()["policies"] == []


def test_delete_policy_404(client, home_id):
    resp = client.delete(f"/api/homes/{home_id}/insurance/nope")
    assert resp.status_code == 404


def test_upload_attachment(client, home_id):
    save_insurance(home_id, make_doc())
    resp = client.post(
        f"/api/homes/{home_id}/insurance/ins1/attachments",
        files={"file": ("policy.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "policy.pdf"
    policy = client.get(f"/api/homes/{home_id}/insurance").json()["policies"][0]
    assert "policy.pdf" in policy["attachments"]


def test_upload_unsupported_type_rejected(client, home_id):
    save_insurance(home_id, make_doc())
    resp = client.post(
        f"/api/homes/{home_id}/insurance/ins1/attachments",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_get_attachment(client, home_id):
    save_insurance(home_id, make_doc())
    client.post(
        f"/api/homes/{home_id}/insurance/ins1/attachments",
        files={"file": ("policy.pdf", b"%PDF-1.4 test content", "application/pdf")},
    )
    resp = client.get(f"/api/homes/{home_id}/insurance/ins1/attachments/policy.pdf")
    assert resp.status_code == 200
    assert "pdf" in resp.headers["content-type"]


def test_delete_attachment(client, home_id):
    save_insurance(home_id, make_doc())
    client.post(
        f"/api/homes/{home_id}/insurance/ins1/attachments",
        files={"file": ("policy.pdf", b"%PDF test", "application/pdf")},
    )
    resp = client.delete(f"/api/homes/{home_id}/insurance/ins1/attachments/policy.pdf")
    assert resp.status_code == 204
    policy = client.get(f"/api/homes/{home_id}/insurance").json()["policies"][0]
    assert "policy.pdf" not in policy["attachments"]


def test_delete_policy_removes_attachments(client, tmp_path, home_id):
    save_insurance(home_id, make_doc())
    client.post(
        f"/api/homes/{home_id}/insurance/ins1/attachments",
        files={"file": ("policy.pdf", b"%PDF test", "application/pdf")},
    )
    client.delete(f"/api/homes/{home_id}/insurance/ins1")
    attach_dir = tmp_path / "homes" / home_id / "insurance-attachments" / "ins1"
    assert not attach_dir.exists()


def test_activity_log_records_insurance_actions(client, home_id):
    resp = client.post(
        f"/api/homes/{home_id}/insurance",
        json={"name": "Travel Insurance", "categoryId": "icat-travel", "premiumFrequency": "annual"},
    )
    policy_id = resp.json()["id"]
    log = client.get(f"/api/homes/{home_id}/activity").json()
    entry = next(e for e in log["entries"] if e["module"] == "insurance" and e["action"] == "create")
    assert entry["entityLabel"] == "Travel Insurance"
    assert entry["refId"] == policy_id
```

(If the activity feed endpoint or response shape differs from `/api/homes/{home_id}/activity` returning `{"entries": [...]}` with `entityLabel`/`refId` keys, adjust this last test to match — check `test_works.py`'s sibling activity assertions, or `routes/activity.py`, for the exact shape before running.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_insurance.py -v`
Expected: FAIL — `myhome.routes.insurance` doesn't exist, 404s on all routes.

- [ ] **Step 3: Create `routes/insurance.py`**

```python
import mimetypes
import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..deps import get_current_user_id
from ..models_insurance import InsurancePolicy, InsurancePolicyCreate, InsurancePolicyUpdate, InsuranceDocument
from ..persistence_activity import log_activity
from ..persistence_insurance import (
    delete_all_attachments,
    delete_attachment,
    generate_pdf_thumbnail,
    get_attachment_path,
    load_insurance,
    save_attachment,
    save_insurance,
)

router = APIRouter()


@router.get("/api/homes/{home_id}/insurance", response_model=InsuranceDocument)
def get_insurance(home_id: str) -> InsuranceDocument:
    return load_insurance(home_id)


@router.post("/api/homes/{home_id}/insurance", response_model=InsurancePolicy, status_code=201)
def create_policy(
    home_id: str, body: InsurancePolicyCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> InsurancePolicy:
    doc = load_insurance(home_id)
    policy = InsurancePolicy(id=str(uuid.uuid4()), **body.model_dump())
    doc.policies.append(policy)
    save_insurance(home_id, doc)
    log_activity(home_id, current_user_id, "insurance", "create", policy.name, policy.id)
    return policy


@router.put("/api/homes/{home_id}/insurance/{id}", status_code=204)
def update_policy(
    home_id: str, id: str, body: InsurancePolicyUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_insurance(home_id)
    policy = next((p for p in doc.policies if p.id == id), None)
    if not policy:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)
    save_insurance(home_id, doc)
    log_activity(home_id, current_user_id, "insurance", "update", policy.name, id)


@router.delete("/api/homes/{home_id}/insurance/{id}", status_code=204)
def delete_policy(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_insurance(home_id)
    policy = next((p for p in doc.policies if p.id == id), None)
    if policy is None:
        raise HTTPException(status_code=404)
    doc.policies = [p for p in doc.policies if p.id != id]
    save_insurance(home_id, doc)
    delete_all_attachments(home_id, id)
    log_activity(home_id, current_user_id, "insurance", "delete", policy.name, id)


_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"


_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _validate_id(policy_id: str) -> None:
    if not _ID_RE.fullmatch(policy_id):
        raise HTTPException(status_code=400, detail="Invalid id")


def _validate_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


@router.post("/api/homes/{home_id}/insurance/{id}/attachments", status_code=201)
async def upload_attachment(home_id: str, id: str, file: UploadFile) -> dict:
    _validate_id(id)
    doc = load_insurance(home_id)
    policy = next((p for p in doc.policies if p.id == id), None)
    if not policy:
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
    if filename not in policy.attachments:
        policy.attachments.append(filename)
    save_insurance(home_id, doc)
    return {"filename": filename}


@router.get("/api/homes/{home_id}/insurance/{id}/attachments/{filename}")
def get_attachment(home_id: str, id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    path = get_attachment_path(home_id, id, filename)
    if not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", filename=filename)


@router.delete("/api/homes/{home_id}/insurance/{id}/attachments/{filename}", status_code=204)
def remove_attachment(home_id: str, id: str, filename: str) -> None:
    _validate_id(id)
    _validate_filename(filename)
    doc = load_insurance(home_id)
    policy = next((p for p in doc.policies if p.id == id), None)
    if not policy:
        raise HTTPException(status_code=404)
    if not delete_attachment(home_id, id, filename):
        raise HTTPException(status_code=404)
    policy.attachments = [a for a in policy.attachments if a != filename]
    save_insurance(home_id, doc)
```

- [ ] **Step 4: Register the router in `main.py`**

Add `insurance` to the `from .routes import (...)` block (alphabetical position, after `inventory` before `kb` — check the exact existing import list first since it may not be alphabetized; place it near `works`/`contacts` if so), and add the include line near the other per-module routers:

```python
app.include_router(insurance.router)
```

(Add this line directly after `app.include_router(contacts.router)`.)

- [ ] **Step 5: Register `"insurance"` in the activity-log allowlist**

In `packages/backend/src/myhome/models_activity.py`, add `"insurance"` to the `Literal`:

```python
    module: Literal["chores", "works", "costs", "inventory", "consumables", "kb", "locations", "properties", "build", "contacts", "insurance"]
```

In `packages/backend/src/myhome/persistence_activity.py`, add an entry to `MODULE_NOUNS`:

```python
MODULE_NOUNS = {
    "chores": "chore", "works": "work", "costs": "cost entry",
    "inventory": "inventory item", "consumables": "consumable", "kb": "KB article",
    "locations": "location", "properties": "property", "build": "build task",
    "contacts": "contact", "insurance": "insurance policy",
}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_insurance.py -v`
Expected: All PASS. If the activity-log test's response shape doesn't match, fix the test to match `routes/activity.py`'s actual schema rather than the route code.

- [ ] **Step 7: Run the full backend suite to check nothing else broke**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: All PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/backend/src/myhome/routes/insurance.py packages/backend/src/myhome/main.py packages/backend/src/myhome/models_activity.py packages/backend/src/myhome/persistence_activity.py packages/backend/tests/test_insurance.py
git commit -m "feat(insurance): add REST routes, attachments, activity log registration"
```

---

## Task 4: Backend — Cost sync (`includeInCosts` toggle) + Costs route guard

**Files:**
- Modify: `packages/backend/src/myhome/routes/insurance.py`
- Modify: `packages/backend/src/myhome/routes/costs.py`
- Modify: `packages/backend/tests/test_insurance.py`
- Modify: `packages/backend/tests/test_costs.py` (or equivalent existing Costs route test file — confirm exact filename first with `ls packages/backend/tests/test_costs*`)

**Interfaces:**
- Consumes: `load_costs`/`save_costs` (existing `persistence_costs.py`), `CostEntry` (existing `models_costs.py`), `InsurancePolicy` (Task 2).
- Produces: `_sync_cost_entry(home_id, policy) -> str | None` in `routes/insurance.py`, called from `create_policy`/`update_policy`/`delete_policy`.

- [ ] **Step 1: Write the failing cost-sync tests**

Add to `packages/backend/tests/test_insurance.py`:

```python
from myhome.persistence_costs import load_costs


def test_create_policy_with_include_in_costs_syncs_cost_entry(client, home_id):
    payload = {
        "name": "Home Insurance — AXA", "categoryId": "icat-home", "premiumAmount": 45.0,
        "premiumFrequency": "monthly", "includeInCosts": True, "startDate": "2026-01-01",
    }
    resp = client.post(f"/api/homes/{home_id}/insurance", json=payload)
    policy = resp.json()
    assert policy["linkedCostEntryId"] is not None

    costs = load_costs(home_id)
    assert len(costs.entries) == 1
    entry = costs.entries[0]
    assert entry.id == policy["linkedCostEntryId"]
    assert entry.categoryId == "cat-insurance"
    assert entry.totalAmount == 540.0  # 45 * 12
    assert entry.sourceModule == "insurance"
    assert entry.sourceId == policy["id"]
    assert entry.date == "2026-01-01"


def test_create_policy_without_include_in_costs_does_not_sync(client, home_id):
    payload = {
        "name": "Travel Insurance", "categoryId": "icat-travel", "premiumAmount": 120.0,
        "premiumFrequency": "annual", "includeInCosts": False,
    }
    resp = client.post(f"/api/homes/{home_id}/insurance", json=payload)
    assert resp.json()["linkedCostEntryId"] is None
    assert load_costs(home_id).entries == []


def test_toggling_include_in_costs_on_creates_synced_entry(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/insurance", json={
        "name": "Life Insurance", "categoryId": "icat-life", "premiumAmount": 30.0,
        "premiumFrequency": "monthly", "includeInCosts": False,
    })
    policy_id = resp.json()["id"]
    assert load_costs(home_id).entries == []

    client.put(f"/api/homes/{home_id}/insurance/{policy_id}", json={"includeInCosts": True})
    costs = load_costs(home_id)
    assert len(costs.entries) == 1
    assert costs.entries[0].sourceId == policy_id


def test_toggling_include_in_costs_off_removes_synced_entry(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/insurance", json={
        "name": "Home Insurance", "categoryId": "icat-home", "premiumAmount": 45.0,
        "premiumFrequency": "monthly", "includeInCosts": True,
    })
    policy_id = resp.json()["id"]
    assert len(load_costs(home_id).entries) == 1

    client.put(f"/api/homes/{home_id}/insurance/{policy_id}", json={"includeInCosts": False})
    assert load_costs(home_id).entries == []


def test_updating_premium_updates_synced_cost_entry_amount(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/insurance", json={
        "name": "Home Insurance", "categoryId": "icat-home", "premiumAmount": 45.0,
        "premiumFrequency": "monthly", "includeInCosts": True,
    })
    policy_id = resp.json()["id"]
    client.put(f"/api/homes/{home_id}/insurance/{policy_id}", json={"premiumAmount": 50.0})
    costs = load_costs(home_id)
    assert len(costs.entries) == 1
    assert costs.entries[0].totalAmount == 600.0  # 50 * 12


def test_deleting_synced_policy_removes_cost_entry(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/insurance", json={
        "name": "Home Insurance", "categoryId": "icat-home", "premiumAmount": 45.0,
        "premiumFrequency": "monthly", "includeInCosts": True,
    })
    policy_id = resp.json()["id"]
    assert len(load_costs(home_id).entries) == 1
    client.delete(f"/api/homes/{home_id}/insurance/{policy_id}")
    assert load_costs(home_id).entries == []
```

Add to the Costs route test file (confirm exact filename/fixtures first — e.g. `test_costs.py`):

```python
def test_update_synced_cost_entry_rejected(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/insurance", json={
        "name": "Home Insurance", "categoryId": "icat-home", "premiumAmount": 45.0,
        "premiumFrequency": "monthly", "includeInCosts": True,
    })
    entry_id = resp.json()["linkedCostEntryId"]
    resp2 = client.put(f"/api/homes/{home_id}/costs/entries/{entry_id}", json={"totalAmount": 999.0})
    assert resp2.status_code == 400


def test_delete_synced_cost_entry_rejected(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/insurance", json={
        "name": "Home Insurance", "categoryId": "icat-home", "premiumAmount": 45.0,
        "premiumFrequency": "monthly", "includeInCosts": True,
    })
    entry_id = resp.json()["linkedCostEntryId"]
    resp2 = client.delete(f"/api/homes/{home_id}/costs/entries/{entry_id}")
    assert resp2.status_code == 400
```

(These two tests need an `import` for whatever `client`/`home_id` fixtures the existing Costs test file already uses — match its existing style; if the file is named differently, e.g. `test_costs_routes.py`, add there instead.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_insurance.py -k sync -v`
Expected: FAIL — no cost entries are created (`CostEntry` also doesn't have `sourceModule`/`sourceId` fields yet).

- [ ] **Step 3: Add `sourceModule`/`sourceId` to `models_costs.py`**

```python
class CostEntry(BaseModel):
    id: str
    categoryId: str
    date: str
    totalAmount: float
    quantity: float | None = None
    unitPrice: float | None = None
    contactId: str | None = None
    notes: str = ""
    roomId: str | None = None
    attachments: list[str] = []
    sourceModule: str | None = None
    sourceId: str | None = None
```

Add the same two fields to `CostEntryUpdate` is **not** needed (route guard in Step 5 blocks edits to synced entries entirely — `CostEntryCreate` doesn't need them either since only the insurance sync path sets them, via direct `CostEntry(...)` construction, not through the `CostEntryCreate` schema).

Update `persistence_costs.py`'s `load_costs`/`save_costs` to round-trip the two new columns (already present on `cost_entries` from Task 1's migration):

```python
    return CostsDocument(entries=[
        CostEntry(
            id=r["id"], categoryId=r["category_id"], date=r["date"], totalAmount=r["total_amount"],
            quantity=r["quantity"], unitPrice=r["unit_price"], contactId=r["contact_id"],
            notes=r["notes"], roomId=r["room_id"], attachments=json.loads(r["attachments"]),
            sourceModule=r["source_module"], sourceId=r["source_id"],
        )
        for r in rows
    ])
```

```python
            conn.execute(cost_entries_table.insert(), [
                {
                    "id": e.id, "home_id": home_id, "order_index": i, "category_id": e.categoryId,
                    "date": e.date, "total_amount": e.totalAmount, "quantity": e.quantity,
                    "unit_price": e.unitPrice, "contact_id": e.contactId, "notes": e.notes,
                    "room_id": e.roomId, "attachments": json.dumps(e.attachments),
                    "source_module": e.sourceModule, "source_id": e.sourceId,
                }
                for i, e in enumerate(doc.entries)
            ])
```

- [ ] **Step 4: Add the sync helper and wire it into `routes/insurance.py`**

Add imports and the helper functions at the top of `routes/insurance.py` (after the existing imports):

```python
from datetime import date

from ..models_costs import CostEntry
from ..persistence_costs import load_costs, save_costs

_FREQUENCY_MULTIPLIER = {"monthly": 12, "quarterly": 4, "annual": 1, "other": 1}


def _annualized_amount(amount: float, frequency: str) -> float:
    return amount * _FREQUENCY_MULTIPLIER[frequency]


def _sync_cost_entry(home_id: str, policy: InsurancePolicy) -> str | None:
    costs_doc = load_costs(home_id)
    costs_doc.entries = [e for e in costs_doc.entries if e.id != policy.linkedCostEntryId]
    linked_id = None
    if policy.includeInCosts and policy.premiumAmount is not None:
        linked_id = policy.linkedCostEntryId or str(uuid.uuid4())
        costs_doc.entries.append(CostEntry(
            id=linked_id,
            categoryId="cat-insurance",
            date=policy.startDate or date.today().isoformat(),
            totalAmount=_annualized_amount(policy.premiumAmount, policy.premiumFrequency),
            contactId=policy.contactId,
            notes=f"{policy.name} ({policy.premiumFrequency})",
            sourceModule="insurance",
            sourceId=policy.id,
        ))
    save_costs(home_id, costs_doc)
    return linked_id
```

Update `create_policy`, `update_policy`, and `delete_policy` to call it:

```python
@router.post("/api/homes/{home_id}/insurance", response_model=InsurancePolicy, status_code=201)
def create_policy(
    home_id: str, body: InsurancePolicyCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> InsurancePolicy:
    doc = load_insurance(home_id)
    policy = InsurancePolicy(id=str(uuid.uuid4()), **body.model_dump())
    policy.linkedCostEntryId = _sync_cost_entry(home_id, policy)
    doc.policies.append(policy)
    save_insurance(home_id, doc)
    log_activity(home_id, current_user_id, "insurance", "create", policy.name, policy.id)
    return policy


@router.put("/api/homes/{home_id}/insurance/{id}", status_code=204)
def update_policy(
    home_id: str, id: str, body: InsurancePolicyUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_insurance(home_id)
    policy = next((p for p in doc.policies if p.id == id), None)
    if not policy:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)
    policy.linkedCostEntryId = _sync_cost_entry(home_id, policy)
    save_insurance(home_id, doc)
    log_activity(home_id, current_user_id, "insurance", "update", policy.name, id)


@router.delete("/api/homes/{home_id}/insurance/{id}", status_code=204)
def delete_policy(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_insurance(home_id)
    policy = next((p for p in doc.policies if p.id == id), None)
    if policy is None:
        raise HTTPException(status_code=404)
    policy.includeInCosts = False
    _sync_cost_entry(home_id, policy)
    doc.policies = [p for p in doc.policies if p.id != id]
    save_insurance(home_id, doc)
    delete_all_attachments(home_id, id)
    log_activity(home_id, current_user_id, "insurance", "delete", policy.name, id)
```

- [ ] **Step 5: Guard synced entries in `routes/costs.py`**

Add a check at the top of `update_entry` and `delete_entry`:

```python
@router.put("/api/homes/{home_id}/costs/entries/{id}", status_code=204)
def update_entry(
    home_id: str, id: str, body: CostEntryUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_costs(home_id)
    entry = next((e for e in doc.entries if e.id == id), None)
    if not entry:
        raise HTTPException(status_code=404)
    if entry.sourceModule is not None:
        raise HTTPException(status_code=400, detail=f"This entry is synced from {entry.sourceModule} — edit it there instead")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    save_costs(home_id, doc)
    log_activity(home_id, current_user_id, "costs", "update", _cost_label(entry), id)


@router.delete("/api/homes/{home_id}/costs/entries/{id}", status_code=204)
def delete_entry(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_costs(home_id)
    entry = next((e for e in doc.entries if e.id == id), None)
    if entry is None:
        raise HTTPException(status_code=404)
    if entry.sourceModule is not None:
        raise HTTPException(status_code=400, detail=f"This entry is synced from {entry.sourceModule} — edit it there instead")
    doc.entries = [e for e in doc.entries if e.id != id]
    save_costs(home_id, doc)
    delete_all_attachments(home_id, id)
    log_activity(home_id, current_user_id, "costs", "delete", _cost_label(entry), id)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_insurance.py tests/test_costs*.py -v`
Expected: All PASS.

- [ ] **Step 7: Run the full backend suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: All PASS — this also confirms the `CostEntry` field addition didn't break any existing Costs tests (it's additive/optional with a default of `None`).

- [ ] **Step 8: Commit**

```bash
git add packages/backend/src/myhome/routes/insurance.py packages/backend/src/myhome/routes/costs.py packages/backend/src/myhome/models_costs.py packages/backend/src/myhome/persistence_costs.py packages/backend/tests/test_insurance.py packages/backend/tests/test_costs*.py
git commit -m "feat(insurance): sync includeInCosts policies to a linked Costs entry"
```

---

## Task 5: Backend — Insurance Categories in Settings

**Files:**
- Modify: `packages/backend/src/myhome/models_settings.py`
- Modify: `packages/backend/src/myhome/persistence_settings.py`
- Modify: `packages/backend/src/myhome/routes/settings.py`
- Modify: `packages/backend/tests/test_settings.py` (confirm exact filename with `ls packages/backend/tests/test_settings*`)

**Interfaces:**
- Produces: `InsuranceCategory{id, name, emoji}`, `_default_insurance_categories()`, `SettingsDocument.insuranceCategories: list[InsuranceCategory]`, `PUT /api/homes/{home_id}/settings/insurance-categories` — consumed by Task 10/11's frontend.

- [ ] **Step 1: Write the failing settings test**

Add to the existing Settings test file:

```python
def test_settings_defaults_include_insurance_categories(client, home_id):
    resp = client.get(f"/api/homes/{home_id}/settings")
    cats = resp.json()["insuranceCategories"]
    assert [c["id"] for c in cats] == [
        "icat-home", "icat-auto", "icat-health", "icat-life", "icat-travel", "icat-liability",
    ]
    assert cats[0]["name"] == "Home"
    assert cats[0]["emoji"] == "🏠"


def test_put_insurance_categories(client, home_id):
    resp = client.put(
        f"/api/homes/{home_id}/settings/insurance-categories",
        json=[{"id": "icat-custom", "name": "Pet", "emoji": "🐶"}],
    )
    assert resp.status_code == 204
    cats = client.get(f"/api/homes/{home_id}/settings").json()["insuranceCategories"]
    assert cats == [{"id": "icat-custom", "name": "Pet", "emoji": "🐶"}]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_settings.py -k insurance -v`
Expected: FAIL — `insuranceCategories` key missing from the response, `insurance-categories` route 404s.

- [ ] **Step 3: Add `InsuranceCategory` to `models_settings.py`**

```python
class InsuranceCategory(BaseModel):
    id: str
    name: str
    emoji: str
```

Add the default-seed function near `_default_work_categories()`:

```python
def _default_insurance_categories() -> list[InsuranceCategory]:
    return [
        InsuranceCategory(id="icat-home",      name="Home",      emoji="🏠"),
        InsuranceCategory(id="icat-auto",      name="Auto",      emoji="🚗"),
        InsuranceCategory(id="icat-health",    name="Health",    emoji="⚕️"),
        InsuranceCategory(id="icat-life",      name="Life",      emoji="❤️"),
        InsuranceCategory(id="icat-travel",    name="Travel",    emoji="✈️"),
        InsuranceCategory(id="icat-liability", name="Liability", emoji="🛡️"),
    ]
```

Add `insuranceCategories` to `SettingsDocument`:

```python
class SettingsDocument(BaseModel):
    version: int = 1
    costCategories: list[CostCategory] = []
    inventoryCategories: list[InventoryCategory] = []
    workCategories: list[WorkCategory] = []
    contactTypes: list[ContactType] = []
    consumableUnits: list[str] = []
    consumableCategories: list[ConsumableCategory] = []
    insuranceCategories: list[InsuranceCategory] = []
    notifications: NotificationSettings = NotificationSettings()
```

Also add `CostCategory(id="cat-insurance", name="Insurance", emoji="🛡️", unit=None, color="#7a5cc4")` to `_default_cost_categories()`'s returned list, so brand-new homes get it via the normal lazy-seed path (the migration in Task 1 only backfills existing homes):

```python
def _default_cost_categories() -> list[CostCategory]:
    return [
        CostCategory(id="cat-fuel",        name="Fuel / Mazout",  emoji="🛢", unit="L",      color="#4466cc"),
        CostCategory(id="cat-electricity", name="Electricity",    emoji="💡", unit="kWh",    color="#44aacc"),
        CostCategory(id="cat-water",       name="Water",          emoji="💧", unit="m³",     color="#44ccaa"),
        CostCategory(id="cat-wood",        name="Wood",           emoji="🪵", unit="stère",  color="#cc8844"),
        CostCategory(id="cat-tax",         name="Property Tax",   emoji="🏠", unit=None,     color="#9966cc"),
        CostCategory(id="cat-insurance",   name="Insurance",      emoji="🛡️", unit=None,     color="#7a5cc4"),
    ]
```

- [ ] **Step 4: Wire `persistence_settings.py`**

Add imports:

```python
from .models_settings import (
    ConsumableCategory,
    CostCategory,
    CostCategoryPlacement,
    CostCategoryPosition,
    InventoryCategory,
    InsuranceCategory,
    NotificationSettings,
    SettingsDocument,
    ContactType,
    WorkCategory,
    _default_cost_categories,
    _default_consumable_units,
    _default_inventory_categories,
    _default_work_categories,
    _default_contact_types,
    _default_insurance_categories,
)
from .schema import (
    consumable_categories as consumable_categories_table,
    cost_categories as cost_categories_table,
    inventory_categories as inventory_categories_table,
    settings as settings_table,
    contact_types as contact_types_table,
    work_categories as work_categories_table,
    insurance_categories as insurance_categories_table,
)
```

In `load_settings`, add `insuranceCategories=_default_insurance_categories()` to the early `row is None` return, add the row query, and add it to the final constructed `SettingsDocument`:

```python
        if row is None:
            return SettingsDocument(
                costCategories=_default_cost_categories(),
                inventoryCategories=_default_inventory_categories(),
                workCategories=_default_work_categories(),
                consumableUnits=_default_consumable_units(),
                contactTypes=_default_contact_types(),
                insuranceCategories=_default_insurance_categories(),
            )
        ...
        insurance_cat_rows = conn.execute(
            select(insurance_categories_table).where(insurance_categories_table.c.home_id == home_id)
            .order_by(insurance_categories_table.c.order_index)
        ).mappings().all()

    return SettingsDocument(
        ...
        insuranceCategories=[
            InsuranceCategory(id=r["id"], name=r["name"], emoji=r["emoji"]) for r in insurance_cat_rows
        ],
        notifications=NotificationSettings(...),
    )
```

In `save_settings`, add the delete-then-reinsert block after the `consumable_categories_table` block:

```python
        conn.execute(insurance_categories_table.delete().where(insurance_categories_table.c.home_id == home_id))
        if doc.insuranceCategories:
            conn.execute(insurance_categories_table.insert(), [
                {"id": c.id, "home_id": home_id, "order_index": i, "name": c.name, "emoji": c.emoji}
                for i, c in enumerate(doc.insuranceCategories)
            ])
```

- [ ] **Step 5: Add the route in `routes/settings.py`**

```python
from ..models_settings import (
    ConsumableCategory,
    CostCategory,
    CostCategoryPlacement,
    InventoryCategory,
    NotificationSettings,
    WorkCategory,
    ContactType,
    InsuranceCategory,
    SettingsDocument,
)
```

```python
@router.put("/api/homes/{home_id}/settings/insurance-categories", status_code=204)
def put_insurance_categories(home_id: str, body: list[InsuranceCategory]) -> None:
    doc = load_settings(home_id)
    doc.insuranceCategories = body
    save_settings(home_id, doc)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_settings.py -v`
Expected: All PASS.

- [ ] **Step 7: Run the full backend suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: All PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/backend/src/myhome/models_settings.py packages/backend/src/myhome/persistence_settings.py packages/backend/src/myhome/routes/settings.py packages/backend/tests/test_settings.py
git commit -m "feat(insurance): add editable Insurance Categories to Settings"
```

---

## Task 6: Backend — MCP tools for Insurance

**Files:**
- Create: `packages/backend/src/myhome/mcp_tools_insurance.py`
- Modify: `packages/backend/src/myhome/mcp_app.py`
- Create: `packages/backend/tests/test_mcp_tools_insurance.py`

**Interfaces:**
- Consumes: `load_insurance`/`save_insurance` (Task 2), `InsurancePolicy` (Task 2), `_require_role`/`_resolve_home_id`/`mcp` (existing `mcp_server.py`).
- Note: MCP tools intentionally do **not** run the cost-sync logic from Task 4 (that lives in the HTTP route layer only) — an MCP-created/updated policy with `include_in_costs=True` will not appear in Costs until edited via the UI/API route. This mirrors how `mcp_tools_works.py` doesn't duplicate any route-only side effects either. Document this in the tool docstring.

- [ ] **Step 1: Write the failing MCP tool test**

Create `packages/backend/tests/test_mcp_tools_insurance.py`, modeled on `test_mcp_tools_works.py` (check that file for the exact `ctx`/role-mocking fixture pattern used across MCP tool tests before writing — likely a `_FakeCtx`/`_mock_request` helper shared via `conftest.py` or duplicated per test file):

```python
import pytest
from myhome.mcp_tools_insurance import (
    _create_insurance_policy_impl,
    _delete_insurance_policy_impl,
    _list_insurance_policies_impl,
    _update_insurance_policy_impl,
)
from myhome.mcp_server import _resolve_home_id


def test_create_and_list_policy(home_id, monkeypatch):
    monkeypatch.setattr("myhome.mcp_tools_insurance._resolve_home_id", lambda h: home_id)
    created = _create_insurance_policy_impl(
        home_id, name="Home Insurance", category_id="icat-home", premium_frequency="monthly",
    )
    assert created["name"] == "Home Insurance"
    listed = _list_insurance_policies_impl(home_id)
    assert len(listed["policies"]) == 1


def test_update_policy(home_id, monkeypatch):
    monkeypatch.setattr("myhome.mcp_tools_insurance._resolve_home_id", lambda h: home_id)
    created = _create_insurance_policy_impl(home_id, name="Home Insurance", category_id="icat-home", premium_frequency="monthly")
    updated = _update_insurance_policy_impl(home_id, created["id"], premium_amount=45.0)
    assert updated["premiumAmount"] == 45.0


def test_update_policy_unknown_id_raises(home_id, monkeypatch):
    monkeypatch.setattr("myhome.mcp_tools_insurance._resolve_home_id", lambda h: home_id)
    with pytest.raises(ValueError):
        _update_insurance_policy_impl(home_id, "nope", premium_amount=1.0)


def test_delete_policy(home_id, monkeypatch):
    monkeypatch.setattr("myhome.mcp_tools_insurance._resolve_home_id", lambda h: home_id)
    created = _create_insurance_policy_impl(home_id, name="Home Insurance", category_id="icat-home", premium_frequency="monthly")
    result = _delete_insurance_policy_impl(home_id, created["id"])
    assert result == {"deleted": created["id"]}
    assert _list_insurance_policies_impl(home_id)["policies"] == []
```

(This test file needs the same `home_id`/DB-setup fixtures `test_mcp_tools_works.py` uses — read that file first and match its exact fixture usage; the sketch above assumes a `home_id` fixture equivalent to the one in `conftest.py`, but MCP-tool tests may set up the database differently since they call `_impl` functions directly rather than going through `TestClient`. Adjust setup accordingly.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_mcp_tools_insurance.py -v`
Expected: FAIL — `myhome.mcp_tools_insurance` doesn't exist.

- [ ] **Step 3: Create `mcp_tools_insurance.py`**

```python
from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_insurance import InsurancePolicy
from .persistence_insurance import load_insurance, save_insurance

_VALID_FREQUENCIES = ("monthly", "quarterly", "annual", "other")


def _list_insurance_policies_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_insurance(resolved).model_dump()


def _create_insurance_policy_impl(
    home_id: str | None,
    name: str,
    category_id: str,
    contact_id: str | None = None,
    policy_number: str | None = None,
    coverage_summary: str = "",
    conditions_url: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    premium_amount: float | None = None,
    premium_frequency: str = "annual",
    include_in_costs: bool = False,
    alternatives: str = "",
    notes: str = "",
) -> dict:
    if premium_frequency not in _VALID_FREQUENCIES:
        raise ValueError(f"premium_frequency must be one of {_VALID_FREQUENCIES}")
    resolved = _resolve_home_id(home_id)
    doc = load_insurance(resolved)
    policy = InsurancePolicy(
        id=str(uuid.uuid4()), name=name, categoryId=category_id, contactId=contact_id,
        policyNumber=policy_number, coverageSummary=coverage_summary, conditionsUrl=conditions_url,
        startDate=start_date, endDate=end_date, premiumAmount=premium_amount,
        premiumFrequency=premium_frequency, includeInCosts=include_in_costs,
        alternatives=alternatives, notes=notes,
    )
    doc.policies.append(policy)
    save_insurance(resolved, doc)
    return policy.model_dump()


def _update_insurance_policy_impl(home_id: str | None, policy_id: str, **fields) -> dict:
    if fields.get("premiumFrequency") is not None and fields["premiumFrequency"] not in _VALID_FREQUENCIES:
        raise ValueError(f"premium_frequency must be one of {_VALID_FREQUENCIES}")
    resolved = _resolve_home_id(home_id)
    doc = load_insurance(resolved)
    policy = next((p for p in doc.policies if p.id == policy_id), None)
    if policy is None:
        raise ValueError(f"Unknown policy_id {policy_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(policy, field, value)
    save_insurance(resolved, doc)
    return policy.model_dump()


def _delete_insurance_policy_impl(home_id: str | None, policy_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_insurance(resolved)
    before = len(doc.policies)
    doc.policies = [p for p in doc.policies if p.id != policy_id]
    if len(doc.policies) == before:
        raise ValueError(f"Unknown policy_id {policy_id!r}")
    save_insurance(resolved, doc)
    return {"deleted": policy_id}


@mcp.tool()
async def list_insurance_policies(ctx: Context, home_id: str | None = None) -> dict:
    """List insurance policies for a home (home, auto, health, life, travel, liability, etc.)."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_insurance_policies_impl(home_id)


@mcp.tool()
async def create_insurance_policy(
    ctx: Context,
    name: str,
    category_id: str,
    home_id: str | None = None,
    contact_id: str | None = None,
    policy_number: str | None = None,
    coverage_summary: str = "",
    conditions_url: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    premium_amount: float | None = None,
    premium_frequency: str = "annual",
    include_in_costs: bool = False,
    alternatives: str = "",
    notes: str = "",
) -> dict:
    """Create an insurance policy. premium_frequency is 'monthly', 'quarterly', 'annual', or 'other'.
    category_id should match an id from get_settings's insuranceCategories. Note: unlike the web UI,
    this tool does NOT sync include_in_costs=True policies into the Costs module — that sync only
    runs through the HTTP route layer. Use the app UI or REST API if the Costs sync matters."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_insurance_policy_impl(
        home_id, name, category_id, contact_id, policy_number, coverage_summary, conditions_url,
        start_date, end_date, premium_amount, premium_frequency, include_in_costs, alternatives, notes,
    )


@mcp.tool()
async def update_insurance_policy(
    ctx: Context,
    policy_id: str,
    home_id: str | None = None,
    name: str | None = None,
    category_id: str | None = None,
    contact_id: str | None = None,
    policy_number: str | None = None,
    coverage_summary: str | None = None,
    conditions_url: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    premium_amount: float | None = None,
    premium_frequency: str | None = None,
    include_in_costs: bool | None = None,
    alternatives: str | None = None,
    notes: str | None = None,
) -> dict:
    """Update fields on an existing insurance policy. See create_insurance_policy's note about Costs sync."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_insurance_policy_impl(
        home_id, policy_id, name=name, categoryId=category_id, contactId=contact_id,
        policyNumber=policy_number, coverageSummary=coverage_summary, conditionsUrl=conditions_url,
        startDate=start_date, endDate=end_date, premiumAmount=premium_amount,
        premiumFrequency=premium_frequency, includeInCosts=include_in_costs,
        alternatives=alternatives, notes=notes,
    )


@mcp.tool()
async def delete_insurance_policy(ctx: Context, policy_id: str, home_id: str | None = None) -> dict:
    """Delete an insurance policy."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_insurance_policy_impl(home_id, policy_id)
```

- [ ] **Step 4: Register the module in `mcp_app.py`**

```python
from . import (  # noqa: F401 - imported for the side effect of registering tools
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

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_mcp_tools_insurance.py -v`
Expected: All PASS (after adjusting fixture setup to match `test_mcp_tools_works.py`'s actual pattern per Step 1's note).

- [ ] **Step 6: Run the full backend suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: All PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_insurance.py packages/backend/src/myhome/mcp_app.py packages/backend/tests/test_mcp_tools_insurance.py
git commit -m "feat(insurance): add MCP tools for insurance policy CRUD"
```

---

## Task 7: Backend — Demo data

**Files:**
- Modify: `packages/backend/src/myhome/demo_content.py`
- Modify: `packages/backend/src/myhome/demo_data.py`
- Modify (test): find and extend the existing demo-seeding test (`grep -rn "seed_demo_home" packages/backend/tests/` to locate it)

**Interfaces:**
- Consumes: `generate_demo_contacts()`, `SettingsDocument` (existing `demo_content.py`), `HouseDocument` (existing `.models`).
- Produces: `generate_demo_insurance(settings, contacts, rng) -> InsuranceDocument`, called from `seed_demo_home()`.

- [ ] **Step 1: Write the failing demo-seeding assertion**

Find the existing test that calls `seed_demo_home` (likely `test_demo_data.py` or similar — run `grep -rln "seed_demo_home" packages/backend/tests/`) and add:

```python
def test_seed_demo_home_creates_insurance_policies(client, home_id):
    from myhome.demo_data import seed_demo_home
    seed_demo_home(home_id)
    resp = client.get(f"/api/homes/{home_id}/insurance")
    policies = resp.json()["policies"]
    assert len(policies) >= 3
    home_policies = [p for p in policies if p["categoryId"] == "icat-home"]
    assert any(p["includeInCosts"] for p in home_policies)
    non_home = [p for p in policies if p["categoryId"] != "icat-home"]
    assert any(not p["includeInCosts"] for p in non_home)
```

(Match this test's structure — imports, fixtures — to whatever the existing demo-seeding test file already uses; the sketch above assumes the same `client`/`home_id` fixtures as other route tests.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd packages/backend && python -m pytest -k "seed_demo_home_creates_insurance" -v`
Expected: FAIL — no insurance data seeded.

- [ ] **Step 3: Add demo insurance content to `demo_content.py`**

Add `INSURANCE_POLICIES` near `WORKS`, and `_INSURANCE_CATEGORIES` near the other demo category lists (following the exact `_default_insurance_categories()` id/name/emoji set from Task 5, so demo homes use the same real category ids the rest of the app expects):

```python
_INSURANCE_CATEGORIES = [
    InsuranceCategory(id="icat-home",      name="Home",      emoji="🏠"),
    InsuranceCategory(id="icat-auto",      name="Auto",      emoji="🚗"),
    InsuranceCategory(id="icat-health",    name="Health",    emoji="⚕️"),
    InsuranceCategory(id="icat-life",      name="Life",      emoji="❤️"),
    InsuranceCategory(id="icat-travel",    name="Travel",    emoji="✈️"),
    InsuranceCategory(id="icat-liability", name="Liability", emoji="🛡️"),
]

# (name, categoryId, premiumAmount, premiumFrequency, includeInCosts)
INSURANCE_POLICIES: list[tuple[str, str, float, str, bool]] = [
    ("Home Insurance — AXA", "icat-home", 42.0, "monthly", True),
    ("Car Insurance — Allianz", "icat-auto", 65.0, "monthly", False),
    ("Health Insurance — Mutuelle Générale", "icat-health", 180.0, "monthly", False),
    ("Life Insurance — CNP", "icat-life", 25.0, "monthly", False),
    ("Annual Travel Insurance — Europ Assistance", "icat-travel", 89.0, "annual", False),
]
```

Add `InsuranceCategory` to the `from .models_settings import (...)` block at the top, and add `insuranceCategories=list(_INSURANCE_CATEGORIES)` to `generate_demo_settings()`'s returned `SettingsDocument`.

- [ ] **Step 4: Add `generate_demo_insurance` to `demo_data.py`**

Add the import:

```python
from .demo_content import (
    ...
    INSURANCE_POLICIES,
    ...
)
from .models_insurance import InsuranceDocument, InsurancePolicy
from . import (
    ...
    persistence_insurance,
    ...
)
```

Add the generator function near `generate_demo_works`:

```python
def generate_demo_insurance(settings: SettingsDocument, contacts: list[Contact], rng: random.Random) -> InsuranceDocument:
    today = date.today()
    contact_ids = [c.id for c in contacts if c.typeId == "ctype-service"]
    policies: list[InsurancePolicy] = []
    for name, category_id, premium, frequency, include_in_costs in INSURANCE_POLICIES:
        start = today - timedelta(days=rng.randint(30, 300))
        end = start + timedelta(days=365)
        policies.append(InsurancePolicy(
            id=str(uuid.uuid4()), name=name, categoryId=category_id,
            contactId=rng.choice(contact_ids) if contact_ids else None,
            premiumAmount=premium, premiumFrequency=frequency, includeInCosts=include_in_costs,
            startDate=start.isoformat(), endDate=end.isoformat(),
        ))
    return InsuranceDocument(policies=policies)
```

Wire it into `seed_demo_home`:

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
    insurance_doc = generate_demo_insurance(settings, contacts, rng)

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
    persistence_insurance.save_insurance(home_id, insurance_doc)

    attach_demo_files(home_id, chores_doc, inventory_doc, costs_doc, works_doc, rng)
    persistence_chores.save_chores(home_id, chores_doc)
    persistence_inventory.save_inventory(home_id, inventory_doc)
    persistence_costs.save_costs(home_id, costs_doc)
    persistence_works.save_works(home_id, works_doc)
```

Note: demo insurance is seeded independently of `costs_doc` — it does **not** go through the `_sync_cost_entry` route logic from Task 4 (that's HTTP-route-only, same as the MCP tools). The demo Home policy's `includeInCosts=True` flag will be correct in the UI, but won't retroactively appear in `costs_doc`'s seeded entries; this is acceptable for demo data (a user editing the demo policy afterward through the UI will trigger the real sync).

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd packages/backend && python -m pytest -k "seed_demo_home_creates_insurance" -v`
Expected: PASS.

- [ ] **Step 6: Run the full backend suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: All PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/demo_content.py packages/backend/src/myhome/demo_data.py packages/backend/tests/
git commit -m "feat(insurance): seed demo insurance policies"
```

---

## Task 8: Frontend — `insuranceStore.svelte.ts`

**Files:**
- Create: `packages/editor/src/lib/insuranceStore.svelte.ts`
- Create: `packages/editor/test/insuranceStore.test.ts`

**Interfaces:**
- Produces: `InsurancePolicy`, `InsuranceDocument` (types), `createInsuranceStore(getHomeId)` returning `{ policies, loaded, loadError, createPolicy, updatePolicy, deletePolicy, uploadAttachment, deleteAttachment, reload }` — consumed by Task 10's `InsurancePage.svelte`/`InsuranceModal.svelte` and by `App.svelte`.

- [ ] **Step 1: Write the failing store test**

Create `packages/editor/test/insuranceStore.test.ts` (modeled on `worksStore.test.ts`):

```typescript
import { describe, it, expect, afterEach, vi } from "vitest";
import { createInsuranceStore } from "../src/lib/insuranceStore.svelte";
import type { InsurancePolicy } from "../src/lib/insuranceStore.svelte";

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

function makePolicy(overrides: Partial<InsurancePolicy> = {}): InsurancePolicy {
  return {
    id: "ins1", name: "Home Insurance", categoryId: "icat-home", contactId: null,
    policyNumber: null, coverageSummary: "", conditionsUrl: null, startDate: null, endDate: null,
    premiumAmount: 45, premiumFrequency: "monthly", includeInCosts: true,
    alternatives: "", notes: "", attachments: [], linkedCostEntryId: "c1",
    ...overrides,
  };
}

const emptyDoc = { version: 1, policies: [] };

describe("insuranceStore — init", () => {
  it("loads policies from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, policies: [makePolicy()] }));
    const store = createInsuranceStore(getHomeId);
    await tick();
    expect(store.policies.length).toBe(1);
    expect(store.policies[0].id).toBe("ins1");
    expect(store.loaded).toBe(true);
  });

  it("marks loaded on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("net fail")));
    const store = createInsuranceStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("net fail");
  });

  it("does not fetch when no homeId provided", async () => {
    const fetchFn = vi.fn();
    vi.stubGlobal("fetch", fetchFn);
    const store = createInsuranceStore();
    await tick();
    expect(fetchFn).not.toHaveBeenCalled();
    expect(store.loaded).toBe(true);
  });
});

describe("insuranceStore — createPolicy", () => {
  it("posts to /api/homes/{homeId}/insurance and refreshes", async () => {
    const created = makePolicy({ id: "ins2", name: "Travel Insurance" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, policies: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createInsuranceStore(getHomeId);
    await tick();
    await store.createPolicy({
      name: "Travel Insurance", categoryId: "icat-travel", contactId: null, policyNumber: null,
      coverageSummary: "", conditionsUrl: null, startDate: null, endDate: null,
      premiumAmount: null, premiumFrequency: "annual", includeInCosts: false, alternatives: "", notes: "",
    });
    await tick();
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/insurance`);
    expect(fetchFn.mock.calls[1][1].method).toBe("POST");
    expect(store.policies.length).toBe(1);
  });
});

describe("insuranceStore — deletePolicy", () => {
  it("calls DELETE /api/homes/{homeId}/insurance/{id}", async () => {
    const fetchFn = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createInsuranceStore(getHomeId);
    await tick();
    await store.deletePolicy("ins1");
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/insurance/ins1`);
    expect(fetchFn.mock.calls[1][1].method).toBe("DELETE");
  });
});

describe("insuranceStore — uploadAttachment", () => {
  it("posts multipart form to /api/homes/{homeId}/insurance/{id}/attachments", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({ filename: "policy.pdf" }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createInsuranceStore(getHomeId);
    await tick();
    const file = new File(["%PDF"], "policy.pdf", { type: "application/pdf" });
    const filename = await store.uploadAttachment("ins1", file);
    expect(filename).toBe("policy.pdf");
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/insurance/ins1/attachments`);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd packages/editor && npx vitest run test/insuranceStore.test.ts`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Create `insuranceStore.svelte.ts`**

```typescript
// packages/editor/src/lib/insuranceStore.svelte.ts

export interface InsurancePolicy {
  id: string;
  name: string;
  categoryId: string;
  contactId: string | null;
  policyNumber: string | null;
  coverageSummary: string;
  conditionsUrl: string | null;
  startDate: string | null;
  endDate: string | null;
  premiumAmount: number | null;
  premiumFrequency: "monthly" | "quarterly" | "annual" | "other";
  includeInCosts: boolean;
  alternatives: string;
  notes: string;
  attachments: string[];
  linkedCostEntryId: string | null;
}

export interface InsuranceDocument {
  version: number;
  policies: InsurancePolicy[];
}

export function createInsuranceStore(getHomeId: () => string | null = () => null) {
  const policies = $state<InsurancePolicy[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/insurance`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: InsuranceDocument = await resp.json();
      policies.length = 0;
      for (const p of doc.policies) policies.push(p);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createPolicy(
    data: Omit<InsurancePolicy, "id" | "attachments" | "linkedCostEntryId">
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/insurance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updatePolicy(
    id: string,
    patch: Partial<Omit<InsurancePolicy, "id" | "attachments" | "linkedCostEntryId">>
  ): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/insurance/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deletePolicy(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/insurance/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function uploadAttachment(id: string, file: File): Promise<string> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`/api/homes/${homeId}/insurance/${id}/attachments`, {
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
    const resp = await fetch(`/api/homes/${homeId}/insurance/${id}/attachments/${filename}`, {
      method: "DELETE",
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  init();

  return {
    get policies() { return policies as InsurancePolicy[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createPolicy,
    updatePolicy,
    deletePolicy,
    uploadAttachment,
    deleteAttachment,
    reload: init,
  };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd packages/editor && npx vitest run test/insuranceStore.test.ts`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/insuranceStore.svelte.ts packages/editor/test/insuranceStore.test.ts
git commit -m "feat(insurance): add insuranceStore.svelte.ts"
```

---

## Task 9: Frontend — `settingsStore.svelte.ts` insurance categories

**Files:**
- Modify: `packages/editor/src/lib/settingsStore.svelte.ts`
- Modify: `packages/editor/test/settingsStore.test.ts` (confirm filename with `ls packages/editor/test/settingsStore*`)

**Interfaces:**
- Produces: `InsuranceCategory` type, `store.insuranceCategories`, `store.updateInsuranceCategories(list)` — consumed by Task 10's `InsurancePage.svelte`/`InsuranceModal.svelte` and Task 11's Settings tab.

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/settingsStore.test.ts` (match its existing style/fixtures — likely near the `workCategories`/`updateWorkCategories` tests):

```typescript
describe("settingsStore — insuranceCategories", () => {
  it("loads insuranceCategories from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, {
      version: 1, costCategories: [], inventoryCategories: [], workCategories: [],
      contactTypes: [], consumableUnits: [], consumableCategories: [],
      insuranceCategories: [{ id: "icat-home", name: "Home", emoji: "🏠" }],
      notifications: {},
    }));
    const store = createSettingsStore(getHomeId);
    await tick();
    expect(store.insuranceCategories).toEqual([{ id: "icat-home", name: "Home", emoji: "🏠" }]);
  });

  it("updateInsuranceCategories PUTs to /api/homes/{homeId}/settings/insurance-categories", async () => {
    const fetchFn = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ version: 1, costCategories: [], inventoryCategories: [], workCategories: [], contactTypes: [], consumableUnits: [], consumableCategories: [], insuranceCategories: [], notifications: {} }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createSettingsStore(getHomeId);
    await tick();
    await store.updateInsuranceCategories([{ id: "icat-pet", name: "Pet", emoji: "🐶" }]);
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/settings/insurance-categories`);
    expect(fetchFn.mock.calls[1][1].method).toBe("PUT");
  });
});
```

(Adjust `makeFetch`/`HOME`/`tick`/`getHomeId` helper names to match whatever the existing test file already defines — do not redefine duplicates.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd packages/editor && npx vitest run test/settingsStore.test.ts -t insuranceCategories`
Expected: FAIL — `store.insuranceCategories` undefined, `updateInsuranceCategories` not a function.

- [ ] **Step 3: Add insurance categories to `settingsStore.svelte.ts`**

```typescript
export interface InsuranceCategory {
  id: string;
  name: string;
  emoji: string;
}
```

Add to `SettingsDocument` interface:

```typescript
export interface SettingsDocument {
  version: number;
  costCategories: CostCategory[];
  inventoryCategories: InventoryCategory[];
  workCategories: WorkCategory[];
  contactTypes: ContactType[];
  consumableUnits: string[];
  consumableCategories: ConsumableCategory[];
  insuranceCategories: InsuranceCategory[];
  notifications: NotificationSettings;
}
```

Add state + init loading:

```typescript
  const insuranceCategories = $state<InsuranceCategory[]>([]);
```

```typescript
      consumableCategories.length = 0;
      for (const c of (doc.consumableCategories ?? [])) consumableCategories.push(c);
      insuranceCategories.length = 0;
      for (const c of (doc.insuranceCategories ?? [])) insuranceCategories.push(c);
      if (doc.notifications) Object.assign(notificationSettings, doc.notifications);
```

Add the update function:

```typescript
  async function updateInsuranceCategories(list: InsuranceCategory[]): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/settings/insurance-categories`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(list),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }
```

Add to the returned object:

```typescript
    get insuranceCategories() { return insuranceCategories as InsuranceCategory[]; },
    ...
    updateInsuranceCategories,
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd packages/editor && npx vitest run test/settingsStore.test.ts`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/settingsStore.svelte.ts packages/editor/test/settingsStore.test.ts
git commit -m "feat(insurance): add insuranceCategories to settingsStore"
```

---

## Task 10: Frontend — `InsurancePage.svelte`, `InsuranceModal.svelte`, routing, locale

**Files:**
- Create: `packages/editor/src/lib/components/InsurancePage.svelte`
- Create: `packages/editor/src/lib/components/InsuranceModal.svelte`
- Modify: `packages/editor/src/App.svelte`
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`
- Create: `packages/editor/test/InsurancePage.test.ts`
- Create: `packages/editor/test/InsuranceModal.test.ts`

**Interfaces:**
- Consumes: `createInsuranceStore`/`InsurancePolicy` (Task 8), `store.insuranceCategories`/`store.contactTypes`-equivalent via `settingsStore` (Task 9), `contactsStore` (existing), `DonutChart`/`assignCategoryColors` (existing, from `InventoryPage.svelte`'s pattern), `MediaGallery`/`Lightbox`/`DatePicker`/`Modal`/`Input`/`Button`/`MarkdownEditor`/`Card`/`SortableTable`/`Tabs` (existing shared UI), `homesStore.activeHomeId` (existing singleton, for correctly home-scoped attachment URLs — see Step 3's note).

- [ ] **Step 1: Write the failing page test**

Create `packages/editor/test/InsurancePage.test.ts` (modeled on `WorksPage.test.ts`):

```typescript
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import InsurancePage from "../src/lib/components/InsurancePage.svelte";
import type { InsurancePolicy } from "../src/lib/insuranceStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makePolicy(overrides: Partial<InsurancePolicy> = {}): InsurancePolicy {
  return {
    id: "ins1", name: "Home Insurance", categoryId: "icat-home", contactId: null,
    policyNumber: null, coverageSummary: "", conditionsUrl: null, startDate: null, endDate: null,
    premiumAmount: 45, premiumFrequency: "monthly", includeInCosts: true,
    alternatives: "", notes: "", attachments: [], linkedCostEntryId: "c1",
    ...overrides,
  };
}

function makeInsuranceStore(policies: InsurancePolicy[]) {
  return {
    policies, loaded: true, loadError: null,
    createPolicy: vi.fn(), updatePolicy: vi.fn(), deletePolicy: vi.fn(),
    uploadAttachment: vi.fn(), deleteAttachment: vi.fn(),
  };
}

function makeSettingsStore() {
  return { insuranceCategories: [{ id: "icat-home", name: "Home", emoji: "🏠" }] };
}

function makeContactsStore() {
  return { contacts: [] };
}

describe("InsurancePage — list rendering", () => {
  it("renders a row for each policy", () => {
    const store = makeInsuranceStore([makePolicy(), makePolicy({ id: "ins2", name: "Travel Insurance", categoryId: "icat-travel", includeInCosts: false })]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InsurancePage, {
      target,
      props: { store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore() },
    });
    flushSync();

    expect(target.textContent).toContain("Home Insurance");
    expect(target.textContent).toContain("Travel Insurance");

    unmount(comp);
  });
});

describe("InsurancePage — add policy", () => {
  it("opens the create modal when Add policy is clicked", () => {
    const store = makeInsuranceStore([]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InsurancePage, {
      target,
      props: { store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore() },
    });
    flushSync();

    const addButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Add policy"));
    addButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".ui-modal-title")?.textContent).toContain("New policy");

    unmount(comp);
  });
});
```

Create `packages/editor/test/InsuranceModal.test.ts`:

```typescript
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import InsuranceModal from "../src/lib/components/InsuranceModal.svelte";
import type { InsurancePolicy } from "../src/lib/insuranceStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makePolicy(overrides: Partial<InsurancePolicy> = {}): InsurancePolicy {
  return {
    id: "ins1", name: "Home Insurance", categoryId: "icat-home", contactId: null,
    policyNumber: null, coverageSummary: "", conditionsUrl: null, startDate: null, endDate: null,
    premiumAmount: 45, premiumFrequency: "monthly", includeInCosts: true,
    alternatives: "", notes: "", attachments: [], linkedCostEntryId: "c1",
    ...overrides,
  };
}

function makeInsuranceStore(policies: InsurancePolicy[] = []) {
  return {
    policies, loaded: true, loadError: null,
    createPolicy: vi.fn(), updatePolicy: vi.fn(), deletePolicy: vi.fn(),
    uploadAttachment: vi.fn(), deleteAttachment: vi.fn(),
  };
}

function makeSettingsStore() {
  return { insuranceCategories: [{ id: "icat-home", name: "Home", emoji: "🏠" }, { id: "icat-travel", name: "Travel", emoji: "✈️" }] };
}

function makeContactsStore() {
  return { contacts: [] };
}

describe("InsuranceModal — create", () => {
  it("defaults includeInCosts to checked when category is Home", async () => {
    const store = makeInsuranceStore();
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InsuranceModal, {
      target,
      props: { policy: null, store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore(), onclose: vi.fn() },
    });
    flushSync();

    const checkbox = target.querySelector('input[type="checkbox"]') as HTMLInputElement;
    expect(checkbox.checked).toBe(true);

    unmount(comp);
  });

  it("calls createPolicy with entered fields on save", async () => {
    const store = makeInsuranceStore();
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InsuranceModal, {
      target,
      props: { policy: null, store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore(), onclose: vi.fn() },
    });
    flushSync();

    const nameInput = target.querySelector(".ui-modal input") as HTMLInputElement;
    nameInput.value = "New Policy";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();

    const saveButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Create"));
    saveButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await Promise.resolve();

    expect(store.createPolicy).toHaveBeenCalledOnce();
    expect(store.createPolicy.mock.calls[0][0].name).toBe("New Policy");

    unmount(comp);
  });
});

describe("InsuranceModal — edit", () => {
  it("pre-fills fields from the existing policy", () => {
    const policy = makePolicy({ name: "Existing Policy" });
    const store = makeInsuranceStore([policy]);
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InsuranceModal, {
      target,
      props: { policy, store, settingsStore: makeSettingsStore(), contactsStore: makeContactsStore(), onclose: vi.fn() },
    });
    flushSync();

    const nameInput = target.querySelector(".ui-modal input") as HTMLInputElement;
    expect(nameInput.value).toBe("Existing Policy");

    unmount(comp);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/InsurancePage.test.ts test/InsuranceModal.test.ts`
Expected: FAIL — components don't exist.

- [ ] **Step 3: Create `InsuranceModal.svelte`**

```svelte
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createInsuranceStore, InsurancePolicy } from "../insuranceStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createContactsStore } from "../contactsStore.svelte";
  import type { MediaItem } from "./ui/mediaTypes";
  import { apiUrl } from "../apiUrl";
  import { homesStore } from "../homesStore.svelte";
  import DatePicker from "./DatePicker.svelte";
  import Modal from "./ui/Modal.svelte";
  import Input from "./ui/Input.svelte";
  import Button from "./ui/Button.svelte";
  import MarkdownEditor from "./ui/MarkdownEditor.svelte";
  import MediaGallery from "./ui/MediaGallery.svelte";
  import Lightbox from "./ui/Lightbox.svelte";

  type InsuranceStore = ReturnType<typeof createInsuranceStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type ContactsStore = ReturnType<typeof createContactsStore>;

  interface Props {
    policy: InsurancePolicy | null;
    store: InsuranceStore;
    settingsStore: SettingsStore;
    contactsStore: ContactsStore;
    onclose: () => void;
  }

  let { policy, store, settingsStore, contactsStore, onclose }: Props = $props();

  const isCreate = policy === null;

  let activeTab = $state<"details" | "cost" | "coverage" | "alternatives">("details");
  let name = $state(policy?.name ?? "");
  let categoryId = $state(policy?.categoryId ?? settingsStore.insuranceCategories[0]?.id ?? "");
  let contactId = $state(policy?.contactId ?? "");
  let policyNumber = $state(policy?.policyNumber ?? "");
  let startDate = $state(policy?.startDate ?? "");
  let endDate = $state(policy?.endDate ?? "");
  let premiumAmount = $state<string>(policy?.premiumAmount != null ? String(policy.premiumAmount) : "");
  let premiumFrequency = $state<InsurancePolicy["premiumFrequency"]>(policy?.premiumFrequency ?? "annual");
  let includeInCosts = $state(policy?.includeInCosts ?? categoryId === "icat-home");
  let coverageSummary = $state(policy?.coverageSummary ?? "");
  let conditionsUrl = $state(policy?.conditionsUrl ?? "");
  let alternatives = $state(policy?.alternatives ?? "");
  let notes = $state(policy?.notes ?? "");

  let editingNotes = $state(isCreate);
  let saving = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let error = $state<string | null>(null);
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);

  let lightboxOpen = $state(false);
  let lightboxIndex = $state(0);

  async function handleSave(): Promise<void> {
    if (!name.trim()) { error = $_('insurance.modal.nameRequired'); return; }
    if (!categoryId) { error = $_('insurance.modal.categoryRequired'); return; }
    saving = true; error = null;
    const patch = {
      name: name.trim(),
      categoryId,
      contactId: contactId || null,
      policyNumber: policyNumber.trim() || null,
      coverageSummary: coverageSummary.trim(),
      conditionsUrl: conditionsUrl.trim() || null,
      startDate: startDate || null,
      endDate: endDate || null,
      premiumAmount: premiumAmount ? parseFloat(premiumAmount) || null : null,
      premiumFrequency,
      includeInCosts,
      alternatives: alternatives.trim(),
      notes: notes.trim(),
    };
    try {
      if (isCreate) {
        await store.createPolicy(patch);
        onclose();
      } else {
        await store.updatePolicy(policy!.id, patch);
        editingNotes = false;
        onclose();
      }
    } catch (e) {
      error = e instanceof Error ? e.message : $_('insurance.modal.saveFailed');
    } finally {
      saving = false;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!policy) return;
    deleting = true;
    try {
      await store.deletePolicy(policy.id);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : $_('insurance.modal.deleteFailed');
      deleting = false;
    }
  }

  async function handleUpload(files: File[]): Promise<void> {
    if (!policy) return;
    uploading = true; uploadError = null;
    try {
      for (const file of files) {
        await store.uploadAttachment(policy.id, file);
      }
    } catch (err) {
      uploadError = err instanceof Error ? err.message : $_('insurance.modal.uploadFailed');
    } finally {
      uploading = false;
    }
  }

  async function handleDeleteAttachment(id: string): Promise<void> {
    if (!policy) return;
    try {
      await store.deleteAttachment(policy.id, id);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : $_('insurance.modal.deleteFailed');
    }
  }

  function handleItemClick(index: number): void {
    lightboxIndex = index;
    lightboxOpen = true;
  }

  const currentPolicy = $derived(
    policy ? (store.policies.find(p => p.id === policy.id) ?? policy) : null
  );
  const attachmentCount = $derived(currentPolicy?.attachments.length ?? 0);

  const mediaItems = $derived<MediaItem[]>(
    (currentPolicy?.attachments ?? []).map(fname => {
      const homeId = homesStore.activeHomeId;
      const url = apiUrl(`/api/homes/${homeId}/insurance/${policy!.id}/attachments/${fname}`);
      const isPdf = fname.toLowerCase().endsWith(".pdf");
      return {
        id: fname,
        name: fname,
        url,
        thumbnailUrl: isPdf ? `${url}.thumb.jpg` : url,
        type: isPdf ? "document" : "image",
      };
    })
  );
</script>

<Modal open={true} title={isCreate ? `＋ ${$_('insurance.modal.newPolicy')}` : $_('insurance.modal.editPolicy')} {onclose} width="min(92vw, 820px)">
  <div class="tabs">
    <button class="tab" class:active={activeTab === "details"} onclick={() => { activeTab = "details"; }}>{$_('chores.editModal.info')}</button>
    <button class="tab" class:active={activeTab === "cost"} onclick={() => { activeTab = "cost"; }}>{$_('insurance.modal.costTab')}</button>
    <button class="tab" class:active={activeTab === "coverage"} onclick={() => { activeTab = "coverage"; }}>{$_('insurance.modal.coverageTab')}</button>
    <button class="tab" class:active={activeTab === "alternatives"} onclick={() => { activeTab = "alternatives"; }}>{$_('insurance.modal.alternativesTab')}</button>
  </div>

  {#if activeTab === "details"}
    <div class="row">
      <label>{$_('insurance.page.name')} *</label>
      <Input bind:value={name} placeholder={$_('insurance.modal.namePlaceholder')} />
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('costs.page.category')} *</label>
        <select class="native-input" bind:value={categoryId}>
          {#each settingsStore.insuranceCategories as cat}
            <option value={cat.id}>{cat.emoji} {cat.name}</option>
          {/each}
        </select>
      </div>
      <div class="row">
        <label>{$_('insurance.modal.policyNumber')}</label>
        <Input bind:value={policyNumber} placeholder={$_('insurance.modal.policyNumberPlaceholder')} />
      </div>
    </div>
    <div class="row">
      <label>{$_('costs.entryModal.supplier')}</label>
      <select class="native-input" bind:value={contactId}>
        <option value="">{$_('works.modal.noneOption')}</option>
        {#each contactsStore.contacts as c}
          <option value={c.id}>{c.name}</option>
        {/each}
      </select>
    </div>
    <div class="row-pair">
      <div class="row">
        <label>{$_('insurance.page.startDate')}</label>
        <DatePicker bind:value={startDate} />
      </div>
      <div class="row">
        <label>{$_('insurance.page.endDate')}</label>
        <DatePicker bind:value={endDate} />
      </div>
    </div>
  {:else if activeTab === "cost"}
    <div class="row-pair">
      <div class="row">
        <label>{$_('insurance.modal.premiumAmount')}</label>
        <input class="native-input" type="number" min="0" step="0.01" bind:value={premiumAmount} placeholder="0.00" />
      </div>
      <div class="row">
        <label>{$_('insurance.modal.premiumFrequency')}</label>
        <select class="native-input" bind:value={premiumFrequency}>
          <option value="monthly">{$_('insurance.frequency.monthly')}</option>
          <option value="quarterly">{$_('insurance.frequency.quarterly')}</option>
          <option value="annual">{$_('insurance.frequency.annual')}</option>
          <option value="other">{$_('insurance.frequency.other')}</option>
        </select>
      </div>
    </div>
    <label class="checkbox-row">
      <input type="checkbox" bind:checked={includeInCosts} />
      {$_('insurance.modal.includeInCosts')}
    </label>
    <p class="hint">{$_('insurance.modal.includeInCostsHint')}</p>
  {:else if activeTab === "coverage"}
    <div class="row">
      <label>{$_('insurance.modal.coverageSummary')}</label>
      <textarea class="native-input desc-area" bind:value={coverageSummary} placeholder={$_('insurance.modal.coverageSummaryPlaceholder')} rows="3"></textarea>
    </div>
    <div class="row">
      <label>{$_('insurance.modal.conditionsUrl')}</label>
      <Input bind:value={conditionsUrl} placeholder="https://…" />
    </div>
    {#if isCreate}
      <p class="hint">{$_('insurance.modal.attachAfterCreate')}</p>
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
  {:else}
    <div class="row">
      <label>{$_('insurance.modal.alternatives')}</label>
      <textarea class="native-input desc-area" bind:value={alternatives} placeholder={$_('insurance.modal.alternativesPlaceholder')} rows="4"></textarea>
    </div>
    <MarkdownEditor
      bind:value={notes}
      bind:editing={editingNotes}
      placeholder={$_('works.modal.notesPlaceholder')}
      minHeight="140px"
    />
    {#if editingNotes && !isCreate}
      <Button variant="secondary" onclick={() => { editingNotes = false; }}>{$_('works.modal.doneEditing')}</Button>
    {/if}
  {/if}

  {#if error}<div class="modal-error">{error}</div>{/if}

  {#snippet footer()}
    {#if !isCreate}
      {#if confirmDelete}
        <span class="confirm-text">{$_('settings.categories.deleteConfirm')}</span>
        <Button variant="danger" disabled={deleting} onclick={handleDelete}>✓ {$_('works.modal.confirm')}</Button>
        <Button variant="ghost" onclick={() => { confirmDelete = false; }}>✕</Button>
      {:else}
        <Button variant="danger" onclick={() => { confirmDelete = true; }}>🗑 {$_('common.delete')}</Button>
      {/if}
    {/if}
    <span class="spacer"></span>
    <Button variant="primary" disabled={saving} onclick={handleSave}>
      {saving ? $_('settings.security.saving') : isCreate ? $_('settings.security.create') : $_('common.save')}
    </Button>
  {/snippet}
</Modal>

{#if lightboxOpen && mediaItems.length > 0}
  <Lightbox items={mediaItems} initialIndex={lightboxIndex} onclose={() => { lightboxOpen = false; }} />
{/if}

<style>
  .tabs { display: flex; border-bottom: 1px solid var(--border); margin-bottom: var(--space-3); }
  .tab {
    padding: 8px 16px; background: none; border: none; border-bottom: 2px solid transparent;
    color: var(--text-muted); font-size: 12px; cursor: pointer; font-family: var(--font-sans);
  }
  .tab:hover { color: var(--text); }
  .tab.active { border-bottom-color: var(--accent); color: var(--text); }

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
  .desc-area { resize: vertical; min-height: 48px; }

  .checkbox-row { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text); margin-bottom: 4px; cursor: pointer; }
  .hint { font-size: 11px; color: var(--text-faint); margin: 0 0 var(--space-3); }

  .modal-error { padding: 8px 0 0; font-size: 11px; color: var(--danger); }
  .spacer { flex: 1; }
  .confirm-text { font-size: 11px; color: var(--danger); }
</style>
```

- [ ] **Step 4: Create `InsurancePage.svelte`**

```svelte
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { createInsuranceStore, InsurancePolicy } from "../insuranceStore.svelte";
  import type { createSettingsStore } from "../settingsStore.svelte";
  import type { createContactsStore } from "../contactsStore.svelte";
  import InsuranceModal from "./InsuranceModal.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";
  import SortableTable from "./ui/SortableTable.svelte";
  import type { Column } from "./ui/SortableTable.types";
  import Card from "./ui/Card.svelte";
  import DonutChart from "./DonutChart.svelte";
  import { assignCategoryColors } from "../colorAssignment";

  type InsuranceStore = ReturnType<typeof createInsuranceStore>;
  type SettingsStore = ReturnType<typeof createSettingsStore>;
  type ContactsStore = ReturnType<typeof createContactsStore>;

  interface Props {
    store: InsuranceStore;
    settingsStore: SettingsStore;
    contactsStore: ContactsStore;
  }

  let { store, settingsStore, contactsStore }: Props = $props();

  let modalPolicy = $state<InsurancePolicy | "create" | null>(null);
  let searchQuery = $state("");
  let categoryFilter = $state("");

  const categoryMap = $derived(
    new Map(settingsStore.insuranceCategories.map(c => [c.id, c]))
  );
  const contactMap = $derived(
    new Map(contactsStore.contacts.map(c => [c.id, c]))
  );

  const FREQUENCY_MULTIPLIER: Record<string, number> = { monthly: 12, quarterly: 4, annual: 1, other: 1 };
  function annualized(p: InsurancePolicy): number {
    return p.premiumAmount != null ? p.premiumAmount * (FREQUENCY_MULTIPLIER[p.premiumFrequency] ?? 1) : 0;
  }

  const filteredPolicies = $derived(store.policies.filter(p => {
    if (categoryFilter && p.categoryId !== categoryFilter) return false;
    if (searchQuery && !p.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  }));

  const totalAnnualCost = $derived(store.policies.reduce((sum, p) => sum + annualized(p), 0));

  const categoryBreakdown = $derived((() => {
    const totals = new Map<string, number>();
    for (const p of store.policies) {
      const key = p.categoryId;
      totals.set(key, (totals.get(key) ?? 0) + annualized(p));
    }
    const colors = assignCategoryColors([...totals.keys()]);
    return [...totals.entries()].map(([id, amount]) => {
      const cat = categoryMap.get(id);
      return {
        id, label: cat?.name ?? id, emoji: cat?.emoji ?? "🛡️",
        color: colors.get(id) ?? "var(--chart-series-1)",
        valueLabel: `${fmt(amount)} €`,
        pct: totalAnnualCost > 0 ? (amount / totalAnnualCost) * 100 : 0,
      };
    });
  })());

  function daysUntil(dateStr: string | null): number | null {
    if (!dateStr) return null;
    return Math.round((new Date(dateStr).getTime() - Date.now()) / 86400000);
  }

  function renewalChip(p: InsurancePolicy): { label: string; color: string } | null {
    const days = daysUntil(p.endDate);
    if (days === null) return null;
    if (days < 0) return { label: `✕ ${$_('insurance.page.expired')}`, color: "#f44336" };
    if (days <= 30) return { label: `⚠ ${days}d`, color: "#ff9800" };
    return { label: "✓", color: "#4caf50" };
  }

  function fmt(n: number): string {
    return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
</script>

<div class="page">

  {#if store.policies.length === 0}
    <div class="empty-charts">
      <span class="empty-icon">🛡️</span>
      <p>{$_('insurance.page.emptyCharts')}</p>
    </div>
  {:else}
    <div class="chart-card-wrap">
      <Card>
        <div class="chart-inner">
          <div class="pie-area">
            <div class="chart-label">{$_('insurance.page.byCategory')}</div>
            <DonutChart
              segments={categoryBreakdown}
              centerLabel={$_('insurance.page.annualCost')}
              centerValue={`${fmt(totalAnnualCost)} €`}
              showLabels={true}
            />
          </div>
          <div class="chart-divider"></div>
          <div class="stats-area">
            <div class="chart-label">{$_('chores.page.atAGlance')}</div>
            <div class="stat-chips-col">
              <div class="stat-chip">
                <div class="stat-title">{$_('insurance.page.policies')}</div>
                <div class="stat-value">{store.policies.length}</div>
              </div>
              <div class="stat-chip">
                <div class="stat-title">{$_('insurance.page.annualCost')}</div>
                <div class="stat-value">{fmt(totalAnnualCost)} €</div>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  {/if}

  <div class="table-card-wrap">
    <Card style="display:flex; flex-direction:column; padding:0; overflow:hidden; flex:1; min-height:0;">
    <div class="toolbar">
      <Input placeholder={$_('insurance.page.search')} bind:value={searchQuery} />
      <select class="native-input filter-sel" bind:value={categoryFilter}>
        <option value="">{$_('costs.page.allCategories')}</option>
        {#each settingsStore.insuranceCategories as cat}
          <option value={cat.id}>{cat.emoji} {cat.name}</option>
        {/each}
      </select>
      <Button onclick={() => { modalPolicy = "create"; }}>＋ {$_('insurance.page.addPolicy')}</Button>
    </div>

    <div class="table-wrapper">
      {#snippet emojiCell(p: InsurancePolicy)}
        {categoryMap.get(p.categoryId)?.emoji ?? "🛡️"}
      {/snippet}
      {#snippet nameCell(p: InsurancePolicy)}
        {p.name}
      {/snippet}
      {#snippet categoryCell(p: InsurancePolicy)}
        {categoryMap.get(p.categoryId)?.name ?? "—"}
      {/snippet}
      {#snippet providerCell(p: InsurancePolicy)}
        {contactMap.get(p.contactId ?? "")?.name ?? "—"}
      {/snippet}
      {#snippet premiumCell(p: InsurancePolicy)}
        {p.premiumAmount != null ? `${fmt(p.premiumAmount)} € / ${$_('insurance.frequency.' + p.premiumFrequency)}` : "—"}
      {/snippet}
      {#snippet endDateCell(p: InsurancePolicy)}
        {p.endDate ?? "—"}
        {#if renewalChip(p)}
          {@const chip = renewalChip(p)}
          <span class="chip" style="color:{chip!.color}">{chip!.label}</span>
        {/if}
      {/snippet}

      <SortableTable
        columns={[
          { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
          { key: "name", label: $_('insurance.page.name'), sortValue: (p) => p.name, cellClass: "name-cell", cell: nameCell },
          { key: "category", label: $_('costs.page.category'), sortValue: (p) => categoryMap.get(p.categoryId)?.name ?? null, cell: categoryCell },
          { key: "provider", label: $_('costs.entryModal.supplier'), sortValue: (p) => contactMap.get(p.contactId ?? "")?.name ?? null, cell: providerCell },
          { key: "premium", label: $_('insurance.page.premium'), sortValue: (p) => annualized(p), cell: premiumCell },
          { key: "endDate", label: $_('insurance.page.endDate'), sortValue: (p) => (p.endDate ? new Date(p.endDate) : null), cell: endDateCell },
        ] as Column<InsurancePolicy>[]}
        rows={filteredPolicies}
        rowKey={(p) => p.id}
        rowClick={(p) => { modalPolicy = p; }}
        emptyMessage={store.policies.length === 0 ? $_('insurance.page.emptyNoPolicies') : $_('insurance.page.emptyNoMatch')}
      />
    </div>

    <div class="footer">{$_('insurance.page.footer', { values: { n: filteredPolicies.length } })}</div>
    </Card>
  </div>
</div>

{#if modalPolicy !== null}
  <InsuranceModal
    policy={modalPolicy === "create" ? null : modalPolicy}
    {store}
    {settingsStore}
    {contactsStore}
    onclose={() => { modalPolicy = null; }}
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
  .chart-inner { display: flex; gap: 24px; align-items: center; }
  .chart-label {
    font-size: 10px; color: var(--text-faint); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }
  .pie-area { flex-shrink: 0; }
  .chart-divider { width: 1px; background: var(--border); align-self: stretch; flex-shrink: 0; margin: 0 8px; }

  .stats-area { flex: 1; min-width: 0; }
  .stat-chips-col { display: flex; flex-direction: column; gap: 8px; max-width: 220px; }
  .stat-chip {
    background: var(--surface-alt); border: 1px solid var(--border);
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
  .chip { font-size: 10px; font-weight: 500; margin-left: 6px; }

  .footer { padding: var(--space-2) var(--space-4); border-top: 1px solid var(--border); font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
</style>
```

- [ ] **Step 5: Wire routing in `App.svelte`**

Add the store instantiation near the other stores:

```typescript
  import InsurancePage from "./lib/components/InsurancePage.svelte";
  import { createInsuranceStore } from "./lib/insuranceStore.svelte";
```

```typescript
  const insuranceStore = createInsuranceStore(getHomeId);
```

Add it to whatever reload-on-home-switch list `worksStore.reload()` appears in (around `App.svelte:110`):

```typescript
    insuranceStore.reload();
```

Replace the placeholder route:

```svelte
      {:else if currentRoute === "#/insurance"}
        <InsurancePage store={insuranceStore} {settingsStore} {contactsStore} />
      {/if}
```

- [ ] **Step 6: Add locale strings**

Add to `packages/editor/src/lib/locales/en.json`, as a new top-level `"insurance"` section (placed alphabetically near `"inventory"`/`"kb"`, or simply appended before the closing brace — check the file's existing top-level key ordering first):

```json
  "insurance": {
    "page": {
      "emptyCharts": "No insurance policies yet — click ＋ Add policy to get started.",
      "byCategory": "By category",
      "annualCost": "Annual cost",
      "policies": "Policies",
      "search": "Search policies…",
      "addPolicy": "Add policy",
      "name": "Name",
      "premium": "Premium",
      "startDate": "Start date",
      "endDate": "Renewal date",
      "expired": "Expired",
      "emptyNoPolicies": "No insurance policies yet — click ＋ Add policy to get started.",
      "emptyNoMatch": "No policies match your filters.",
      "footer": "{n} policies"
    },
    "frequency": {
      "monthly": "month",
      "quarterly": "quarter",
      "annual": "year",
      "other": "other"
    },
    "modal": {
      "newPolicy": "New policy",
      "editPolicy": "Edit policy",
      "namePlaceholder": "e.g. Home Insurance — AXA",
      "nameRequired": "Name is required",
      "categoryRequired": "Category is required",
      "costTab": "Cost",
      "coverageTab": "Coverage",
      "alternativesTab": "Alternatives",
      "policyNumber": "Policy number",
      "policyNumberPlaceholder": "POL-123456",
      "premiumAmount": "Premium (€)",
      "premiumFrequency": "Billed",
      "includeInCosts": "Include in Costs module",
      "includeInCostsHint": "When on, this policy's annualized premium is kept in sync as an entry in the Costs module. Turn this off for policies that shouldn't count toward household costs (e.g. travel, life).",
      "coverageSummary": "What it covers",
      "coverageSummaryPlaceholder": "Summary of coverage…",
      "conditionsUrl": "Conditions / policy link",
      "attachAfterCreate": "Save the policy first to attach documents.",
      "alternatives": "Alternatives / competitors",
      "alternativesPlaceholder": "Notes on competing quotes…",
      "saveFailed": "Save failed",
      "deleteFailed": "Delete failed",
      "uploadFailed": "Upload failed"
    }
  },
```

Add the matching French section to `fr.json` (translate the same keys — e.g. `"emptyCharts": "Aucune police d'assurance pour l'instant — cliquez sur ＋ Ajouter une police pour commencer."`, following this project's existing French tone in the `"works"` section of `fr.json`).

Also add `"insurance": "Insurance categories"`-equivalent key for the future Settings tab label — actually this belongs to Task 11; skip it here.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/InsurancePage.test.ts test/InsuranceModal.test.ts`
Expected: All PASS.

- [ ] **Step 8: Run the full frontend suite**

Run: `cd packages/editor && npx vitest run`
Expected: All PASS.

- [ ] **Step 9: Commit**

```bash
git add packages/editor/src/lib/components/InsurancePage.svelte packages/editor/src/lib/components/InsuranceModal.svelte packages/editor/src/App.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/InsurancePage.test.ts packages/editor/test/InsuranceModal.test.ts
git commit -m "feat(insurance): add InsurancePage, InsuranceModal, routing, locale"
```

---

## Task 11: Frontend — Settings "Insurance Categories" tab

**Files:**
- Modify: `packages/editor/src/lib/components/settings/SettingsCategories.svelte`
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`
- Modify: `packages/editor/test/SettingsCategories.test.ts` (confirm filename with `ls packages/editor/test/SettingsCategories*`)

**Interfaces:**
- Consumes: `store.insuranceCategories`/`store.updateInsuranceCategories` (Task 9), `InsuranceCategory` type (Task 9).

- [ ] **Step 1: Write the failing test**

Add to the existing `SettingsCategories.test.ts` (match its existing store-mock/render pattern):

```typescript
describe("SettingsCategories — insurance tab", () => {
  it("renders insurance categories and adds a new one", async () => {
    const store = makeSettingsStore({ insuranceCategories: [{ id: "icat-home", name: "Home", emoji: "🏠" }] });
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(SettingsCategories, { target, props: { store } });
    flushSync();

    const insuranceTab = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Insurance categories"));
    insuranceTab?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(target.textContent).toContain("Home");

    unmount(comp);
  });
});
```

(Match `makeSettingsStore`'s exact shape and any `updateInsuranceCategories: vi.fn()` mock to whatever the existing test file's helper already provides for `updateWorkCategories`, etc. — extend that helper rather than duplicating it.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd packages/editor && npx vitest run test/SettingsCategories.test.ts -t insurance`
Expected: FAIL — no "Insurance categories" tab exists.

- [ ] **Step 3: Add the Insurance Categories tab to `SettingsCategories.svelte`**

Add the type import:

```typescript
  import type { createSettingsStore, CostCategory, ConsumableCategory, InventoryCategory, WorkCategory, ContactType, InsuranceCategory } from "../../settingsStore.svelte";
```

Extend the tab union and tab bar:

```typescript
  type CategoryTab = "cost" | "inventory" | "work" | "contactTypes" | "consumables" | "insurance";
```

```svelte
<Tabs
  tabs={[
    { id: "cost", label: $_('settings.categories.tabs.cost') },
    { id: "inventory", label: $_('settings.categories.tabs.inventory') },
    { id: "work", label: $_('settings.categories.tabs.work') },
    { id: "contactTypes", label: $_('settings.categories.tabs.contactTypes') },
    { id: "consumables", label: $_('settings.categories.tabs.consumables') },
    { id: "insurance", label: $_('settings.categories.tabs.insurance') },
  ]}
  active={activeTab}
  onchange={(id) => { activeTab = id as CategoryTab; }}
/>
```

Add the state and handlers (following the `WorkCategory` block exactly, since `InsuranceCategory` has the same `{id, name, emoji}` shape):

```typescript
  // --- Insurance categories ---
  let editingInsuranceId = $state<string | null>(null);
  let insuranceDraft = $state<InsuranceCategory>({ id: "", name: "", emoji: "" });
  let showNewInsuranceForm = $state(false);
  let newInsuranceDraft = $state({ name: "", emoji: "" });
  let confirmDeleteInsuranceId = $state<string | null>(null);
  let insuranceError = $state<string | null>(null);

  function startEditInsurance(cat: InsuranceCategory): void {
    editingInsuranceId = cat.id;
    insuranceDraft = { ...cat };
    insuranceError = null;
  }

  function cancelEditInsurance(): void { editingInsuranceId = null; insuranceError = null; }

  async function saveEditInsurance(): Promise<void> {
    if (!insuranceDraft.name.trim()) { insuranceError = $_('settings.general.nameRequired'); return; }
    const updated = store.insuranceCategories.map(c =>
      c.id === editingInsuranceId ? { ...insuranceDraft, name: insuranceDraft.name.trim() } : c
    );
    await store.updateInsuranceCategories(updated);
    editingInsuranceId = null; insuranceError = null;
  }

  async function deleteInsuranceCategory(id: string): Promise<void> {
    await store.updateInsuranceCategories(store.insuranceCategories.filter(c => c.id !== id));
    confirmDeleteInsuranceId = null;
  }

  async function addInsuranceCategory(): Promise<void> {
    if (!newInsuranceDraft.name.trim()) { insuranceError = $_('settings.general.nameRequired'); return; }
    const newCat: InsuranceCategory = {
      id: crypto.randomUUID(),
      name: newInsuranceDraft.name.trim(),
      emoji: newInsuranceDraft.emoji || "🛡️",
    };
    await store.updateInsuranceCategories([...store.insuranceCategories, newCat]);
    newInsuranceDraft = { name: "", emoji: "" };
    showNewInsuranceForm = false; insuranceError = null;
  }
```

Add the tab panel markup (mirroring the `{#if activeTab === "work"}` block exactly, right after it):

```svelte
{#if activeTab === "insurance"}
  <Card>
    <div class="section-header">
      <h2>{$_('settings.categories.tabs.insurance')}</h2>
      <Button onclick={() => { showNewInsuranceForm = true; insuranceError = null; }}>＋ {$_('common.add')}</Button>
    </div>
    <div class="table-wrapper">
      {#snippet insuranceEmojiCell(cat: InsuranceCategory)}
        {#if editingInsuranceId === cat.id}
          <EmojiPicker bind:value={insuranceDraft.emoji} />
        {:else}
          {cat.emoji}
        {/if}
      {/snippet}
      {#snippet insuranceNameCell(cat: InsuranceCategory)}
        {#if editingInsuranceId === cat.id}
          <Input bind:value={insuranceDraft.name} placeholder={$_('settings.categories.name')} />
        {:else}
          {cat.name}
        {/if}
      {/snippet}
      {#snippet insuranceActionsCell(cat: InsuranceCategory)}
        {#if editingInsuranceId === cat.id}
          <button class="icon-action ok" onclick={saveEditInsurance} title={$_('common.save')}>✓</button>
          <button class="icon-action" onclick={cancelEditInsurance} title={$_('common.cancel')}>✕</button>
        {:else if confirmDeleteInsuranceId === cat.id}
          <span class="confirm-text">{$_('settings.categories.deleteConfirm')}</span>
          <button class="icon-action danger" onclick={() => deleteInsuranceCategory(cat.id)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteInsuranceId = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => startEditInsurance(cat)} title={$_('common.edit')}>✏</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteInsuranceId = cat.id; }} title={$_('common.delete')}>🗑</button>
        {/if}
      {/snippet}
      {#snippet insuranceNewRow()}
        <td><EmojiPicker bind:value={newInsuranceDraft.emoji} /></td>
        <td class="name-cell-input"><Input bind:value={newInsuranceDraft.name} placeholder={$_('settings.categories.nameRequiredPlaceholder')} /></td>
        <td class="actions">
          <button class="icon-action ok" onclick={addInsuranceCategory} title={$_('common.add')}>✓</button>
          <button class="icon-action" onclick={() => { showNewInsuranceForm = false; insuranceError = null; }} title={$_('common.cancel')}>✕</button>
        </td>
      {/snippet}
      <SortableTable
        columns={[
          { key: "emoji", label: $_('settings.categories.emoji'), sortable: false, cellClass: "emoji-cell", cell: insuranceEmojiCell },
          { key: "name", label: $_('settings.categories.name'), sortValue: (c) => c.name, cellClass: (c) => editingInsuranceId === c.id ? "name-cell-input" : "", cell: insuranceNameCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: insuranceActionsCell },
        ] as Column<InsuranceCategory>[]}
        rows={store.insuranceCategories}
        rowKey={(c) => c.id}
        rowClass={(c) => editingInsuranceId === c.id ? "editing-row" : ""}
        extraRow={showNewInsuranceForm ? insuranceNewRow : undefined}
      />
    </div>
    {#if insuranceError}<div class="error">{insuranceError}</div>{/if}
  </Card>
{/if}
```

- [ ] **Step 4: Add the tab label locale key**

Add `"insurance": "Insurance categories"` to `settings.categories.tabs` in `en.json`:

```json
      "tabs": {
        "cost": "Cost categories",
        "inventory": "Inventory categories",
        "work": "Work categories",
        "contactTypes": "Contact Types",
        "consumables": "Consumables",
        "insurance": "Insurance categories"
      },
```

Add the French equivalent (e.g. `"insurance": "Catégories d'assurance"`) to the matching `settings.categories.tabs` block in `fr.json`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/SettingsCategories.test.ts`
Expected: All PASS.

- [ ] **Step 6: Run the full frontend suite**

Run: `cd packages/editor && npx vitest run`
Expected: All PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsCategories.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/SettingsCategories.test.ts
git commit -m "feat(insurance): add Insurance Categories tab to Settings"
```

---

## Task 12: Manual verification

Use the `webapp-testing` skill to drive a real browser against a running dev instance (see the project's dev-server recipe — check `CLAUDE.md`/recent memory for the known orphaned-uvicorn-worker and broken-editable-install gotchas before starting servers). Walk through:

1. Open Settings → Insurance categories: confirm the 6 defaults (Home, Auto, Health, Life, Travel, Liability) render with correct emoji, add a custom one, rename one, delete one, confirm changes persist on reload.
2. Open the Insurance page (`#/insurance`): confirm the placeholder "Soon" badge is gone from the nav and the real page loads.
3. Add a Home-category policy with a premium and "Include in Costs" checked (should default to checked when Home is selected). Save. Confirm it appears in the list with a renewal badge if `endDate` is within 30 days.
4. Open the Costs page: confirm a matching entry now appears under the "Insurance" category, and that clicking into it shows it as read-only/blocked from editing (per Task 4's route guard — check what the frontend actually does with the 400 response; if the Costs entry modal doesn't yet special-case this, at minimum confirm the guard rejects a raw API edit attempt).
5. Add a Travel-category policy with "Include in Costs" left unchecked. Confirm nothing new appears in Costs.
6. Edit the Home policy: toggle "Include in Costs" off. Confirm its Costs entry disappears. Toggle it back on. Confirm it reappears.
7. Delete the Home policy. Confirm its Costs entry is also gone.
8. Attach a PDF and an image to a policy via the Coverage tab; confirm both show thumbnails and open in the lightbox.
9. Set a conditions URL and a coverage summary; confirm they display/save correctly.
10. Fill in the Alternatives free-text field; confirm it saves.
11. Spin up a fresh demo home; confirm it seeds ~5 insurance policies spanning categories, with at least one Home-category policy showing `includeInCosts: true` in the UI.
12. Switch the UI language to French (if there's a language switcher) and spot-check the Insurance page/modal/settings tab render translated strings without missing-key fallbacks.

Report back concrete pass/fail per item — do not claim success without having actually clicked through the flow in a browser per this project's verification standard.

---

## Task 13: Final full-suite verification

- [ ] **Step 1: Run the full backend suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: All PASS.

- [ ] **Step 2: Run the full frontend suite**

Run: `cd packages/editor && npx vitest run`
Expected: All PASS.

- [ ] **Step 3: Run typecheck/lint if configured**

Run: `cd packages/editor && npx svelte-check` (or whatever this project's existing typecheck command is — check `package.json` scripts first) and any backend lint command (`ruff check` if configured).
Expected: No new errors introduced by this plan's changes.

- [ ] **Step 4: Review the diff for stray debug code, TODOs, or leftover placeholder text**

Run: `git diff main --stat` and skim the full diff for anything that shouldn't ship.

- [ ] **Step 5: Update memory**

Per this project's established practice (see `feedback_execution_preference` and prior module-completion memories), record a `project_insurance_module_status` memory noting merge status, test counts, and anything non-obvious found during implementation (e.g. the pre-existing works/inventory/costs attachment-URL home-scoping bug discovered in Task 10 that was *not* fixed here since it's out of scope — flag it for a future pass).

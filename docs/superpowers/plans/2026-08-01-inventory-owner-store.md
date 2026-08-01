# Inventory Owner & Store Fields Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add creatable-dropdown Owner and Store fields to Inventory items, and convert Inventory's free-text `category` field to `categoryId` so it matches the id-referencing pattern already used by Works/Costs/Consumables/Insurance.

**Architecture:** New per-home `owners`/`stores` entity lists (same shape/persistence pattern as the existing category tables), two new nullable plain-string columns (`owner_id`, `store_id`, no `ForeignKey`) plus a converted `category_id` column on `inventory_items`, a schema-version-7 migration that backfills `category_id` from the old free-text values, and a new shared `CreatableSelect.svelte` combobox (type to filter existing entries, or create a new one inline) used for all three fields in `InventoryModal`, with matching filters/columns on `InventoryPage` and management tabs in `SettingsCategories`.

**Tech Stack:** FastAPI + SQLAlchemy Core (SQLite) backend, pytest; Svelte 5 (runes) + vitest frontend; svelte-i18n (EN/FR).

**Spec:** `docs/superpowers/specs/2026-08-01-inventory-owner-store-design.md`

## Global Constraints

- `owner_id`/`store_id`/`category_id` are plain `String` columns with no `ForeignKey` — same convention as every other category/contact reference in this codebase (`schema.py:242-244`).
- Owner and Store are single-value per item — no multi-owner/joint-ownership arrays.
- No default seed data for `owners`/`stores` (empty list on a fresh home).
- Never `DROP COLUMN` in a migration — this codebase leaves superseded columns undeclared in the `Table()` object rather than dropping them at the DDL level.
- Every new user-facing string needs both an `en.json` and an `fr.json` entry — never land one without the other.
- `settingsStore.svelte.ts` and `inventoryStore.svelte.ts` use bare `fetch(...)` calls (not the `apiUrl()` helper used by some component files) — match that existing convention when adding methods to these two files.
- Svelte components in this codebase use Svelte 5 runes (`$state`, `$derived`, `$props`, `$bindable`) — no Svelte 4 syntax (`export let`, stores via `$:`).
- Frontend component tests use raw Svelte 5 `mount`/`unmount`/`flushSync` from `"svelte"` (not `@testing-library/svelte`).

---

## Task 1: Backend — Owner & Store settings lists

**Files:**
- Modify: `packages/backend/src/myhome/models_settings.py`
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/persistence_settings.py`
- Modify: `packages/backend/src/myhome/routes/settings.py`
- Test: `packages/backend/tests/test_settings.py`

**Interfaces:**
- Produces: `Owner{id: str, name: str}`, `Store{id: str, name: str}` (in `models_settings.py`); `SettingsDocument.owners: list[Owner]`, `SettingsDocument.stores: list[Store]`; routes `PUT /api/homes/{home_id}/settings/owners` and `PUT /api/homes/{home_id}/settings/stores`, both `body: list[Owner]`/`list[Store]`, `204` on success.

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_settings.py` (near `test_put_inventory_categories`):

```python
def test_put_owners(client, home_id):
    new_owners = [
        {"id": "o1", "name": "Alice"},
        {"id": "o2", "name": "Bob"},
    ]
    resp = client.put(f"/api/homes/{home_id}/settings/owners", json=new_owners)
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/settings").json()
    assert len(data["owners"]) == 2
    assert data["owners"][1]["name"] == "Bob"


def test_put_stores(client, home_id):
    new_stores = [
        {"id": "s1", "name": "Ikea"},
        {"id": "s2", "name": "Amazon"},
    ]
    resp = client.put(f"/api/homes/{home_id}/settings/stores", json=new_stores)
    assert resp.status_code == 204
    data = client.get(f"/api/homes/{home_id}/settings").json()
    assert len(data["stores"]) == 2
    assert data["stores"][1]["name"] == "Amazon"


def test_get_settings_owners_stores_default_empty(client, home_id):
    data = client.get(f"/api/homes/{home_id}/settings").json()
    assert data["owners"] == []
    assert data["stores"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_settings.py -k "owners or stores" -v`
Expected: FAIL — `PUT .../settings/owners` and `.../settings/stores` return 404 (routes don't exist), and `data["owners"]`/`data["stores"]` raise `KeyError`.

- [ ] **Step 3: Implement Owner/Store across models, schema, persistence, and routes**

In `packages/backend/src/myhome/models_settings.py`, add after the `InsuranceCategory` class (before `class NotificationSettings`):

```python
class Owner(BaseModel):
    id: str
    name: str


class Store(BaseModel):
    id: str
    name: str
```

Add two fields to `SettingsDocument` (after `insuranceCategories`, before `notifications`):

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
    owners: list[Owner] = []
    stores: list[Store] = []
    notifications: NotificationSettings = NotificationSettings()
```

In `packages/backend/src/myhome/schema.py`, add two tables right after the `inventory_categories` table definition (same shape, no `emoji` column, matching `InventoryCategory`):

```python
owners = Table(
    "owners", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
)

stores = Table(
    "stores", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
)
```

In `packages/backend/src/myhome/persistence_settings.py`:

1. Extend the imports:

```python
from .models_settings import (
    ConsumableCategory,
    CostCategory,
    CostCategoryPlacement,
    CostCategoryPosition,
    InventoryCategory,
    InsuranceCategory,
    NotificationSettings,
    Owner,
    SettingsDocument,
    Store,
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
    owners as owners_table,
    settings as settings_table,
    contact_types as contact_types_table,
    stores as stores_table,
    work_categories as work_categories_table,
    insurance_categories as insurance_categories_table,
)
```

2. In `load_settings`, add two more row queries alongside the existing ones (inside the `with engine.connect() as conn:` block, after `insurance_cat_rows`):

```python
        owner_rows = conn.execute(
            select(owners_table).where(owners_table.c.home_id == home_id)
            .order_by(owners_table.c.order_index)
        ).mappings().all()
        store_rows = conn.execute(
            select(stores_table).where(stores_table.c.home_id == home_id)
            .order_by(stores_table.c.order_index)
        ).mappings().all()
```

Then add to the `SettingsDocument(...)` construction that follows (after `insuranceCategories=[...]`):

```python
        owners=[Owner(id=r["id"], name=r["name"]) for r in owner_rows],
        stores=[Store(id=r["id"], name=r["name"]) for r in store_rows],
```

(The `if row is None:` early-return branch above it does **not** need an `owners=`/`stores=` addition — `SettingsDocument`'s field defaults already give it `[]`.)

3. In `save_settings`, add two more delete+insert blocks at the end, after the `insurance_categories_table` block:

```python
        conn.execute(owners_table.delete().where(owners_table.c.home_id == home_id))
        if doc.owners:
            conn.execute(owners_table.insert(), [
                {"id": o.id, "home_id": home_id, "order_index": i, "name": o.name}
                for i, o in enumerate(doc.owners)
            ])

        conn.execute(stores_table.delete().where(stores_table.c.home_id == home_id))
        if doc.stores:
            conn.execute(stores_table.insert(), [
                {"id": s.id, "home_id": home_id, "order_index": i, "name": s.name}
                for i, s in enumerate(doc.stores)
            ])
```

In `packages/backend/src/myhome/routes/settings.py`:

1. Extend the import: add `Owner` and `Store` to the `from ..models_settings import (...)` list.
2. Add two routes, next to `put_insurance_categories`:

```python
@router.put("/api/homes/{home_id}/settings/owners", status_code=204)
def put_owners(home_id: str, body: list[Owner]) -> None:
    doc = load_settings(home_id)
    doc.owners = body
    save_settings(home_id, doc)


@router.put("/api/homes/{home_id}/settings/stores", status_code=204)
def put_stores(home_id: str, body: list[Store]) -> None:
    doc = load_settings(home_id)
    doc.stores = body
    save_settings(home_id, doc)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_settings.py -v`
Expected: PASS (all tests in the file, including the 3 new ones).

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/models_settings.py packages/backend/src/myhome/schema.py packages/backend/src/myhome/persistence_settings.py packages/backend/src/myhome/routes/settings.py packages/backend/tests/test_settings.py
git commit -m "feat(backend): add Owner and Store per-home settings lists"
```

---

## Task 2: Backend — convert Inventory's `category` to `categoryId`, add `ownerId`/`storeId`

**Files:**
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/migrations.py`
- Modify: `packages/backend/src/myhome/models_inventory.py`
- Modify: `packages/backend/src/myhome/persistence_inventory.py`
- Modify: `packages/backend/src/myhome/demo_data.py`
- Test: `packages/backend/tests/test_migrations.py`
- Test: `packages/backend/tests/test_inventory.py`
- Test: `packages/backend/tests/test_inventory_persistence.py`
- Test: `packages/backend/tests/test_demo_data.py`

**Interfaces:**
- Produces: `InventoryItem.categoryId: str | None`, `InventoryItem.ownerId: str | None`, `InventoryItem.storeId: str | None` (replacing `InventoryItem.category: str`); same rename on `InventoryItemCreate`/`InventoryItemUpdate`. Migration version 7.

This task touches every backend call site that constructs an `InventoryItem` with `category=...` or reads `.category`/`["category"]` **except** `mcp_tools_inventory.py` (handled in Task 3 — no existing test there asserts on the category value, so it's safe to defer). Everything in this task's own file list must go together: the schema/migration change alone would break `persistence_inventory.py` (which reads a column the new table no longer declares), and the model rename alone would break every test/demo-data call site that still says `category=`.

- [ ] **Step 1: Write the failing migration test**

Add to `packages/backend/tests/test_migrations.py` (after the existing insurance-support test):

```python
def test_run_migrations_backfills_inventory_category_id(tmp_path):
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE homes (id VARCHAR PRIMARY KEY, name VARCHAR, type VARCHAR, created_at VARCHAR)"
        ))
        conn.execute(text("INSERT INTO homes (id, name, type, created_at) VALUES ('h1', 'Home 1', 'existing', '2026-01-01')"))
        conn.execute(text(
            "CREATE TABLE inventory_categories (id VARCHAR NOT NULL, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, PRIMARY KEY (id, home_id))"
        ))
        conn.execute(text(
            "INSERT INTO inventory_categories (id, home_id, order_index, name) VALUES ('inv-electronics', 'h1', 0, 'Electronics')"
        ))
        conn.execute(text(
            "CREATE TABLE inventory_items (id VARCHAR PRIMARY KEY, home_id VARCHAR NOT NULL, "
            "order_index INTEGER NOT NULL, name VARCHAR NOT NULL, emoji VARCHAR NOT NULL, "
            "category VARCHAR NOT NULL, brand VARCHAR, model VARCHAR, serial_number VARCHAR, "
            "purchase_date VARCHAR, purchase_price FLOAT, warranty_expiry_date VARCHAR, "
            "notes VARCHAR NOT NULL, attachments TEXT NOT NULL, placement_floor_id VARCHAR, "
            "placement_room_id VARCHAR, placement_x FLOAT, placement_y FLOAT)"
        ))
        conn.execute(text(
            "INSERT INTO inventory_items (id, home_id, order_index, name, emoji, category, notes, attachments) "
            "VALUES ('i1', 'h1', 0, 'TV', '📺', 'Electronics', '', '[]')"
        ))
        conn.execute(text(
            "INSERT INTO inventory_items (id, home_id, order_index, name, emoji, category, notes, attachments) "
            "VALUES ('i2', 'h1', 1, 'Drill', '🔩', 'Tools', '', '[]')"
        ))
        conn.execute(text(
            "INSERT INTO inventory_items (id, home_id, order_index, name, emoji, category, notes, attachments) "
            "VALUES ('i3', 'h1', 2, 'Misc', '📦', '', '', '[]')"
        ))
        conn.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        conn.execute(text("INSERT INTO schema_version (version) VALUES (6)"))

    run_migrations(engine)

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        cats = conn.execute(
            text("SELECT id, name FROM inventory_categories WHERE home_id = 'h1' ORDER BY order_index")
        ).mappings().all()
        items = conn.execute(
            text("SELECT id, category_id, owner_id, store_id FROM inventory_items WHERE home_id = 'h1' ORDER BY order_index")
        ).mappings().all()

    assert version == CURRENT_VERSION
    assert [c["name"] for c in cats] == ["Electronics", "Tools"]
    tools_id = next(c["id"] for c in cats if c["name"] == "Tools")
    assert items[0]["category_id"] == "inv-electronics"
    assert items[1]["category_id"] == tools_id
    assert items[2]["category_id"] is None
    assert items[0]["owner_id"] is None
    assert items[0]["store_id"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_migrations.py::test_run_migrations_backfills_inventory_category_id -v`
Expected: FAIL — `category_id`/`owner_id`/`store_id` columns don't exist yet (`OperationalError: no such column`).

- [ ] **Step 3: Add the columns to `schema.py` and write migration 7**

In `packages/backend/src/myhome/schema.py`, replace the `category` column in `inventory_items` with three new nullable columns, and add a comment above the table matching the `cost_entries` comment style:

```python
# category_id/owner_id/store_id are plain columns, no ForeignKey -- same
# convention as cost_entries.category_id/contact_id (schema.py:242-244).
# Upgraded databases keep a legacy `category` TEXT column from before
# migration 7, undeclared here (dead) rather than dropped -- this codebase
# avoids DROP COLUMN DDL, see migrations.py's _add_inventory_owner_store_and_category_id.
inventory_items = Table(
    "inventory_items", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
    Column("category_id", String),
    Column("owner_id", String),
    Column("store_id", String),
    Column("brand", String),
    Column("model", String),
    Column("serial_number", String),
    Column("purchase_date", String),
    Column("purchase_price", Float),
    Column("warranty_expiry_date", String),
    Column("notes", String, nullable=False),
    Column("attachments", Text, nullable=False),
    Column("placement_floor_id", String),
    Column("placement_room_id", String),
    Column("placement_x", Float),
    Column("placement_y", Float),
)
```

In `packages/backend/src/myhome/migrations.py`, add `import uuid` at the top (after the `from collections.abc import Callable` line), then add the migration function right after `_add_insurance_support`:

```python
def _add_inventory_owner_store_and_category_id(conn: Connection) -> None:
    # inventory_items.category (free-text) becomes category_id, referencing
    # inventory_categories the same way Works/Costs/Consumables already
    # reference their categories. owner_id/store_id are brand new, always
    # NULL for pre-existing rows -- see the design spec at
    # docs/superpowers/specs/2026-08-01-inventory-owner-store-design.md.
    conn.execute(text("ALTER TABLE inventory_items ADD COLUMN owner_id VARCHAR"))
    conn.execute(text("ALTER TABLE inventory_items ADD COLUMN store_id VARCHAR"))
    conn.execute(text("ALTER TABLE inventory_items ADD COLUMN category_id VARCHAR"))

    home_ids = [r[0] for r in conn.execute(text("SELECT id FROM homes")).all()]
    for home_id in home_ids:
        existing = conn.execute(
            text("SELECT id, name FROM inventory_categories WHERE home_id = :h"),
            {"h": home_id},
        ).all()
        by_name = {name.strip().lower(): cat_id for cat_id, name in existing}
        next_order = len(existing)

        rows = conn.execute(
            text("SELECT id, category FROM inventory_items WHERE home_id = :h"),
            {"h": home_id},
        ).all()
        for item_id, category_text in rows:
            text_val = (category_text or "").strip()
            if not text_val:
                continue
            key = text_val.lower()
            cat_id = by_name.get(key)
            if cat_id is None:
                cat_id = str(uuid.uuid4())
                conn.execute(
                    text(
                        "INSERT INTO inventory_categories (id, home_id, order_index, name) "
                        "VALUES (:id, :h, :i, :name)"
                    ),
                    {"id": cat_id, "h": home_id, "i": next_order, "name": text_val},
                )
                by_name[key] = cat_id
                next_order += 1
            conn.execute(
                text("UPDATE inventory_items SET category_id = :cid WHERE id = :iid"),
                {"cid": cat_id, "iid": item_id},
            )
```

Bump `CURRENT_VERSION` to `7` and register the migration:

```python
CURRENT_VERSION = 7
```

```python
MIGRATIONS: list[tuple[int, Callable[[Connection], None]]] = [
    (2, _drop_kb_folders_table),
    (3, _add_ha_user_id_column),
    (4, _scope_category_tables_by_home),
    (5, _absorb_suppliers_into_contacts),
    (6, _add_insurance_support),
    (7, _add_inventory_owner_store_and_category_id),
]
```

- [ ] **Step 4: Run migration test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_migrations.py -v`
Expected: PASS (all tests in the file, including the new one).

- [ ] **Step 5: Rename `category` to `categoryId` in `models_inventory.py`, add `ownerId`/`storeId`**

Replace `category: str = ""` with `categoryId: str | None = None`, and add `ownerId: str | None = None` and `storeId: str | None = None`, on all three of `InventoryItem`, `InventoryItemCreate`, `InventoryItemUpdate`:

```python
class InventoryItem(BaseModel):
    id: str
    name: str
    emoji: str = "📦"
    categoryId: str | None = None
    ownerId: str | None = None
    storeId: str | None = None
    brand: str | None = None
    model: str | None = None
    serialNumber: str | None = None
    purchaseDate: str | None = None
    purchasePrice: float | None = None
    warrantyExpiryDate: str | None = None
    notes: str = ""
    attachments: list[str] = []
    placement: InventoryPlacement | None = None


class InventoryDocument(BaseModel):
    version: int = 1
    items: list[InventoryItem] = []


class InventoryItemCreate(BaseModel):
    name: str
    emoji: str = "📦"
    categoryId: str | None = None
    ownerId: str | None = None
    storeId: str | None = None
    brand: str | None = None
    model: str | None = None
    serialNumber: str | None = None
    purchaseDate: str | None = None
    purchasePrice: float | None = None
    warrantyExpiryDate: str | None = None
    notes: str = ""


class InventoryItemUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None
    categoryId: str | None = None
    ownerId: str | None = None
    storeId: str | None = None
    brand: str | None = None
    model: str | None = None
    serialNumber: str | None = None
    purchaseDate: str | None = None
    purchasePrice: float | None = None
    warrantyExpiryDate: str | None = None
    notes: str | None = None
```

- [ ] **Step 6: Update `persistence_inventory.py`'s field mapping**

In `load_inventory`, replace the `InventoryItem(...)` construction:

```python
    return InventoryDocument(items=[
        InventoryItem(
            id=r["id"], name=r["name"], emoji=r["emoji"], categoryId=r["category_id"],
            ownerId=r["owner_id"], storeId=r["store_id"], brand=r["brand"],
            model=r["model"], serialNumber=r["serial_number"], purchaseDate=r["purchase_date"],
            purchasePrice=r["purchase_price"], warrantyExpiryDate=r["warranty_expiry_date"],
            notes=r["notes"], attachments=json.loads(r["attachments"]),
            placement=(
                InventoryPlacement(
                    floorId=r["placement_floor_id"], roomId=r["placement_room_id"],
                    position=InventoryPosition(x=r["placement_x"], y=r["placement_y"]),
                )
                if r["placement_floor_id"] is not None else None
            ),
        )
        for r in rows
    ])
```

In `save_inventory`, replace the insert dict:

```python
            conn.execute(inventory_items_table.insert(), [
                {
                    "id": it.id, "home_id": home_id, "order_index": i, "name": it.name, "emoji": it.emoji,
                    "category_id": it.categoryId, "owner_id": it.ownerId, "store_id": it.storeId,
                    "brand": it.brand, "model": it.model,
                    "serial_number": it.serialNumber, "purchase_date": it.purchaseDate,
                    "purchase_price": it.purchasePrice, "warranty_expiry_date": it.warrantyExpiryDate,
                    "notes": it.notes, "attachments": json.dumps(it.attachments),
                    "placement_floor_id": it.placement.floorId if it.placement else None,
                    "placement_room_id": it.placement.roomId if it.placement else None,
                    "placement_x": it.placement.position.x if it.placement else None,
                    "placement_y": it.placement.position.y if it.placement else None,
                }
                for i, it in enumerate(doc.items)
            ])
```

- [ ] **Step 7: Fix the mechanical `category=`/`category`/`.category` call sites this rename breaks**

In `packages/backend/src/myhome/demo_data.py`'s `generate_demo_inventory`, change the `InventoryItem(...)` construction's `category=category_id,` to `categoryId=category_id,` (the loop variable is already named `category_id` and already holds a category **id**, e.g. `"inv-electronics"` — see `INVENTORY_ITEMS` in `demo_content.py` — so this is a pure kwarg rename, no logic change).

In `packages/backend/tests/test_inventory.py`, `test_create_item_defaults` currently asserts `assert data["category"] == ""`. Change it to:

```python
def test_create_item_defaults(client, home_id):
    resp = client.post(f"/api/homes/{home_id}/inventory/items", json={"name": "Generic item"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["emoji"] == "📦"
    assert data["categoryId"] is None
    assert data["ownerId"] is None
    assert data["storeId"] is None
    assert data["placement"] is None
```

In `packages/backend/tests/test_inventory_persistence.py`, update `make_doc()`'s `category="Electronics"` to `categoryId="cat-electronics"` (an arbitrary id string is fine here — this test round-trips through the DB, it doesn't validate against a real `inventory_categories` row):

```python
def make_doc() -> InventoryDocument:
    return InventoryDocument(
        version=1,
        items=[
            InventoryItem(
                id="i1",
                name="Samsung TV",
                emoji="📺",
                categoryId="cat-electronics",
                purchasePrice=1200.0,
                warrantyExpiryDate="2026-05-12",
                placement=InventoryPlacement(
                    floorId="f1",
                    roomId="r1",
                    position=InventoryPosition(x=3.4, y=2.1),
                ),
            )
        ],
    )
```

In `packages/backend/tests/test_demo_data.py`, `test_generate_demo_inventory_items_have_valid_category_and_placement` currently does `assert item.category in category_ids`. Change to `assert item.categoryId in category_ids`.

Finally, grep for any other reference this rename might have missed (everything under `mcp_tools_inventory.py` is expected and handled separately in Task 3 — don't touch it here):

Run: `cd packages/backend && grep -rn '"category"\|\.category\b\|category=' src tests --include='*.py' | grep -v mcp_tools_inventory`
Expected: no remaining hits outside files already updated in this step (if there are others, apply the same `category` → `categoryId` rename to them before continuing).

- [ ] **Step 8: Run the full touched-module test suite to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_migrations.py tests/test_inventory.py tests/test_inventory_persistence.py tests/test_demo_data.py -v`
Expected: PASS (every test in all four files).

- [ ] **Step 9: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/migrations.py packages/backend/src/myhome/models_inventory.py packages/backend/src/myhome/persistence_inventory.py packages/backend/src/myhome/demo_data.py packages/backend/tests/test_migrations.py packages/backend/tests/test_inventory.py packages/backend/tests/test_inventory_persistence.py packages/backend/tests/test_demo_data.py
git commit -m "feat(backend): convert inventory category to categoryId, add ownerId/storeId"
```

---

## Task 3: Backend — MCP tools resolve owner/store/category by name

**Files:**
- Modify: `packages/backend/src/myhome/mcp_tools_inventory.py`
- Test: `packages/backend/tests/test_mcp_tools_inventory.py`

**Interfaces:**
- Consumes: `InventoryItem.categoryId/ownerId/storeId` (Task 2); `SettingsDocument.owners/stores/inventoryCategories`, `load_settings`/`save_settings` (Task 1, plus existing `persistence_settings.py`).
- Produces: `_resolve_or_create(entries: list, name: str | None, make: Callable[[str, str], object]) -> str | None` — the name-to-id resolver reused for all three fields. `create_inventory_item`/`update_inventory_item` MCP tools gain `owner: str | None`/`store: str | None` params; `category`/`owner`/`store` stay name-based (not id-based) at the tool boundary.

The MCP tool surface stays name-based (an LLM caller shouldn't need to look up a uuid first) — a caller passes `category="Tools"`, `owner="Alice"`, `store="Ikea"`, and the resolver matches an existing entry case-insensitively or creates a new one, exactly mirroring what the frontend's `CreatableSelect` does.

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_mcp_tools_inventory.py`:

```python
def test_create_item_resolves_category_owner_store_by_name(home_id):
    from myhome.mcp_tools_inventory import _create_inventory_item_impl
    from myhome.persistence_settings import load_settings

    item = _create_inventory_item_impl(home_id, "Drill", category="Tools", owner="Alice", store="Ikea")
    settings_doc = load_settings(home_id)
    assert item["categoryId"] == next(c.id for c in settings_doc.inventoryCategories if c.name == "Tools")
    assert item["ownerId"] == next(o.id for o in settings_doc.owners if o.name == "Alice")
    assert item["storeId"] == next(s.id for s in settings_doc.stores if s.name == "Ikea")


def test_create_item_reuses_existing_owner_on_second_call(home_id):
    from myhome.mcp_tools_inventory import _create_inventory_item_impl
    from myhome.persistence_settings import load_settings

    _create_inventory_item_impl(home_id, "Drill", owner="Alice")
    _create_inventory_item_impl(home_id, "Sander", owner="Alice")
    settings_doc = load_settings(home_id)
    assert len([o for o in settings_doc.owners if o.name == "Alice"]) == 1


def test_create_item_blank_category_owner_store_stays_none(home_id):
    from myhome.mcp_tools_inventory import _create_inventory_item_impl

    item = _create_inventory_item_impl(home_id, "Mystery Box")
    assert item["categoryId"] is None
    assert item["ownerId"] is None
    assert item["storeId"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_mcp_tools_inventory.py -v`
Expected: FAIL — `_create_inventory_item_impl` doesn't accept `owner`/`store` kwargs (`TypeError: unexpected keyword argument`), and `item["categoryId"]` doesn't get set from the name (since `InventoryItem` no longer has a `category` field to silently absorb the old kwarg).

- [ ] **Step 3: Implement the resolver and rewire the create/update tools**

Replace the full contents of `packages/backend/src/myhome/mcp_tools_inventory.py`:

```python
from __future__ import annotations

import uuid
from collections.abc import Callable

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_inventory import InventoryItem
from .models_settings import InventoryCategory, Owner, Store
from .persistence_inventory import load_inventory, save_inventory
from .persistence_settings import load_settings, save_settings


def _resolve_or_create(entries: list, name: str | None, make: Callable[[str, str], object]) -> str | None:
    """Match `name` case-insensitively against `entries` (a list of objects
    with .id/.name, e.g. Owner/Store/InventoryCategory); append a new entry
    (mutating `entries` in place) via `make(new_id, name)` if no match.
    Returns the matching/new entry's id, or None if name is blank/None."""
    if not name or not name.strip():
        return None
    text = name.strip()
    for entry in entries:
        if entry.name.strip().lower() == text.lower():
            return entry.id
    new_id = str(uuid.uuid4())
    entries.append(make(new_id, text))
    return new_id


def _list_inventory_items_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_inventory(resolved).model_dump()


def _create_inventory_item_impl(
    home_id: str | None,
    name: str,
    emoji: str = "📦",
    category: str = "",
    owner: str | None = None,
    store: str | None = None,
    brand: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
    purchase_date: str | None = None,
    purchase_price: float | None = None,
    warranty_expiry_date: str | None = None,
    notes: str = "",
) -> dict:
    resolved = _resolve_home_id(home_id)
    settings_doc = load_settings(resolved)
    category_id = _resolve_or_create(settings_doc.inventoryCategories, category, lambda i, n: InventoryCategory(id=i, name=n))
    owner_id = _resolve_or_create(settings_doc.owners, owner, lambda i, n: Owner(id=i, name=n))
    store_id = _resolve_or_create(settings_doc.stores, store, lambda i, n: Store(id=i, name=n))
    save_settings(resolved, settings_doc)

    doc = load_inventory(resolved)
    item = InventoryItem(
        id=str(uuid.uuid4()), name=name, emoji=emoji, categoryId=category_id, ownerId=owner_id,
        storeId=store_id, brand=brand, model=model, serialNumber=serial_number,
        purchaseDate=purchase_date, purchasePrice=purchase_price,
        warrantyExpiryDate=warranty_expiry_date, notes=notes,
    )
    doc.items.append(item)
    save_inventory(resolved, doc)
    return item.model_dump()


def _update_inventory_item_impl(home_id: str | None, item_id: str, **fields) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_inventory(resolved)
    item = next((i for i in doc.items if i.id == item_id), None)
    if item is None:
        raise ValueError(f"Unknown item_id {item_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(item, field, value)
    save_inventory(resolved, doc)
    return item.model_dump()


def _delete_inventory_item_impl(home_id: str | None, item_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_inventory(resolved)
    before = len(doc.items)
    doc.items = [i for i in doc.items if i.id != item_id]
    if len(doc.items) == before:
        raise ValueError(f"Unknown item_id {item_id!r}")
    save_inventory(resolved, doc)
    return {"deleted": item_id}


@mcp.tool()
async def list_inventory_items(ctx: Context, home_id: str | None = None) -> dict:
    """List all inventory items for a home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_inventory_items_impl(home_id)


@mcp.tool()
async def create_inventory_item(
    ctx: Context,
    name: str,
    home_id: str | None = None,
    emoji: str = "📦",
    category: str = "",
    owner: str | None = None,
    store: str | None = None,
    brand: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
    purchase_date: str | None = None,
    purchase_price: float | None = None,
    warranty_expiry_date: str | None = None,
    notes: str = "",
) -> dict:
    """Add an inventory item. category/owner/store should match existing names from
    get_settings (inventoryCategories, owners, stores respectively, e.g. category
    Electronics/Furniture/Appliance/Tool/Artwork/Other) -- a name with no match
    automatically creates a new entry in that list."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_inventory_item_impl(
        home_id, name, emoji, category, owner, store, brand, model, serial_number,
        purchase_date, purchase_price, warranty_expiry_date, notes,
    )


@mcp.tool()
async def update_inventory_item(
    ctx: Context,
    item_id: str,
    home_id: str | None = None,
    name: str | None = None,
    emoji: str | None = None,
    category: str | None = None,
    owner: str | None = None,
    store: str | None = None,
    brand: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
    purchase_date: str | None = None,
    purchase_price: float | None = None,
    warranty_expiry_date: str | None = None,
    notes: str | None = None,
) -> dict:
    """Update fields on an existing inventory item. Only pass the fields you want to
    change. category/owner/store are name-based, same auto-create behavior as
    create_inventory_item; passing one leaves the item's existing value in place."""
    await _require_role(ctx.request_context.request, "normal")
    resolved = _resolve_home_id(home_id)
    settings_doc = load_settings(resolved)
    category_id = _resolve_or_create(settings_doc.inventoryCategories, category, lambda i, n: InventoryCategory(id=i, name=n)) if category else None
    owner_id = _resolve_or_create(settings_doc.owners, owner, lambda i, n: Owner(id=i, name=n)) if owner else None
    store_id = _resolve_or_create(settings_doc.stores, store, lambda i, n: Store(id=i, name=n)) if store else None
    if category or owner or store:
        save_settings(resolved, settings_doc)
    return _update_inventory_item_impl(
        home_id, item_id, name=name, emoji=emoji, categoryId=category_id, ownerId=owner_id,
        storeId=store_id, brand=brand, model=model, serialNumber=serial_number,
        purchaseDate=purchase_date, purchasePrice=purchase_price,
        warrantyExpiryDate=warranty_expiry_date, notes=notes,
    )


@mcp.tool()
async def delete_inventory_item(ctx: Context, item_id: str, home_id: str | None = None) -> dict:
    """Delete an inventory item."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_inventory_item_impl(home_id, item_id)
```

Note `_create_inventory_item_impl`'s positional-arg order changed (`owner`, `store` inserted after `category`) — this matches the updated `create_inventory_item` tool's call to it above; there are no other callers of `_create_inventory_item_impl` in the codebase besides tests and this tool.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_mcp_tools_inventory.py -v`
Expected: PASS (all tests in the file, including the pre-existing ones — `test_create_and_list_item` still passes since it never asserted on the category value).

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_inventory.py packages/backend/tests/test_mcp_tools_inventory.py
git commit -m "feat(backend): MCP inventory tools resolve category/owner/store by name"
```

---

## Task 4: Backend — demo data for owners/stores

**Files:**
- Modify: `packages/backend/src/myhome/demo_content.py`
- Modify: `packages/backend/src/myhome/demo_data.py`
- Test: `packages/backend/tests/test_demo_data.py`

**Interfaces:**
- Consumes: `SettingsDocument.owners/stores` (Task 1), `InventoryItem.ownerId/storeId` (Task 2).
- Produces: `generate_demo_settings()` now populates `owners`/`stores`; `generate_demo_inventory` assigns `ownerId`/`storeId` to a subset of demo items.

This task is purely additive on top of Task 2's `categoryId` rename (already applied to `demo_data.py` in Task 2, step 7) — no existing test needs changing here.

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_demo_data.py` (near the other `generate_demo_inventory` tests):

```python
def test_generate_demo_inventory_items_have_valid_owner_and_store_when_set():
    house = generate_demo_house()
    settings = generate_demo_settings()
    doc = generate_demo_inventory(house, settings, random.Random(42))
    owner_ids = {o.id for o in settings.owners}
    store_ids = {s.id for s in settings.stores}
    owned = [i for i in doc.items if i.ownerId is not None]
    stored = [i for i in doc.items if i.storeId is not None]
    assert len(owned) > 0
    assert len(stored) > 0
    assert all(i.ownerId in owner_ids for i in owned)
    assert all(i.storeId in store_ids for i in stored)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_demo_data.py::test_generate_demo_inventory_items_have_valid_owner_and_store_when_set -v`
Expected: FAIL — `owned`/`stored` are both empty (`settings.owners`/`settings.stores` are empty lists, `generate_demo_inventory` never sets `ownerId`/`storeId`).

- [ ] **Step 3: Add demo owners/stores and wire them into inventory generation**

In `packages/backend/src/myhome/demo_content.py`, add `Owner, Store` to the `models_settings` import, then add two new lists near `_INVENTORY_CATEGORIES`:

```python
_OWNERS = [
    Owner(id="owner-alex", name="Alex"),
    Owner(id="owner-jordan", name="Jordan"),
]

_STORES = [
    Store(id="store-ikea", name="IKEA"),
    Store(id="store-amazon", name="Amazon"),
    Store(id="store-local", name="Local Hardware Store"),
]
```

Wire them into `generate_demo_settings()`:

```python
def generate_demo_settings() -> SettingsDocument:
    return SettingsDocument(
        costCategories=list(_COST_CATEGORIES),
        workCategories=list(_WORK_CATEGORIES),
        inventoryCategories=list(_INVENTORY_CATEGORIES),
        consumableCategories=list(_CONSUMABLE_CATEGORIES),
        insuranceCategories=list(_INSURANCE_CATEGORIES),
        contactTypes=_default_contact_types(),
        consumableUnits=_default_consumable_units(),
        owners=list(_OWNERS),
        stores=list(_STORES),
    )
```

In `packages/backend/src/myhome/demo_data.py`'s `generate_demo_inventory`, assign a randomized owner/store to most items (70%/60% respectively, so both "owned/no owner" and "bought at/unknown store" states show up in the demo data):

```python
def generate_demo_inventory(house: HouseDocument, settings: SettingsDocument, rng: random.Random) -> InventoryDocument:
    today = date.today()
    items: list[InventoryItem] = []

    for name, emoji, category_id, (price_min, price_max) in INVENTORY_ITEMS:
        hints = INVENTORY_CATEGORY_ROOM_HINTS.get(category_id, [])
        room_label = rng.choice(hints) if hints else house.floors[0].rooms[0].label
        room = _find_room(house, room_label)
        floor_id = _floor_id_for_room(house, room.id)

        purchase_days_ago = rng.randint(30, 5 * 365)
        purchase_date = today - timedelta(days=purchase_days_ago)
        warranty_days = rng.randint(365, 3 * 365)
        warranty_expiry = purchase_date + timedelta(days=warranty_days)
        cx, cy = room_centroid(room)

        owner_id = rng.choice(settings.owners).id if settings.owners and rng.random() < 0.7 else None
        store_id = rng.choice(settings.stores).id if settings.stores and rng.random() < 0.6 else None

        items.append(InventoryItem(
            id=str(uuid.uuid4()),
            name=name,
            emoji=emoji,
            categoryId=category_id,
            ownerId=owner_id,
            storeId=store_id,
            purchaseDate=purchase_date.isoformat(),
            purchasePrice=round(rng.uniform(price_min, price_max), 2),
            warrantyExpiryDate=warranty_expiry.isoformat(),
            placement=InventoryPlacement(
                floorId=floor_id, roomId=room.id,
                position=InventoryPosition(x=cx + rng.uniform(-0.8, 0.8), y=cy + rng.uniform(-0.8, 0.8)),
            ),
        ))

    return InventoryDocument(items=items)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_demo_data.py tests/test_demo_content.py -v`
Expected: PASS (all tests in both files).

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/demo_content.py packages/backend/src/myhome/demo_data.py packages/backend/tests/test_demo_data.py
git commit -m "feat(backend): seed demo owners/stores and assign them to demo inventory items"
```

---

## Task 5: Frontend — `CreatableSelect.svelte` shared component

**Files:**
- Create: `packages/editor/src/lib/components/ui/CreatableSelect.svelte`
- Test: `packages/editor/test/CreatableSelect.test.ts`
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`

**Interfaces:**
- Produces: `<CreatableSelect bind:value={id} options={[{id,name}]} oncreate={(name) => Promise<{id,name}>} placeholder? onchange?={(id: string|null) => void} />` — a combobox bound (via `$bindable`) to an entity id. Consumed by `InventoryModal.svelte` in Task 7.

Popover mechanics replicate `EmojiPicker.svelte`'s existing `portal` action (`use:portal` appends the panel to `document.body`) + `position:fixed` computed from `getBoundingClientRect()`, so the dropdown isn't clipped by `Modal`'s `overflow` styling.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/CreatableSelect.test.ts`:

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import CreatableSelect from "../src/lib/components/ui/CreatableSelect.svelte";

afterEach(() => { document.body.innerHTML = ""; });

const OPTIONS = [
  { id: "o1", name: "Alice" },
  { id: "o2", name: "Bob" },
];

describe("CreatableSelect", () => {
  it("shows the selected option's name when closed", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(CreatableSelect, {
      target,
      props: { value: "o2", options: OPTIONS, oncreate: vi.fn() },
    });
    flushSync();
    expect((target.querySelector(".cs-input") as HTMLInputElement).value).toBe("Bob");
    unmount(comp);
  });

  it("opens the panel on focus and filters options as you type", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(CreatableSelect, {
      target,
      props: { value: null, options: OPTIONS, oncreate: vi.fn() },
    });
    flushSync();
    const input = target.querySelector(".cs-input") as HTMLInputElement;
    input.dispatchEvent(new FocusEvent("focus", { bubbles: true }));
    flushSync();
    input.value = "ali";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const labels = Array.from(document.querySelectorAll(".cs-option")).map((el) => el.textContent?.trim());
    expect(labels).toContain("Alice");
    expect(labels).not.toContain("Bob");
    unmount(comp);
  });

  it("selecting an existing option calls onchange with its id and closes the panel", () => {
    const onchange = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(CreatableSelect, {
      target,
      props: { value: null, options: OPTIONS, oncreate: vi.fn(), onchange },
    });
    flushSync();
    const input = target.querySelector(".cs-input") as HTMLInputElement;
    input.dispatchEvent(new FocusEvent("focus", { bubbles: true }));
    flushSync();
    (document.querySelector(".cs-option") as HTMLElement).click();
    flushSync();
    expect(onchange).toHaveBeenCalledWith("o1");
    expect(document.querySelector(".cs-panel")).toBeNull();
    unmount(comp);
  });

  it("typing a brand-new name shows a create row that calls oncreate and adopts the returned id", async () => {
    const oncreate = vi.fn().mockResolvedValue({ id: "o3", name: "Carol" });
    const onchange = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(CreatableSelect, {
      target,
      props: { value: null, options: OPTIONS, oncreate, onchange },
    });
    flushSync();
    const input = target.querySelector(".cs-input") as HTMLInputElement;
    input.dispatchEvent(new FocusEvent("focus", { bubbles: true }));
    flushSync();
    input.value = "Carol";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const createRow = document.querySelector(".cs-create") as HTMLElement;
    expect(createRow.textContent).toContain("Carol");
    createRow.click();
    await Promise.resolve();
    flushSync();
    expect(oncreate).toHaveBeenCalledWith("Carol");
    expect(onchange).toHaveBeenCalledWith("o3");
    unmount(comp);
  });

  it("does not show a create row when the typed text exactly matches an existing option", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(CreatableSelect, {
      target,
      props: { value: null, options: OPTIONS, oncreate: vi.fn() },
    });
    flushSync();
    const input = target.querySelector(".cs-input") as HTMLInputElement;
    input.dispatchEvent(new FocusEvent("focus", { bubbles: true }));
    flushSync();
    input.value = "alice";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    expect(document.querySelector(".cs-create")).toBeNull();
    unmount(comp);
  });

  it("clicking the clear button calls onchange with null", () => {
    const onchange = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(CreatableSelect, {
      target,
      props: { value: "o1", options: OPTIONS, oncreate: vi.fn(), onchange },
    });
    flushSync();
    (target.querySelector(".cs-clear") as HTMLElement).click();
    flushSync();
    expect(onchange).toHaveBeenCalledWith(null);
    unmount(comp);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/CreatableSelect.test.ts`
Expected: FAIL — the component file doesn't exist yet (`Failed to resolve import`).

- [ ] **Step 3: Implement `CreatableSelect.svelte`**

Create `packages/editor/src/lib/components/ui/CreatableSelect.svelte`:

```svelte
<script lang="ts">
  import { _ } from "svelte-i18n";

  interface Option {
    id: string;
    name: string;
  }

  interface Props {
    value: string | null;
    options: Option[];
    placeholder?: string;
    oncreate: (name: string) => Promise<Option>;
    onchange?: (id: string | null) => void;
  }

  let { value = $bindable(), options, placeholder = "", oncreate, onchange }: Props = $props();

  let open = $state(false);
  let query = $state("");
  let wrapper = $state<HTMLElement | null>(null);
  let panelEl = $state<HTMLElement | null>(null);
  let triggerEl = $state<HTMLInputElement | null>(null);
  let panelLeft = $state(0);
  let panelTop = $state(0);
  let panelWidth = $state(0);
  let highlightIndex = $state(0);
  let creating = $state(false);

  const selectedName = $derived(options.find((o) => o.id === value)?.name ?? "");
  const displayValue = $derived(open ? query : selectedName);

  const filtered = $derived(
    options.filter((o) => o.name.toLowerCase().includes(query.trim().toLowerCase()))
  );
  const exactMatch = $derived(
    filtered.some((o) => o.name.toLowerCase() === query.trim().toLowerCase())
  );
  const showCreateRow = $derived(query.trim().length > 0 && !exactMatch);

  // Teleport the panel to <body> so position:fixed isn't affected by
  // ancestor CSS transforms (e.g. Modal uses translate(-50%,-50%)) --
  // same mechanism as EmojiPicker.svelte's portal action.
  function portal(node: HTMLElement): { destroy(): void } {
    document.body.appendChild(node);
    return {
      destroy() {
        if (document.body.contains(node)) document.body.removeChild(node);
      },
    };
  }

  function openPanel(): void {
    if (triggerEl) {
      const rect = triggerEl.getBoundingClientRect();
      panelLeft = rect.left;
      panelTop = rect.bottom + 4;
      panelWidth = rect.width;
    }
    query = "";
    open = true;
    highlightIndex = 0;
  }

  function closePanel(): void {
    open = false;
    query = "";
  }

  function selectOption(o: Option): void {
    value = o.id;
    onchange?.(o.id);
    closePanel();
  }

  async function createFromQuery(): Promise<void> {
    const name = query.trim();
    if (!name || creating) return;
    creating = true;
    try {
      const created = await oncreate(name);
      value = created.id;
      onchange?.(created.id);
      closePanel();
    } finally {
      creating = false;
    }
  }

  function handleInput(e: Event): void {
    query = (e.target as HTMLInputElement).value;
    highlightIndex = 0;
    if (!open) openPanel();
  }

  function handleKeydown(e: KeyboardEvent): void {
    if (e.key === "Escape") { closePanel(); return; }
    const total = filtered.length + (showCreateRow ? 1 : 0);
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (total > 0) highlightIndex = (highlightIndex + 1) % total;
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (total > 0) highlightIndex = (highlightIndex - 1 + total) % total;
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      if (highlightIndex < filtered.length) {
        if (filtered[highlightIndex]) selectOption(filtered[highlightIndex]);
      } else if (showCreateRow) {
        createFromQuery();
      }
    }
  }

  function handleClickOutside(e: MouseEvent): void {
    const target = e.target as Node;
    if (wrapper?.contains(target) || panelEl?.contains(target)) return;
    closePanel();
  }

  function clearValue(): void {
    value = null;
    onchange?.(null);
    query = "";
  }
</script>

<svelte:window onclick={handleClickOutside} />

<span class="cs-wrap" bind:this={wrapper}>
  <input
    class="cs-input"
    bind:this={triggerEl}
    value={displayValue}
    {placeholder}
    oninput={handleInput}
    onfocus={openPanel}
    onkeydown={handleKeydown}
  />
  {#if value && !open}
    <button type="button" class="cs-clear" onclick={clearValue}>✕</button>
  {/if}

  {#if open}
    <div class="cs-panel" style="left:{panelLeft}px;top:{panelTop}px;min-width:{panelWidth}px" bind:this={panelEl} use:portal>
      {#each filtered as o, i}
        <button
          type="button"
          class="cs-option"
          class:highlighted={i === highlightIndex}
          onclick={() => selectOption(o)}
        >
          {o.name}
        </button>
      {/each}
      {#if showCreateRow}
        <button
          type="button"
          class="cs-option cs-create"
          class:highlighted={highlightIndex === filtered.length}
          disabled={creating}
          onclick={createFromQuery}
        >
          {$_('common.createOption', { values: { name: query.trim() } })}
        </button>
      {/if}
    </div>
  {/if}
</span>

<style>
  .cs-wrap { position: relative; display: inline-flex; align-items: center; width: 100%; }
  .cs-input {
    width: 100%; background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
    padding: 8px 28px 8px 12px; border-radius: var(--radius-md); font-size: 13px;
    font-family: var(--font-sans); box-sizing: border-box;
  }
  .cs-input:focus { outline: none; border-color: var(--accent); }
  .cs-clear {
    position: absolute; right: 6px; background: none; border: none; color: var(--text-faint);
    cursor: pointer; font-size: 11px; padding: 2px;
  }
  .cs-clear:hover { color: var(--danger); }
  .cs-panel {
    position: fixed; z-index: 9999; background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); box-shadow: var(--shadow-md); max-height: 220px; overflow-y: auto;
    padding: 4px;
  }
  .cs-option {
    display: block; width: 100%; text-align: left; background: none; border: none; color: var(--text);
    font-size: 13px; padding: 6px 8px; border-radius: var(--radius-sm); cursor: pointer;
    font-family: var(--font-sans);
  }
  .cs-option:hover, .cs-option.highlighted { background: var(--surface-hover); }
  .cs-create { color: var(--accent); }
</style>
```

Add the `common.createOption` key to `packages/editor/src/lib/locales/en.json`'s `"common"` object:

```json
"createOption": "+ Create \"{name}\""
```

And to `packages/editor/src/lib/locales/fr.json`'s `"common"` object:

```json
"createOption": "+ Créer « {name} »"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/CreatableSelect.test.ts`
Expected: PASS (all 6 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/CreatableSelect.svelte packages/editor/test/CreatableSelect.test.ts packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json
git commit -m "feat(frontend): add CreatableSelect shared combobox component"
```

---

## Task 6: Frontend — `settingsStore.svelte.ts` Owner/Store state

**Files:**
- Modify: `packages/editor/src/lib/settingsStore.svelte.ts`
- Test: `packages/editor/test/settingsStore.test.ts`

**Interfaces:**
- Consumes: `PUT /api/homes/{home_id}/settings/owners`, `/settings/stores` (Task 1).
- Produces: `store.owners: Owner[]`, `store.stores: Store[]`, `store.updateOwners(list)`, `store.updateStores(list)`, `store.createOwner(name): Promise<Owner>`, `store.createStore(name): Promise<Store>`, `store.createInventoryCategory(name): Promise<InventoryCategory>` — the three `create*` methods are the `oncreate` implementations `InventoryModal`/`InventoryPage` (Task 7/8) pass into `CreatableSelect`.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/settingsStore.test.ts`:

```ts
describe("createSettingsStore — owners/stores", () => {
  it("loads owners and stores from the fetched document", async () => {
    const doc = {
      version: 1, costCategories: [], inventoryCategories: [], workCategories: [],
      contactTypes: [], consumableUnits: [], consumableCategories: [], insuranceCategories: [],
      owners: [{ id: "o1", name: "Alice" }], stores: [{ id: "s1", name: "Ikea" }],
      notifications: {
        enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
        haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
      },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
    const store = createSettingsStore(() => "home-1");
    await tick();
    expect(store.owners).toEqual([{ id: "o1", name: "Alice" }]);
    expect(store.stores).toEqual([{ id: "s1", name: "Ikea" }]);
  });

  it("createOwner appends a new owner and PUTs the full list", async () => {
    const doc = {
      version: 1, costCategories: [], inventoryCategories: [], workCategories: [],
      contactTypes: [], consumableUnits: [], consumableCategories: [], insuranceCategories: [],
      owners: [{ id: "o1", name: "Alice" }], stores: [],
      notifications: {
        enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
        haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
      },
    };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc });
    vi.stubGlobal("fetch", fetchMock);
    const store = createSettingsStore(() => "home-1");
    await tick();

    fetchMock.mockResolvedValue({ ok: true, status: 204, json: async () => ({}) });
    const created = await store.createOwner("Bob");
    expect(created.name).toBe("Bob");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/homes/home-1/settings/owners",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify([{ id: "o1", name: "Alice" }, created]),
      }),
    );
  });

  it("createStore appends a new store and PUTs the full list", async () => {
    const doc = {
      version: 1, costCategories: [], inventoryCategories: [], workCategories: [],
      contactTypes: [], consumableUnits: [], consumableCategories: [], insuranceCategories: [],
      owners: [], stores: [],
      notifications: {
        enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
        haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
      },
    };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc });
    vi.stubGlobal("fetch", fetchMock);
    const store = createSettingsStore(() => "home-1");
    await tick();

    fetchMock.mockResolvedValue({ ok: true, status: 204, json: async () => ({}) });
    const created = await store.createStore("Amazon");
    expect(created.name).toBe("Amazon");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/homes/home-1/settings/stores",
      expect.objectContaining({ method: "PUT", body: JSON.stringify([created]) }),
    );
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/settingsStore.test.ts`
Expected: FAIL — `store.owners`/`store.stores`/`store.createOwner`/`store.createStore` are all `undefined`.

- [ ] **Step 3: Implement Owner/Store state and methods**

In `packages/editor/src/lib/settingsStore.svelte.ts`, add two interfaces after `InsuranceCategory`:

```ts
export interface Owner {
  id: string;
  name: string;
}

export interface Store {
  id: string;
  name: string;
}
```

Add two fields to the `SettingsDocument` interface:

```ts
export interface SettingsDocument {
  version: number;
  costCategories: CostCategory[];
  inventoryCategories: InventoryCategory[];
  workCategories: WorkCategory[];
  contactTypes: ContactType[];
  consumableUnits: string[];
  consumableCategories: ConsumableCategory[];
  insuranceCategories: InsuranceCategory[];
  owners: Owner[];
  stores: Store[];
  notifications: NotificationSettings;
}
```

Inside `createSettingsStore`, add two `$state` arrays alongside `insuranceCategories`:

```ts
  const owners = $state<Owner[]>([]);
  const stores = $state<Store[]>([]);
```

In `init()`, add loading logic after the `insuranceCategories` block:

```ts
      owners.length = 0;
      for (const o of (doc.owners ?? [])) owners.push(o);
      stores.length = 0;
      for (const s of (doc.stores ?? [])) stores.push(s);
```

Add `updateOwners`/`updateStores`, matching the existing `updateInsuranceCategories` shape exactly:

```ts
  async function updateOwners(list: Owner[]): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/settings/owners`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(list),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateStores(list: Store[]): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/settings/stores`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(list),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }
```

Add the three `create*` helpers, right after `updateStores`:

```ts
  async function createOwner(name: string): Promise<Owner> {
    const created: Owner = { id: crypto.randomUUID(), name };
    await updateOwners([...owners, created]);
    return created;
  }

  async function createStore(name: string): Promise<Store> {
    const created: Store = { id: crypto.randomUUID(), name };
    await updateStores([...stores, created]);
    return created;
  }

  async function createInventoryCategory(name: string): Promise<InventoryCategory> {
    const created: InventoryCategory = { id: crypto.randomUUID(), name };
    await updateInventoryCategories([...inventoryCategories, created]);
    return created;
  }
```

Finally, extend the returned object:

```ts
  return {
    get costCategories() { return costCategories as CostCategory[]; },
    get inventoryCategories() { return inventoryCategories as InventoryCategory[]; },
    get workCategories() { return workCategories as WorkCategory[]; },
    get contactTypes() { return contactTypes as ContactType[]; },
    get consumableUnits() { return consumableUnits as string[]; },
    get consumableCategories() { return consumableCategories as ConsumableCategory[]; },
    get insuranceCategories() { return insuranceCategories as InsuranceCategory[]; },
    get owners() { return owners as Owner[]; },
    get stores() { return stores as Store[]; },
    get notificationSettings() { return notificationSettings as NotificationSettings; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    updateCostCategories,
    updateInventoryCategories,
    updateWorkCategories,
    updateContactTypes,
    updateConsumableUnits,
    updateConsumableCategories,
    updateInsuranceCategories,
    updateOwners,
    updateStores,
    createOwner,
    createStore,
    createInventoryCategory,
    updateNotificationSettings,
    placeCostCategory,
    reload: init,
  };
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/settingsStore.test.ts`
Expected: PASS (all tests in the file).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/settingsStore.svelte.ts packages/editor/test/settingsStore.test.ts
git commit -m "feat(frontend): add owners/stores state and create helpers to settingsStore"
```

---

## Task 7: Frontend — `InventoryModal.svelte` category/owner/store fields

**Files:**
- Modify: `packages/editor/src/lib/inventoryStore.svelte.ts`
- Modify: `packages/editor/src/lib/components/InventoryModal.svelte`
- Test: `packages/editor/test/InventoryModal.test.ts`
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`

**Interfaces:**
- Consumes: `CreatableSelect` (Task 5); `store.createInventoryCategory/createOwner/createStore` (Task 6, wired in via props from `App.svelte` in Task 9).
- Produces: `InventoryItem.categoryId/ownerId/storeId: string | null` (replacing `InventoryItem.category: string`); `InventoryModal` props gain `owners: Option[]`, `stores: Option[]`, `oncreatecategory`/`oncreateowner`/`oncreatestore: (name: string) => Promise<Option>`, and `inventoryCategories` changes from `string[]` to `Option[]`.

- [ ] **Step 1: Update `inventoryStore.svelte.ts`'s `InventoryItem` interface**

In `packages/editor/src/lib/inventoryStore.svelte.ts`, replace `category: string;` with:

```ts
  categoryId: string | null;
  ownerId: string | null;
  storeId: string | null;
```

so the full interface reads:

```ts
export interface InventoryItem {
  id: string;
  name: string;
  emoji: string;
  categoryId: string | null;
  ownerId: string | null;
  storeId: string | null;
  brand: string | null;
  model: string | null;
  serialNumber: string | null;
  purchaseDate: string | null;
  purchasePrice: number | null;
  warrantyExpiryDate: string | null;
  notes: string;
  attachments: string[];
  placement: InventoryPlacement | null;
}
```

No other change is needed in this file — `createItem`/`updateItem` reference the interface via `Omit<InventoryItem, ...>`/`Partial<...>`, so they pick up the new fields automatically.

- [ ] **Step 2: Write the failing test**

In `packages/editor/test/InventoryModal.test.ts`, update the `makeItem()` helper's `category: "Electronics",` to:

```ts
    categoryId: "cat-electronics", ownerId: null, storeId: null,
```

Then add a new test (near the existing "Media tab" test):

```ts
describe("InventoryModal — category/owner/store", () => {
  it("saves the selected categoryId/ownerId/storeId", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const item = makeItem();
    const store = makeStore(item);
    const app = mount(InventoryModal, {
      target,
      props: {
        item, store, onclose: vi.fn(),
        inventoryCategories: [{ id: "cat-electronics", name: "Electronics" }],
        owners: [{ id: "o1", name: "Alice" }],
        stores: [{ id: "s1", name: "Ikea" }],
        oncreatecategory: vi.fn(),
        oncreateowner: vi.fn(),
        oncreatestore: vi.fn(),
      },
    });
    flushSync();
    const saveButton = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.trim() === "Save")!;
    saveButton.click();
    flushSync();
    expect(store.updateItem).toHaveBeenCalledWith(
      "i1",
      expect.objectContaining({ categoryId: "cat-electronics", ownerId: null, storeId: null }),
    );
    unmount(app);
  });
});
```

Update every other `mount(InventoryModal, ...)` call in this file — grep for them:

Run: `grep -n "mount(InventoryModal" packages/editor/test/InventoryModal.test.ts`

For each match, add `owners: [], stores: [], oncreatecategory: vi.fn(), oncreateowner: vi.fn(), oncreatestore: vi.fn()` to its `props: {...}` object alongside the existing `inventoryCategories` key (which stays present but now needs to be an `Option[]`, e.g. `inventoryCategories: []` still type-checks fine as an empty array either way).

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/InventoryModal.test.ts`
Expected: FAIL — `InventoryModal` doesn't accept/use `owners`/`stores`/`oncreatecategory`/`oncreateowner`/`oncreatestore` yet, and still reads `item.category` (now `undefined`).

- [ ] **Step 4: Implement the field changes in `InventoryModal.svelte`**

Add the import, right after the other `ui/` component imports:

```svelte
  import CreatableSelect from "./ui/CreatableSelect.svelte";
```

Replace the `Props` interface:

```ts
  interface Option {
    id: string;
    name: string;
  }

  interface Props {
    item: InventoryItem | null;
    store: InvStore;
    inventoryCategories: Option[];
    owners: Option[];
    stores: Option[];
    oncreatecategory: (name: string) => Promise<Option>;
    oncreateowner: (name: string) => Promise<Option>;
    oncreatestore: (name: string) => Promise<Option>;
    onclose: () => void;
    onplaceonmap?: (itemId: string) => void;
  }

  let {
    item, store, inventoryCategories, owners, stores,
    oncreatecategory, oncreateowner, oncreatestore,
    onclose, onplaceonmap,
  }: Props = $props();
```

Replace the `category` state declaration with three id-based ones:

```ts
  let categoryId = $state<string | null>(item?.categoryId ?? null);
  let ownerId = $state<string | null>(item?.ownerId ?? null);
  let storeId = $state<string | null>(item?.storeId ?? null);
```

In `handleSave`, replace `category: category.trim(),` with:

```ts
      categoryId,
      ownerId,
      storeId,
```

Replace the category `<div class="row">` block:

```svelte
    <div class="row">
      <label>{$_('costs.page.category')}</label>
      <div class="flex-grow">
        <CreatableSelect bind:value={categoryId} options={inventoryCategories} oncreate={oncreatecategory} placeholder={$_('inventory.modal.categoryPlaceholder')} />
      </div>
    </div>
    <div class="row">
      <label>{$_('inventory.modal.owner')}</label>
      <div class="flex-grow">
        <CreatableSelect bind:value={ownerId} options={owners} oncreate={oncreateowner} placeholder={$_('inventory.modal.ownerPlaceholder')} />
      </div>
      <label style="margin-left:12px">{$_('inventory.modal.store')}</label>
      <div class="flex-grow">
        <CreatableSelect bind:value={storeId} options={stores} oncreate={oncreatestore} placeholder={$_('inventory.modal.storePlaceholder')} />
      </div>
    </div>
```

(This removes the old `<input list="inv-cat-list">`/`<datalist>` block entirely.)

Add to `packages/editor/src/lib/locales/en.json`'s `"inventory"."modal"` object:

```json
"owner": "Owner",
"store": "Store",
"ownerPlaceholder": "e.g. Alex, Both of us…",
"storePlaceholder": "e.g. IKEA, Amazon…"
```

Add to `packages/editor/src/lib/locales/fr.json`'s `"inventory"."modal"` object:

```json
"owner": "Propriétaire",
"store": "Magasin",
"ownerPlaceholder": "ex. Alex, Nous deux…",
"storePlaceholder": "ex. IKEA, Amazon…"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/InventoryModal.test.ts`
Expected: PASS (every test in the file).

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/inventoryStore.svelte.ts packages/editor/src/lib/components/InventoryModal.svelte packages/editor/test/InventoryModal.test.ts packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json
git commit -m "feat(frontend): InventoryModal category/owner/store via CreatableSelect"
```

---

## Task 8: Frontend — `InventoryPage.svelte` filters/columns

**Files:**
- Modify: `packages/editor/src/lib/components/InventoryPage.svelte`
- Test: `packages/editor/test/InventoryPage.test.ts`
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`

**Interfaces:**
- Consumes: `InventoryItem.categoryId/ownerId/storeId` (Task 7).
- Produces: `InventoryPage` props gain `owners: Option[]`, `stores: Option[]`, `oncreatecategory`/`oncreateowner`/`oncreatestore`; `inventoryCategories` prop changes from `string[]` to `Option[]`; two new filter dropdowns + table columns (Owner, Store).

- [ ] **Step 1: Write the failing test**

In `packages/editor/test/InventoryPage.test.ts`, update `makeItem()`'s `category: "Tools",` to `categoryId: "cat-tools", ownerId: null, storeId: null,`.

Update every `makeItem({ ... category: "..." ... })` call in the existing tests to use `categoryId` with matching ids (e.g. `category: "Tools"` → `categoryId: "cat-tools"`, `category: "Electronics"` → `categoryId: "cat-electronics"`) — grep for them:

Run: `grep -n "category:" packages/editor/test/InventoryPage.test.ts`

For each `mount(InventoryPage, ...)` call, add the matching `inventoryCategories` prop (mapping the ids used in that test's items to display names) plus `owners: [], stores: [], oncreatecategory: vi.fn(), oncreateowner: vi.fn(), oncreatestore: vi.fn()`, e.g. for a test using `categoryId: "cat-tools"` and `categoryId: "cat-electronics"`:

```ts
      inventoryCategories: [
        { id: "cat-tools", name: "Tools" },
        { id: "cat-electronics", name: "Electronics" },
      ],
      owners: [], stores: [],
      oncreatecategory: vi.fn(), oncreateowner: vi.fn(), oncreatestore: vi.fn(),
```

Add a new test:

```ts
describe("InventoryPage — owner/store filters and columns", () => {
  it("filters by owner and shows the resolved owner name in the table", () => {
    const store = makeStore([
      makeItem({ id: "i1", name: "Drill", ownerId: "o1" }),
      makeItem({ id: "i2", name: "Saw", ownerId: "o2" }),
    ]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(InventoryPage, {
      target,
      props: {
        store, floorStore: { floors: [] },
        inventoryCategories: [], owners: [{ id: "o1", name: "Alice" }, { id: "o2", name: "Bob" }], stores: [],
        oncreatecategory: vi.fn(), oncreateowner: vi.fn(), oncreatestore: vi.fn(),
      },
    });
    flushSync();
    expect(target.textContent).toContain("Alice");
    expect(target.textContent).toContain("Bob");
    const ownerSelects = Array.from(target.querySelectorAll("select")).filter((s) =>
      Array.from(s.querySelectorAll("option")).some((o) => o.textContent === "Alice"),
    );
    expect(ownerSelects.length).toBe(1);
    unmount(app);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/InventoryPage.test.ts`
Expected: FAIL — `InventoryPage` doesn't render owner names or an owner filter yet, and the pre-existing tests break on the `category` → `categoryId` rename.

- [ ] **Step 3: Implement `InventoryPage.svelte`'s id-based category and new owner/store filters/columns**

Replace the `Props` interface and destructure:

```ts
  interface Option {
    id: string;
    name: string;
  }

  interface Props {
    store: InvStore;
    floorStore: HouseStore;
    inventoryCategories?: Option[];
    owners?: Option[];
    stores?: Option[];
    oncreatecategory: (name: string) => Promise<Option>;
    oncreateowner: (name: string) => Promise<Option>;
    oncreatestore: (name: string) => Promise<Option>;
    selectedItemId?: string | null;
    onclearselection?: () => void;
    onplaceonmap?: (itemId: string) => void;
  }

  let {
    store,
    floorStore,
    inventoryCategories = [],
    owners = [],
    stores = [],
    oncreatecategory,
    oncreateowner,
    oncreatestore,
    selectedItemId = null,
    onclearselection,
    onplaceonmap,
  }: Props = $props();
```

Add name-resolution derived state and helpers, and new filter state, right after the `allRooms` derived:

```ts
  let ownerFilter = $state("");
  let storeFilter = $state("");

  const categoryNameById = $derived(new Map(inventoryCategories.map((c) => [c.id, c.name])));
  const ownerNameById = $derived(new Map(owners.map((o) => [o.id, o.name])));
  const storeNameById = $derived(new Map(stores.map((s) => [s.id, s.name])));

  function categoryName(id: string | null): string {
    return (id && categoryNameById.get(id)) || "";
  }
  function ownerName(id: string | null): string {
    return (id && ownerNameById.get(id)) || "";
  }
  function storeName(id: string | null): string {
    return (id && storeNameById.get(id)) || "";
  }
```

Replace `allCategories` and add `allOwnerIds`/`allStoreIds`:

```ts
  const allCategories = $derived(
    [...new Set(store.items.map((i) => i.categoryId).filter((id): id is string => !!id))]
  );
  const allOwnerIds = $derived(
    [...new Set(store.items.map((i) => i.ownerId).filter((id): id is string => !!id))]
  );
  const allStoreIds = $derived(
    [...new Set(store.items.map((i) => i.storeId).filter((id): id is string => !!id))]
  );
```

In `categoryCounts`, replace `item.category` with `categoryName(item.categoryId)`:

```ts
  const categoryCounts = $derived((() => {
    const counts = new Map<string, number>();
    for (const item of store.items) {
      const key = categoryName(item.categoryId) || $_('inventory.page.uncategorized');
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([category, count]): CategoryCount => ({ category, count }))
      .sort((a, b) => b.count - a.count);
  })());
```

In `filtered`, replace the category check and add owner/store checks:

```ts
  const filtered = $derived(
    store.items.filter((i) => {
      if (
        searchQuery &&
        !i.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
        return false;
      if (roomFilter) {
        if (!i.placement?.roomId) return false;
        if (i.placement.roomId !== roomFilter) return false;
      }
      if (categoryFilter && i.categoryId !== categoryFilter) return false;
      if (ownerFilter && i.ownerId !== ownerFilter) return false;
      if (storeFilter && i.storeId !== storeFilter) return false;
      return true;
    })
  );
```

Replace the category `<select>` in the toolbar and add owner/store ones right after it:

```svelte
      <select class="native-input" bind:value={categoryFilter}>
        <option value="">{$_('costs.page.allCategories')}</option>
        {#each allCategories as id}
          <option value={id}>{categoryName(id)}</option>
        {/each}
      </select>
      <select class="native-input" bind:value={ownerFilter}>
        <option value="">{$_('inventory.page.allOwners')}</option>
        {#each allOwnerIds as id}
          <option value={id}>{ownerName(id)}</option>
        {/each}
      </select>
      <select class="native-input" bind:value={storeFilter}>
        <option value="">{$_('inventory.page.allStores')}</option>
        {#each allStoreIds as id}
          <option value={id}>{storeName(id)}</option>
        {/each}
      </select>
```

Update the `categoryCell` snippet and add `ownerCell`/`storeCell`:

```svelte
      {#snippet categoryCell(item: InventoryItem)}
        {categoryName(item.categoryId) || "—"}
      {/snippet}
      {#snippet ownerCell(item: InventoryItem)}
        {ownerName(item.ownerId) || "—"}
      {/snippet}
      {#snippet storeCell(item: InventoryItem)}
        {storeName(item.storeId) || "—"}
      {/snippet}
```

Update the `columns` array (category's `sortValue`, plus two new columns after it):

```svelte
      <SortableTable
        columns={[
          { key: "emoji", label: "", sortable: false, cellClass: "emoji-cell", cell: emojiCell },
          { key: "name", label: $_('chores.editModal.name'), sortValue: (i) => i.name, cellClass: "name-cell", cell: nameCell },
          { key: "category", label: $_('costs.page.category'), sortValue: (i) => categoryName(i.categoryId) || null, cell: categoryCell },
          { key: "owner", label: $_('inventory.modal.owner'), sortValue: (i) => ownerName(i.ownerId) || null, cell: ownerCell },
          { key: "store", label: $_('inventory.modal.store'), sortValue: (i) => storeName(i.storeId) || null, cell: storeCell },
          { key: "room", label: $_('costs.page.room'), sortValue: (i) => roomName(i.placement?.roomId), cell: roomCell },
          { key: "purchased", label: $_('inventory.page.purchased'), sortValue: (i) => (i.purchaseDate ? new Date(i.purchaseDate) : null), cell: purchasedCell },
          { key: "cost", label: $_('inventory.page.cost'), sortValue: (i) => i.purchasePrice, cell: costCell },
          { key: "warranty", label: $_('inventory.pinPopup.warranty'), sortable: false, cell: warrantyCell },
        ] as Column<InventoryItem>[]}
```

Finally, pass the new props down to `InventoryModal`:

```svelte
{#if modalItem}
  <InventoryModal
    item={modalItem === "create" ? null : modalItem}
    {store}
    {inventoryCategories}
    {owners}
    {stores}
    {oncreatecategory}
    {oncreateowner}
    {oncreatestore}
    onclose={() => { modalItem = null; }}
    onplaceonmap={onplaceonmap
      ? (id) => { modalItem = null; onplaceonmap!(id); }
      : undefined}
  />
{/if}
```

Add to `packages/editor/src/lib/locales/en.json`'s `"inventory"."page"` object:

```json
"allOwners": "All owners",
"allStores": "All stores"
```

Add to `packages/editor/src/lib/locales/fr.json`'s `"inventory"."page"` object:

```json
"allOwners": "Tous les propriétaires",
"allStores": "Tous les magasins"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/InventoryPage.test.ts`
Expected: PASS (every test in the file).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/InventoryPage.svelte packages/editor/test/InventoryPage.test.ts packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json
git commit -m "feat(frontend): InventoryPage owner/store filters and columns"
```

---

## Task 9: Frontend — `App.svelte` wiring

**Files:**
- Modify: `packages/editor/src/App.svelte`

**Interfaces:**
- Consumes: `settingsStore.owners/stores/createInventoryCategory/createOwner/createStore` (Task 6); `InventoryPage`'s new prop shape (Task 8).

`App.svelte` doesn't have a dedicated test file covering the Inventory route wiring (confirmed by grep — `App.test.ts`/`App.routing.test.ts`/`App.furniture.test.ts` don't reference `inventoryCategories`/`InventoryPage`), so this task's correctness check is the TypeScript build plus the full existing App test suite (to catch any incidental regression).

- [ ] **Step 1: Update the `InventoryPage` wiring**

In `packages/editor/src/App.svelte`, replace the `<InventoryPage ... />` block:

```svelte
      {:else if currentRoute === "#/inventory"}
        <InventoryPage
          store={inventoryStore}
          {floorStore}
          inventoryCategories={settingsStore.inventoryCategories}
          owners={settingsStore.owners}
          stores={settingsStore.stores}
          oncreatecategory={settingsStore.createInventoryCategory}
          oncreateowner={settingsStore.createOwner}
          oncreatestore={settingsStore.createStore}
          selectedItemId={selectedInventoryItemId}
          onclearselection={() => { selectedInventoryItemId = null; }}
          onplaceonmap={(id) => {
            const next = new Set(activeLayers);
            next.add("inventory");
            activeLayers = next;
            pickerHighlightId = id;
            pickerOpen = true;
            window.location.hash = "#/plan";
          }}
        />
```

- [ ] **Step 2: Verify the TypeScript build and existing tests pass**

Run: `cd packages/editor && npm run typecheck`
Expected: no new type errors involving `App.svelte`/`InventoryPage`/`InventoryModal`.

Run: `cd packages/editor && npx vitest run test/App.test.ts test/App.routing.test.ts test/App.furniture.test.ts`
Expected: PASS (no regressions).

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/App.svelte
git commit -m "feat(frontend): wire owner/store data and creators into InventoryPage"
```

---

## Task 10: Frontend — `SettingsCategories.svelte` Owners/Stores tabs

**Files:**
- Modify: `packages/editor/src/lib/components/settings/SettingsCategories.svelte`
- Test: `packages/editor/test/SettingsCategories.test.ts`
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`

**Interfaces:**
- Consumes: `store.owners/stores/updateOwners/updateStores` (Task 6).

Mirrors the existing "Contact Types" tab exactly (simple name-only add/rename/delete table).

- [ ] **Step 1: Write the failing test**

Update `makeStore()` in `packages/editor/test/SettingsCategories.test.ts` to add `owners`/`stores` state and their `update*` mocks:

```ts
    owners: [{ id: "o1", name: "Alice" }],
    stores: [{ id: "s1", name: "Ikea" }],
    updateOwners: vi.fn(),
    updateStores: vi.fn(),
```

(add these alongside the existing `insuranceCategories`/`updateInsuranceCategories` entries in the object).

Add a new test:

```ts
  it("switches to the Owners tab and shows existing owners", () => {
    const app = mount(SettingsCategories, { target, props: { store: makeStore() } });
    flushSync();
    const tab = [...target.querySelectorAll(".tab")].find((b) => b.textContent === "Owners")!;
    (tab as HTMLButtonElement).click();
    flushSync();
    expect(target.textContent).toContain("Alice");
    unmount(app);
  });

  it("switches to the Stores tab and shows existing stores", () => {
    const app = mount(SettingsCategories, { target, props: { store: makeStore() } });
    flushSync();
    const tab = [...target.querySelectorAll(".tab")].find((b) => b.textContent === "Stores")!;
    (tab as HTMLButtonElement).click();
    flushSync();
    expect(target.textContent).toContain("Ikea");
    unmount(app);
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/SettingsCategories.test.ts`
Expected: FAIL — no "Owners"/"Stores" tab exists yet.

- [ ] **Step 3: Add the Owners and Stores tabs**

In `packages/editor/src/lib/components/settings/SettingsCategories.svelte`:

1. Extend the type import: add `Owner, Store` to the `from "../../settingsStore.svelte"` import list.
2. Extend `CategoryTab`:

```ts
  type CategoryTab = "cost" | "inventory" | "work" | "contactTypes" | "consumables" | "insurance" | "owners" | "stores";
```

3. Add state + handlers for both tabs, right after the "Contact types" block (mirroring it exactly, once per entity):

```ts
  // --- Owners ---
  let editingOwnerId = $state<string | null>(null);
  let ownerDraft = $state<Owner>({ id: "", name: "" });
  let showNewOwnerForm = $state(false);
  let newOwnerDraft = $state({ name: "" });
  let confirmDeleteOwnerId = $state<string | null>(null);
  let ownerError = $state<string | null>(null);

  function startEditOwner(o: Owner): void {
    editingOwnerId = o.id;
    ownerDraft = { ...o };
    ownerError = null;
  }

  function cancelEditOwner(): void { editingOwnerId = null; ownerError = null; }

  async function saveEditOwner(): Promise<void> {
    if (!ownerDraft.name.trim()) { ownerError = $_('settings.general.nameRequired'); return; }
    const updated = store.owners.map(o =>
      o.id === editingOwnerId ? { ...ownerDraft, name: ownerDraft.name.trim() } : o
    );
    await store.updateOwners(updated);
    editingOwnerId = null; ownerError = null;
  }

  async function deleteOwner(id: string): Promise<void> {
    await store.updateOwners(store.owners.filter(o => o.id !== id));
    confirmDeleteOwnerId = null;
  }

  async function addOwner(): Promise<void> {
    if (!newOwnerDraft.name.trim()) { ownerError = $_('settings.general.nameRequired'); return; }
    const newOwner: Owner = { id: crypto.randomUUID(), name: newOwnerDraft.name.trim() };
    await store.updateOwners([...store.owners, newOwner]);
    newOwnerDraft = { name: "" };
    showNewOwnerForm = false;
    ownerError = null;
  }

  // --- Stores ---
  let editingStoreId = $state<string | null>(null);
  let storeDraft = $state<Store>({ id: "", name: "" });
  let showNewStoreForm = $state(false);
  let newStoreDraft = $state({ name: "" });
  let confirmDeleteStoreId = $state<string | null>(null);
  let storeError = $state<string | null>(null);

  function startEditStore(s: Store): void {
    editingStoreId = s.id;
    storeDraft = { ...s };
    storeError = null;
  }

  function cancelEditStore(): void { editingStoreId = null; storeError = null; }

  async function saveEditStore(): Promise<void> {
    if (!storeDraft.name.trim()) { storeError = $_('settings.general.nameRequired'); return; }
    const updated = store.stores.map(s =>
      s.id === editingStoreId ? { ...storeDraft, name: storeDraft.name.trim() } : s
    );
    await store.updateStores(updated);
    editingStoreId = null; storeError = null;
  }

  async function deleteStore(id: string): Promise<void> {
    await store.updateStores(store.stores.filter(s => s.id !== id));
    confirmDeleteStoreId = null;
  }

  async function addStore(): Promise<void> {
    if (!newStoreDraft.name.trim()) { storeError = $_('settings.general.nameRequired'); return; }
    const newStore: Store = { id: crypto.randomUUID(), name: newStoreDraft.name.trim() };
    await store.updateStores([...store.stores, newStore]);
    newStoreDraft = { name: "" };
    showNewStoreForm = false;
    storeError = null;
  }
```

4. Add two entries to the `<Tabs>` list at the top of the markup:

```svelte
    { id: "owners", label: $_('settings.categories.tabs.owners') },
    { id: "stores", label: $_('settings.categories.tabs.stores') },
```

5. Add the two tab bodies, right after the `{#if activeTab === "insurance"}` block, mirroring the "contactTypes" block's markup exactly (single `name` column + actions):

```svelte
{#if activeTab === "owners"}
  <Card>
    <div class="section-header">
      <h2>{$_('settings.categories.tabs.owners')}</h2>
      <Button onclick={() => { showNewOwnerForm = true; ownerError = null; }}>＋ {$_('common.add')}</Button>
    </div>
    <div class="table-wrapper">
      {#snippet ownerNameCell(o: Owner)}
        {#if editingOwnerId === o.id}
          <Input bind:value={ownerDraft.name} placeholder={$_('settings.categories.name')} />
        {:else}
          {o.name}
        {/if}
      {/snippet}
      {#snippet ownerActionsCell(o: Owner)}
        {#if editingOwnerId === o.id}
          <button class="icon-action ok" onclick={saveEditOwner} title={$_('common.save')}>✓</button>
          <button class="icon-action" onclick={cancelEditOwner} title={$_('common.cancel')}>✕</button>
        {:else if confirmDeleteOwnerId === o.id}
          <span class="confirm-text">{$_('settings.categories.deleteConfirm')}</span>
          <button class="icon-action danger" onclick={() => deleteOwner(o.id)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteOwnerId = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => startEditOwner(o)} title={$_('common.edit')}>✏</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteOwnerId = o.id; }} title={$_('common.delete')}>🗑</button>
        {/if}
      {/snippet}
      {#snippet ownerNewRow()}
        <td class="name-cell-input wide"><Input bind:value={newOwnerDraft.name} placeholder={$_('settings.categories.nameRequiredPlaceholder')} /></td>
        <td class="actions">
          <button class="icon-action ok" onclick={addOwner} title={$_('common.add')}>✓</button>
          <button class="icon-action" onclick={() => { showNewOwnerForm = false; ownerError = null; }} title={$_('common.cancel')}>✕</button>
        </td>
      {/snippet}
      <SortableTable
        columns={[
          { key: "name", label: $_('settings.categories.name'), sortValue: (o) => o.name, cellClass: (o) => editingOwnerId === o.id ? "name-cell-input wide" : "", cell: ownerNameCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: ownerActionsCell },
        ] as Column<Owner>[]}
        rows={store.owners}
        rowKey={(o) => o.id}
        rowClass={(o) => editingOwnerId === o.id ? "editing-row" : ""}
        extraRow={showNewOwnerForm ? ownerNewRow : undefined}
      />
    </div>
    {#if ownerError}<div class="error">{ownerError}</div>{/if}
  </Card>
{/if}

{#if activeTab === "stores"}
  <Card>
    <div class="section-header">
      <h2>{$_('settings.categories.tabs.stores')}</h2>
      <Button onclick={() => { showNewStoreForm = true; storeError = null; }}>＋ {$_('common.add')}</Button>
    </div>
    <div class="table-wrapper">
      {#snippet storeNameCell(s: Store)}
        {#if editingStoreId === s.id}
          <Input bind:value={storeDraft.name} placeholder={$_('settings.categories.name')} />
        {:else}
          {s.name}
        {/if}
      {/snippet}
      {#snippet storeActionsCell(s: Store)}
        {#if editingStoreId === s.id}
          <button class="icon-action ok" onclick={saveEditStore} title={$_('common.save')}>✓</button>
          <button class="icon-action" onclick={cancelEditStore} title={$_('common.cancel')}>✕</button>
        {:else if confirmDeleteStoreId === s.id}
          <span class="confirm-text">{$_('settings.categories.deleteConfirm')}</span>
          <button class="icon-action danger" onclick={() => deleteStore(s.id)}>✓</button>
          <button class="icon-action" onclick={() => { confirmDeleteStoreId = null; }}>✕</button>
        {:else}
          <button class="icon-action" onclick={() => startEditStore(s)} title={$_('common.edit')}>✏</button>
          <button class="icon-action danger" onclick={() => { confirmDeleteStoreId = s.id; }} title={$_('common.delete')}>🗑</button>
        {/if}
      {/snippet}
      {#snippet storeNewRow()}
        <td class="name-cell-input wide"><Input bind:value={newStoreDraft.name} placeholder={$_('settings.categories.nameRequiredPlaceholder')} /></td>
        <td class="actions">
          <button class="icon-action ok" onclick={addStore} title={$_('common.add')}>✓</button>
          <button class="icon-action" onclick={() => { showNewStoreForm = false; storeError = null; }} title={$_('common.cancel')}>✕</button>
        </td>
      {/snippet}
      <SortableTable
        columns={[
          { key: "name", label: $_('settings.categories.name'), sortValue: (s) => s.name, cellClass: (s) => editingStoreId === s.id ? "name-cell-input wide" : "", cell: storeNameCell },
          { key: "actions", label: "", sortable: false, cellClass: "actions", cell: storeActionsCell },
        ] as Column<Store>[]}
        rows={store.stores}
        rowKey={(s) => s.id}
        rowClass={(s) => editingStoreId === s.id ? "editing-row" : ""}
        extraRow={showNewStoreForm ? storeNewRow : undefined}
      />
    </div>
    {#if storeError}<div class="error">{storeError}</div>{/if}
  </Card>
{/if}
```

Add to `packages/editor/src/lib/locales/en.json`'s `"settings"."categories"."tabs"` object:

```json
"owners": "Owners",
"stores": "Stores"
```

Add to `packages/editor/src/lib/locales/fr.json`'s `"settings"."categories"."tabs"` object:

```json
"owners": "Propriétaires",
"stores": "Magasins"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/SettingsCategories.test.ts`
Expected: PASS (every test in the file).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsCategories.svelte packages/editor/test/SettingsCategories.test.ts packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json
git commit -m "feat(frontend): Owners and Stores management tabs in Settings"
```

---

## Task 11: Manual verification

**Files:** none (uses the running app)

- [ ] **Step 1: Run the full backend and frontend test suites**

Run: `cd packages/backend && python -m pytest -q`
Expected: PASS, no failures anywhere in the suite (not just the files touched by this plan).

Run: `cd packages/editor && npx vitest run`
Expected: PASS, no failures anywhere in the suite.

- [ ] **Step 2: Start the app and verify end-to-end, using the `webapp-testing` skill**

Start the dev server (check `packages/editor/package.json` / `packages/backend`'s run instructions, or use this project's `run` skill if one is configured), then in a browser:

1. Open an existing home's Inventory page. Create a new item, type a brand-new Owner name into the Owner field, and confirm it becomes selected on the item.
2. Open Settings ▸ Categories ▸ Owners and confirm the just-created owner appears there.
3. Repeat steps 1-2 for Store (Settings ▸ Categories ▸ Stores).
4. Repeat steps 1-2 for Category, confirming a brand-new category typed in the modal now actually appears in Settings ▸ Categories ▸ Inventory categories afterward (this is the fix for the pre-existing bug described in the spec).
5. On the Inventory list page, use the Owner and Store filter dropdowns and confirm they narrow the table to matching rows only.
6. Edit an existing item and pick an *existing* (not new) Owner from the dropdown — confirm it saves without creating a duplicate entry.
7. Rename an Owner in Settings ▸ Categories ▸ Owners and confirm every Inventory item referencing it shows the new name (both in the table and if reopened in the modal).
8. Spin up a fresh Demo home (if the project has one) and confirm some Inventory items show a non-empty Owner/Store on the list page, proving the demo-data seeding worked.

- [ ] **Step 3: Report results**

If any manual check fails, treat it as a bug in the relevant task above — fix it there (don't patch around it here) and re-run this task's steps 1-2 from the top.

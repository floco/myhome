# Inventory Owner & Store Fields — Design Spec

**Date:** 2026-08-01
**Status:** Draft

## Overview

Adds two new fields to Inventory items: **Owner** (who owns the item — a
person, a couple, a company) and **Store** (where it was purchased). Both
are edited via a new creatable-combobox: type to filter existing entries,
or pick "+ Create '...'" to add a new one on the spot without leaving the
form. Both are per-home lists managed independently of Contacts (an item's
store is not folded into the Contacts/Suppliers directory) and independently
of each other, and both also get a management tab in Settings ▸ Categories
(rename/delete), matching how every other per-home reference list already
works in this app.

While building the new combobox component, this spec also fixes an existing
inconsistency it would otherwise be inconsistent *not* to fix: Inventory's
`category` field is currently a free-text `<input list>`/`<datalist>` — typing
a brand-new category name does **not** create a real `InventoryCategory`
entry, unlike every other category-bearing module (Works, Costs, Consumables,
Insurance), which all reference a real per-home category list by id. This
spec converts Inventory's `category` (free string) to `categoryId`, using the
same new combobox, bringing it in line with the rest of the app.

Owner and Store are single-value per item (no joint/multi-ownership), follow
the existing `categoryId`/`contactId` convention (plain string column, no
`ForeignKey` — see `schema.py:242-244`), and both get filter dropdowns +
sortable table columns on the Inventory list page, matching Category's
existing treatment there.

Out of scope: linking Store to Contacts, multi-owner/joint ownership, an
"owner" concept on any module other than Inventory, Home-dashboard or
floor-plan surfacing of owner/store.

---

## 1. Data Model

### New per-home entity lists

`models_settings.py` gains two new models, same shape as `InventoryCategory`:

```python
class Owner(BaseModel):
    id: str
    name: str

class Store(BaseModel):
    id: str
    name: str
```

No default seed data (empty list on a fresh home — there's no sensible
universal default the way "Electronics"/"Furniture" are for categories).
`SettingsDocument` gains `owners: list[Owner] = []` and
`stores: list[Store] = []`.

### `schema.py`

Two new tables, identical shape to `inventory_categories`:

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

`inventory_items` changes: add `owner_id` and `store_id` (nullable String,
no FK — same convention as `cost_entries.contact_id`). The existing
`category` column (`String NOT NULL`, free text) is replaced by `category_id`
(nullable String, no FK):

```python
inventory_items = Table(
    "inventory_items", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
    Column("category_id", String),          # was: category (String, nullable=False)
    Column("owner_id", String),             # new
    Column("store_id", String),             # new
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

### Migration (schema version 7)

`metadata.create_all()` handles the two brand-new `owners`/`stores` tables
and is a no-op for any pre-existing installation missing them. It does
**not** add columns to an existing `inventory_items` table, and it does not
backfill data, so a real migration is needed:

```python
def _add_inventory_owner_store_and_category_id(conn: Connection) -> None:
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

The old `category` column is **left in place** on upgraded databases rather
than dropped — this codebase avoids `DROP COLUMN` DDL (see the
rename-recreate-copy-drop dance in `_scope_category_tables_by_home` for why
schema surgery here is handled cautiously). It's simply no longer declared
on the `Table()` object, so SQLAlchemy never reads or writes it again; a
one-line comment on the table def notes it's dead legacy data from before
migration 7. Fresh installs never have the column at all (`create_all()`
builds the table from the `Table()` object above, which doesn't include it).

`CURRENT_VERSION` → 7, `MIGRATIONS` gets `(7, _add_inventory_owner_store_and_category_id)`.

---

## 2. Backend

### `models_inventory.py`

`category: str = ""` → `categoryId: str | None = None` across `InventoryItem`,
`InventoryItemCreate`, `InventoryItemUpdate`; add `ownerId: str | None = None`
and `storeId: str | None = None` to all three.

### `persistence_settings.py` / `routes/settings.py`

`load_settings`/`save_settings` extended for `owners`/`stores` exactly like
the `workCategories` block (select-order-by-order_index on load,
delete-then-bulk-insert on save). New routes:

```
PUT /api/homes/{home_id}/settings/owners   body: list[Owner]
PUT /api/homes/{home_id}/settings/stores   body: list[Store]
```

### `persistence_inventory.py`

`load_inventory`/`save_inventory` swap `category`/`r["category"]` for
`categoryId`/`r["category_id"]`, add `ownerId`/`owner_id` and
`storeId`/`store_id` to both directions.

### `routes/inventory.py`

No route signature changes — `InventoryItemCreate`/`Update` already carry
the new field names through `model_dump()`.

### `mcp_tools_inventory.py`

The MCP tool surface stays **name-based** for LLM ergonomics (an LLM caller
shouldn't have to first look up a uuid) rather than switching to ids. A
shared resolver, used for `category`, `owner`, and `store` alike:

```python
def _resolve_or_create_entity(home_id: str, name: str | None, doc: SettingsDocument, field: str) -> str | None:
    """Match `name` case-insensitively against doc.<field> (owners/stores/
    inventoryCategories); create+append a new entry if no match. Returns the
    entry's id, or None if name is None/blank."""
```

`create_inventory_item`/`update_inventory_item` gain `owner: str | None`
and `store: str | None` string params (mirroring the existing `category`
param), each resolved via `_resolve_or_create_entity` against
`load_settings(home_id)` before constructing/patching the `InventoryItem`
with `ownerId`/`storeId`/`categoryId`. `category`'s existing docstring note
("category should match an inventoryCategories name from get_settings")
already documents this name-based contract; extended to mention it now also
auto-creates a matching entry, same as owner/store.

### Demo data

`demo_content.py`/`demo_data.py`: existing demo inventory records currently
set `category="..."` as free text — switch to `categoryId` referencing the
demo home's seeded `inventoryCategories`, and add a small set of demo
`owners`/`stores` entries with a couple of items referencing them (proves
the feature end-to-end in the demo home, per the existing "every module
gets demo coverage" pattern).

---

## 3. Frontend

### New shared component: `CreatableSelect.svelte`

`packages/editor/src/lib/components/ui/CreatableSelect.svelte`. Props:

```ts
interface Props {
  value: string | null;                    // selected entity id
  options: { id: string; name: string }[];
  placeholder?: string;
  oncreate: (name: string) => Promise<{ id: string; name: string }>;
}
```

Renders as a text input showing the selected option's resolved name. On
focus/typing it opens a listbox filtered by substring match (case-insensitive)
against `options`; arrow keys/click select an option (sets `value` to its
`id`, closes). If the typed text has no exact case-insensitive match among
`options` and is non-empty, a trailing `+ Create "…"` row appears; picking it
calls `oncreate(text)`, awaits the created `{id, name}`, sets `value` to the
new id, and closes. Clearing the input entirely sets `value` to `null`.
Popover uses the same portal-to-`document.body` pattern as `EmojiPicker`
(see `feedback_svelte5_jsdom_event_delegation` / EmojiPicker's own portal
fix) so it isn't clipped inside `Modal`'s overflow. Escape closes without
changing `value`; Enter selects the highlighted row or triggers create if
none is highlighted and text is present.

### `settingsStore.svelte.ts`

Add `owners`/`stores` state (fetched alongside the rest of `SettingsDocument`),
plus:

```ts
async function createOwner(name: string): Promise<Owner>
async function createStore(name: string): Promise<Store>
async function createInventoryCategory(name: string): Promise<InventoryCategory>
```

Each appends a `{ id: crypto.randomUUID(), name }` to the current list,
`PUT`s the full array (reusing `updateOwners`/`updateStores`/
`updateInventoryCategories`), and returns the new entity — this is the
`oncreate` implementation `InventoryModal`/`InventoryPage` pass into
`CreatableSelect`. (`SettingsCategories.svelte`'s existing
`addInventoryCategory` keeps its own local logic for its own form, unrelated
to this new path — no shared code needed between the two UIs beyond the
store's `update*` methods they both already call.)

### `InventoryModal.svelte`

- `inventoryCategories: string[]` prop → `inventoryCategories: { id: string; name: string }[]`;
  add `owners`/`stores` props of the same shape, plus `oncreatecategory`/
  `oncreateowner`/`oncreatestore` callback props.
- Category row: `<input list>`/`<datalist>` replaced by
  `<CreatableSelect bind:value={categoryId} options={inventoryCategories} oncreate={oncreatecategory} />`.
- Two new rows, same pattern, for Owner (`ownerId`/`owners`/`oncreateowner`)
  and Store (`storeId`/`stores`/`oncreatestore`) — placed after the Brand/Model
  row.
- `handleSave`'s `patch` sends `categoryId`, `ownerId`, `storeId` in place of
  `category`.

### `InventoryPage.svelte`

- Props: `inventoryCategories`/`owners`/`stores` become `{id,name}[]`
  (passed through to the modal unchanged in shape).
- `allCategories`/`categoryCounts`/`categoryBreakdown`/category filter/table
  cell: resolve `categoryId` → name via a `Map` built from the
  `inventoryCategories` prop for display (chart labels, filter option text,
  table cell); filtering/grouping keys on the id, not the resolved string.
- Two new filter dropdowns (Owner, Store) next to the existing Category
  filter, and two new sortable table columns, built the same way as the
  Category column (id-keyed filter/sort, name resolved for display via the
  `owners`/`stores` maps).

### `App.svelte`

Wiring updates: pass `settingsStore.inventoryCategories`/`.owners`/`.stores`
(now the raw `{id,name}[]` from the store, not `.map(c => c.name)`) into both
`InventoryPage` and (already forwarded through it) `InventoryModal`, plus the
three `oncreate*` callbacks bound to `settingsStore.createInventoryCategory`/
`createOwner`/`createStore`.

### `SettingsCategories.svelte`

Two new tabs, "Owners" and "Stores", each a simple name-only add/rename/
delete table — identical pattern to the existing "Contact Types" tab
(`editingXId`/`xDraft`/`showNewXForm`/`newXDraft`/`confirmDeleteXId`/`xError`
state + `startEdit`/`cancelEdit`/`saveEdit`/`delete`/`add` functions, one
`SortableTable` with a `name` column + actions column).

---

## 4. i18n

New keys, EN + FR, in both locale files:

- `inventory.modal.owner` / `.store` — field labels
- `inventory.page.allOwners` / `.allStores` — filter "any" option
  (mirrors `costs.page.allCategories`)
- `settings.categories.tabs.owners` / `.tabs.stores`
- `common.createOption` — `"+ Create \"{name}\""` / `"+ Créer « {name} »"`,
  used by `CreatableSelect` (interpolated with `values: { name }`)

No changes to existing keys — `inventory.modal.categoryPlaceholder` and
`costs.page.category`/`costs.page.allCategories` (reused by Inventory today)
stay as they are; `CreatableSelect`'s placeholder is passed in per-usage from
the existing category placeholder plus two new ones for owner/store.

---

## 5. Testing

**Backend** (pytest): migration 7 (new columns present; existing free-text
categories backfilled to matching/new `inventory_categories` rows;
`owner_id`/`store_id` start `NULL`; fresh installs via `create_all()` skip
the migration and have no legacy `category` column at all); `owners`/`stores`
settings CRUD routes; `persistence_inventory` round-trip with
`categoryId`/`ownerId`/`storeId`; MCP `_resolve_or_create_entity` (matches
existing case-insensitively, creates+appends on no match, returns `None` for
blank/`None` input) and `create_inventory_item`/`update_inventory_item`
end-to-end with `owner`/`store` name params.

**Frontend** (vitest): `CreatableSelect` (filter-as-you-type, select existing,
create-new calls `oncreate` and adopts the returned id, clear sets `null`,
portal renders outside the modal's clipping container, keyboard nav);
`settingsStore`'s three `create*` methods; `InventoryModal`'s three new/
changed fields (save patch shape, create-inline flow); `InventoryPage`'s
category/owner/store filters, columns, and chart resolving ids to names
correctly.

**Manual verification** (webapp-testing skill, before calling this done):
create an item, type a brand-new Owner name, confirm it's both selected on
the item and appears in Settings ▸ Categories ▸ Owners afterward; same for
Store; same for a brand-new Category (confirming the fix); filter the
Inventory list by Owner/Store/Category and confirm correct rows; edit an
existing item's owner to an existing (not new) entry via the dropdown; rename
an Owner in Settings and confirm every item referencing it shows the new
name; run the migration against a pre-existing demo/dev database and spot-
check a handful of items kept their original category text as the resolved
`categoryId` name.

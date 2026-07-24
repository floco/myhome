# Contacts Module — Design Spec

**Date:** 2026-07-24
**Status:** Approved

## Overview

Central directory of external parties — contractors, suppliers, service
providers, agents, notaries — referenced from other modules instead of each
module keeping its own free-text or minimal stand-in. Replaces the existing
`#/contacts` placeholder (reserved nav entry 👤, module id already present in
`ALL_MODULE_IDS`).

This module absorbs the existing minimal Settings "Suppliers" list
(`id`, `name` only, used by Works and Costs) — Suppliers is dropped entirely
and those modules now reference Contacts. It also becomes the real target
for House Build Tracking's `contractor_id`, which today is a free-text
column (see `2026-07-23-house-build-tracking-design.md` §1, which explicitly
anticipated this: "When a real Contractor module ships, this becomes a real
dropdown/FK against the same column with no schema change").

Each contact has exactly one **type** (Contractor / Supplier / Service
Provider / Agent / Notary / Other by default), drawn from a per-home
editable list managed in Settings — the same pattern as Work/Inventory/Cost
categories — not a hardcoded enum. Contacts themselves are full records
(name, company, phone, email, address, website, notes) managed in their own
module page, not in Settings.

Out of scope for this pass: Consumables integration (it has no supplier-like
field today — checked `schema.py`, confirmed absent — so there's nothing to
migrate or wire up; can be added later as a fresh feature), floor-plan pins
(people/companies aren't physical map objects, unlike Works/Inventory),
migrating existing Supplier rows into Contacts (explicitly declined — fresh
start, old `suppliers` table is dropped), a rich searchable picker component
(a type-filtered `<select>` is enough at today's realistic list sizes).

---

## 1. Data Model

SQLite via SQLAlchemy Core, following the existing `schema.py`/
`persistence_x.py` "whole document, delete-all-then-reinsert per save"
pattern (same as Works/Properties/Build). Home-scoped with an `(id, home_id)`
composite primary key from creation — not the bare `id` PK that the
category/supplier tables originally shipped with and had to be migrated
away from in `2026-07-24`'s predecessor bugfix
(`feedback_category_table_home_scoping_bug`).

### `contacts`

```
id:            str
home_id:       str
order_index:   int
name:          str
company_name:  str | None
type_id:       str            # references SettingsDocument.contactTypes[].id, not a hard FK
phone:         str | None
email:         str | None
address:       str | None
website:       str | None
notes:         str
```

### `ContactType` (new entry in `SettingsDocument`, `models_settings.py`)

```
class ContactType(BaseModel):
    id: str
    name: str
```

`SettingsDocument.contactTypes: list[ContactType] = []`, following the exact
`WorkCategory`/`InventoryCategory` shape — a per-home editable list, cleared
and reinserted wholesale on save via `persistence_settings.py`, same as every
other category-like list there.

**Default seed** (`_default_contact_types()` in `models_settings.py`,
mirroring `_default_work_categories()`):

```
ContactType(id="ctype-contractor", name="Contractor"),
ContactType(id="ctype-supplier",   name="Supplier"),
ContactType(id="ctype-service",    name="Service Provider"),
ContactType(id="ctype-agent",      name="Agent"),
ContactType(id="ctype-notary",     name="Notary"),
ContactType(id="ctype-other",      name="Other"),
```

### Cross-module reference columns (renamed/repurposed, not new)

- `cost_entries.supplier_id` → renamed `contact_id` (schema.py:215)
- `works.supplier_id` → renamed `contact_id` (schema.py:254)
- `build_tasks.contractor_id` → **name unchanged**, semantics change from
  free text to a Contact reference (schema.py, build model)

All three stay plain unvalidated string columns, consistent with the
existing "no hard FK on category/supplier-like columns" rule documented at
`schema.py:202-204` (settings-like lists are cleared/reinserted
independently of the rows referencing them). The frontend resolves the name
for display and falls back to "—" if the referenced contact no longer
exists (same convention as Properties' `locationId` resolution).

### Migration

`migrations.py`, new version 5:

```python
def _absorb_suppliers_into_contacts(conn: Connection) -> None:
    conn.execute(text("ALTER TABLE cost_entries RENAME COLUMN supplier_id TO contact_id"))
    conn.execute(text("ALTER TABLE works RENAME COLUMN supplier_id TO contact_id"))
    conn.execute(text("DROP TABLE IF EXISTS suppliers"))
```

New tables (`contacts`) and the new `contactTypes` list inside the existing
`settings` document/table need no migration entry — additive changes are
handled by `create_all()` per the module's existing docstring. Fresh installs
never run this migration (they start at `CURRENT_VERSION` with the renamed
columns already in `schema.py`).

### Delete protection

`DELETE /api/homes/{id}/contacts/{cid}` first checks `build_tasks
.contractor_id`, `works.contact_id`, `cost_entries.contact_id` for rows
referencing this contact. If any exist, the route returns `409` with a JSON
list of `{module, id, label}` describing what references it, and the row is
not deleted. The same lookup powers an always-visible "Used in" panel on the
contact's edit view (not just surfaced on a failed delete attempt).

---

## 2. Backend

New files, following the Works/Properties/Build pattern of "new files only":

| File | Purpose |
|------|---------|
| `models_contacts.py` | `Contact`, `ContactCreate`, `ContactUpdate` |
| `persistence_contacts.py` | CRUD + `get_contact_usage(home_id, contact_id)` cross-table reference lookup |
| `routes/contacts.py` | REST routes below |
| `mcp_tools_contacts.py` | `list_contacts`, `create_contact`, `update_contact`, `delete_contact`, mirroring `mcp_tools_works.py`'s `_*_impl` + `@mcp.tool()` pattern, role-gated the same way (`ro` for list, `normal` for mutations); added to `mcp_app.py`'s import list |

Changes to existing files:

- `models_settings.py`: add `ContactType`, `_default_contact_types()`, drop
  `Supplier` and `_default_suppliers` (there was no default supplier seed,
  so this is just removing the now-unused model/field).
- `routes/settings.py`: remove `PUT /api/homes/{id}/settings/suppliers`
  (line 63-66).
- `persistence_settings.py`: remove all `suppliers`/`Supplier` handling
  (load + save), add `contactTypes` load + save (identical shape).
- `schema.py`: remove `suppliers` table; rename `supplier_id` → `contact_id`
  on `cost_entries` and `works`; add `contacts` table.
- `mcp_tools_build.py:103-110`: update the `contractor_id` param docstring
  to note it must reference a Contact (type Contractor), rather than
  accepting arbitrary text.
- `demo_content.py`: replace `_SUPPLIERS`/`Supplier(...)` with a `_CONTACTS`
  list of full `Contact` objects (keep the same 9 supplier-flavored
  businesses, typed `ctype-supplier`/`ctype-service`, plus 2-3
  `ctype-contractor` ones for variety); `generate_demo_settings()` drops
  `suppliers=` and adds `contactTypes=_default_contact_types()` (demo home
  uses the same default type list, not a bespoke one — there's no need for
  demo-specific types the way there is for demo-specific categories, since
  types aren't spread thin across many records the way categories are).
- `demo_data.py`: add `generate_demo_contacts() -> list[Contact]` (returns
  `_CONTACTS`), called and saved via `persistence_contacts.save_contacts`
  in `seed_demo_home()`; `generate_demo_costs`/`generate_demo_works` change
  their `supplier_ids = [s.id for s in settings.suppliers]` line to source
  contact ids from the new contacts list instead, filtered to
  supplier/service-provider types. No demo build-tracker seeding exists
  today (the demo home doesn't call `build_template.py`), so there's no
  demo `contractor_id` data to update.

### REST API

```
GET    /api/homes/{id}/contacts                    → list contacts
POST   /api/homes/{id}/contacts                     → create contact
PUT    /api/homes/{id}/contacts/{cid}                → update contact
DELETE /api/homes/{id}/contacts/{cid}                → delete, 409 + usage list if referenced
GET    /api/homes/{id}/contacts/{cid}/usage          → { references: [{module, id, label}] }, used for the always-visible "Used in" panel
```

Every mutating route calls `log_activity(home_id, user_id, "contacts",
action, label, ref_id)`, reusing the existing activity log
(`persistence_activity.py`) — `"contacts"` added to its `MODULE_NOUNS` dict.

### Module registration

- `models_homes.py`: `"contacts"` already present in `ALL_MODULE_IDS`; no
  change needed there. Add `"contacts"` to `DEFAULT_EXISTING_MODULES` (it
  currently has `works`/`costs`, which will depend on contacts for their
  supplier field) and to `DEFAULT_PROJECT_MODULES` (has `works` and `build`,
  same reasoning). `DEFAULT_DEMO_MODULES` already includes it via
  `list(ALL_MODULE_IDS)`.
- `NavMenu.svelte`: drop `placeholder: true` from the existing `contacts`
  entry.

---

## 3. Frontend

**`contactsStore.svelte.ts`** — fetch/cache contacts list, CRUD methods
mirroring the REST routes, `getUsage(contactId)` for the usage panel.
Mirrors `worksStore.svelte.ts`.

**`ContactsPage.svelte`** (route `#/contacts`, replaces `PlaceholderPage`) —
matches the Chores/Build-tracker single-page layout:

- **Summary row** (top, `Card`/`StatTile`): count per contact type.
- **Table** (below, `Card` + `SortableTable`): toolbar with search
  (name/company) and type filter, "+ Add contact" button. Columns: name,
  company, type (chip), phone, email. Row click opens `ContactModal`.

**`ContactModal.svelte`** — structurally mirrors `WorkModal`/`PropertyModal`:
name, company name, type select (from `settingsStore.contactTypes`), phone,
email, address, website, notes textarea, a read-only "Used in" list (from
`getUsage`) shown when non-empty, Save/Delete/Cancel. Delete is disabled
(with an inline explanation) when usage is non-empty, rather than only
failing after the fact.

**Settings changes**:

- Remove the existing Suppliers admin card.
- Add a "Contact Types" admin card, same list-editor pattern as
  Work/Inventory categories (add/rename/reorder/delete, `id`+`name` only).

**Consumers of the renamed/repurposed reference columns**:

- `BuildTaskModal` / `TaskModal.svelte`: contractor field changes from a
  free-text input to a `<select>` sourced from `contactsStore`, filtered to
  `type_id === "ctype-contractor"` (falls back to showing all contacts if
  no contacts of that type exist yet, so the field is never a dead end).
- `WorkModal.svelte` (currently a plain `<select>` on `supplierId`,
  `WorkModal.svelte:189`) and the Costs entry modal: rebind to `contactId`,
  `<select>` sourced from `contactsStore` filtered to Supplier + Service
  Provider types.

---

## 4. Testing

**Backend** (pytest, mirroring `test_works.py` /
`test_works_persistence.py` / `test_mcp_tools_works.py`): CRUD for
contacts; usage lookup across build/works/costs; delete blocked when
referenced, allowed when not; migration test (rename columns + drop
suppliers table, existing rows preserved under the new column name);
settings CRUD for `contactTypes`; MCP tool coverage.

**Frontend** (vitest): store CRUD + usage; table render/sort/filter
(type + search); modal save/delete, delete-disabled-when-in-use; Contact
Types settings card CRUD; `WorkModal`/Costs modal/`TaskModal` contact
dropdowns filtered by type and resolving "—" for a deleted contact.

**Manual verification** (webapp-testing skill, before calling this done):
add contacts of each default type, link one as a build task's contractor
and one as a work's/cost's contact, confirm the "Used in" panel reflects
both, attempt to delete an in-use contact and confirm it's blocked with the
correct reference list, delete an unused contact successfully, rename a
Contact Type in Settings and confirm it reflects across the app, and spin
up a fresh demo home to confirm it seeds contacts and that Works/Costs
demo records show resolved contact names (not "—").

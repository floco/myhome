# Insurance Module — Design Spec

**Date:** 2026-07-25
**Status:** Approved

## Overview

Replaces the existing `#/insurance` placeholder (🛡️, `placeholder: true` in
`NavMenu.svelte`) with a real module for tracking every insurance policy
covering the home, the family, vehicles, travel, etc. Each policy records
its provider (linked to Contacts), validity/renewal dates, premium, a link
and/or attached documents describing what it covers, and a free-text field
for noting competitor alternatives.

Structurally this mirrors the Works module end to end (SQLite via
SQLAlchemy Core, whole-document load/save persistence, attachments via the
existing file-storage helpers, a per-home editable category list following
the Work/Inventory/Consumable category pattern). No floor-plan/room
placement — policies aren't physical objects, unlike Inventory/Works/
Consumables.

The one new mechanic this module introduces: an insurance record can be
flagged **"include in Costs"**. When on, the backend keeps a real
`CostEntry` (annualized premium, under a new "Insurance" cost category) in
sync in the Costs module automatically. This is how "only home insurance
counts toward the household Costs totals, but a travel or life policy
doesn't" is implemented — the toggle defaults on for the pre-populated Home
category and off for everything else, but is a per-record override so the
user isn't locked to category defaults.

Note: `models_homes.py`'s module lists already have uncommitted local
changes (present at session start) that drop the dead `budget`/`visits`/
`checklist` placeholders and add `"insurance"` to `ALL_MODULE_IDS`,
`DEFAULT_EXISTING_MODULES`, and `DEFAULT_PROJECT_MODULES`; `NavMenu.svelte`
and `SettingsGeneral.svelte` have matching uncommitted edits. This spec
builds on top of that existing state rather than redoing it — those diffs
are expected to land as part of this work.

Out of scope: floor-plan pins/room placement, renewal surfacing outside the
Insurance page itself (nav badge / Home dashboard widget), a structured
multi-field "alternatives" list (kept as one free-text area), MCP write
tools beyond the standard CRUD set already established for other modules.

---

## 1. Data Model

Two new tables in `schema.py`, following the `works`/`work_categories`
shape exactly, plus two additive columns on the existing `cost_entries`
table.

### `insurance_categories`

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

Same shape as `work_categories`. Default seed, `_default_insurance_categories()`
in `models_settings.py`, mirroring `_default_work_categories()`:

```python
InsuranceCategory(id="icat-home",      name="Home",      emoji="🏠"),
InsuranceCategory(id="icat-auto",      name="Auto",      emoji="🚗"),
InsuranceCategory(id="icat-health",    name="Health",    emoji="⚕️"),
InsuranceCategory(id="icat-life",      name="Life",      emoji="❤️"),
InsuranceCategory(id="icat-travel",    name="Travel",    emoji="✈️"),
InsuranceCategory(id="icat-liability", name="Liability", emoji="🛡️"),
```

### `insurance_policies`

```python
insurance_policies = Table(
    "insurance_policies", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("category_id", String, nullable=False),
    Column("contact_id", String),               # provider, no hard FK (category/contact convention)
    Column("policy_number", String),
    Column("coverage_summary", String, nullable=False),   # "" default, not null like other notes fields
    Column("conditions_url", String),
    Column("start_date", String),
    Column("end_date", String),                  # renewal/expiry date
    Column("premium_amount", Float),
    Column("premium_frequency", String, nullable=False),  # "monthly"|"quarterly"|"annual"|"other"
    Column("include_in_costs", Boolean, nullable=False),
    Column("alternatives", String, nullable=False),        # free text, "" default
    Column("notes", String, nullable=False),
    Column("attachments", Text, nullable=False),           # JSON list, "[]" default
    Column("linked_cost_entry_id", String),                # set/cleared by the cost-sync logic
)
```

`category_id`/`contact_id` are plain columns (no `ForeignKey`), consistent
with the existing rule that category/contact-like references stay
unvalidated strings since their target tables are independently
cleared-and-reinserted by `save_settings`/`save_contacts`.

### `cost_entries` additive columns

```python
Column("source_module", String),   # e.g. "insurance"; NULL for manually-entered costs
Column("source_id", String),       # the insurance_policies.id that produced this entry
```

These identify auto-synced entries so the Costs UI can mark them read-only
("Synced from Insurance — edit the policy instead") and so the sync logic
can find/update/delete its own row.

### Migration

`metadata.create_all()` handles the two brand-new tables for existing
databases with no migration needed. But `cost_entries` already exists for
every home, and `insurance_categories` needs its defaults backfilled for
existing homes the same way migration 5 backfilled `contact_types` (a
home's `settings` row already exists, so `load_settings()`'s lazy
"row is None → seed every default" path won't fire for it again — see
`persistence_settings.py:39-47`). New migration version 6,
`_add_insurance_support`:

```python
def _add_insurance_support(conn: Connection) -> None:
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
```

`CURRENT_VERSION` bumps to 6, `MIGRATIONS` gets `(6, _add_insurance_support)`.
`_default_cost_categories()` in `models_settings.py` also gains the same
`CostCategory(id="cat-insurance", name="Insurance", emoji="🛡️", unit=None,
color="#7a5cc4")` entry so brand-new homes get it through the normal
lazy-seed path too (both the migration backfill and the default-list
addition are needed — same dual-update pattern used for `contact_types` in
the Contacts spec).

---

## 2. Backend

New files, following the Works pattern:

| File | Purpose |
|------|---------|
| `models_insurance.py` | `InsurancePolicy`, `InsurancePolicyCreate`, `InsurancePolicyUpdate`, `InsuranceDocument` |
| `persistence_insurance.py` | `load_insurance(home_id)`, `save_insurance(home_id, doc)`, attachment helpers (`save_attachment`/`get_attachment_path`/`delete_attachment`/`delete_all_attachments`), mirroring `persistence_works.py` |
| `routes/insurance.py` | REST routes below, including the cost-sync logic |
| `mcp_tools_insurance.py` | `list_insurance_policies`, `create_insurance_policy`, `update_insurance_policy`, `delete_insurance_policy`, `_*_impl` + `@mcp.tool()` pattern mirroring `mcp_tools_works.py`, added to `mcp_app.py`'s import list |

`InsurancePolicy` field types mirror the table above 1:1 (camelCase on the
Pydantic side, e.g. `includeInCosts: bool`, `linkedCostEntryId: str | None`,
`attachments: list[str] = []`). `premiumFrequency` is
`Literal["monthly", "quarterly", "annual", "other"]`, matching how `Work`
inlines its `status` literal rather than a separate enum class.

### Cost sync

Lives in `routes/insurance.py`'s create/update/delete handlers — there are
no dedicated `create_cost_entry`/`update_cost_entry` functions anywhere in
this codebase (Costs itself does load-modify-save inline in its routes), so
Insurance's sync follows the same load-modify-save style directly against
`load_costs`/`save_costs`:

```python
def _annualized_amount(amount: float, frequency: str) -> float:
    return amount * {"monthly": 12, "quarterly": 4, "annual": 1, "other": 1}[frequency]

def _sync_cost_entry(home_id: str, policy: InsurancePolicy) -> str | None:
    """Create/update/delete the linked CostEntry to match policy.includeInCosts.
    Returns the linked CostEntry id (or None if not synced)."""
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
            attachments=[],
            sourceModule="insurance",
            sourceId=policy.id,
        ))
    save_costs(home_id, costs_doc)
    return linked_id
```

Called from `create_policy`/`update_policy` after computing the new
`InsurancePolicy`, before `save_insurance` (the returned id is written back
onto `policy.linkedCostEntryId` and persisted). `delete_policy` calls it
with `includeInCosts=False` to remove any linked entry, then deletes the
policy and its attachments. This keeps Costs itself completely unaware of
Insurance — it just has rows tagged `source_module="insurance"`.

### REST API

```
GET    /api/homes/{id}/insurance                              → list policies
POST   /api/homes/{id}/insurance                               → create
PUT    /api/homes/{id}/insurance/{pid}                          → update (exclude_unset)
DELETE /api/homes/{id}/insurance/{pid}                          → delete (+ linked cost entry, + attachments)
POST   /api/homes/{id}/insurance/{pid}/attachments               → upload (multipart, same allowlist as Works)
GET    /api/homes/{id}/insurance/{pid}/attachments/{filename}     → download
DELETE /api/homes/{id}/insurance/{pid}/attachments/{filename}      → delete
```

`log_activity(home_id, current_user_id, "insurance", action, policy.name,
policy.id)` after every mutation, `"insurance"` added to `MODULE_NOUNS`.

### `models_settings.py` / `persistence_settings.py`

Add `InsuranceCategory{id, name, emoji}`, `_default_insurance_categories()`,
`SettingsDocument.insuranceCategories: list[InsuranceCategory] = []`.
`persistence_settings.py` gets the same load (lazy-seed on `row is None`)
and delete-then-reinsert-on-save treatment as `workCategories`.

### Costs UI awareness of synced entries

`routes/costs.py`'s update/delete handlers reject edits to entries where
`source_module` is set (400, "This entry is synced from Insurance — edit
the policy instead") — the only change needed in the Costs module itself.

### Demo data

`demo_content.py`: add 3-4 `InsurancePolicy` records spanning Home (with
`includeInCosts=True`) and non-Home categories. `demo_data.py`:
`generate_demo_insurance()` + seeding call in `seed_demo_home()`, same
pattern as Works.

---

## 3. Frontend

**`insuranceStore.svelte.ts`** — fetch/cache policies + attachments CRUD,
mirrors `worksStore.svelte.ts`.

**`InsurancePage.svelte`** (route `#/insurance`, replaces `PlaceholderPage`)
— same shell as `InventoryPage.svelte`/`WorksPage.svelte`:
- Summary card (top): donut chart of annualized cost by category
  (`assignCategoryColors`) + a small table of policies sorted by soonest
  `endDate`, following the module-summary-card pattern from PR #59.
- `SortableTable` below: search, category filter dropdown, "+ Add policy"
  button. Columns: name, category (chip), provider (resolved contact name
  or "—"), premium (amount + frequency), end date with a "renews soon"
  badge (reusing Inventory's warranty-expiry-badge styling) when `endDate`
  is within 30 days. Row click opens the modal.

**`InsuranceModal.svelte`** — tabbed CRUD mirroring `InventoryModal.svelte`:
- **Details**: name, category select, provider (`contactId`, Contacts
  picker), policy number, start/end date (`DatePicker`).
- **Cost**: premium amount, frequency select, "Include in Costs" checkbox
  (auto-checked when category = Home on create, freely overridable after).
- **Coverage**: coverage summary textarea, conditions URL input,
  `MediaGallery` attachments (policy documents).
- **Alternatives**: single free-text textarea.
- Notes field, Save/Delete/Cancel.

**Settings**: new "Insurance Categories" tab in `SettingsCategories.svelte`,
identical add/rename/reorder/delete pattern (id/name/emoji) as the Work
categories tab.

**Nav/routing/locale**: drop `placeholder: true` from the `insurance` entry
in `NavMenu.svelte` (already present, uncommitted) and
`SettingsGeneral.svelte`; wire `#/insurance` → `InsurancePage` in
`App.svelte` in place of `PlaceholderPage`; replace the placeholder
strings in `en.json`/`fr.json` with real labels for the page, modal tabs,
and fields; add an Insurance entry to `searchIndex.ts`.

---

## 4. Testing

**Backend** (pytest, mirroring `test_works.py`/`test_works_persistence.py`/
`test_mcp_tools_works.py`): CRUD + attachments for insurance policies;
cost-sync — creates a `CostEntry` when `includeInCosts` toggles on,
updates it when premium/frequency/dates change, removes it when toggled
off or the policy is deleted; Costs route rejects direct edits/deletes of
`source_module="insurance"` entries; `insuranceCategories` settings CRUD;
migration 6 test (new columns present, existing homes get backfilled
categories + `cat-insurance`, fresh installs get it via `create_all` +
default list without running the migration); MCP tool coverage.

**Frontend** (vitest): store CRUD; summary card chart/table; list
render/sort/filter/search + renewal-soon badge; modal save/delete across
all four tabs, contact picker, attachment upload; Insurance Categories
settings tab CRUD.

**Manual verification** (webapp-testing skill, before calling this done):
add a Home-category policy with `includeInCosts` on, confirm a matching
entry appears in the Costs page and is read-only there; add a Travel policy
with the toggle off, confirm nothing appears in Costs; toggle an existing
policy's include-in-costs off and confirm the Costs entry disappears;
delete a synced policy and confirm its Costs entry is gone too; rename an
Insurance Category in Settings and confirm it reflects on the page; spin up
a fresh demo home and confirm it seeds insurance records with a resolved
provider name.

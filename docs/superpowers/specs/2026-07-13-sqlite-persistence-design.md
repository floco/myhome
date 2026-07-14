# SQLite Persistence Migration — Design

## Goal

Replace the current "one JSON file per document, rewritten wholesale on every
save" persistence pattern with a real relational SQLite database, as a
foundation for the app's continued growth. This is a maturity/foundation
change, not a response to a specific performance or concurrency incident.

## Scope

### In scope — moves to SQLite

Every module currently backed by a per-home or global JSON document:

- Per-home: `chores`, `costs`, `inventory`, `works`, `consumables`,
  `settings`, `activity_log`, `notifications_state`
- Global: `homes`, `users`, `tokens`, `oidc_config`, `mcp_config`,
  `backup_config`, `backup_state`

### Out of scope — stays as files

- **KB entries** (`kb/*.md` with frontmatter) — unchanged.
- **All `*-attachments/` media directories** (chores, costs, inventory,
  works, kb) — unchanged, still plain files on disk referenced by filename.
- **`house.json` (the floor-plan document)** — deeply nested CAD-like data
  (floors → walls/openings/rooms/furniture, arbitrary point polygons) that
  is always loaded and saved as a single whole by the floor-plan editor and
  never queried piecemeal. Normalizing it into tables would be substantial
  schema work for no query benefit. It becomes a single JSON blob column in
  a `house_documents` table (one row per home), the same "opaque document"
  treatment as KB/media, just stored in SQLite instead of a `.json` file so
  it's still covered by the one backup/restore mechanism. Other modules
  keep referencing `floorId`/`roomId` as plain string foreign keys into this
  blob, exactly as today.
- Not touching the redundancy between each entity's `attachments: list[str]`
  field and the filesystem listing of its attachments directory — orthogonal
  to this migration.

## Architecture

- **Single SQLite file**: `<DATA_DIR>/myhome.db`, mirroring the existing
  convention of global files (`users.json`, `homes.json`, etc.) living at
  the `DATA_DIR` root.
- **SQLAlchemy Core** (no ORM). A new `schema.py` defines `Table` objects
  for every table below. A new `db.py` owns engine creation: WAL mode,
  `check_same_thread=False`, and an engine cache keyed by the resolved
  `DATA_DIR` path (not a single process-wide singleton) — this is what lets
  tests, which `monkeypatch.setenv("DATA_DIR", str(tmp_path))` per test,
  transparently get an isolated fresh database per test with no fixture
  changes.
- **Persistence-layer contract is preserved.** Every
  `load_x(home_id) -> XDocument` / `save_x(home_id, doc: XDocument)`
  function in `persistence_x.py` keeps its exact signature, still built on
  and returning the same Pydantic models (`ChoreDocument`, `CostsDocument`,
  etc.) used throughout the app today. Only the *internals* change, from
  JSON file I/O to SQL via SQLAlchemy Core. Routes, `mcp_tools_*.py`,
  `chore_scheduling.py`, `demo_data.py`, `notification_scheduler.py`, and
  every other caller are unaffected.
- **Save semantics**: `save_x` runs a single DB transaction that deletes all
  rows for that `home_id` (and module) and re-inserts from the document.
  This mirrors today's "rewrite the whole file" behavior exactly — no
  subtle behavior change — while replacing the tmp-file-then-rename trick
  with real transactional atomicity.

## Schema design

General rule: nested single-value fields that are meaningfully queried
(e.g. `placement.floorId` / `roomId` / `position.x/y`) are flattened into
real columns. Free-form dict/list fields with no independent identity
(`frequencyMetadata`, `attachments` list, `scopes`, `warrantyNotified`) are
stored as a JSON text column — they are never filtered or joined on, so
normalizing them would add complexity for no benefit.

### Global tables

- `homes` (id PK, name, type, created_at)
- `home_modules` (home_id FK, module_id) — replaces the `enabledModules`
  JSON list with a real junction table
- `users` (id PK, username unique, password_hash, role, created_at,
  auth_provider, oidc_sub)
- `api_tokens` (id PK, name, token_hash, role, owner_id FK → users.id,
  created_at, last_used_at)
- `oidc_config` (single row: enabled, provider_name, issuer, client_id,
  client_secret, default_role, scopes JSON)
- `mcp_config` (single row: enabled)
- `backup_config` (single row: enabled, frequency, time, dayOfWeek,
  dayOfMonth, retentionCount)
- `backup_state` (single row: lastRunDate)
- `schema_version` (single row: version int) — see Migrations below

### Per-home tables (all FK `home_id` → `homes.id`)

- `house_documents` (home_id PK, doc JSON) — floor-plan blob carve-out
- `chores`, `chore_assignments` (FK chore_id → chores.id),
  `chore_completions` (FK chore_id → chores.id)
- `cost_entries` (FK category_id → cost_categories.id, FK supplier_id →
  suppliers.id)
- `cost_categories`, `inventory_categories`, `work_categories`,
  `suppliers`, `consumable_categories` — promoted from `SettingsDocument`'s
  JSON lists to real tables, since other tables already reference them by
  id (a concrete relational win: real foreign keys instead of string ids
  matched in Python)
- `inventory_items` (FK category via `category` string field unchanged —
  see note below)
- `works` (FK supplier_id, category_id)
- `consumables` (FK category_id), `consumable_transactions` (FK
  consumable_id → consumables.id)
- `consumable_units` — stays a JSON column on the per-home `settings` row
  (a flat list of strings; nothing references it by id)
- `settings` (single row per home: `consumable_units` JSON,
  `notifications_*` columns flattened from the nested
  `NotificationSettings` object)
- `activity_log_entries` (indexed on `home_id` + `timestamp`, for the
  existing 90-day retention prune)
- `notification_state` (home_id PK, warranty_notified JSON,
  last_push_digest_date)

Note: `InventoryItem.category` is currently a freeform string, not an id
reference into `inventory_categories` (unlike costs/works which use
`categoryId`). This migration does not change that — the column moves
as-is; making it a real FK would be a product/behavior change out of scope
here.

## Migrations (schema evolution going forward)

A `schema_version` table holds a single integer. A small ordered list of
hand-written migration functions (`CREATE TABLE IF NOT EXISTS ...`,
`ALTER TABLE ... ADD COLUMN ...`) runs at startup, each gated on the current
version, in the same lightweight spirit as the app's existing homegrown
migration patterns — just centralized in one place instead of scattered
inline checks in each `load_x`. No Alembic, no new dependency.

## Cutover — no JSON→SQLite data migration

Per explicit decision: this is a clean cutover, not a data migration.

- The new `load_x`/`save_x` functions never read the old `*.json` files.
  On upgrade, existing JSON data is simply orphaned (not auto-deleted, not
  imported) — operators start fresh.
- `migrate_legacy_if_needed()` in `persistence_homes.py` (the
  pre-multi-home JSON consolidation shuffle) becomes dead code, since its
  entire job was moving JSON files that will now never be read again. It
  is deleted, along with the legacy-migration test cases in
  `test_homes_persistence.py`.
- Inline "old-format" compatibility shims that exist purely to patch old
  JSON on load also become dead code and are removed:
  - `persistence_chores.py`'s `frequencyMetadata` backfill migration
  - `persistence_costs.py`'s `supplier` → `supplierId` backfill migration
  - Their corresponding old-shape-JSON test cases (e.g. `test_costs.py`'s
    inline old-data write)

## Testing impact

Minimal. `conftest.py`'s `_make_users` already isolates each test via
`monkeypatch.setenv("DATA_DIR", str(tmp_path))`; since the SQLite engine
cache keys off that same path, every test still gets a fully isolated,
fresh database automatically — no fixture rewrite needed. A handful of
tests that assert directly on `*.json` file existence (e.g. some backup
tests) are updated to check the `.db` file / DB rows instead, as a
mechanical follow-along change made module-by-module as each
`persistence_x.py` is converted.

## Deployment impact

None beyond the file change. `DATA_DIR` is already the persisted Docker
volume; `myhome.db` is just one more file in it. The existing zip-based
backup (`iter_backup_files` walks `DATA_DIR`) picks it up automatically
with no code change needed.

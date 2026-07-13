# SQLite Persistence Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace every per-home/global JSON document (`chores.json`, `costs.json`, `homes.json`, `users.json`, etc.) with tables in a single SQLite database, while KB markdown files, all `*-attachments/` media directories, and the floor-plan document keep their current "opaque blob" treatment.

**Architecture:** A new `schema.py` defines SQLAlchemy Core `Table` objects; a new `db.py` owns a per-`DATA_DIR` cached `Engine` (WAL mode, foreign keys on) plus schema bootstrap. Every `persistence_x.py` module keeps its exact `load_x(home_id) -> XDocument` / `save_x(home_id, doc)` function signatures — only their internals change from JSON file I/O to SQL. `save_x` deletes all rows for that `home_id` (or, for the `homes` table specifically, diffs and upserts — see Task 2) and re-inserts from the document inside one transaction, mirroring today's "rewrite the whole file" semantics exactly.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x Core (no ORM), stdlib `sqlite3` via SQLAlchemy's `pysqlite` driver, pytest.

## Global Constraints

- Every `persistence_x.py` module's public `load_x`/`save_x` function signatures are unchanged — callers in `routes/*.py`, `mcp_tools_*.py`, `chore_scheduling.py`, `demo_data.py`, `notification_scheduler.py`, `backup_scheduler.py` are never touched by this plan.
- **Hard SQL foreign keys (`ForeignKey(..., ondelete="CASCADE")`) are only declared between a table and its parent when both are cleared-and-reinserted together inside the *same* `save_x()` transaction** (e.g. `chore_assignments.chore_id → chores.id`, both rewritten inside `save_chores()`). Cross-module references that are written by *different* `save_x()` calls at different times (e.g. `cost_entries.category_id → cost_categories.id`, written by `save_costs()` and `save_settings()` respectively) stay plain, unconstrained `_id` columns — exactly like today's Python-only string matching — because a hard FK there would make one module's save fail with an `IntegrityError` while another module's save is mid-transaction. The one exception is every per-home table's `home_id` column, which **does** get `ForeignKey("homes.id", ondelete="CASCADE")`, so deleting a home cascades to all its relational data (Task 2 changes `save_homes()` to a diff/upsert specifically so this cascade only ever fires for a genuinely deleted home, never transiently).
- Every table that stores one row per item of a `Document`'s list field gets an `order_index INTEGER NOT NULL` column, populated with that item's index in the list at save time, and `load_x` reads with `ORDER BY order_index` — this preserves the list ordering JSON arrays gave for free. The one exception is `activity_log_entries`, which is already strictly ordered by its own `timestamp` column and is exempted from this rule.
- Nested single-value fields that are meaningfully queried (`placement.floorId`/`roomId`/`position.x`/`position.y`) are flattened into real columns (`placement_floor_id`, `placement_room_id`, `placement_x`, `placement_y`). Free-form dict/list fields with no independent identity (`frequencyMetadata`, `attachments`, `scopes`, `warrantyNotified`) are stored as a `Text` column holding `json.dumps(...)`.
- No JSON→SQLite data migration. `persistence_x.py` never reads old `*.json` files again after conversion. Dead code that existed only to migrate/patch old JSON is deleted in the same task that converts its module.
- Single database file at `<DATA_DIR>/myhome.db`. `DATA_DIR` defaults to `/data`, same as every existing persistence module.
- KB entries (`kb/*.md`), all `*-attachments/` directories, and the `_home_dir()`/attachment helper functions in each `persistence_x.py` are **not** touched by this plan.
- New dependency: add `"sqlalchemy>=2.0"` to `packages/backend/pyproject.toml`'s `dependencies` list (Task 1).
- Run backend tests with: `cd packages/backend && python -m pytest tests/ -q` (or a narrower path/`-k` filter per task).

---

### Task 1: Engine, schema bootstrap, and migration scaffolding

**Files:**
- Create: `packages/backend/src/myhome/schema.py`
- Create: `packages/backend/src/myhome/migrations.py`
- Create: `packages/backend/src/myhome/db.py`
- Modify: `packages/backend/pyproject.toml`
- Modify: `/projects/myhome/.gitignore`
- Test: `packages/backend/tests/test_db.py`

**Interfaces:**
- Produces: `myhome.schema.metadata` (a `sqlalchemy.MetaData` instance, empty for now — later tasks add `Table` objects to this same file); `myhome.db.get_engine() -> sqlalchemy.engine.Engine`; `myhome.migrations.run_migrations(engine: Engine) -> None`.

- [ ] **Step 1: Add the SQLAlchemy dependency**

Edit `packages/backend/pyproject.toml`, in the `dependencies` list, add a line after `"mcp>=1.28",`:

```toml
    "mcp>=1.28",
    "sqlalchemy>=2.0",
```

- [ ] **Step 2: Install it**

Run: `cd packages/backend && pip install -e ".[dev]"`
Expected: SQLAlchemy installs with no errors.

- [ ] **Step 3: Ignore runtime SQLite files**

Edit `/projects/myhome/.gitignore`, append:

```
*.db
*.db-wal
*.db-shm
```

- [ ] **Step 4: Create the (initially empty) schema module**

Create `packages/backend/src/myhome/schema.py`:

```python
# packages/backend/src/myhome/schema.py
"""SQLAlchemy Core table definitions for the SQLite persistence layer.

Every persistence_x.py module's tables live here, added incrementally as
each module is converted. See the Global Constraints in
docs/superpowers/plans/2026-07-13-sqlite-persistence.md for the rules on
when a home_id/parent-id column gets a hard ForeignKey vs. stays a plain
column, and for the order_index convention.
"""
from __future__ import annotations

from sqlalchemy import MetaData

metadata = MetaData()
```

- [ ] **Step 5: Create the migration runner**

Create `packages/backend/src/myhome/migrations.py`:

```python
# packages/backend/src/myhome/migrations.py
"""Schema-version bookkeeping for the SQLite persistence layer.

metadata.create_all() (called from db.get_engine()) handles all additive
schema changes -- new tables, and it's a no-op for tables that already
exist. This module exists for the harder case that create_all() can't
handle: column renames, type changes, backfills. MIGRATIONS is empty today
because this plan only ever adds tables; future work appends
(version, fn) pairs here as real schema alterations are needed.
"""
from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

CURRENT_VERSION = 1

MIGRATIONS: list[tuple[int, Callable[[Connection], None]]] = []


def run_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
        ))
        row = conn.execute(text("SELECT version FROM schema_version")).first()
        if row is None:
            conn.execute(
                text("INSERT INTO schema_version (version) VALUES (:v)"),
                {"v": CURRENT_VERSION},
            )
            current = CURRENT_VERSION
        else:
            current = row[0]
        for target_version, fn in MIGRATIONS:
            if target_version > current:
                fn(conn)
                conn.execute(text("UPDATE schema_version SET version = :v"), {"v": target_version})
                current = target_version
```

- [ ] **Step 6: Create the engine module**

Create `packages/backend/src/myhome/db.py`:

```python
# packages/backend/src/myhome/db.py
"""Owns the SQLite engine for the persistence layer.

Engines are cached per resolved DATA_DIR path rather than as a single
process-wide singleton -- this is what lets tests, which
monkeypatch.setenv("DATA_DIR", str(tmp_path)) per test, transparently get
an isolated fresh database with no fixture changes. The cache is bounded
(_MAX_CACHED_ENGINES) so a long-running test suite that touches hundreds
of distinct tmp_path DATA_DIRs doesn't accumulate open SQLite file handles
forever; in a real deployment DATA_DIR never changes, so the cache holds
exactly one engine for the process lifetime.
"""
from __future__ import annotations

import os
from collections import OrderedDict
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from .migrations import run_migrations
from .schema import metadata

_MAX_CACHED_ENGINES = 8
_engines: "OrderedDict[str, Engine]" = OrderedDict()


def _db_path() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "myhome.db"


def get_engine() -> Engine:
    path = str(_db_path())
    if path in _engines:
        _engines.move_to_end(path)
        return _engines[path]

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    metadata.create_all(engine)
    run_migrations(engine)

    _engines[path] = engine
    if len(_engines) > _MAX_CACHED_ENGINES:
        _, evicted = _engines.popitem(last=False)
        evicted.dispose()
    return engine
```

- [ ] **Step 7: Write the failing tests**

Create `packages/backend/tests/test_db.py`:

```python
from sqlalchemy import text

from myhome.db import get_engine


def test_get_engine_creates_db_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_engine()
    assert (tmp_path / "myhome.db").exists()


def test_get_engine_returns_cached_instance_for_same_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert get_engine() is get_engine()


def test_get_engine_sets_wal_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    engine = get_engine()
    with engine.connect() as conn:
        mode = conn.execute(text("PRAGMA journal_mode")).scalar()
    assert mode == "wal"


def test_get_engine_enables_foreign_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    engine = get_engine()
    with engine.connect() as conn:
        enabled = conn.execute(text("PRAGMA foreign_keys")).scalar()
    assert enabled == 1


def test_get_engine_bootstraps_schema_version(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    engine = get_engine()
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
    assert version == 1


def test_get_engine_creates_separate_db_per_data_dir(tmp_path, monkeypatch):
    dir_a, dir_b = tmp_path / "a", tmp_path / "b"
    monkeypatch.setenv("DATA_DIR", str(dir_a))
    engine_a = get_engine()
    monkeypatch.setenv("DATA_DIR", str(dir_b))
    engine_b = get_engine()
    assert engine_a is not engine_b
    assert (dir_a / "myhome.db").exists()
    assert (dir_b / "myhome.db").exists()


def test_get_engine_evicts_oldest_beyond_cache_limit(tmp_path, monkeypatch):
    first_path = tmp_path / "dir0"
    monkeypatch.setenv("DATA_DIR", str(first_path))
    first_engine = get_engine()
    for i in range(1, 9):
        monkeypatch.setenv("DATA_DIR", str(tmp_path / f"dir{i}"))
        get_engine()
    monkeypatch.setenv("DATA_DIR", str(first_path))
    assert get_engine() is not first_engine
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_db.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 9: Commit**

```bash
git add packages/backend/pyproject.toml packages/backend/src/myhome/schema.py \
        packages/backend/src/myhome/migrations.py packages/backend/src/myhome/db.py \
        packages/backend/tests/test_db.py .gitignore
git commit -m "feat: add SQLite engine, schema bootstrap, and migration scaffolding"
```

---

### Task 2: Homes + home_modules

**Files:**
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/persistence_homes.py`
- Modify: `packages/backend/src/myhome/main.py`
- Modify: `packages/backend/tests/test_homes_persistence.py`

**Interfaces:**
- Consumes: `myhome.db.get_engine() -> Engine`, `myhome.schema.metadata`.
- Produces: `schema.homes`, `schema.home_modules` tables. `persistence_homes.load_homes() -> HomesDocument`, `save_homes(doc: HomesDocument) -> None`, `create_home(name, home_type) -> Home`, `patch_home(...) -> Home | None`, `delete_home(home_id) -> bool` — same signatures as before, `migrate_legacy_if_needed` removed.

- [ ] **Step 1: Add the tables to schema.py**

Append to `packages/backend/src/myhome/schema.py`:

```python
from sqlalchemy import Column, ForeignKey, Integer, String, Table

homes = Table(
    "homes", metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("type", String, nullable=False),
    Column("created_at", String, nullable=False),
)

home_modules = Table(
    "home_modules", metadata,
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("module_id", String, primary_key=True),
    Column("order_index", Integer, nullable=False),
)
```

- [ ] **Step 2: Rewrite the failing tests first**

Replace the contents of `packages/backend/tests/test_homes_persistence.py` (the legacy-migration tests are dropped — there is no more legacy JSON to migrate from):

```python
# packages/backend/tests/test_homes_persistence.py
from myhome.persistence_homes import (
    create_home,
    delete_home,
    load_homes,
    patch_home,
    save_homes,
)


def test_load_returns_empty_when_no_data(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert load_homes().homes == []


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
    assert doc.homes[0].enabledModules == home.enabledModules


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
    assert load_homes().homes[0].enabledModules == ["home", "plan"]


def test_patch_home_returns_none_for_unknown_id(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert patch_home("nonexistent", name="X", home_type=None, enabled_modules=None) is None


def test_delete_home_removes_from_registry_and_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home = create_home("Test", "existing")
    home_dir = tmp_path / "homes" / home.id
    assert home_dir.is_dir()
    assert delete_home(home.id) is True
    assert not home_dir.exists()
    assert load_homes().homes == []


def test_delete_home_returns_false_for_unknown_id(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert delete_home("nonexistent") is False


def test_save_homes_preserves_untouched_homes(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home_a = create_home("Home A", "existing")
    home_b = create_home("Home B", "existing")
    patch_home(home_a.id, name="Home A Renamed", home_type=None, enabled_modules=None)
    doc = load_homes()
    ids = {h.id for h in doc.homes}
    assert ids == {home_a.id, home_b.id}
    names = {h.id: h.name for h in doc.homes}
    assert names[home_a.id] == "Home A Renamed"
    assert names[home_b.id] == "Home B"


def test_delete_one_home_does_not_remove_another(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    home_a = create_home("Home A", "existing")
    home_b = create_home("Home B", "existing")
    delete_home(home_a.id)
    remaining = load_homes().homes
    assert len(remaining) == 1
    assert remaining[0].id == home_b.id


def test_save_homes_direct_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from myhome.models_homes import Home, HomesDocument
    doc = HomesDocument(homes=[
        Home(id="h1", name="A", type="existing", enabledModules=["home", "chores"], createdAt="2026-01-01T00:00:00+00:00"),
    ])
    save_homes(doc)
    loaded = load_homes()
    assert len(loaded.homes) == 1
    assert loaded.homes[0].enabledModules == ["home", "chores"]
```

- [ ] **Step 3: Run the rewritten tests against the current JSON implementation as a sanity check**

Run: `cd packages/backend && python -m pytest tests/test_homes_persistence.py -v`
Expected: PASS. The JSON-based `persistence_homes.py` hasn't changed yet, so this only confirms the rewritten test file itself is valid Python with correct assertions; the real regression check that these behaviors survive the SQL conversion is in Step 6.

- [ ] **Step 4: Rewrite persistence_homes.py**

Replace the full contents of `packages/backend/src/myhome/persistence_homes.py`:

```python
# packages/backend/src/myhome/persistence_homes.py
from __future__ import annotations

import os
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import get_engine
from .demo_data import seed_demo_home
from .ids import InvalidIdError
from .models_homes import (
    Home,
    HomesDocument,
    DEFAULT_EXISTING_MODULES,
    DEFAULT_PROJECT_MODULES,
    DEFAULT_DEMO_MODULES,
)
from .schema import home_modules as home_modules_table, homes as homes_table


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data"))


def _home_dir(home_id: str) -> Path:
    # Normalize lexically (no filesystem access -- Path.resolve() follows
    # symlinks and touches disk, which CodeQL's own path-injection sink set
    # flags even before any check runs) then verify containment within
    # homes_root. This is CodeQL's own recommended py/path-injection
    # sanitizer shape: os.path.normpath + startswith against a safe root.
    # Still needed here for the home's kb/ and *-attachments/ directories,
    # which remain plain files on disk.
    homes_root = os.path.normpath(os.path.join(str(_data_dir()), "homes"))
    candidate = os.path.normpath(os.path.join(homes_root, home_id))
    if not candidate.startswith(homes_root + os.sep):
        raise InvalidIdError(f"Invalid home_id: {home_id!r}")
    return Path(candidate)


def load_homes() -> HomesDocument:
    engine = get_engine()
    with engine.connect() as conn:
        home_rows = conn.execute(select(homes_table)).mappings().all()
        module_rows = conn.execute(
            select(home_modules_table).order_by(
                home_modules_table.c.home_id, home_modules_table.c.order_index
            )
        ).mappings().all()
    modules_by_home: dict[str, list[str]] = {}
    for r in module_rows:
        modules_by_home.setdefault(r["home_id"], []).append(r["module_id"])
    homes_list = [
        Home(
            id=r["id"],
            name=r["name"],
            type=r["type"],
            enabledModules=modules_by_home.get(r["id"], []),
            createdAt=r["created_at"],
        )
        for r in home_rows
    ]
    return HomesDocument(homes=homes_list)


def save_homes(doc: HomesDocument) -> None:
    # homes.id is a hard FK target from every per-home table (chores,
    # costs, ...), each written by its own save_x() at a different time
    # than this one -- so, unlike other modules' save_x(), this can't
    # blindly truncate-and-reinsert the whole table (that would transiently
    # delete every home's row and cascade-delete all of its data on every
    # single create_home/patch_home call). Instead: upsert every home in
    # the document, and only delete home ids that have genuinely been
    # removed from the document (i.e. delete_home()).
    engine = get_engine()
    with engine.begin() as conn:
        existing_ids = {row[0] for row in conn.execute(select(homes_table.c.id))}
        new_ids = {home.id for home in doc.homes}
        removed_ids = existing_ids - new_ids
        if removed_ids:
            conn.execute(homes_table.delete().where(homes_table.c.id.in_(removed_ids)))
        for home in doc.homes:
            stmt = sqlite_insert(homes_table).values(
                id=home.id, name=home.name, type=home.type, created_at=home.createdAt,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[homes_table.c.id],
                set_={"name": stmt.excluded.name, "type": stmt.excluded.type, "created_at": stmt.excluded.created_at},
            )
            conn.execute(stmt)
            conn.execute(home_modules_table.delete().where(home_modules_table.c.home_id == home.id))
            if home.enabledModules:
                conn.execute(home_modules_table.insert(), [
                    {"home_id": home.id, "module_id": module_id, "order_index": i}
                    for i, module_id in enumerate(home.enabledModules)
                ])


def create_home(name: str, home_type: str) -> Home:
    if home_type == "existing":
        modules = DEFAULT_EXISTING_MODULES[:]
    elif home_type == "demo":
        modules = DEFAULT_DEMO_MODULES[:]
    else:
        modules = DEFAULT_PROJECT_MODULES[:]
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

    if home_type == "demo":
        try:
            seed_demo_home(home.id)
        except Exception:
            doc.homes = [h for h in doc.homes if h.id != home.id]
            save_homes(doc)
            home_dir = _home_dir(home.id)
            if home_dir.exists():
                shutil.rmtree(home_dir)
            raise

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
```

- [ ] **Step 5: Remove the now-dead legacy migration call in main.py**

Edit `packages/backend/src/myhome/main.py`, remove these two lines near the bottom:

```python
from .persistence_homes import migrate_legacy_if_needed
migrate_legacy_if_needed()
```

(Leave the blank line structure around `_first_boot()` intact — just delete these two lines and the file ends after `_first_boot()`.)

- [ ] **Step 6: Run the tests**

Run: `cd packages/backend && python -m pytest tests/test_homes_persistence.py tests/test_homes.py tests/test_main.py -v`
Expected: all PASS.

- [ ] **Step 7: Run the full suite to check for regressions from the main.py change**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: PASS (some later-task tests, e.g. auth first-boot detection, are not yet converted — they still pass because persistence_auth.py hasn't changed yet).

- [ ] **Step 8: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/persistence_homes.py \
        packages/backend/src/myhome/main.py packages/backend/tests/test_homes_persistence.py
git commit -m "feat: move homes registry to SQLite with cascade-safe upsert"
```

---

### Task 3: Users, API tokens, OIDC config

**Files:**
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/persistence_auth.py`
- Modify: `packages/backend/src/myhome/main.py`
- Modify: `packages/backend/tests/test_auth_persistence.py`

**Interfaces:**
- Produces: `schema.users`, `schema.api_tokens`, `schema.oidc_config` tables. `persistence_auth.load_users/save_users/load_tokens/save_tokens/load_oidc_config/save_oidc_config` — same signatures. `initial_admin_password_file()`/`clear_initial_admin_password()` unchanged (still file-based).

- [ ] **Step 1: Add the tables to schema.py**

Append to `packages/backend/src/myhome/schema.py`:

```python
from sqlalchemy import Boolean, Text

users = Table(
    "users", metadata,
    Column("id", String, primary_key=True),
    Column("username", String, nullable=False, unique=True),
    Column("password_hash", String),
    Column("role", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("auth_provider", String, nullable=False),
    Column("oidc_sub", String),
    Column("order_index", Integer, nullable=False),
)

# api_tokens.owner_id intentionally has no ForeignKey: users and tokens are
# saved by different, independently-timed save_x() calls (see the hard-FK
# rule in the plan's Global Constraints), so this stays a plain matched-in-
# Python string column exactly like today.
api_tokens = Table(
    "api_tokens", metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("token_hash", String, nullable=False),
    Column("role", String, nullable=False),
    Column("owner_id", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("last_used_at", String),
    Column("order_index", Integer, nullable=False),
)

oidc_config = Table(
    "oidc_config", metadata,
    Column("id", Integer, primary_key=True),
    Column("enabled", Boolean, nullable=False),
    Column("provider_name", String, nullable=False),
    Column("issuer", String, nullable=False),
    Column("client_id", String, nullable=False),
    Column("client_secret", String, nullable=False),
    Column("default_role", String, nullable=False),
    Column("scopes", Text, nullable=False),
)
```

- [ ] **Step 2: Rewrite the failing tests**

Replace `packages/backend/tests/test_auth_persistence.py`'s file-existence assertions (the rest of the file's round-trip tests are unchanged and stay green throughout). Edit the file: remove `test_save_users_atomic_write` and `test_save_oidc_config_atomic_write` (they assert on a `.tmp` file, a JSON-only implementation detail with no SQL equivalent — round-trip coverage of the same data already exists in the surrounding tests) and add:

```python
def test_save_and_load_users_preserves_order(data_dir):
    from myhome.models_auth import User, UserDocument
    from myhome.persistence_auth import load_users, save_users
    doc = UserDocument(users=[
        User(id="u1", username="alice", role="admin", created_at="2026-01-01T00:00:00+00:00"),
        User(id="u2", username="bob", role="normal", created_at="2026-01-02T00:00:00+00:00"),
    ])
    save_users(doc)
    loaded = load_users()
    assert [u.username for u in loaded.users] == ["alice", "bob"]
```

(Delete the two atomic-write tests referenced above from the file; keep every other test as-is.)

- [ ] **Step 3: Run to confirm the new test passes against the current JSON implementation, and the deleted tests are gone**

Run: `cd packages/backend && python -m pytest tests/test_auth_persistence.py -v`
Expected: PASS (sanity check before conversion).

- [ ] **Step 4: Rewrite persistence_auth.py**

Replace the full contents of `packages/backend/src/myhome/persistence_auth.py`:

```python
# packages/backend/src/myhome/persistence_auth.py
import json
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import get_engine
from .models_auth import ApiToken, OidcConfig, TokenDocument, User, UserDocument
from .schema import api_tokens as api_tokens_table, oidc_config as oidc_config_table, users as users_table


def initial_admin_password_file() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / ".initial-admin-password"


def clear_initial_admin_password() -> None:
    """Delete the one-time first-boot password file, if present.

    Called on every successful login: the file only exists to hand the
    generated admin password to the operator once, so as soon as *any*
    login succeeds it has served its purpose and should stop existing on
    disk (bounds the plaintext-at-rest window instead of leaving it there
    indefinitely).
    """
    initial_admin_password_file().unlink(missing_ok=True)


def load_users() -> UserDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(select(users_table).order_by(users_table.c.order_index)).mappings().all()
    return UserDocument(users=[
        User(
            id=r["id"], username=r["username"], password_hash=r["password_hash"], role=r["role"],
            created_at=r["created_at"], auth_provider=r["auth_provider"], oidc_sub=r["oidc_sub"],
        )
        for r in rows
    ])


def save_users(doc: UserDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(users_table.delete())
        if doc.users:
            conn.execute(users_table.insert(), [
                {
                    "id": u.id, "order_index": i, "username": u.username, "password_hash": u.password_hash,
                    "role": u.role, "created_at": u.created_at, "auth_provider": u.auth_provider,
                    "oidc_sub": u.oidc_sub,
                }
                for i, u in enumerate(doc.users)
            ])


def load_tokens() -> TokenDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(select(api_tokens_table).order_by(api_tokens_table.c.order_index)).mappings().all()
    return TokenDocument(tokens=[
        ApiToken(
            id=r["id"], name=r["name"], token_hash=r["token_hash"], role=r["role"],
            owner_id=r["owner_id"], created_at=r["created_at"], last_used_at=r["last_used_at"],
        )
        for r in rows
    ])


def save_tokens(doc: TokenDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(api_tokens_table.delete())
        if doc.tokens:
            conn.execute(api_tokens_table.insert(), [
                {
                    "id": t.id, "order_index": i, "name": t.name, "token_hash": t.token_hash,
                    "role": t.role, "owner_id": t.owner_id, "created_at": t.created_at,
                    "last_used_at": t.last_used_at,
                }
                for i, t in enumerate(doc.tokens)
            ])


def load_oidc_config() -> OidcConfig:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(select(oidc_config_table).where(oidc_config_table.c.id == 1)).mappings().first()
    if row is None:
        return OidcConfig()
    return OidcConfig(
        enabled=bool(row["enabled"]), provider_name=row["provider_name"], issuer=row["issuer"],
        client_id=row["client_id"], client_secret=row["client_secret"], default_role=row["default_role"],
        scopes=json.loads(row["scopes"]),
    )


def save_oidc_config(config: OidcConfig) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        stmt = sqlite_insert(oidc_config_table).values(
            id=1, enabled=config.enabled, provider_name=config.provider_name, issuer=config.issuer,
            client_id=config.client_id, client_secret=config.client_secret, default_role=config.default_role,
            scopes=json.dumps(config.scopes),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[oidc_config_table.c.id],
            set_={
                "enabled": stmt.excluded.enabled, "provider_name": stmt.excluded.provider_name,
                "issuer": stmt.excluded.issuer, "client_id": stmt.excluded.client_id,
                "client_secret": stmt.excluded.client_secret, "default_role": stmt.excluded.default_role,
                "scopes": stmt.excluded.scopes,
            },
        )
        conn.execute(stmt)
```

- [ ] **Step 5: Update main.py's first-boot check**

Edit `packages/backend/src/myhome/main.py`, in `_first_boot()`, replace:

```python
    if (data_dir / "users.json").exists():
        return
```

with:

```python
    from .persistence_auth import load_users

    if load_users().users:
        return
```

(Remove the now-unneeded `if not data_dir.exists(): return` guard's comment reference to "CI/test import without fixture" only if it no longer applies — it still does, since `get_engine()` also needs `DATA_DIR` to exist for its `mkdir`; leave that early-return as-is.)

- [ ] **Step 6: Run the tests**

Run: `cd packages/backend && python -m pytest tests/test_auth_persistence.py tests/test_auth.py tests/test_auth_users.py tests/test_auth_roles.py tests/test_auth_tokens.py tests/test_auth_oidc.py tests/test_oidc.py tests/test_main.py -v`
Expected: all PASS.

- [ ] **Step 7: Run the full suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/persistence_auth.py \
        packages/backend/src/myhome/main.py packages/backend/tests/test_auth_persistence.py
git commit -m "feat: move users, api tokens, and oidc config to SQLite"
```

---

### Task 4: MCP config, backup config/state

**Files:**
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/persistence_mcp.py`
- Modify: `packages/backend/src/myhome/persistence_backup.py`
- Modify: `packages/backend/tests/test_mcp_config.py`
- Modify: `packages/backend/tests/test_backup_persistence.py`

**Interfaces:**
- Produces: `schema.mcp_config`, `schema.backup_config`, `schema.backup_state` tables. `persistence_mcp.load_mcp_config/save_mcp_config` and `persistence_backup.load_backup_config/save_backup_config/load_backup_state/save_backup_state` — same signatures. `persistence_backup.py`'s zip/file functions (`create_backup`, `list_backups`, `get_backup_path`, `delete_backup`, `iter_backup_files`) are untouched.

- [ ] **Step 1: Add the tables to schema.py**

Append to `packages/backend/src/myhome/schema.py`:

```python
mcp_config = Table(
    "mcp_config", metadata,
    Column("id", Integer, primary_key=True),
    Column("enabled", Boolean, nullable=False),
)

backup_config = Table(
    "backup_config", metadata,
    Column("id", Integer, primary_key=True),
    Column("enabled", Boolean, nullable=False),
    Column("frequency", String, nullable=False),
    Column("time", String, nullable=False),
    Column("day_of_week", Integer, nullable=False),
    Column("day_of_month", Integer, nullable=False),
    Column("retention_count", Integer, nullable=False),
)

backup_state = Table(
    "backup_state", metadata,
    Column("id", Integer, primary_key=True),
    Column("last_run_date", String),
)
```

- [ ] **Step 2: Check the existing MCP config test for file-specific assertions**

Run: `cd packages/backend && grep -n "json\|\.exists()" tests/test_mcp_config.py`
Expected: no output, or only unrelated matches — `test_mcp_config.py` tests the route, not file existence, so it likely needs no changes. If it does reference `mcp_config.json` directly, remove that assertion the same way as Step 2 in prior tasks.

- [ ] **Step 3: Update backup persistence tests**

Edit `packages/backend/tests/test_backup_persistence.py`: the config/state round-trip tests (`test_load_backup_config_returns_defaults_when_no_file`, `test_save_and_load_backup_config_round_trips`, `test_load_backup_state_returns_defaults_when_no_file`, `test_save_and_load_backup_state_round_trips`) need no changes — they only call the public functions and assert on returned values. Every other test in that file (`test_create_backup_*`, `test_list_backups_*`, `test_get_backup_path_*`, `test_delete_backup_*`) is about the zip/file logic and is completely unaffected. No edits needed to this file.

- [ ] **Step 4: Rewrite persistence_mcp.py**

Replace the full contents of `packages/backend/src/myhome/persistence_mcp.py`:

```python
# packages/backend/src/myhome/persistence_mcp.py
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import get_engine
from .models_mcp import McpConfig
from .schema import mcp_config as mcp_config_table


def load_mcp_config() -> McpConfig:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(select(mcp_config_table).where(mcp_config_table.c.id == 1)).mappings().first()
    if row is None:
        return McpConfig()
    return McpConfig(enabled=bool(row["enabled"]))


def save_mcp_config(config: McpConfig) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        stmt = sqlite_insert(mcp_config_table).values(id=1, enabled=config.enabled)
        stmt = stmt.on_conflict_do_update(
            index_elements=[mcp_config_table.c.id], set_={"enabled": stmt.excluded.enabled},
        )
        conn.execute(stmt)
```

- [ ] **Step 5: Rewrite the config/state parts of persistence_backup.py**

Edit `packages/backend/src/myhome/persistence_backup.py`. Remove the `import json` at the top if backup config/state were its only JSON users (it still is — `iter_backup_files`/`create_backup` etc. don't use `json`, so remove the import). Add new imports:

```python
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import get_engine
from .schema import backup_config as backup_config_table, backup_state as backup_state_table
```

Remove the `_config_file()` and `_state_file()` helper functions. Replace `load_backup_config`, `save_backup_config`, `load_backup_state`, `save_backup_state` with:

```python
def load_backup_config() -> BackupConfig:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(select(backup_config_table).where(backup_config_table.c.id == 1)).mappings().first()
    if row is None:
        return BackupConfig()
    return BackupConfig(
        enabled=bool(row["enabled"]), frequency=row["frequency"], time=row["time"],
        dayOfWeek=row["day_of_week"], dayOfMonth=row["day_of_month"], retentionCount=row["retention_count"],
    )


def save_backup_config(config: BackupConfig) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        stmt = sqlite_insert(backup_config_table).values(
            id=1, enabled=config.enabled, frequency=config.frequency, time=config.time,
            day_of_week=config.dayOfWeek, day_of_month=config.dayOfMonth, retention_count=config.retentionCount,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[backup_config_table.c.id],
            set_={
                "enabled": stmt.excluded.enabled, "frequency": stmt.excluded.frequency, "time": stmt.excluded.time,
                "day_of_week": stmt.excluded.day_of_week, "day_of_month": stmt.excluded.day_of_month,
                "retention_count": stmt.excluded.retention_count,
            },
        )
        conn.execute(stmt)


def load_backup_state() -> BackupState:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(select(backup_state_table).where(backup_state_table.c.id == 1)).mappings().first()
    if row is None:
        return BackupState()
    return BackupState(lastRunDate=row["last_run_date"])


def save_backup_state(state: BackupState) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        stmt = sqlite_insert(backup_state_table).values(id=1, last_run_date=state.lastRunDate)
        stmt = stmt.on_conflict_do_update(
            index_elements=[backup_state_table.c.id], set_={"last_run_date": stmt.excluded.last_run_date},
        )
        conn.execute(stmt)
```

- [ ] **Step 6: Run the tests**

Run: `cd packages/backend && python -m pytest tests/test_mcp_config.py tests/test_backup_persistence.py tests/test_backup.py tests/test_backup_scheduler.py -v`
Expected: all PASS.

- [ ] **Step 7: Run the full suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/persistence_mcp.py \
        packages/backend/src/myhome/persistence_backup.py
git commit -m "feat: move mcp/backup config and backup state to SQLite"
```

---

### Task 5: Settings (categories, suppliers, notification settings)

**Files:**
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/persistence_settings.py`
- Modify: `packages/backend/tests/test_settings_persistence.py`

**Interfaces:**
- Produces: `schema.cost_categories`, `schema.inventory_categories`, `schema.work_categories`, `schema.suppliers`, `schema.consumable_categories`, `schema.settings` tables. `persistence_settings.load_settings(home_id) -> SettingsDocument`, `save_settings(home_id, doc) -> None` — same signatures.
- Note: `category_id`/`supplier_id` columns added to `cost_entries`/`works`/`consumables` in later tasks stay plain (no hard FK) per the Global Constraints rule — `save_settings()` clears and reinserts these category tables independently of `save_costs()`/`save_works()`/`save_consumables()`, and a hard FK would raise an `IntegrityError` the instant categories are cleared while a cost entry still references one.

- [ ] **Step 1: Add the tables to schema.py**

Append to `packages/backend/src/myhome/schema.py`:

```python
from sqlalchemy import Float

cost_categories = Table(
    "cost_categories", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
    Column("unit", String),
    Column("color", String, nullable=False),
    Column("placement_floor_id", String),
    Column("placement_x", Float),
    Column("placement_y", Float),
)

inventory_categories = Table(
    "inventory_categories", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
)

work_categories = Table(
    "work_categories", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
)

suppliers = Table(
    "suppliers", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
)

consumable_categories = Table(
    "consumable_categories", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
)

settings = Table(
    "settings", metadata,
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("consumable_units", Text, nullable=False),
    Column("notif_enabled", Boolean, nullable=False),
    Column("notif_chores_due_soon_threshold", Float, nullable=False),
    Column("notif_warranty_days_threshold", Integer, nullable=False),
    Column("notif_ha_push_enabled", Boolean, nullable=False),
    Column("notif_ha_notify_service", String),
    Column("notif_ha_push_time", String, nullable=False),
)
```

- [ ] **Step 2: Update the tests**

Edit `packages/backend/tests/test_settings_persistence.py`: remove `test_load_does_not_create_file_when_missing` and `test_save_creates_file` (JSON-file-specific, no SQL equivalent needed — round trip already covers persistence) and `test_save_creates_data_dir_if_missing`. Add order-preservation and full-round-trip coverage:

```python
def test_round_trip_preserves_all_category_lists_and_notifications(tmp_path, monkeypatch):
    from myhome.models_settings import (
        ConsumableCategory, NotificationSettings, Supplier, WorkCategory,
    )
    _setup(tmp_path, monkeypatch)
    doc = SettingsDocument(
        costCategories=[
            CostCategory(id="c1", name="Fuel", emoji="🛢", unit="L", color="#111111"),
            CostCategory(id="c2", name="Water", emoji="💧", unit="m3", color="#222222"),
        ],
        inventoryCategories=[InventoryCategory(id="i1", name="Electronics")],
        workCategories=[WorkCategory(id="w1", name="Plumbing", emoji="🔧")],
        suppliers=[Supplier(id="s1", name="Acme")],
        consumableUnits=["count", "L"],
        consumableCategories=[ConsumableCategory(id="cc1", name="Cleaning", emoji="🧽")],
        notifications=NotificationSettings(
            enabled=False, choresDueSoonThreshold=0.5, warrantyDaysThreshold=45,
            haPushEnabled=True, haNotifyService="notify.mobile_app", haPushTime="09:30",
        ),
    )
    save_settings(HOME_ID, doc)
    loaded = load_settings(HOME_ID)
    assert [c.id for c in loaded.costCategories] == ["c1", "c2"]
    assert loaded.workCategories[0].name == "Plumbing"
    assert loaded.suppliers[0].name == "Acme"
    assert loaded.consumableUnits == ["count", "L"]
    assert loaded.consumableCategories[0].emoji == "🧽"
    assert loaded.notifications.enabled is False
    assert loaded.notifications.haNotifyService == "notify.mobile_app"
    assert loaded.notifications.haPushTime == "09:30"
```

- [ ] **Step 3: Rewrite persistence_settings.py**

Replace the full contents of `packages/backend/src/myhome/persistence_settings.py`:

```python
# packages/backend/src/myhome/persistence_settings.py
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import get_engine
from .models_settings import (
    ConsumableCategory,
    CostCategory,
    CostCategoryPlacement,
    CostCategoryPosition,
    InventoryCategory,
    NotificationSettings,
    SettingsDocument,
    Supplier,
    WorkCategory,
    _default_cost_categories,
    _default_consumable_units,
    _default_inventory_categories,
    _default_work_categories,
)
from .schema import (
    consumable_categories as consumable_categories_table,
    cost_categories as cost_categories_table,
    inventory_categories as inventory_categories_table,
    settings as settings_table,
    suppliers as suppliers_table,
    work_categories as work_categories_table,
)


def load_settings(home_id: str) -> SettingsDocument:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(select(settings_table).where(settings_table.c.home_id == home_id)).mappings().first()
        if row is None:
            return SettingsDocument(
                costCategories=_default_cost_categories(),
                inventoryCategories=_default_inventory_categories(),
                workCategories=_default_work_categories(),
                consumableUnits=_default_consumable_units(),
            )
        cost_rows = conn.execute(
            select(cost_categories_table).where(cost_categories_table.c.home_id == home_id)
            .order_by(cost_categories_table.c.order_index)
        ).mappings().all()
        inv_rows = conn.execute(
            select(inventory_categories_table).where(inventory_categories_table.c.home_id == home_id)
            .order_by(inventory_categories_table.c.order_index)
        ).mappings().all()
        work_rows = conn.execute(
            select(work_categories_table).where(work_categories_table.c.home_id == home_id)
            .order_by(work_categories_table.c.order_index)
        ).mappings().all()
        supplier_rows = conn.execute(
            select(suppliers_table).where(suppliers_table.c.home_id == home_id)
            .order_by(suppliers_table.c.order_index)
        ).mappings().all()
        consumable_cat_rows = conn.execute(
            select(consumable_categories_table).where(consumable_categories_table.c.home_id == home_id)
            .order_by(consumable_categories_table.c.order_index)
        ).mappings().all()

    return SettingsDocument(
        costCategories=[
            CostCategory(
                id=r["id"], name=r["name"], emoji=r["emoji"], unit=r["unit"], color=r["color"],
                placement=(
                    CostCategoryPlacement(
                        floorId=r["placement_floor_id"],
                        position=CostCategoryPosition(x=r["placement_x"], y=r["placement_y"]),
                    )
                    if r["placement_floor_id"] is not None else None
                ),
            )
            for r in cost_rows
        ],
        inventoryCategories=[InventoryCategory(id=r["id"], name=r["name"]) for r in inv_rows],
        workCategories=[WorkCategory(id=r["id"], name=r["name"], emoji=r["emoji"]) for r in work_rows],
        suppliers=[Supplier(id=r["id"], name=r["name"]) for r in supplier_rows],
        consumableUnits=json.loads(row["consumable_units"]) or _default_consumable_units(),
        consumableCategories=[
            ConsumableCategory(id=r["id"], name=r["name"], emoji=r["emoji"]) for r in consumable_cat_rows
        ],
        notifications=NotificationSettings(
            enabled=bool(row["notif_enabled"]),
            choresDueSoonThreshold=row["notif_chores_due_soon_threshold"],
            warrantyDaysThreshold=row["notif_warranty_days_threshold"],
            haPushEnabled=bool(row["notif_ha_push_enabled"]),
            haNotifyService=row["notif_ha_notify_service"],
            haPushTime=row["notif_ha_push_time"],
        ),
    )


def save_settings(home_id: str, doc: SettingsDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        stmt = sqlite_insert(settings_table).values(
            home_id=home_id,
            consumable_units=json.dumps(doc.consumableUnits),
            notif_enabled=doc.notifications.enabled,
            notif_chores_due_soon_threshold=doc.notifications.choresDueSoonThreshold,
            notif_warranty_days_threshold=doc.notifications.warrantyDaysThreshold,
            notif_ha_push_enabled=doc.notifications.haPushEnabled,
            notif_ha_notify_service=doc.notifications.haNotifyService,
            notif_ha_push_time=doc.notifications.haPushTime,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[settings_table.c.home_id],
            set_={
                "consumable_units": stmt.excluded.consumable_units,
                "notif_enabled": stmt.excluded.notif_enabled,
                "notif_chores_due_soon_threshold": stmt.excluded.notif_chores_due_soon_threshold,
                "notif_warranty_days_threshold": stmt.excluded.notif_warranty_days_threshold,
                "notif_ha_push_enabled": stmt.excluded.notif_ha_push_enabled,
                "notif_ha_notify_service": stmt.excluded.notif_ha_notify_service,
                "notif_ha_push_time": stmt.excluded.notif_ha_push_time,
            },
        )
        conn.execute(stmt)

        conn.execute(cost_categories_table.delete().where(cost_categories_table.c.home_id == home_id))
        if doc.costCategories:
            conn.execute(cost_categories_table.insert(), [
                {
                    "id": c.id, "home_id": home_id, "order_index": i, "name": c.name, "emoji": c.emoji,
                    "unit": c.unit, "color": c.color,
                    "placement_floor_id": c.placement.floorId if c.placement else None,
                    "placement_x": c.placement.position.x if c.placement else None,
                    "placement_y": c.placement.position.y if c.placement else None,
                }
                for i, c in enumerate(doc.costCategories)
            ])

        conn.execute(inventory_categories_table.delete().where(inventory_categories_table.c.home_id == home_id))
        if doc.inventoryCategories:
            conn.execute(inventory_categories_table.insert(), [
                {"id": c.id, "home_id": home_id, "order_index": i, "name": c.name}
                for i, c in enumerate(doc.inventoryCategories)
            ])

        conn.execute(work_categories_table.delete().where(work_categories_table.c.home_id == home_id))
        if doc.workCategories:
            conn.execute(work_categories_table.insert(), [
                {"id": c.id, "home_id": home_id, "order_index": i, "name": c.name, "emoji": c.emoji}
                for i, c in enumerate(doc.workCategories)
            ])

        conn.execute(suppliers_table.delete().where(suppliers_table.c.home_id == home_id))
        if doc.suppliers:
            conn.execute(suppliers_table.insert(), [
                {"id": s.id, "home_id": home_id, "order_index": i, "name": s.name}
                for i, s in enumerate(doc.suppliers)
            ])

        conn.execute(consumable_categories_table.delete().where(consumable_categories_table.c.home_id == home_id))
        if doc.consumableCategories:
            conn.execute(consumable_categories_table.insert(), [
                {"id": c.id, "home_id": home_id, "order_index": i, "name": c.name, "emoji": c.emoji}
                for i, c in enumerate(doc.consumableCategories)
            ])
```

- [ ] **Step 4: Run the tests**

Run: `cd packages/backend && python -m pytest tests/test_settings_persistence.py tests/test_settings.py tests/test_mcp_tools_settings.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/persistence_settings.py \
        packages/backend/tests/test_settings_persistence.py
git commit -m "feat: move settings and category lists to SQLite"
```

---

### Task 6: Chores, assignments, completions

**Files:**
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/persistence_chores.py`
- Modify: `packages/backend/tests/test_chore_persistence.py`
- Modify: `packages/backend/tests/test_chores.py` (only if it exercises the frequencyMetadata backfill)

**Interfaces:**
- Produces: `schema.chores`, `schema.chore_assignments`, `schema.chore_completions` tables. `persistence_chores.load_chores(home_id) -> ChoreDocument`, `save_chores(home_id, doc) -> None` — same signatures. Attachment functions (`get_attachment_path`, `save_attachment`, `delete_attachment`, `delete_all_attachments`, `generate_pdf_thumbnail`) and `_home_dir`/`_attachments_dir` are untouched.

- [ ] **Step 1: Add the tables to schema.py**

Append to `packages/backend/src/myhome/schema.py`:

```python
chores = Table(
    "chores", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("donetick_id", Integer),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
    Column("period_days", Float, nullable=False),
    Column("frequency_type", String, nullable=False),
    Column("frequency", Integer, nullable=False),
    Column("frequency_metadata", Text, nullable=False),
    Column("schedule_from_due", Boolean, nullable=False),
    Column("next_due_date", String, nullable=False),
    Column("description", String, nullable=False),
    Column("attachments", Text, nullable=False),
)

chore_assignments = Table(
    "chore_assignments", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("chore_id", String, ForeignKey("chores.id", ondelete="CASCADE"), nullable=False),
    Column("room_id", String),
    Column("position_x", Float),
    Column("position_y", Float),
    Column("next_due_date", String, nullable=False),
)

chore_completions = Table(
    "chore_completions", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("chore_id", String, ForeignKey("chores.id", ondelete="CASCADE"), nullable=False),
    Column("assignment_id", String),
    Column("completed_at", String, nullable=False),
    Column("scheduled_due", String, nullable=False),
    Column("notes", String, nullable=False),
)
```

- [ ] **Step 2: Update the persistence test**

Edit `packages/backend/tests/test_chore_persistence.py`: remove `test_save_creates_file` and `test_save_creates_data_dir_if_missing` (JSON-file-specific). Add:

```python
def test_round_trip_preserves_completions_and_order(tmp_path, monkeypatch):
    from myhome.models_chores import CompletionRecord
    _setup(tmp_path, monkeypatch)
    doc = ChoreDocument(
        chores=[
            Chore(id="c1", name="Sweep", emoji="🧹", periodDays=7, nextDueDate="2027-01-01T00:00:00Z"),
            Chore(id="c2", name="Mop", emoji="🪣", periodDays=14, nextDueDate="2027-01-08T00:00:00Z"),
        ],
        completions=[
            CompletionRecord(id="comp1", choreId="c1", completedAt="2026-12-25T00:00:00Z", scheduledDue="2026-12-24T00:00:00Z"),
        ],
    )
    save_chores(HOME_ID, doc)
    loaded = load_chores(HOME_ID)
    assert [c.id for c in loaded.chores] == ["c1", "c2"]
    assert loaded.completions[0].choreId == "c1"
    assert loaded.completions[0].scheduledDue == "2026-12-24T00:00:00Z"


def test_assignment_without_position_round_trips(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = ChoreDocument(
        chores=[Chore(id="c1", name="Sweep", emoji="🧹", periodDays=7, nextDueDate="2027-01-01T00:00:00Z")],
        assignments=[Assignment(id="a1", choreId="c1")],
    )
    save_chores(HOME_ID, doc)
    loaded = load_chores(HOME_ID)
    assert loaded.assignments[0].position is None
```

- [ ] **Step 3: Confirm no test depends on the frequencyMetadata/nextDueDate load-time backfills being removed**

These two "migrations" in today's `load_chores()` are pure legacy-JSON-compat shims, not live application behavior: `routes/chores.py:153-155` already derives `frequency`/`frequencyMetadata` from `periodDays` at chore-*creation* time (`if data["frequency"] == 0: ...`), and `routes/chores.py:289` already fills a new assignment's `nextDueDate` from the parent chore at assignment-*creation* time (`next_due = body.nextDueDate or chore.nextDueDate`). No test in `tests/test_chores.py` or `tests/test_chore_scheduling.py` writes a raw `chores.json` file to exercise the load-time backfill (confirmed: no `write_text`/`.json` file writes in either file), so no test needs to be removed for this task — the backfills simply aren't reimplemented in Step 4 below.

- [ ] **Step 4: Rewrite persistence_chores.py's load/save**

Edit `packages/backend/src/myhome/persistence_chores.py`. Keep `import json` (used below to serialize `frequency_metadata`/`attachments`). Add:

```python
from sqlalchemy import select

from .db import get_engine
from .models_chores import Assignment, Chore, CompletionRecord, Position
from .schema import (
    chore_assignments as chore_assignments_table,
    chore_completions as chore_completions_table,
    chores as chores_table,
)
```

Also update the existing `from .models_chores import ChoreDocument` line at the top of the file to include the new names: `from .models_chores import Assignment, Chore, ChoreDocument, CompletionRecord, Position` (a single combined import line — remove the duplicate added above and keep just this one).

Replace `_chores_file()`, `load_chores`, and `save_chores` with:

```python
def load_chores(home_id: str) -> ChoreDocument:
    engine = get_engine()
    with engine.connect() as conn:
        chore_rows = conn.execute(
            select(chores_table).where(chores_table.c.home_id == home_id).order_by(chores_table.c.order_index)
        ).mappings().all()
        assignment_rows = conn.execute(
            select(chore_assignments_table).where(chore_assignments_table.c.home_id == home_id)
            .order_by(chore_assignments_table.c.order_index)
        ).mappings().all()
        completion_rows = conn.execute(
            select(chore_completions_table).where(chore_completions_table.c.home_id == home_id)
            .order_by(chore_completions_table.c.order_index)
        ).mappings().all()

    chores = [
        Chore(
            id=r["id"], donetickId=r["donetick_id"], name=r["name"], emoji=r["emoji"],
            periodDays=r["period_days"], frequencyType=r["frequency_type"], frequency=r["frequency"],
            frequencyMetadata=json.loads(r["frequency_metadata"]), scheduleFromDue=bool(r["schedule_from_due"]),
            nextDueDate=r["next_due_date"], description=r["description"], attachments=json.loads(r["attachments"]),
        )
        for r in chore_rows
    ]
    assignments = [
        Assignment(
            id=r["id"], choreId=r["chore_id"], roomId=r["room_id"],
            position=Position(x=r["position_x"], y=r["position_y"]) if r["position_x"] is not None else None,
            nextDueDate=r["next_due_date"],
        )
        for r in assignment_rows
    ]
    completions = [
        CompletionRecord(
            id=r["id"], choreId=r["chore_id"], assignmentId=r["assignment_id"],
            completedAt=r["completed_at"], scheduledDue=r["scheduled_due"], notes=r["notes"],
        )
        for r in completion_rows
    ]
    return ChoreDocument(chores=chores, assignments=assignments, completions=completions)


def save_chores(home_id: str, doc: ChoreDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(chore_completions_table.delete().where(chore_completions_table.c.home_id == home_id))
        conn.execute(chore_assignments_table.delete().where(chore_assignments_table.c.home_id == home_id))
        conn.execute(chores_table.delete().where(chores_table.c.home_id == home_id))
        if doc.chores:
            conn.execute(chores_table.insert(), [
                {
                    "id": c.id, "home_id": home_id, "order_index": i, "donetick_id": c.donetickId,
                    "name": c.name, "emoji": c.emoji, "period_days": c.periodDays,
                    "frequency_type": c.frequencyType, "frequency": c.frequency,
                    "frequency_metadata": json.dumps(c.frequencyMetadata), "schedule_from_due": c.scheduleFromDue,
                    "next_due_date": c.nextDueDate, "description": c.description,
                    "attachments": json.dumps(c.attachments),
                }
                for i, c in enumerate(doc.chores)
            ])
        if doc.assignments:
            conn.execute(chore_assignments_table.insert(), [
                {
                    "id": a.id, "home_id": home_id, "order_index": i, "chore_id": a.choreId, "room_id": a.roomId,
                    "position_x": a.position.x if a.position else None,
                    "position_y": a.position.y if a.position else None,
                    "next_due_date": a.nextDueDate,
                }
                for i, a in enumerate(doc.assignments)
            ])
        if doc.completions:
            conn.execute(chore_completions_table.insert(), [
                {
                    "id": c.id, "home_id": home_id, "order_index": i, "chore_id": c.choreId,
                    "assignment_id": c.assignmentId, "completed_at": c.completedAt,
                    "scheduled_due": c.scheduledDue, "notes": c.notes,
                }
                for i, c in enumerate(doc.completions)
            ])
```

Keep `import json` at the top of the file (it's still used above) and keep every attachment-related function (`_home_dir`, `_attachments_dir`, `get_attachment_path`, `save_attachment`, `delete_attachment`, `delete_all_attachments`, `generate_pdf_thumbnail`) exactly as they are today.

- [ ] **Step 5: Run the tests**

Run: `cd packages/backend && python -m pytest tests/test_chore_persistence.py tests/test_chores.py tests/test_chore_scheduling.py tests/test_mcp_tools_chores.py -v`
Expected: all PASS.

- [ ] **Step 6: Run the full suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/persistence_chores.py \
        packages/backend/tests/test_chore_persistence.py
git commit -m "feat: move chores, assignments, and completions to SQLite"
```

---

### Task 7: Cost entries

**Files:**
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/persistence_costs.py`
- Modify: `packages/backend/tests/test_costs_persistence.py`
- Modify: `packages/backend/tests/test_costs.py` (remove the old-format `supplier` backfill test)

**Interfaces:**
- Produces: `schema.cost_entries` table. `persistence_costs.load_costs(home_id) -> CostsDocument`, `save_costs(home_id, doc) -> None` — same signatures. Attachment functions untouched.

- [ ] **Step 1: Add the table to schema.py**

Append to `packages/backend/src/myhome/schema.py`:

```python
cost_entries = Table(
    "cost_entries", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    # category_id/supplier_id are plain columns, no ForeignKey -- see the
    # hard-FK rule in this plan's Global Constraints (settings' category
    # tables are cleared/reinserted by a different save_x() call).
    Column("category_id", String, nullable=False),
    Column("date", String, nullable=False),
    Column("total_amount", Float, nullable=False),
    Column("quantity", Float),
    Column("unit_price", Float),
    Column("supplier_id", String),
    Column("notes", String, nullable=False),
    Column("room_id", String),
    Column("attachments", Text, nullable=False),
)
```

- [ ] **Step 2: Remove the old-format migration test**

Edit `packages/backend/tests/test_costs.py`: delete the `test_old_supplier_field_loads_with_supplierId_none` test function (it writes a pre-2026-06-21-shaped `costs.json` with a freeform `"supplier"` string field directly to disk via `(tmp_path / "homes" / home_id / "costs.json").write_text(json.dumps(old_data))` and asserts the backend drops it in favor of `supplierId=None` — this exercised loading old JSON, which no longer applies now that SQL is the only storage).

- [ ] **Step 3: Update test_costs_persistence.py**

Edit `packages/backend/tests/test_costs_persistence.py`: remove `test_save_creates_file` and `test_save_creates_data_dir_if_missing`. Add:

```python
def test_round_trip_preserves_order(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = CostsDocument(entries=[
        CostEntry(id="e1", categoryId="cat-fuel", date="2025-01-01", totalAmount=100.0),
        CostEntry(id="e2", categoryId="cat-water", date="2025-02-01", totalAmount=50.0),
    ])
    save_costs(HOME_ID, doc)
    loaded = load_costs(HOME_ID)
    assert [e.id for e in loaded.entries] == ["e1", "e2"]
```

- [ ] **Step 4: Rewrite persistence_costs.py's load/save**

Edit `packages/backend/src/myhome/persistence_costs.py`. Keep `import json` (still used by `attachments` serialization below). Remove the "Migration: entries saved before 2026-06-21..." comment above `load_costs`. Add:

```python
from sqlalchemy import select

from .db import get_engine
from .schema import cost_entries as cost_entries_table
```

Replace `_costs_file()`, `load_costs`, and `save_costs` with:

```python
def load_costs(home_id: str) -> CostsDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(cost_entries_table).where(cost_entries_table.c.home_id == home_id)
            .order_by(cost_entries_table.c.order_index)
        ).mappings().all()
    return CostsDocument(entries=[
        CostEntry(
            id=r["id"], categoryId=r["category_id"], date=r["date"], totalAmount=r["total_amount"],
            quantity=r["quantity"], unitPrice=r["unit_price"], supplierId=r["supplier_id"],
            notes=r["notes"], roomId=r["room_id"], attachments=json.loads(r["attachments"]),
        )
        for r in rows
    ])


def save_costs(home_id: str, doc: CostsDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(cost_entries_table.delete().where(cost_entries_table.c.home_id == home_id))
        if doc.entries:
            conn.execute(cost_entries_table.insert(), [
                {
                    "id": e.id, "home_id": home_id, "order_index": i, "category_id": e.categoryId,
                    "date": e.date, "total_amount": e.totalAmount, "quantity": e.quantity,
                    "unit_price": e.unitPrice, "supplier_id": e.supplierId, "notes": e.notes,
                    "room_id": e.roomId, "attachments": json.dumps(e.attachments),
                }
                for i, e in enumerate(doc.entries)
            ])
```

Keep `import json` at the top (still used above), and keep every attachment function untouched.

- [ ] **Step 5: Run the tests**

Run: `cd packages/backend && python -m pytest tests/test_costs_persistence.py tests/test_costs.py tests/test_mcp_tools_costs.py -v`
Expected: all PASS.

- [ ] **Step 6: Run the full suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/persistence_costs.py \
        packages/backend/tests/test_costs_persistence.py packages/backend/tests/test_costs.py
git commit -m "feat: move cost entries to SQLite"
```

---

### Task 8: Inventory items

**Files:**
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/persistence_inventory.py`
- Modify: `packages/backend/tests/test_inventory_persistence.py`

**Interfaces:**
- Produces: `schema.inventory_items` table. `persistence_inventory.load_inventory(home_id) -> InventoryDocument`, `save_inventory(home_id, doc) -> None` — same signatures. Attachment functions untouched.

- [ ] **Step 1: Add the table to schema.py**

Append to `packages/backend/src/myhome/schema.py`:

```python
inventory_items = Table(
    "inventory_items", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
    Column("category", String, nullable=False),
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

- [ ] **Step 2: Update the test**

Edit `packages/backend/tests/test_inventory_persistence.py`: remove `test_save_creates_file` and any `test_save_creates_data_dir_if_missing`. Add:

```python
def test_item_without_placement_round_trips(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = InventoryDocument(items=[InventoryItem(id="i2", name="Toaster")])
    save_inventory(HOME_ID, doc)
    loaded = load_inventory(HOME_ID)
    assert loaded.items[0].placement is None


def test_round_trip_preserves_order(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = InventoryDocument(items=[
        InventoryItem(id="i1", name="TV"),
        InventoryItem(id="i2", name="Toaster"),
    ])
    save_inventory(HOME_ID, doc)
    loaded = load_inventory(HOME_ID)
    assert [i.id for i in loaded.items] == ["i1", "i2"]
```

- [ ] **Step 3: Rewrite persistence_inventory.py's load/save**

Edit `packages/backend/src/myhome/persistence_inventory.py`. Keep `import json` (still used below). Change the existing `from .models_inventory import InventoryDocument` line to `from .models_inventory import InventoryDocument, InventoryItem, InventoryPlacement, InventoryPosition`, and add:

```python
from sqlalchemy import select

from .db import get_engine
from .schema import inventory_items as inventory_items_table
```

Replace `_inventory_file()`, `load_inventory`, and `save_inventory` with:

```python
def load_inventory(home_id: str) -> InventoryDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(inventory_items_table).where(inventory_items_table.c.home_id == home_id)
            .order_by(inventory_items_table.c.order_index)
        ).mappings().all()
    return InventoryDocument(items=[
        InventoryItem(
            id=r["id"], name=r["name"], emoji=r["emoji"], category=r["category"], brand=r["brand"],
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


def save_inventory(home_id: str, doc: InventoryDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(inventory_items_table.delete().where(inventory_items_table.c.home_id == home_id))
        if doc.items:
            conn.execute(inventory_items_table.insert(), [
                {
                    "id": it.id, "home_id": home_id, "order_index": i, "name": it.name, "emoji": it.emoji,
                    "category": it.category, "brand": it.brand, "model": it.model,
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

- [ ] **Step 4: Run the tests**

Run: `cd packages/backend && python -m pytest tests/test_inventory_persistence.py tests/test_inventory.py tests/test_mcp_tools_inventory.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/persistence_inventory.py \
        packages/backend/tests/test_inventory_persistence.py
git commit -m "feat: move inventory items to SQLite"
```

---

### Task 9: Works

**Files:**
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/persistence_works.py`
- Modify: `packages/backend/tests/test_works_persistence.py`

**Interfaces:**
- Produces: `schema.works` table. `persistence_works.load_works(home_id) -> WorksDocument`, `save_works(home_id, doc) -> None` — same signatures. Attachment functions untouched.

- [ ] **Step 1: Add the table to schema.py**

Append to `packages/backend/src/myhome/schema.py`:

```python
works = Table(
    "works", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("title", String, nullable=False),
    Column("description", String, nullable=False),
    Column("status", String, nullable=False),
    Column("category_id", String),
    Column("date", String, nullable=False),
    Column("total_cost", Float),
    Column("supplier_id", String),
    Column("notes", String, nullable=False),
    Column("attachments", Text, nullable=False),
    Column("placement_floor_id", String),
    Column("placement_x", Float),
    Column("placement_y", Float),
)
```

- [ ] **Step 2: Update the test**

Edit `packages/backend/tests/test_works_persistence.py`: remove `test_file_not_created_on_read` and `test_save_creates_file`. Add:

```python
def test_round_trip_preserves_placement_and_order(tmp_path, monkeypatch):
    from myhome.models_works import WorkPlacement, WorkPosition
    _setup(tmp_path, monkeypatch)
    doc = WorksDocument(works=[
        Work(id="w1", title="Boiler repair", status="done", date="2025-11-10",
             placement=WorkPlacement(floorId="f1", position=WorkPosition(x=1.0, y=2.0))),
        Work(id="w2", title="Roof check", status="planned", date="2025-12-01"),
    ])
    save_works(HOME_ID, doc)
    loaded = load_works(HOME_ID)
    assert [w.id for w in loaded.works] == ["w1", "w2"]
    assert loaded.works[0].placement.position.x == 1.0
    assert loaded.works[1].placement is None
```

- [ ] **Step 3: Rewrite persistence_works.py's load/save**

Edit `packages/backend/src/myhome/persistence_works.py`. Change the existing `from .models_works import WorksDocument` line to `from .models_works import Work, WorkPlacement, WorkPosition, WorksDocument`, and add:

```python
from sqlalchemy import select

from .db import get_engine
from .schema import works as works_table
```

Replace `_works_file()`, `load_works`, and `save_works` with:

```python
def load_works(home_id: str) -> WorksDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(works_table).where(works_table.c.home_id == home_id).order_by(works_table.c.order_index)
        ).mappings().all()
    return WorksDocument(works=[
        Work(
            id=r["id"], title=r["title"], description=r["description"], status=r["status"],
            categoryId=r["category_id"], date=r["date"], totalCost=r["total_cost"],
            supplierId=r["supplier_id"], notes=r["notes"], attachments=json.loads(r["attachments"]),
            placement=(
                WorkPlacement(floorId=r["placement_floor_id"], position=WorkPosition(x=r["placement_x"], y=r["placement_y"]))
                if r["placement_floor_id"] is not None else None
            ),
        )
        for r in rows
    ])


def save_works(home_id: str, doc: WorksDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(works_table.delete().where(works_table.c.home_id == home_id))
        if doc.works:
            conn.execute(works_table.insert(), [
                {
                    "id": w.id, "home_id": home_id, "order_index": i, "title": w.title,
                    "description": w.description, "status": w.status, "category_id": w.categoryId,
                    "date": w.date, "total_cost": w.totalCost, "supplier_id": w.supplierId,
                    "notes": w.notes, "attachments": json.dumps(w.attachments),
                    "placement_floor_id": w.placement.floorId if w.placement else None,
                    "placement_x": w.placement.position.x if w.placement else None,
                    "placement_y": w.placement.position.y if w.placement else None,
                }
                for i, w in enumerate(doc.works)
            ])
```

Keep `import json` at the top of the file.

- [ ] **Step 4: Run the tests**

Run: `cd packages/backend && python -m pytest tests/test_works_persistence.py tests/test_works.py tests/test_mcp_tools_works.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/persistence_works.py \
        packages/backend/tests/test_works_persistence.py
git commit -m "feat: move works to SQLite"
```

---

### Task 10: Consumables and transactions

**Files:**
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/persistence_consumables.py`
- Modify: `packages/backend/tests/test_consumables_persistence.py`

**Interfaces:**
- Produces: `schema.consumables`, `schema.consumable_transactions` tables. `persistence_consumables.load_consumables(home_id) -> ConsumableDocument`, `save_consumables(home_id, doc) -> None` — same signatures.

- [ ] **Step 1: Add the tables to schema.py**

Append to `packages/backend/src/myhome/schema.py`:

```python
consumables = Table(
    "consumables", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("emoji", String, nullable=False),
    Column("unit", String, nullable=False),
    Column("quantity", Float, nullable=False),
    Column("min_quantity", Float, nullable=False),
    Column("category_id", String),
    Column("description", String, nullable=False),
    Column("placement_floor_id", String),
    Column("placement_room_id", String),
    Column("placement_x", Float),
    Column("placement_y", Float),
)

consumable_transactions = Table(
    "consumable_transactions", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("order_index", Integer, nullable=False),
    Column("consumable_id", String, ForeignKey("consumables.id", ondelete="CASCADE"), nullable=False),
    Column("delta", Float, nullable=False),
    Column("quantity_after", Float, nullable=False),
    Column("note", String, nullable=False),
    Column("timestamp", String, nullable=False),
)
```

- [ ] **Step 2: Update the test**

Edit `packages/backend/tests/test_consumables_persistence.py`: remove `test_save_creates_file` and `test_save_creates_data_dir_if_missing`. Add:

```python
def test_round_trip_preserves_order(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = ConsumableDocument(consumables=[
        Consumable(id="c1", name="Batteries"),
        Consumable(id="c2", name="Soap"),
    ])
    save_consumables(HOME_ID, doc)
    loaded = load_consumables(HOME_ID)
    assert [c.id for c in loaded.consumables] == ["c1", "c2"]
```

- [ ] **Step 3: Rewrite persistence_consumables.py's load/save**

Replace the full contents of `packages/backend/src/myhome/persistence_consumables.py`:

```python
# packages/backend/src/myhome/persistence_consumables.py
from __future__ import annotations

from sqlalchemy import select

from .db import get_engine
from .models_consumables import (
    Consumable,
    ConsumableDocument,
    ConsumablePlacement,
    ConsumablePosition,
    ConsumableTransaction,
)
from .schema import consumable_transactions as consumable_transactions_table, consumables as consumables_table


def load_consumables(home_id: str) -> ConsumableDocument:
    engine = get_engine()
    with engine.connect() as conn:
        consumable_rows = conn.execute(
            select(consumables_table).where(consumables_table.c.home_id == home_id)
            .order_by(consumables_table.c.order_index)
        ).mappings().all()
        transaction_rows = conn.execute(
            select(consumable_transactions_table).where(consumable_transactions_table.c.home_id == home_id)
            .order_by(consumable_transactions_table.c.order_index)
        ).mappings().all()

    consumables = [
        Consumable(
            id=r["id"], name=r["name"], emoji=r["emoji"], unit=r["unit"], quantity=r["quantity"],
            minQuantity=r["min_quantity"], categoryId=r["category_id"], description=r["description"],
            placement=(
                ConsumablePlacement(
                    floorId=r["placement_floor_id"], roomId=r["placement_room_id"],
                    position=ConsumablePosition(x=r["placement_x"], y=r["placement_y"]),
                )
                if r["placement_floor_id"] is not None else None
            ),
        )
        for r in consumable_rows
    ]
    transactions = [
        ConsumableTransaction(
            id=r["id"], consumableId=r["consumable_id"], delta=r["delta"],
            quantityAfter=r["quantity_after"], note=r["note"], timestamp=r["timestamp"],
        )
        for r in transaction_rows
    ]
    return ConsumableDocument(consumables=consumables, transactions=transactions)


def save_consumables(home_id: str, doc: ConsumableDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(consumable_transactions_table.delete().where(consumable_transactions_table.c.home_id == home_id))
        conn.execute(consumables_table.delete().where(consumables_table.c.home_id == home_id))
        if doc.consumables:
            conn.execute(consumables_table.insert(), [
                {
                    "id": c.id, "home_id": home_id, "order_index": i, "name": c.name, "emoji": c.emoji,
                    "unit": c.unit, "quantity": c.quantity, "min_quantity": c.minQuantity,
                    "category_id": c.categoryId, "description": c.description,
                    "placement_floor_id": c.placement.floorId if c.placement else None,
                    "placement_room_id": c.placement.roomId if c.placement else None,
                    "placement_x": c.placement.position.x if c.placement else None,
                    "placement_y": c.placement.position.y if c.placement else None,
                }
                for i, c in enumerate(doc.consumables)
            ])
        if doc.transactions:
            conn.execute(consumable_transactions_table.insert(), [
                {
                    "id": t.id, "home_id": home_id, "order_index": i, "consumable_id": t.consumableId,
                    "delta": t.delta, "quantity_after": t.quantityAfter, "note": t.note, "timestamp": t.timestamp,
                }
                for i, t in enumerate(doc.transactions)
            ])
```

- [ ] **Step 4: Run the tests**

Run: `cd packages/backend && python -m pytest tests/test_consumables_persistence.py tests/test_consumables.py tests/test_mcp_tools_consumables.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/persistence_consumables.py \
        packages/backend/tests/test_consumables_persistence.py
git commit -m "feat: move consumables and transactions to SQLite"
```

---

### Task 11: Activity log

**Files:**
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/persistence_activity.py`
- Modify: `packages/backend/tests/test_activity_persistence.py`

**Interfaces:**
- Produces: `schema.activity_log_entries` table (indexed on `home_id`+`timestamp`, no `order_index` — see Global Constraints). `persistence_activity.load_activity_log(home_id) -> ActivityLogDocument`, `save_activity_log(home_id, doc) -> None`, `log_activity(...) -> None`, `describe(entry) -> str` — same signatures.

- [ ] **Step 1: Add the table to schema.py**

Append to `packages/backend/src/myhome/schema.py`:

```python
from sqlalchemy import Index

activity_log_entries = Table(
    "activity_log_entries", metadata,
    Column("id", String, primary_key=True),
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
    Column("timestamp", String, nullable=False),
    Column("user_id", String, nullable=False),
    Column("username", String, nullable=False),
    Column("module", String, nullable=False),
    Column("action", String, nullable=False),
    Column("entity_label", String, nullable=False),
    Column("ref_id", String),
    Index("ix_activity_log_home_timestamp", "home_id", "timestamp"),
)
```

- [ ] **Step 2: Run the existing test file unchanged first**

Run: `cd packages/backend && python -m pytest tests/test_activity_persistence.py -v`
Expected: PASS against the current JSON implementation (no test file changes are needed for this module — none of its tests assert on file existence).

- [ ] **Step 3: Rewrite persistence_activity.py's load/save**

Edit `packages/backend/src/myhome/persistence_activity.py`. At the top of the file, remove these four now-unused imports entirely: `import json`, `import os`, `from pathlib import Path`, `from .ids import InvalidIdError` (all four were only used by `_data_dir()`/`_home_dir()`/`_activity_file()`, which are removed below). Keep `import uuid` and `from datetime import datetime, timedelta, timezone` (still used by `log_activity`). Add:

```python
from sqlalchemy import select

from .db import get_engine
from .schema import activity_log_entries as activity_log_entries_table
```

Replace `_home_dir()`, `_activity_file()`, `load_activity_log`, and `save_activity_log` with:

```python
def load_activity_log(home_id: str) -> ActivityLogDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(activity_log_entries_table).where(activity_log_entries_table.c.home_id == home_id)
            .order_by(activity_log_entries_table.c.timestamp)
        ).mappings().all()
    return ActivityLogDocument(entries=[
        ActivityEntry(
            id=r["id"], timestamp=r["timestamp"], userId=r["user_id"], username=r["username"],
            module=r["module"], action=r["action"], entityLabel=r["entity_label"], refId=r["ref_id"],
        )
        for r in rows
    ])


def save_activity_log(home_id: str, doc: ActivityLogDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(activity_log_entries_table.delete().where(activity_log_entries_table.c.home_id == home_id))
        if doc.entries:
            conn.execute(activity_log_entries_table.insert(), [
                {
                    "id": e.id, "home_id": home_id, "timestamp": e.timestamp, "user_id": e.userId,
                    "username": e.username, "module": e.module, "action": e.action,
                    "entity_label": e.entityLabel, "ref_id": e.refId,
                }
                for e in doc.entries
            ])
```

The rest of the file (`_resolve_username`, `log_activity`, `describe`, `RETENTION_DAYS`, `ACTION_VERBS`, `MODULE_NOUNS`) is unchanged.

- [ ] **Step 4: Run the tests**

Run: `cd packages/backend && python -m pytest tests/test_activity_persistence.py tests/test_activity_route.py tests/test_activity_wiring.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/persistence_activity.py
git commit -m "feat: move activity log to SQLite"
```

---

### Task 12: Notification state

**Files:**
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/persistence_notifications.py`
- Modify: `packages/backend/tests/test_notifications_persistence.py`

**Interfaces:**
- Produces: `schema.notification_state` table. `persistence_notifications.load_notification_state(home_id) -> NotificationState`, `save_notification_state(home_id, state) -> None` — same signatures.

- [ ] **Step 1: Add the table to schema.py**

Append to `packages/backend/src/myhome/schema.py`:

```python
notification_state = Table(
    "notification_state", metadata,
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("warranty_notified", Text, nullable=False),
    Column("last_push_digest_date", String),
)
```

- [ ] **Step 2: Run the existing test file unchanged first**

Run: `cd packages/backend && python -m pytest tests/test_notifications_persistence.py -v`
Expected: PASS against the current JSON implementation — no changes needed to this test file, it only calls the public functions.

- [ ] **Step 3: Rewrite persistence_notifications.py**

Replace the full contents of `packages/backend/src/myhome/persistence_notifications.py`:

```python
# packages/backend/src/myhome/persistence_notifications.py
import json

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import get_engine
from .models_notifications import NotificationState
from .schema import notification_state as notification_state_table


def load_notification_state(home_id: str) -> NotificationState:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            select(notification_state_table).where(notification_state_table.c.home_id == home_id)
        ).mappings().first()
    if row is None:
        return NotificationState()
    return NotificationState(
        warrantyNotified=json.loads(row["warranty_notified"]),
        lastPushDigestDate=row["last_push_digest_date"],
    )


def save_notification_state(home_id: str, state: NotificationState) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        stmt = sqlite_insert(notification_state_table).values(
            home_id=home_id, warranty_notified=json.dumps(state.warrantyNotified),
            last_push_digest_date=state.lastPushDigestDate,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[notification_state_table.c.home_id],
            set_={
                "warranty_notified": stmt.excluded.warranty_notified,
                "last_push_digest_date": stmt.excluded.last_push_digest_date,
            },
        )
        conn.execute(stmt)
```

- [ ] **Step 4: Run the tests**

Run: `cd packages/backend && python -m pytest tests/test_notifications_persistence.py tests/test_notifications.py tests/test_notification_scheduler.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/persistence_notifications.py
git commit -m "feat: move notification state to SQLite"
```

---

### Task 13: House (floor-plan) document

**Files:**
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/persistence.py`
- Modify: `packages/backend/tests/test_persistence.py`

**Interfaces:**
- Produces: `schema.house_documents` table (single JSON blob column, per the Task-1-approved carve-out — the floor plan is always read/written whole, never queried piecemeal). `persistence.load_house(home_id) -> HouseDocument | None`, `save_house(home_id, doc) -> None` — same signatures.

- [ ] **Step 1: Add the table to schema.py**

Append to `packages/backend/src/myhome/schema.py`:

```python
house_documents = Table(
    "house_documents", metadata,
    Column("home_id", String, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True),
    Column("doc", Text, nullable=False),
)
```

- [ ] **Step 2: Update the test**

Replace the full contents of `packages/backend/tests/test_persistence.py`:

```python
# packages/backend/tests/test_persistence.py
from myhome.models import Floor, House, HouseDocument
from myhome.persistence import load_house, save_house

HOME_ID = "test-home"


def make_doc() -> HouseDocument:
    return HouseDocument(
        version=1,
        house=House(name="Test", units="m", gridSnap=0.1),
        floors=[Floor(id="f1", name="Ground", order=0, walls=[], openings=[], rooms=[])],
    )


def test_load_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert load_house(HOME_ID) is None


def test_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_house(HOME_ID, make_doc())
    loaded = load_house(HOME_ID)
    assert loaded is not None
    assert loaded.floors[0].id == "f1"
    assert loaded.house.name == "Test"
    assert loaded.version == 1


def test_save_overwrites_existing_document(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_house(HOME_ID, make_doc())
    updated = make_doc()
    updated.house.name = "Renamed"
    save_house(HOME_ID, updated)
    assert load_house(HOME_ID).house.name == "Renamed"
```

Note: the old `test_save_house_rejects_path_traversal_home_id` test is dropped — `home_id` is now a SQL parameter, not a filesystem path component, so the path-injection concern that guard existed for no longer applies to this module (attachments in every *other* persistence module still build filesystem paths from `home_id` and keep their `_home_dir()` guard unchanged).

- [ ] **Step 3: Rewrite persistence.py**

Replace the full contents of `packages/backend/src/myhome/persistence.py`:

```python
# packages/backend/src/myhome/persistence.py
import json

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import get_engine
from .models import HouseDocument
from .schema import house_documents as house_documents_table


def load_house(home_id: str) -> HouseDocument | None:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            select(house_documents_table.c.doc).where(house_documents_table.c.home_id == home_id)
        ).first()
    if row is None:
        return None
    return HouseDocument.model_validate(json.loads(row[0]))


def save_house(home_id: str, doc: HouseDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        stmt = sqlite_insert(house_documents_table).values(home_id=home_id, doc=json.dumps(doc.model_dump()))
        stmt = stmt.on_conflict_do_update(
            index_elements=[house_documents_table.c.home_id], set_={"doc": stmt.excluded.doc},
        )
        conn.execute(stmt)
```

- [ ] **Step 4: Run the tests**

Run: `cd packages/backend && python -m pytest tests/test_persistence.py tests/test_routes.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/schema.py packages/backend/src/myhome/persistence.py \
        packages/backend/tests/test_persistence.py
git commit -m "feat: move house/floor-plan document to SQLite as a JSON blob"
```

---

### Task 14: Full regression pass and cleanup

**Files:**
- Modify: none expected (verification-only), unless Step 2 or 3 finds something to fix.

- [ ] **Step 1: Run the entire backend test suite**

Run: `cd packages/backend && python -m pytest tests/ -q`
Expected: all tests PASS (this now covers Tasks 1–13's combined effect, including cross-module flows like `test_demo_data.py`/`test_demo_content.py` seeding every module for a demo home, and `test_mcp_integration.py` exercising the MCP tools end-to-end).

- [ ] **Step 2: Grep for any remaining references to removed JSON-era code**

Run: `cd packages/backend && grep -rn "migrate_legacy_if_needed\|_LEGACY_FILES\|_LEGACY_ATTACHMENT_DIRS" src/ tests/`
Expected: no output. If anything matches, remove it.

- [ ] **Step 3: Grep for now-orphaned `_xxx_file()` path helpers left over from the JSON era**

Run: `cd packages/backend && grep -rn "_chores_file\|_costs_file\|_inventory_file\|_works_file\|_consumables_file\|_house_file\|_homes_file\|_activity_file\|_state_file\|_users_file\|_tokens_file\|_oidc_config_file\|_mcp_config_file\|_config_file\|_settings_file" src/`
Expected: no output (every task above replaced these helpers along with their `load_x`/`save_x` functions). If anything matches, it's dead code left behind — remove it.

- [ ] **Step 4: Verify the demo-home smoke path works against a real (non-test) DATA_DIR**

Run:
```bash
cd packages/backend && rm -rf /tmp/myhome-plan-verify && mkdir -p /tmp/myhome-plan-verify \
  && DATA_DIR=/tmp/myhome-plan-verify PYTHONPATH=src python -c "
from myhome.persistence_homes import create_home
from myhome.persistence_chores import load_chores
home = create_home('Verify Home', 'demo')
print('home id:', home.id)
print('chores after demo seed:', len(load_chores(home.id).chores))
"
```
Expected: prints a home id and a nonzero chore count, confirming `create_home()` → `seed_demo_home()` → every converted `save_x()` call works end-to-end against a real SQLite file (not just pytest's `tmp_path`). Then verify the file: `ls -la /tmp/myhome-plan-verify/myhome.db` should exist.

- [ ] **Step 5: Clean up the manual verification directory**

Run: `rm -rf /tmp/myhome-plan-verify`

- [ ] **Step 6: Commit only if Steps 2–3 required changes**

```bash
git add -A
git commit -m "chore: remove dead JSON-era persistence helpers"
```

(Skip this commit if Steps 2–3 found nothing to remove.)

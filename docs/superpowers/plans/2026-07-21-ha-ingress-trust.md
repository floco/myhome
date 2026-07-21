# HA Ingress Trust Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users installed as a Home Assistant add-on skip MyHome's own login screen when accessed through HA's Supervisor ingress proxy, by trusting HA's asserted user identity under a strict, structurally-enforced trust boundary.

**Architecture:** A new `ha_ingress.py` module checks three structural conditions (`SUPERVISOR_TOKEN` env var set, request peer IP is Supervisor's fixed `172.30.32.2` address, and HA's `X-Remote-User-*` headers present) and, if satisfied, resolves or provisions a `User` with a new `auth_provider="ha_ingress"` value. `auth_middleware` in `main.py` calls this as a fallback only when normal cookie/token auth fails, then mints the same JWT cookies used everywhere else so every later request is indistinguishable from a normal session.

**Tech Stack:** FastAPI, SQLAlchemy Core (SQLite), Pydantic, pytest + `fastapi.testclient.TestClient`.

## Global Constraints

- Matching HA identity to a MyHome account is by `ha_user_id` only — never by username, and never auto-linked into an existing `local`- or `oidc`-provider account (spec: Data Model section, reusing the PR #45 account-linking-hardening lesson).
- The trust boundary (`SUPERVISOR_TOKEN` set + peer IP `172.30.32.2` + all three `X-Remote-User-*` headers present) is the only gate — no separate add-on config toggle (spec: Architecture > Trust boundary).
- Standalone Docker deployment (no `SUPERVISOR_TOKEN`) must be completely unaffected — every new code path here is a no-op unless all three trust conditions hold (spec: Background, Edge Cases).
- New `ha_ingress` accounts default to `role="normal"`, except the very first one created while `initial_admin_password_file()` still exists, which becomes `role="admin"` and deletes the placeholder local admin (spec: Provisioning & Bootstrap).
- No admin/role status is ever inferred from HA — that lookup path is explicitly out of scope (spec: Out of Scope).

---

## Task 1: Add `ha_user_id` to the `User` model, schema, and migrations

**Files:**
- Modify: `packages/backend/src/myhome/models_auth.py`
- Modify: `packages/backend/src/myhome/schema.py`
- Modify: `packages/backend/src/myhome/migrations.py`
- Modify: `packages/backend/src/myhome/persistence_auth.py`
- Test: `packages/backend/tests/test_migrations.py` (new)
- Test: `packages/backend/tests/test_auth_persistence.py` (add to existing file)

**Interfaces:**
- Produces: `User.ha_user_id: str | None` field; `users` table gets a nullable `ha_user_id` column; `migrations.CURRENT_VERSION == 3`; `load_users()`/`save_users()` round-trip `ha_user_id`.

- [ ] **Step 1: Write the failing migration test**

Create `packages/backend/tests/test_migrations.py`:

```python
from sqlalchemy import create_engine, text

from myhome.migrations import CURRENT_VERSION, run_migrations
from myhome.schema import metadata


def test_run_migrations_adds_ha_user_id_to_pre_existing_users_table(tmp_path):
    # Simulate a DB created before this migration existed: build the users
    # table via raw SQL without the ha_user_id column, seed one row, and
    # stamp schema_version at 2 (the version immediately before this one).
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users ("
            "id VARCHAR PRIMARY KEY, username VARCHAR NOT NULL, password_hash VARCHAR, "
            "role VARCHAR NOT NULL, created_at VARCHAR NOT NULL, auth_provider VARCHAR NOT NULL, "
            "oidc_sub VARCHAR, order_index INTEGER NOT NULL)"
        ))
        conn.execute(text(
            "INSERT INTO users (id, username, password_hash, role, created_at, auth_provider, oidc_sub, order_index) "
            "VALUES ('u1', 'alice', 'hash', 'admin', '2026-01-01T00:00:00+00:00', 'local', NULL, 0)"
        ))
        conn.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
        conn.execute(text("INSERT INTO schema_version (version) VALUES (2)"))

    run_migrations(engine)

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version")).scalar()
        row = conn.execute(text("SELECT id, username, ha_user_id FROM users WHERE id = 'u1'")).mappings().first()

    assert version == CURRENT_VERSION
    assert row["username"] == "alice"
    assert row["ha_user_id"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_migrations.py -v`
Expected: FAIL — `sqlalchemy.exc.OperationalError: no such column: ha_user_id` (the column doesn't exist yet on this raw-SQL-created table, and there's no migration to add it).

- [ ] **Step 3: Add the field, column, and migration**

In `packages/backend/src/myhome/models_auth.py`, update the `User` class:

```python
class User(BaseModel):
    id: str
    username: str
    password_hash: str | None = None
    role: str  # "admin" | "normal" | "ro"
    created_at: str  # ISO-8601
    auth_provider: str = "local"  # "local" | "oidc" | "ha_ingress"
    oidc_sub: str | None = None  # IdP's stable subject identifier, set only for auth_provider="oidc"
    ha_user_id: str | None = None  # HA's X-Remote-User-Id, set only for auth_provider="ha_ingress"
```

In `packages/backend/src/myhome/schema.py`, update the `users` table definition:

```python
users = Table(
    "users", metadata,
    Column("id", String, primary_key=True),
    Column("username", String, nullable=False, unique=True),
    Column("password_hash", String),
    Column("role", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("auth_provider", String, nullable=False),
    Column("oidc_sub", String),
    Column("ha_user_id", String),
    Column("order_index", Integer, nullable=False),
)
```

In `packages/backend/src/myhome/migrations.py`:

```python
CURRENT_VERSION = 3


def _drop_kb_folders_table(conn: Connection) -> None:
    conn.execute(text("DROP TABLE IF EXISTS kb_folders"))


def _add_ha_user_id_column(conn: Connection) -> None:
    conn.execute(text("ALTER TABLE users ADD COLUMN ha_user_id VARCHAR"))


MIGRATIONS: list[tuple[int, Callable[[Connection], None]]] = [
    (2, _drop_kb_folders_table),
    (3, _add_ha_user_id_column),
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_migrations.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing persistence round-trip test**

Add to `packages/backend/tests/test_auth_persistence.py`:

```python
def test_save_and_load_users_roundtrip_preserves_ha_user_id(data_dir):
    doc = UserDocument(users=[
        User(
            id="u1", username="bob-ha", role="normal", created_at="2026-01-01T00:00:00+00:00",
            auth_provider="ha_ingress", ha_user_id="ha-user-abc123",
        )
    ])
    save_users(doc)
    loaded = load_users()
    assert loaded.users[0].auth_provider == "ha_ingress"
    assert loaded.users[0].ha_user_id == "ha-user-abc123"
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd packages/backend && python -m pytest tests/test_auth_persistence.py -v -k ha_user_id`
Expected: FAIL — `load_users()`/`save_users()` don't read/write `ha_user_id` yet, so it round-trips as `None` even though it was saved as `"ha-user-abc123"`.

- [ ] **Step 7: Thread `ha_user_id` through `load_users`/`save_users`**

In `packages/backend/src/myhome/persistence_auth.py`, update `load_users()`:

```python
def load_users() -> UserDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(select(users_table).order_by(users_table.c.order_index)).mappings().all()
    return UserDocument(users=[
        User(
            id=r["id"], username=r["username"], password_hash=r["password_hash"], role=r["role"],
            created_at=r["created_at"], auth_provider=r["auth_provider"], oidc_sub=r["oidc_sub"],
            ha_user_id=r["ha_user_id"],
        )
        for r in rows
    ])
```

And `save_users()`:

```python
def save_users(doc: UserDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(users_table.delete())
        if doc.users:
            conn.execute(users_table.insert(), [
                {
                    "id": u.id, "order_index": i, "username": u.username, "password_hash": u.password_hash,
                    "role": u.role, "created_at": u.created_at, "auth_provider": u.auth_provider,
                    "oidc_sub": u.oidc_sub, "ha_user_id": u.ha_user_id,
                }
                for i, u in enumerate(doc.users)
            ])
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd packages/backend && python -m pytest tests/test_auth_persistence.py tests/test_migrations.py -v`
Expected: PASS (both files)

- [ ] **Step 9: Run the full backend suite to check for regressions**

Run: `cd packages/backend && python -m pytest -q`
Expected: PASS, no failures introduced.

- [ ] **Step 10: Commit**

```bash
git add packages/backend/src/myhome/models_auth.py packages/backend/src/myhome/schema.py \
        packages/backend/src/myhome/migrations.py packages/backend/src/myhome/persistence_auth.py \
        packages/backend/tests/test_migrations.py packages/backend/tests/test_auth_persistence.py
git commit -m "feat(auth): add ha_user_id column for HA ingress identity"
```

---

## Task 2: `ha_ingress.py` — trust boundary check + user resolution/provisioning

**Files:**
- Create: `packages/backend/src/myhome/ha_ingress.py`
- Test: `packages/backend/tests/test_ha_ingress.py` (new)

**Interfaces:**
- Consumes: `User` (`models_auth.py`, from Task 1, now has `ha_user_id`), `load_users`/`save_users`/`initial_admin_password_file` (`persistence_auth.py`).
- Produces: `async def resolve_ha_ingress_user(request: Request) -> tuple[str, str] | None` — returns `(user_id, role)` for genuine, trusted HA ingress traffic (creating a `User` on first sight of a given `ha_user_id`), or `None` if the request isn't trusted ingress traffic at all. This is the exact function Task 3 wires into `auth_middleware`.

- [ ] **Step 1: Write the failing tests for the trust boundary**

Create `packages/backend/tests/test_ha_ingress.py`:

```python
import pytest
from starlette.requests import Request

from myhome.ha_ingress import _ingress_trust_satisfied


def _make_request(headers: dict[str, str], client_host: str = "172.30.32.2") -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (client_host, 12345),
        "method": "GET",
        "path": "/api/homes",
    }
    return Request(scope)


_FULL_HEADERS = {
    "X-Remote-User-Id": "ha-abc123",
    "X-Remote-User-Name": "jane",
    "X-Remote-User-Display-Name": "Jane Doe",
}


def test_trust_fails_without_supervisor_token(monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    request = _make_request(_FULL_HEADERS)
    assert _ingress_trust_satisfied(request) is None


def test_trust_fails_with_wrong_source_ip(monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    request = _make_request(_FULL_HEADERS, client_host="10.0.0.5")
    assert _ingress_trust_satisfied(request) is None


def test_trust_fails_with_missing_header(monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    partial = dict(_FULL_HEADERS)
    del partial["X-Remote-User-Display-Name"]
    request = _make_request(partial)
    assert _ingress_trust_satisfied(request) is None


def test_trust_succeeds_when_all_conditions_hold(monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    request = _make_request(_FULL_HEADERS)
    assert _ingress_trust_satisfied(request) == ("ha-abc123", "jane", "Jane Doe")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_ha_ingress.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.ha_ingress'`

- [ ] **Step 3: Implement the trust boundary check**

Create `packages/backend/src/myhome/ha_ingress.py`:

```python
# packages/backend/src/myhome/ha_ingress.py
"""HA Supervisor ingress trust: silently authenticate a user who reaches
MyHome through Home Assistant's ingress proxy, using the identity Supervisor
asserts. See docs/superpowers/specs/2026-07-21-ha-ingress-trust-design.md.

Supervisor validates the browser's own HA session before ever forwarding to
the add-on, then attaches X-Remote-User-Id/-Name/-Display-Name headers. Per
HA's own guidance, these are only safe to trust if traffic is also confirmed
to originate from Supervisor's fixed internal proxy address -- otherwise
anyone who could reach the container directly could forge them.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone

from fastapi import Request

from .models_auth import User
from .persistence_auth import initial_admin_password_file, load_users, save_users

SUPERVISOR_INGRESS_IP = "172.30.32.2"


def _ingress_trust_satisfied(request: Request) -> tuple[str, str, str] | None:
    """Return (ha_user_id, ha_username, ha_display_name) if this request is
    trustworthy as genuine HA Supervisor ingress traffic, else None."""
    if not os.environ.get("SUPERVISOR_TOKEN"):
        return None
    if request.client is None or request.client.host != SUPERVISOR_INGRESS_IP:
        return None
    ha_user_id = request.headers.get("x-remote-user-id")
    ha_username = request.headers.get("x-remote-user-name")
    ha_display_name = request.headers.get("x-remote-user-display-name")
    if not (ha_user_id and ha_username and ha_display_name):
        return None
    return (ha_user_id, ha_username, ha_display_name)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_ha_ingress.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Write the failing tests for resolution/provisioning**

Append to `packages/backend/tests/test_ha_ingress.py`:

```python
import pytest

from myhome.ha_ingress import resolve_ha_ingress_user
from myhome.models_auth import User, UserDocument
from myhome.persistence_auth import initial_admin_password_file, load_users, save_users


@pytest.fixture()
def ingress_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    return tmp_path


def _headers_for(user_id: str, username: str, display_name: str) -> dict[str, str]:
    return {
        "X-Remote-User-Id": user_id,
        "X-Remote-User-Name": username,
        "X-Remote-User-Display-Name": display_name,
    }


async def test_resolve_returns_none_when_not_trusted(ingress_env, monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    request = _make_request(_headers_for("ha-1", "jane", "Jane Doe"))
    assert await resolve_ha_ingress_user(request) is None


async def test_first_ever_ingress_login_becomes_admin_and_clears_placeholder(ingress_env):
    from myhome.main import _first_boot
    _first_boot()
    assert initial_admin_password_file().exists()

    request = _make_request(_headers_for("ha-1", "jane", "Jane Doe"))
    user_id, role = await resolve_ha_ingress_user(request)

    assert role == "admin"
    assert not initial_admin_password_file().exists()
    doc = load_users()
    assert [u.username for u in doc.users if u.auth_provider == "local" and u.username == "admin"] == []
    created = next(u for u in doc.users if u.id == user_id)
    assert created.auth_provider == "ha_ingress"
    assert created.ha_user_id == "ha-1"
    assert created.username == "jane"


async def test_second_ingress_user_defaults_to_normal(ingress_env):
    from myhome.main import _first_boot
    _first_boot()

    first_request = _make_request(_headers_for("ha-1", "jane", "Jane Doe"))
    await resolve_ha_ingress_user(first_request)

    second_request = _make_request(_headers_for("ha-2", "bob", "Bob Smith"))
    user_id, role = await resolve_ha_ingress_user(second_request)

    assert role == "normal"
    doc = load_users()
    created = next(u for u in doc.users if u.id == user_id)
    assert created.username == "bob"


async def test_repeat_login_resolves_to_same_user_without_duplicating(ingress_env):
    from myhome.main import _first_boot
    _first_boot()

    request = _make_request(_headers_for("ha-1", "jane", "Jane Doe"))
    first_id, _ = await resolve_ha_ingress_user(request)
    second_id, _ = await resolve_ha_ingress_user(request)

    assert first_id == second_id
    doc = load_users()
    assert len([u for u in doc.users if u.ha_user_id == "ha-1"]) == 1


async def test_username_collision_gets_disambiguated(ingress_env):
    save_users(UserDocument(users=[
        User(id="local-1", username="jane", password_hash="hash", role="admin",
             created_at="2026-01-01T00:00:00+00:00", auth_provider="local"),
    ]))
    request = _make_request(_headers_for("ha-1", "jane", "Jane Doe"))
    user_id, role = await resolve_ha_ingress_user(request)

    doc = load_users()
    created = next(u for u in doc.users if u.id == user_id)
    assert created.username == "jane-2"
    assert role == "normal"  # a local admin already exists/was claimed -- not the bootstrap placeholder


async def test_never_matches_existing_local_or_oidc_user_by_username(ingress_env):
    save_users(UserDocument(users=[
        User(id="local-1", username="jane", password_hash="hash", role="admin",
             created_at="2026-01-01T00:00:00+00:00", auth_provider="local"),
    ]))
    request = _make_request(_headers_for("ha-1", "jane", "Jane Doe"))
    user_id, _role = await resolve_ha_ingress_user(request)

    assert user_id != "local-1"
    doc = load_users()
    assert len(doc.users) == 2
```

Note: `_make_request` is the helper already defined earlier in this same test
file (Step 1) — no need to redefine it. No `@pytest.mark.asyncio` marker is
needed on the `async def test_*` functions above: `pyproject.toml` already
sets `asyncio_mode = "auto"`, so pytest-asyncio (already a dependency,
`pyproject.toml:26`) picks up async test functions automatically.

- [ ] **Step 6: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_ha_ingress.py -v`
Expected: FAIL — `ImportError: cannot import name 'resolve_ha_ingress_user'`

- [ ] **Step 7: Implement resolution/provisioning**

Append to `packages/backend/src/myhome/ha_ingress.py`:

```python
def _unique_username(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    suffix = 2
    while f"{base}-{suffix}" in existing:
        suffix += 1
    return f"{base}-{suffix}"


async def resolve_ha_ingress_user(request: Request) -> tuple[str, str] | None:
    """Resolve or provision a MyHome user for genuine HA ingress traffic.

    Returns (user_id, role), or None if this request isn't trusted ingress
    traffic (see _ingress_trust_satisfied). Matching is by ha_user_id only --
    never by username, and never onto an existing local/oidc-provider account
    (same account-takeover-hardening rule as OIDC's oidc_sub matching).
    """
    trust = _ingress_trust_satisfied(request)
    if trust is None:
        return None
    ha_user_id, ha_username, _ha_display_name = trust

    doc = load_users()
    existing = next((u for u in doc.users if u.ha_user_id == ha_user_id), None)
    if existing is not None:
        return (existing.id, existing.role)

    password_file = initial_admin_password_file()
    is_first_ever = password_file.exists()
    role = "admin" if is_first_ever else "normal"

    existing_usernames = {u.username for u in doc.users}
    username = _unique_username(ha_username, existing_usernames)

    new_user = User(
        id=secrets.token_hex(8),
        username=username,
        password_hash=None,
        role=role,
        created_at=datetime.now(timezone.utc).isoformat(),
        auth_provider="ha_ingress",
        ha_user_id=ha_user_id,
    )

    if is_first_ever:
        doc.users = [
            u for u in doc.users
            if not (u.username == "admin" and u.auth_provider == "local")
        ]
        password_file.unlink(missing_ok=True)

    doc.users.append(new_user)
    save_users(doc)
    return (new_user.id, role)
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_ha_ingress.py -v`
Expected: PASS (all tests from Step 1 and Step 5)

- [ ] **Step 9: Run the full backend suite to check for regressions**

Run: `cd packages/backend && python -m pytest -q`
Expected: PASS, no failures introduced.

- [ ] **Step 10: Commit**

```bash
git add packages/backend/src/myhome/ha_ingress.py packages/backend/tests/test_ha_ingress.py
git commit -m "feat(auth): add HA ingress trust resolution and provisioning"
```

---

## Task 3: Share `set_auth_cookies` and wire ingress trust into `auth_middleware`

**Files:**
- Modify: `packages/backend/src/myhome/deps.py`
- Modify: `packages/backend/src/myhome/routes/auth.py`
- Modify: `packages/backend/src/myhome/main.py`
- Test: `packages/backend/tests/test_main.py` (add to existing file)

**Interfaces:**
- Consumes: `resolve_ha_ingress_user` (Task 2, `ha_ingress.py`), `create_access_token`/`create_refresh_token` (`deps.py`, unchanged).
- Produces: `deps.set_auth_cookies(response: Response, user_id: str, role: str) -> None` (moved from `routes/auth.py`'s private `_set_auth_cookies`, now usable by `main.py` too). `auth_middleware` now falls back to ingress trust before rejecting a request with no valid cookie/token.

- [ ] **Step 1: Write the failing end-to-end test**

Add to `packages/backend/tests/test_main.py`:

```python
def test_ingress_trust_silently_authenticates_and_sets_cookies(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    tc = TestClient(app, client=("172.30.32.2", 12345))

    resp = tc.get("/api/auth/me", headers={
        "X-Remote-User-Id": "ha-1",
        "X-Remote-User-Name": "jane",
        "X-Remote-User-Display-Name": "Jane Doe",
    })

    assert resp.status_code == 200
    assert resp.json()["username"] == "jane"
    assert resp.json()["role"] == "admin"  # first-ever ingress login
    assert "myhome_access" in resp.cookies
    assert "myhome_refresh" in resp.cookies


def test_ingress_trust_does_not_apply_without_supervisor_token(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    tc = TestClient(app, client=("172.30.32.2", 12345))

    resp = tc.get("/api/auth/me", headers={
        "X-Remote-User-Id": "ha-1",
        "X-Remote-User-Name": "jane",
        "X-Remote-User-Display-Name": "Jane Doe",
    })

    assert resp.status_code == 401


def test_ingress_trust_does_not_apply_from_wrong_source_ip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    tc = TestClient(app, client=("10.0.0.5", 12345))

    resp = tc.get("/api/auth/me", headers={
        "X-Remote-User-Id": "ha-1",
        "X-Remote-User-Name": "jane",
        "X-Remote-User-Display-Name": "Jane Doe",
    })

    assert resp.status_code == 401


def test_ingress_trust_session_persists_via_cookie_on_next_request(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    tc = TestClient(app, client=("172.30.32.2", 12345))

    first = tc.get("/api/auth/me", headers={
        "X-Remote-User-Id": "ha-1",
        "X-Remote-User-Name": "jane",
        "X-Remote-User-Display-Name": "Jane Doe",
    })
    assert first.status_code == 200

    # No ingress headers this time -- must still work purely off the cookie
    # the first request set.
    second = tc.get("/api/auth/me")
    assert second.status_code == 200
    assert second.json()["username"] == "jane"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_main.py -v -k ingress_trust`
Expected: FAIL — all four return 401 (or error), since `auth_middleware` doesn't yet fall back to ingress trust.

- [ ] **Step 3: Move `_set_auth_cookies` to `deps.py` as a shared, public helper**

In `packages/backend/src/myhome/deps.py`, add near `create_refresh_token`:

```python
def set_auth_cookies(response, user_id: str, role: str) -> None:
    response.set_cookie("myhome_access", create_access_token(user_id, role), httponly=True, samesite="lax")
    response.set_cookie("myhome_refresh", create_refresh_token(user_id), httponly=True, samesite="lax")
```

(`response` is a `starlette.responses.Response`; left untyped here to avoid
adding a new import purely for the annotation, matching this module's
existing style of light typing on FastAPI-adjacent helpers.)

In `packages/backend/src/myhome/routes/auth.py`:
- Delete the local `_set_auth_cookies` function definition (currently at the
  bottom of the file, `_set_auth_cookies(response, user_id, role)`).
- Add `set_auth_cookies` to the existing `from .deps import ...` line at the
  top of the file.
- Replace both call sites (`_set_auth_cookies(response, user.id, user.role)`
  in `login()` and in the OIDC callback handler) with
  `set_auth_cookies(response, user.id, user.role)`.

- [ ] **Step 4: Run the auth test suite to confirm the refactor didn't break anything**

Run: `cd packages/backend && python -m pytest tests/test_auth.py tests/test_auth_oidc.py tests/test_auth_roles.py tests/test_auth_tokens.py tests/test_auth_users.py -v`
Expected: PASS (unchanged behavior, purely a rename/relocation)

- [ ] **Step 5: Wire `resolve_ha_ingress_user` into `auth_middleware`**

In `packages/backend/src/myhome/main.py`:
- Add to the imports: `from .deps import ROLE_ORDER, get_user_from_request, set_auth_cookies` (extends the
  existing `from .deps import ...` line) and `from .ha_ingress import
  resolve_ha_ingress_user`.
- Replace the body of `auth_middleware` (currently `main.py:99-124`) with:

```python
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if path in _EXEMPT_PATHS:
        return await call_next(request)
    if not (path.startswith("/api/") or path.startswith("/mcp")):
        # Static frontend assets (including the SPA shell at "/") are public --
        # every real route is registered under /api/, so this only ever
        # matches static files. The SPA itself decides whether to show the
        # login screen based on 401s from its own /api/auth/me call; it can't
        # do that if the shell/JS bundle never loads in the first place (e.g.
        # a Home Assistant ingress request, which never carries our cookies).
        return await call_next(request)
    user = await get_user_from_request(request)
    newly_ingress_authenticated = False
    if user is None:
        user = await resolve_ha_ingress_user(request)
        if user is not None:
            newly_ingress_authenticated = True
    if user is None:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    user_id, role = user
    if (
        request.method in ("POST", "PUT", "DELETE", "PATCH")
        and not request.url.path.startswith("/api/auth/")
        and not request.url.path.startswith("/mcp")
        and ROLE_ORDER.get(role, -1) < ROLE_ORDER["normal"]
    ):
        return JSONResponse({"detail": "Insufficient permissions"}, status_code=403)
    request.state.user = user
    response = await call_next(request)
    if newly_ingress_authenticated:
        set_auth_cookies(response, user_id, role)
    return response
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_main.py -v -k ingress_trust`
Expected: PASS (all 4 tests)

- [ ] **Step 7: Run the full backend suite to check for regressions**

Run: `cd packages/backend && python -m pytest -q`
Expected: PASS, no failures introduced. Pay particular attention to
`test_non_api_paths_are_not_gated_by_auth_middleware` and
`test_api_paths_still_require_auth` in `test_main.py` — both must still pass
unchanged, since neither request satisfies the ingress trust conditions.

- [ ] **Step 8: Commit**

```bash
git add packages/backend/src/myhome/deps.py packages/backend/src/myhome/routes/auth.py \
        packages/backend/src/myhome/main.py packages/backend/tests/test_main.py
git commit -m "feat(auth): wire HA ingress trust into auth_middleware"
```

---

## Task 4: Manual verification against a real Home Assistant instance

This task has no code changes — it's the manual verification the design
spec calls out as required before merge, since nothing in Tasks 1-3 proves
HA's Supervisor actually sends these headers/IP the way its docs describe.

**Files:** none (manual verification only)

- [ ] **Step 1: Build and install the add-on on a real HA + Supervisor instance**

Follow the existing add-on install process (local add-on repository, per
`addon/` and `README.md`) to get a build of this branch running as an
installed add-on with ingress enabled.

- [ ] **Step 2: Verify first-ever ingress access becomes admin with no login page**

As the HA admin user who installed the add-on, open it via the HA sidebar
panel (not a direct URL). Confirm:
- No MyHome login page is shown.
- The app loads directly, and Settings > Users shows a new user matching
  your HA username at role `admin`.
- `/data/.initial-admin-password` no longer exists inside the container (or
  the placeholder `admin` local user is gone from Settings > Users).

- [ ] **Step 3: Verify a second HA user gets a normal-role account**

Log into HA as a second, non-admin HA user (create one in HA if needed) and
open the add-on via the sidebar. Confirm a second MyHome user is
auto-created at role `normal`, and the first (admin) session is unaffected.

- [ ] **Step 4: Verify direct/non-ingress access still requires real login**

From another container on the same Docker network (or via
`docker exec`/`curl` from the host, hitting the container's internal IP
directly rather than through Supervisor's ingress path), confirm the app
still returns 401 and requires local password or OIDC login — ingress trust
must not fire for this traffic.

- [ ] **Step 5: Record the outcome**

If all three checks pass, note this in the PR description (see
`superpowers:finishing-a-development-branch`) as manual verification
evidence. If anything deviates from the design spec's assumptions about HA's
header/IP behavior, stop and re-open the design spec rather than patching
around an incorrect assumption.

---

## Self-Review Notes

- **Spec coverage:** Trust boundary (Task 2 Step 3) ✓, identity resolution +
  provisioning + first-login admin promotion + placeholder cleanup (Task 2
  Step 7) ✓, migration for `ha_user_id` (Task 1) ✓, session issuance via
  existing cookie mechanism (Task 3) ✓, manual verification requirement
  (Task 4) ✓. Out-of-scope items (role sync, config toggle, admin-status
  lookup) are correctly not represented by any task.
- **Type consistency:** `resolve_ha_ingress_user(request: Request) ->
  tuple[str, str] | None` (Task 2) matches its call site in `auth_middleware`
  (Task 3) exactly, mirroring `get_user_from_request`'s existing signature.
  `set_auth_cookies(response, user_id: str, role: str) -> None` (Task 3,
  `deps.py`) matches both its `routes/auth.py` call sites and its new
  `main.py` call site.
- **No placeholders:** every step above has literal, runnable code and exact
  file paths; nothing deferred to "add appropriate handling."

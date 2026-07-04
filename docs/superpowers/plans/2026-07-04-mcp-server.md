# MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an in-process MCP (Model Context Protocol) server to the MyHome backend, exposing chores/inventory/consumables/costs/works/KB/homes as MCP tools, gated by an admin-only Settings toggle, reusing the existing API token auth model.

**Architecture:** The `mcp` Python SDK's `FastMCP` is mounted as a Starlette sub-app at `/mcp` inside the existing FastAPI app. Every MCP tool is a thin wrapper: it extracts the caller's `(user_id, role)` from the raw HTTP request (same Bearer-token/JWT-cookie auth already used by the REST API), enforces a minimum role, then calls a plain, directly-testable "impl" function that talks to the same persistence layer the REST routes use. A new global `mcp_config.json` flag (toggled via an admin-only `/api/mcp/config` endpoint and a new Settings card) gates whether `/mcp` responds or 404s.

**Tech Stack:** FastAPI, Starlette, the official `mcp` Python SDK (`mcp.server.fastmcp.FastMCP`, Streamable HTTP transport), Pydantic, pytest/pytest-asyncio, httpx (including `httpx.ASGITransport` for in-process protocol tests), Svelte 5 + vitest for the frontend card.

**Reference spec:** `docs/superpowers/specs/2026-07-04-mcp-server-design.md`

---

## Before You Start

All backend commands below assume your shell's cwd is `packages/backend`. All frontend commands assume `packages/editor`. Run `cd packages/backend` / `cd packages/editor` once at the start of your session (or prefix each command) — the plan won't repeat it.

The `mcp` Python SDK (v1.28+) is used throughout. Two non-obvious facts about it, verified against the installed package source, that later tasks depend on:

1. **Lifespan is not automatic.** Mounting `mcp.streamable_http_app()` into FastAPI via `app.mount("/mcp", ...)` does *not* start the MCP session manager's background task group by itself — Starlette's router only invokes the *top-level* app's own lifespan for ASGI `"lifespan"` scope events; it never forwards them into mounted sub-apps. You must explicitly enter `mcp.session_manager.run()` inside the FastAPI app's own `lifespan`.
2. **The raw HTTP request is reachable from a tool.** A `@mcp.tool()` function that takes a `ctx: Context` parameter can read `ctx.request_context.request` — this is a real Starlette `Request` built from the same ASGI scope as the incoming HTTP call, so it carries the same headers/cookies the REST API's `get_user_from_request()` already knows how to parse.

---

## Task 1: Add the `mcp` dependency

**Files:**
- Modify: `packages/backend/pyproject.toml`

- [ ] **Step 1: Add the dependency**

In `packages/backend/pyproject.toml`, add `"mcp>=1.28"` to the `dependencies` list (after `"bcrypt>=4.0,<5"`):

```toml
dependencies = [
    "fastapi>=0.115",
    "pydantic>=2.0",
    "uvicorn[standard]>=0.34",
    "httpx>=0.27",
    "python-multipart>=0.0.9",
    "pymupdf>=1.24",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "bcrypt>=4.0,<5",
    "mcp>=1.28",
]
```

- [ ] **Step 2: Install it into the project's environment**

Run: `pip install -e .` (or however this project's dev environment installs backend deps — check for a venv under `packages/backend` first)
Expected: `mcp` and its transitive deps (`anyio`, `httpx-sse`, `pydantic-settings`, `sse-starlette`, `starlette`, etc.) install without errors.

- [ ] **Step 3: Verify the import works**

Run: `python -c "from mcp.server.fastmcp import FastMCP, Context; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add packages/backend/pyproject.toml
git commit -m "build: add mcp python sdk dependency"
```

---

## Task 2: MCP on/off config — model, persistence, admin-only route

This is the Settings toggle's backing store: a single global `{"enabled": bool}` file, following the exact same pattern as `users.json`/`tokens.json`.

**Files:**
- Create: `packages/backend/src/myhome/models_mcp.py`
- Create: `packages/backend/src/myhome/persistence_mcp.py`
- Create: `packages/backend/src/myhome/routes/mcp_config.py`
- Modify: `packages/backend/src/myhome/main.py`
- Test: `packages/backend/tests/test_mcp_config.py`

- [ ] **Step 1: Write the model**

Create `packages/backend/src/myhome/models_mcp.py`:

```python
from __future__ import annotations
from pydantic import BaseModel


class McpConfig(BaseModel):
    enabled: bool = False
```

- [ ] **Step 2: Write persistence**

Create `packages/backend/src/myhome/persistence_mcp.py`:

```python
import json
import os
from pathlib import Path

from .models_mcp import McpConfig


def _mcp_config_file() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "mcp_config.json"


def load_mcp_config() -> McpConfig:
    path = _mcp_config_file()
    if not path.exists():
        return McpConfig()
    with path.open() as f:
        return McpConfig.model_validate(json.load(f))


def save_mcp_config(config: McpConfig) -> None:
    path = _mcp_config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(config.model_dump(), f, indent=2)
    tmp.replace(path)
```

- [ ] **Step 3: Write the failing tests**

Create `packages/backend/tests/test_mcp_config.py`:

```python
def test_get_mcp_config_defaults_disabled(client):
    resp = client.get("/api/mcp/config")
    assert resp.status_code == 200
    assert resp.json() == {"enabled": False}


def test_put_mcp_config_enables(client):
    resp = client.put("/api/mcp/config", json={"enabled": True})
    assert resp.status_code == 200
    assert resp.json() == {"enabled": True}
    assert client.get("/api/mcp/config").json() == {"enabled": True}


def test_mcp_config_forbidden_for_non_admin(ro_client):
    resp = ro_client.get("/api/mcp/config")
    assert resp.status_code == 403
    resp2 = ro_client.put("/api/mcp/config", json={"enabled": True})
    assert resp2.status_code == 403
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `pytest tests/test_mcp_config.py -v`
Expected: FAIL — `404 Not Found` (no `/api/mcp/config` route registered yet)

- [ ] **Step 5: Write the route**

Create `packages/backend/src/myhome/routes/mcp_config.py`:

```python
from fastapi import APIRouter

from ..deps import require_auth
from ..models_mcp import McpConfig
from ..persistence_mcp import load_mcp_config, save_mcp_config

router = APIRouter()


@router.get("/api/mcp/config", response_model=McpConfig)
def get_mcp_config(current_user: tuple[str, str] = require_auth("admin")) -> McpConfig:
    return load_mcp_config()


@router.put("/api/mcp/config", response_model=McpConfig)
def put_mcp_config(body: McpConfig, current_user: tuple[str, str] = require_auth("admin")) -> McpConfig:
    save_mcp_config(body)
    return body
```

- [ ] **Step 6: Register the router**

In `packages/backend/src/myhome/main.py`, update the routes import (line 11) and add the include:

```python
from .routes import auth, backup, chores, consumables, costs, ha, homes, house, inventory, kb, mcp_config, settings, svg, works
```

Add, alongside the other `app.include_router(...)` calls (after `app.include_router(consumables.router)`):

```python
app.include_router(mcp_config.router)
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `pytest tests/test_mcp_config.py -v`
Expected: PASS (3 passed)

- [ ] **Step 8: Run the full backend suite to check for regressions**

Run: `pytest -q`
Expected: all existing tests still pass (config file is additive, no existing route touched)

- [ ] **Step 9: Commit**

```bash
git add packages/backend/src/myhome/models_mcp.py packages/backend/src/myhome/persistence_mcp.py \
        packages/backend/src/myhome/routes/mcp_config.py packages/backend/src/myhome/main.py \
        packages/backend/tests/test_mcp_config.py
git commit -m "feat: add admin-gated MCP on/off config endpoint"
```

---

## Task 3: Extract chore due-date scheduling into a shared module

The `complete_chore` MCP tool (Task 7) needs the exact same "advance the due date" logic the REST `POST /chores/{id}/complete` route already has, so behavior can't drift between the two entry points. Today that logic (`_next_due_from_schedule` and its private helpers) lives inline in `routes/chores.py`. This task moves it to its own module so both the route and the MCP tool import the same code — a small, targeted refactor serving the tool we're about to build, not a general cleanup.

**Files:**
- Create: `packages/backend/src/myhome/chore_scheduling.py`
- Modify: `packages/backend/src/myhome/routes/chores.py`
- Test: `packages/backend/tests/test_chore_scheduling.py`

- [ ] **Step 1: Create the shared module**

Create `packages/backend/src/myhome/chore_scheduling.py` with the logic moved verbatim (only the function/dict names lose their leading underscore, since they're now a public shared API) from `packages/backend/src/myhome/routes/chores.py` lines 75–144:

```python
"""Chore due-date advancement, shared by the REST /complete routes and the MCP complete_chore tool."""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta

from .models_chores import Chore

WEEKDAY_NAMES: dict[str, int] = {
    "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4,
    "friday": 5, "saturday": 6, "sunday": 7,
    "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7,
}


def add_months(dt: datetime, months: int) -> datetime:
    total = dt.month - 1 + months
    year = dt.year + total // 12
    month = total % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def add_years(dt: datetime, years: int) -> datetime:
    try:
        return dt.replace(year=dt.year + years)
    except ValueError:
        return dt.replace(year=dt.year + years, month=3, day=1)


def to_weekday_num(d: object) -> int:
    """Convert a Donetick weekday value (int or name string) to a 1-based int."""
    if isinstance(d, str):
        name = d.lower().strip()
        if name in WEEKDAY_NAMES:
            return WEEKDAY_NAMES[name]
        return int(name)
    return int(d)


def next_due_from_schedule(chore: Chore, from_dt: datetime) -> datetime:
    ft = chore.frequencyType
    freq = chore.frequency
    meta: dict = chore.frequencyMetadata or {}
    unit = meta.get("unit", "days")
    if ft == "day_of_the_month":
        allowed_months: set[int] = set(meta.get("months") or range(1, 13))
        next_m = add_months(from_dt.replace(day=1), 1)
        for _ in range(12):
            if next_m.month in allowed_months:
                break
            next_m = add_months(next_m, 1)
        day = min(freq, calendar.monthrange(next_m.year, next_m.month)[1])
        return next_m.replace(day=day)
    if ft == "days_of_the_week":
        days = sorted((to_weekday_num(d) - 1) % 7 for d in (meta.get("days") or []))
        if not days:
            return from_dt + timedelta(weeks=1)
        wd = from_dt.weekday()
        for d in days:
            if d > wd:
                return from_dt + timedelta(days=d - wd)
        return from_dt + timedelta(days=7 - wd + days[0])
    if ft == "weekly":
        return from_dt + timedelta(weeks=freq)
    if ft in ("monthly", "month"):
        return add_months(from_dt, freq)
    if ft in ("yearly", "year"):
        return add_years(from_dt, freq)
    if ft == "interval":
        if unit == "years":
            return add_years(from_dt, freq)
        if unit == "months":
            return add_months(from_dt, freq)
        if unit == "weeks":
            return from_dt + timedelta(weeks=freq)
        return from_dt + timedelta(days=freq)
    return from_dt + timedelta(days=chore.periodDays)
```

- [ ] **Step 2: Update `routes/chores.py` to use the shared module**

In `packages/backend/src/myhome/routes/chores.py`:

1. Delete the now-duplicated definitions: `_WEEKDAY_NAMES` (lines 90–94), `_to_weekday_num` (lines 97–104), `_next_due_from_schedule` (lines 107–144), `_add_months` (lines 75–80), `_add_years` (lines 83–87). Leave `UNIT_DAYS` and `_period_days` in place (still used by the Donetick import, out of scope here).
2. Add the import near the top, alongside the other `..`-relative imports:

```python
from ..chore_scheduling import next_due_from_schedule
```

3. Replace both call sites of the old name with the new one (in `complete_chore` and `complete_assignment`):

```python
next_due = _next_due_from_schedule(chore, from_dt)
```

becomes

```python
next_due = next_due_from_schedule(chore, from_dt)
```

(There are two occurrences — one in `complete_chore`, one in `complete_assignment`.)

- [ ] **Step 3: Run the existing chore tests to confirm no regression**

Run: `pytest tests/test_chores.py tests/test_chore_persistence.py -v`
Expected: all pass, unchanged from before the refactor

- [ ] **Step 4: Write a focused unit test for the extracted module**

Create `packages/backend/tests/test_chore_scheduling.py`:

```python
from datetime import datetime, timezone

from myhome.chore_scheduling import next_due_from_schedule
from myhome.models_chores import Chore


def _chore(**overrides) -> Chore:
    base = dict(
        id="c1", name="Test", emoji="🧹", periodDays=7.0,
        frequencyType="interval", frequency=7, frequencyMetadata={"unit": "days"},
        nextDueDate="2026-07-04T00:00:00Z",
    )
    base.update(overrides)
    return Chore(**base)


def test_interval_days_advances_by_frequency():
    chore = _chore(frequencyType="interval", frequency=3, frequencyMetadata={"unit": "days"})
    from_dt = datetime(2026, 7, 4, tzinfo=timezone.utc)
    result = next_due_from_schedule(chore, from_dt)
    assert result == datetime(2026, 7, 7, tzinfo=timezone.utc)


def test_weekly_advances_by_weeks():
    chore = _chore(frequencyType="weekly", frequency=2)
    from_dt = datetime(2026, 7, 4, tzinfo=timezone.utc)
    result = next_due_from_schedule(chore, from_dt)
    assert result == datetime(2026, 7, 18, tzinfo=timezone.utc)


def test_monthly_advances_by_months():
    chore = _chore(frequencyType="monthly", frequency=1)
    from_dt = datetime(2026, 1, 31, tzinfo=timezone.utc)
    result = next_due_from_schedule(chore, from_dt)
    assert result.month == 2
    assert result.day == 28  # clamped to Feb's last day
```

- [ ] **Step 5: Run the new test**

Run: `pytest tests/test_chore_scheduling.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/chore_scheduling.py packages/backend/src/myhome/routes/chores.py \
        packages/backend/tests/test_chore_scheduling.py
git commit -m "refactor: extract chore due-date scheduling into a shared module"
```

---

## Task 4: MCP core helpers — `mcp_server.py`

This is the shared foundation every tool module (Tasks 5–12) imports: the `FastMCP` instance itself, and two small, independently-testable helpers for auth and multi-home resolution.

**Files:**
- Create: `packages/backend/src/myhome/mcp_server.py`
- Test: `packages/backend/tests/test_mcp_helpers.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_mcp_helpers.py`:

```python
import hashlib

import pytest
from starlette.requests import Request

from myhome.models_auth import ApiToken, TokenDocument
from myhome.models_homes import Home, HomesDocument
from myhome.persistence_auth import save_tokens
from myhome.persistence_homes import save_homes


def _fake_request(authorization: str | None) -> Request:
    headers = [(b"authorization", authorization.encode())] if authorization else []
    scope = {"type": "http", "method": "POST", "path": "/mcp", "headers": headers}
    return Request(scope)


def _seed_token(raw: str, role: str, owner_id: str = "u1") -> None:
    save_tokens(TokenDocument(tokens=[
        ApiToken(
            id="t1", name="Test", token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            role=role, owner_id=owner_id, created_at="2026-01-01T00:00:00+00:00",
        )
    ]))


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-for-mcp-helpers")


async def test_require_role_rejects_no_request():
    from myhome.mcp_server import _require_role
    with pytest.raises(PermissionError):
        await _require_role(None, "ro")


async def test_require_role_rejects_missing_auth_header():
    from myhome.mcp_server import _require_role
    with pytest.raises(PermissionError):
        await _require_role(_fake_request(None), "ro")


async def test_require_role_accepts_sufficient_role():
    from myhome.mcp_server import _require_role
    _seed_token("a" * 64, "normal", owner_id="u1")
    user_id, role = await _require_role(_fake_request("Bearer " + "a" * 64), "normal")
    assert user_id == "u1"
    assert role == "normal"


async def test_require_role_rejects_insufficient_role():
    from myhome.mcp_server import _require_role
    _seed_token("b" * 64, "ro", owner_id="u2")
    with pytest.raises(PermissionError):
        await _require_role(_fake_request("Bearer " + "b" * 64), "normal")


def test_resolve_home_id_auto_resolves_single_home():
    from myhome.mcp_server import _resolve_home_id
    save_homes(HomesDocument(homes=[
        Home(id="h1", name="Only Home", type="existing", enabledModules=[], createdAt="2026-01-01T00:00:00+00:00"),
    ]))
    assert _resolve_home_id(None) == "h1"


def test_resolve_home_id_requires_explicit_id_with_multiple_homes():
    from myhome.mcp_server import _resolve_home_id
    save_homes(HomesDocument(homes=[
        Home(id="h1", name="A", type="existing", enabledModules=[], createdAt="2026-01-01T00:00:00+00:00"),
        Home(id="h2", name="B", type="existing", enabledModules=[], createdAt="2026-01-01T00:00:00+00:00"),
    ]))
    with pytest.raises(ValueError):
        _resolve_home_id(None)
    assert _resolve_home_id("h2") == "h2"


def test_resolve_home_id_rejects_unknown_id():
    from myhome.mcp_server import _resolve_home_id
    save_homes(HomesDocument(homes=[
        Home(id="h1", name="A", type="existing", enabledModules=[], createdAt="2026-01-01T00:00:00+00:00"),
    ]))
    with pytest.raises(ValueError):
        _resolve_home_id("nonexistent")


def test_resolve_home_id_rejects_when_no_homes_exist():
    from myhome.mcp_server import _resolve_home_id
    with pytest.raises(ValueError):
        _resolve_home_id(None)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_mcp_helpers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.mcp_server'`

- [ ] **Step 3: Write `mcp_server.py`**

Create `packages/backend/src/myhome/mcp_server.py`:

```python
from __future__ import annotations

from starlette.requests import Request

from mcp.server.fastmcp import FastMCP

from .deps import ROLE_ORDER, get_user_from_request
from .persistence_homes import load_homes

# streamable_http_path="/" — this FastMCP instance is mounted at "/mcp" by main.py
# (via mcp_app.py), so its own internal route should be registered at the mount's
# root, not at another nested "/mcp".
mcp = FastMCP("MyHome", streamable_http_path="/")


async def _require_role(request: Request | None, min_role: str) -> tuple[str, str]:
    """Resolve the caller's (user_id, role) from the incoming HTTP request and
    enforce a minimum role. Raises PermissionError if unauthenticated or
    under-scoped; FastMCP surfaces this to the MCP client as a tool error."""
    user = await get_user_from_request(request) if request is not None else None
    if user is None:
        raise PermissionError("Authentication required")
    user_id, role = user
    if ROLE_ORDER.get(role, -1) < ROLE_ORDER[min_role]:
        raise PermissionError(
            f"This action requires the '{min_role}' role or higher; your API token is scoped to '{role}'"
        )
    return user_id, role


def _resolve_home_id(home_id: str | None) -> str:
    """Resolve an optional home_id tool argument to a concrete home id.
    Auto-resolves when exactly one home exists; otherwise requires an explicit,
    valid home_id (call list_homes to discover valid ids)."""
    homes = load_homes().homes
    if home_id is not None:
        if not any(h.id == home_id for h in homes):
            valid = [(h.id, h.name) for h in homes]
            raise ValueError(f"Unknown home_id {home_id!r}. Valid homes: {valid}")
        return home_id
    if not homes:
        raise ValueError("No homes exist yet. Call create_home first.")
    if len(homes) == 1:
        return homes[0].id
    valid = [(h.id, h.name) for h in homes]
    raise ValueError(f"home_id is required when multiple homes exist. Valid homes: {valid}")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_mcp_helpers.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/mcp_server.py packages/backend/tests/test_mcp_helpers.py
git commit -m "feat: add MCP auth and home-resolution helpers"
```

---

## Task 5: `mcp_tools_homes.py`

**Files:**
- Create: `packages/backend/src/myhome/mcp_tools_homes.py`
- Test: `packages/backend/tests/test_mcp_tools_homes.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_mcp_tools_homes.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


def test_list_homes_empty_initially():
    from myhome.mcp_tools_homes import _list_homes_impl
    assert _list_homes_impl() == []


def test_create_home():
    from myhome.mcp_tools_homes import _create_home_impl, _list_homes_impl
    home = _create_home_impl("Lake House", "existing")
    assert home["name"] == "Lake House"
    assert home["type"] == "existing"
    assert _list_homes_impl()[0]["id"] == home["id"]


def test_create_home_rejects_invalid_type():
    from myhome.mcp_tools_homes import _create_home_impl
    with pytest.raises(ValueError):
        _create_home_impl("Bad", "mansion")


def test_update_home_renames():
    from myhome.mcp_tools_homes import _create_home_impl, _update_home_impl
    home = _create_home_impl("Old Name", "existing")
    updated = _update_home_impl(home["id"], name="New Name")
    assert updated["name"] == "New Name"


def test_update_home_unknown_id_raises():
    from myhome.mcp_tools_homes import _update_home_impl
    with pytest.raises(ValueError):
        _update_home_impl("nonexistent", name="X")


def test_delete_home():
    from myhome.mcp_tools_homes import _create_home_impl, _delete_home_impl, _list_homes_impl
    home = _create_home_impl("Temp", "existing")
    result = _delete_home_impl(home["id"])
    assert result == {"deleted": home["id"]}
    assert _list_homes_impl() == []


def test_delete_home_unknown_id_raises():
    from myhome.mcp_tools_homes import _delete_home_impl
    with pytest.raises(ValueError):
        _delete_home_impl("nonexistent")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_mcp_tools_homes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.mcp_tools_homes'`

- [ ] **Step 3: Write `mcp_tools_homes.py`**

Create `packages/backend/src/myhome/mcp_tools_homes.py`:

```python
from __future__ import annotations

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, mcp
from .persistence_homes import (
    create_home as ph_create_home,
    delete_home as ph_delete_home,
    load_homes,
    patch_home,
)


def _list_homes_impl() -> list[dict]:
    return [h.model_dump() for h in load_homes().homes]


def _create_home_impl(name: str, home_type: str) -> dict:
    if home_type not in ("existing", "project"):
        raise ValueError("type must be 'existing' or 'project'")
    return ph_create_home(name, home_type).model_dump()


def _update_home_impl(
    home_id: str,
    name: str | None = None,
    home_type: str | None = None,
    enabled_modules: list[str] | None = None,
) -> dict:
    if home_type is not None and home_type not in ("existing", "project"):
        raise ValueError("type must be 'existing' or 'project'")
    home = patch_home(home_id, name, home_type, enabled_modules)
    if home is None:
        raise ValueError(f"Unknown home_id {home_id!r}")
    return home.model_dump()


def _delete_home_impl(home_id: str) -> dict:
    if not ph_delete_home(home_id):
        raise ValueError(f"Unknown home_id {home_id!r}")
    return {"deleted": home_id}


@mcp.tool()
async def list_homes(ctx: Context) -> list[dict]:
    """List every home in this MyHome installation, with id, name, type, and enabled modules."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_homes_impl()


@mcp.tool()
async def create_home(ctx: Context, name: str, type: str) -> dict:
    """Create a new home. type must be 'existing' or 'project'."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_home_impl(name, type)


@mcp.tool()
async def update_home(
    ctx: Context,
    home_id: str,
    name: str | None = None,
    type: str | None = None,
    enabled_modules: list[str] | None = None,
) -> dict:
    """Rename a home, change its type ('existing'/'project'), or change which modules are enabled."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_home_impl(home_id, name, type, enabled_modules)


@mcp.tool()
async def delete_home(ctx: Context, home_id: str) -> dict:
    """Permanently delete a home and ALL of its data (chores, inventory, costs, works,
    KB, consumables). This cannot be undone."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_home_impl(home_id)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_mcp_tools_homes.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_homes.py packages/backend/tests/test_mcp_tools_homes.py
git commit -m "feat: add MCP tools for homes"
```

---

## Task 6: `mcp_tools_settings.py` (read-only)

**Files:**
- Create: `packages/backend/src/myhome/mcp_tools_settings.py`
- Test: `packages/backend/tests/test_mcp_tools_settings.py`

- [ ] **Step 1: Write the failing test**

Create `packages/backend/tests/test_mcp_tools_settings.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


def test_get_settings_returns_default_categories():
    from myhome.mcp_tools_settings import _get_settings_impl
    from myhome.persistence_homes import create_home

    home = create_home("Test Home", "existing")
    doc = _get_settings_impl(home.id)
    assert any(c["name"] == "Electricity" for c in doc["costCategories"])
    assert doc["consumableUnits"] == ["count", "L", "mL", "kg", "g", "packs", "rolls", "pairs"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_mcp_tools_settings.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.mcp_tools_settings'`

- [ ] **Step 3: Write `mcp_tools_settings.py`**

Create `packages/backend/src/myhome/mcp_tools_settings.py`:

```python
from __future__ import annotations

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .persistence_settings import load_settings


def _get_settings_impl(home_id: str) -> dict:
    return load_settings(home_id).model_dump()


@mcp.tool()
async def get_settings(ctx: Context, home_id: str | None = None) -> dict:
    """Get the cost categories, inventory categories, work categories, suppliers,
    consumable units, and consumable categories configured for a home. Use this to
    find valid categoryId/supplierId values before creating cost entries, works,
    or consumables."""
    await _require_role(ctx.request_context.request, "ro")
    resolved = _resolve_home_id(home_id)
    return _get_settings_impl(resolved)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_mcp_tools_settings.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_settings.py packages/backend/tests/test_mcp_tools_settings.py
git commit -m "feat: add read-only MCP get_settings tool"
```

---

## Task 7: `mcp_tools_chores.py`

**Files:**
- Create: `packages/backend/src/myhome/mcp_tools_chores.py`
- Test: `packages/backend/tests/test_mcp_tools_chores.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_mcp_tools_chores.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_chore(home_id):
    from myhome.mcp_tools_chores import _create_chore_impl, _list_chores_impl
    chore = _create_chore_impl(home_id, "Take out trash", "🗑", 7.0, "2026-07-10T00:00:00Z")
    doc = _list_chores_impl(home_id)
    assert doc["chores"][0]["id"] == chore["id"]
    assert doc["chores"][0]["frequency"] == 7  # derived from period_days since frequency=0


def test_update_chore(home_id):
    from myhome.mcp_tools_chores import _create_chore_impl, _update_chore_impl
    chore = _create_chore_impl(home_id, "Water plants", "🌱", 3.0, "2026-07-05T00:00:00Z")
    updated = _update_chore_impl(home_id, chore["id"], name="Water all plants")
    assert updated["name"] == "Water all plants"


def test_update_chore_unknown_id_raises(home_id):
    from myhome.mcp_tools_chores import _update_chore_impl
    with pytest.raises(ValueError):
        _update_chore_impl(home_id, "nonexistent", name="X")


def test_delete_chore(home_id):
    from myhome.mcp_tools_chores import _create_chore_impl, _delete_chore_impl, _list_chores_impl
    chore = _create_chore_impl(home_id, "Mow lawn", "🌿", 14.0, "2026-07-15T00:00:00Z")
    _delete_chore_impl(home_id, chore["id"])
    assert _list_chores_impl(home_id)["chores"] == []


def test_complete_chore_advances_due_date(home_id):
    from myhome.mcp_tools_chores import _complete_chore_impl, _create_chore_impl, _list_chores_impl
    chore = _create_chore_impl(
        home_id, "Vacuum", "🧹", 7.0, "2026-07-04T00:00:00Z",
        frequency_type="interval", frequency=7, frequency_metadata={"unit": "days"},
    )
    result = _complete_chore_impl(home_id, chore["id"], notes="done early")
    assert result["nextDueDate"] != "2026-07-04T00:00:00Z"
    doc = _list_chores_impl(home_id)
    assert len(doc["completions"]) == 1
    assert doc["completions"][0]["notes"] == "done early"


def test_undo_chore_completion(home_id):
    from myhome.mcp_tools_chores import _complete_chore_impl, _create_chore_impl, _list_chores_impl, _undo_chore_completion_impl
    chore = _create_chore_impl(home_id, "Dust", "🪶", 7.0, "2026-07-04T00:00:00Z")
    _complete_chore_impl(home_id, chore["id"])
    completion_id = _list_chores_impl(home_id)["completions"][0]["id"]
    _undo_chore_completion_impl(home_id, completion_id)
    assert _list_chores_impl(home_id)["completions"] == []


def test_undo_unknown_completion_raises(home_id):
    from myhome.mcp_tools_chores import _undo_chore_completion_impl
    with pytest.raises(ValueError):
        _undo_chore_completion_impl(home_id, "nonexistent")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_mcp_tools_chores.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.mcp_tools_chores'`

- [ ] **Step 3: Write `mcp_tools_chores.py`**

Create `packages/backend/src/myhome/mcp_tools_chores.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from mcp.server.fastmcp import Context

from .chore_scheduling import next_due_from_schedule
from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_chores import Chore, CompletionRecord
from .persistence_chores import load_chores, save_chores


def _list_chores_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_chores(resolved).model_dump()


def _create_chore_impl(
    home_id: str | None,
    name: str,
    emoji: str,
    period_days: float,
    next_due_date: str,
    description: str = "",
    frequency_type: str = "interval",
    frequency: int = 0,
    frequency_metadata: dict | None = None,
    schedule_from_due: bool = False,
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_chores(resolved)
    freq = frequency
    meta = frequency_metadata or {}
    if freq == 0:
        freq = max(1, round(period_days))
        meta = {"unit": "days"}
    chore = Chore(
        id=str(uuid.uuid4()),
        name=name,
        emoji=emoji,
        periodDays=period_days,
        nextDueDate=next_due_date,
        description=description,
        frequencyType=frequency_type,
        frequency=freq,
        frequencyMetadata=meta,
        scheduleFromDue=schedule_from_due,
    )
    doc.chores.append(chore)
    save_chores(resolved, doc)
    return chore.model_dump()


def _update_chore_impl(home_id: str | None, chore_id: str, **fields) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_chores(resolved)
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise ValueError(f"Unknown chore_id {chore_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(chore, field, value)
    save_chores(resolved, doc)
    return chore.model_dump()


def _delete_chore_impl(home_id: str | None, chore_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_chores(resolved)
    if not any(c.id == chore_id for c in doc.chores):
        raise ValueError(f"Unknown chore_id {chore_id!r}")
    doc.chores = [c for c in doc.chores if c.id != chore_id]
    doc.assignments = [a for a in doc.assignments if a.choreId != chore_id]
    save_chores(resolved, doc)
    return {"deleted": chore_id}


def _complete_chore_impl(home_id: str | None, chore_id: str, notes: str = "") -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_chores(resolved)
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise ValueError(f"Unknown chore_id {chore_id!r}")
    now = datetime.now(timezone.utc)
    if chore.scheduleFromDue and chore.nextDueDate:
        try:
            from_dt = datetime.fromisoformat(chore.nextDueDate.replace("Z", "+00:00"))
        except ValueError:
            from_dt = now
    else:
        from_dt = now
    next_due = next_due_from_schedule(chore, from_dt)
    next_due_str = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    doc.completions.append(CompletionRecord(
        id=str(uuid.uuid4()),
        choreId=chore_id,
        completedAt=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        scheduledDue=chore.nextDueDate,
        notes=notes,
    ))
    for a in doc.assignments:
        if a.choreId == chore_id:
            a.nextDueDate = next_due_str
    chore.nextDueDate = next_due_str
    save_chores(resolved, doc)
    return chore.model_dump()


def _undo_chore_completion_impl(home_id: str | None, completion_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_chores(resolved)
    if not any(r.id == completion_id for r in doc.completions):
        raise ValueError(f"Unknown completion_id {completion_id!r}")
    doc.completions = [r for r in doc.completions if r.id != completion_id]
    save_chores(resolved, doc)
    return {"deleted": completion_id}


@mcp.tool()
async def list_chores(ctx: Context, home_id: str | None = None) -> dict:
    """List all chores, room assignments, and completion history for a home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_chores_impl(home_id)


@mcp.tool()
async def create_chore(
    ctx: Context,
    name: str,
    emoji: str,
    period_days: float,
    next_due_date: str,
    home_id: str | None = None,
    description: str = "",
    frequency_type: str = "interval",
    frequency: int = 0,
    frequency_metadata: dict | None = None,
    schedule_from_due: bool = False,
) -> dict:
    """Create a new recurring chore. next_due_date is ISO-8601. frequency_type is one of
    'interval' (every N days/weeks/months/years, set via frequency_metadata={'unit': ...}),
    'weekly', 'monthly', 'yearly', 'day_of_the_month', or 'days_of_the_week'. Leave
    frequency at 0 to derive it from period_days for a simple daily interval."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_chore_impl(
        home_id, name, emoji, period_days, next_due_date, description,
        frequency_type, frequency, frequency_metadata, schedule_from_due,
    )


@mcp.tool()
async def update_chore(
    ctx: Context,
    chore_id: str,
    home_id: str | None = None,
    name: str | None = None,
    emoji: str | None = None,
    period_days: float | None = None,
    next_due_date: str | None = None,
    description: str | None = None,
    frequency_type: str | None = None,
    frequency: int | None = None,
    frequency_metadata: dict | None = None,
    schedule_from_due: bool | None = None,
) -> dict:
    """Update fields on an existing chore. Only pass the fields you want to change."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_chore_impl(
        home_id, chore_id,
        name=name, emoji=emoji, periodDays=period_days, nextDueDate=next_due_date,
        description=description, frequencyType=frequency_type, frequency=frequency,
        frequencyMetadata=frequency_metadata, scheduleFromDue=schedule_from_due,
    )


@mcp.tool()
async def delete_chore(ctx: Context, chore_id: str, home_id: str | None = None) -> dict:
    """Delete a chore and its room assignments. Completion history is kept."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_chore_impl(home_id, chore_id)


@mcp.tool()
async def complete_chore(ctx: Context, chore_id: str, home_id: str | None = None, notes: str = "") -> dict:
    """Mark a chore as done now, recording a completion and advancing its next due date
    according to its schedule."""
    await _require_role(ctx.request_context.request, "normal")
    return _complete_chore_impl(home_id, chore_id, notes)


@mcp.tool()
async def undo_chore_completion(ctx: Context, completion_id: str, home_id: str | None = None) -> dict:
    """Delete a completion record (undoes a mistaken complete_chore call). Does not
    revert the chore's next due date."""
    await _require_role(ctx.request_context.request, "normal")
    return _undo_chore_completion_impl(home_id, completion_id)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_mcp_tools_chores.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_chores.py packages/backend/tests/test_mcp_tools_chores.py
git commit -m "feat: add MCP tools for chores"
```

---

## Task 8: `mcp_tools_inventory.py`

**Files:**
- Create: `packages/backend/src/myhome/mcp_tools_inventory.py`
- Test: `packages/backend/tests/test_mcp_tools_inventory.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_mcp_tools_inventory.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_item(home_id):
    from myhome.mcp_tools_inventory import _create_inventory_item_impl, _list_inventory_items_impl
    item = _create_inventory_item_impl(home_id, "Drill", category="Tool", brand="Bosch")
    doc = _list_inventory_items_impl(home_id)
    assert doc["items"][0]["id"] == item["id"]
    assert doc["items"][0]["brand"] == "Bosch"


def test_update_item(home_id):
    from myhome.mcp_tools_inventory import _create_inventory_item_impl, _update_inventory_item_impl
    item = _create_inventory_item_impl(home_id, "TV")
    updated = _update_inventory_item_impl(home_id, item["id"], notes="In living room")
    assert updated["notes"] == "In living room"


def test_update_item_unknown_id_raises(home_id):
    from myhome.mcp_tools_inventory import _update_inventory_item_impl
    with pytest.raises(ValueError):
        _update_inventory_item_impl(home_id, "nonexistent", notes="x")


def test_delete_item(home_id):
    from myhome.mcp_tools_inventory import (
        _create_inventory_item_impl, _delete_inventory_item_impl, _list_inventory_items_impl,
    )
    item = _create_inventory_item_impl(home_id, "Old Fridge")
    _delete_inventory_item_impl(home_id, item["id"])
    assert _list_inventory_items_impl(home_id)["items"] == []


def test_delete_item_unknown_id_raises(home_id):
    from myhome.mcp_tools_inventory import _delete_inventory_item_impl
    with pytest.raises(ValueError):
        _delete_inventory_item_impl(home_id, "nonexistent")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_mcp_tools_inventory.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.mcp_tools_inventory'`

- [ ] **Step 3: Write `mcp_tools_inventory.py`**

Create `packages/backend/src/myhome/mcp_tools_inventory.py`:

```python
from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_inventory import InventoryItem
from .persistence_inventory import load_inventory, save_inventory


def _list_inventory_items_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_inventory(resolved).model_dump()


def _create_inventory_item_impl(
    home_id: str | None,
    name: str,
    emoji: str = "📦",
    category: str = "",
    brand: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
    purchase_date: str | None = None,
    purchase_price: float | None = None,
    warranty_expiry_date: str | None = None,
    notes: str = "",
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_inventory(resolved)
    item = InventoryItem(
        id=str(uuid.uuid4()), name=name, emoji=emoji, category=category, brand=brand,
        model=model, serialNumber=serial_number, purchaseDate=purchase_date,
        purchasePrice=purchase_price, warrantyExpiryDate=warranty_expiry_date, notes=notes,
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
    brand: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
    purchase_date: str | None = None,
    purchase_price: float | None = None,
    warranty_expiry_date: str | None = None,
    notes: str = "",
) -> dict:
    """Add an inventory item. category should match an inventoryCategories name from
    get_settings (e.g. Electronics, Furniture, Appliance, Tool, Artwork, Other)."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_inventory_item_impl(
        home_id, name, emoji, category, brand, model, serial_number,
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
    brand: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
    purchase_date: str | None = None,
    purchase_price: float | None = None,
    warranty_expiry_date: str | None = None,
    notes: str | None = None,
) -> dict:
    """Update fields on an existing inventory item. Only pass the fields you want to change."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_inventory_item_impl(
        home_id, item_id, name=name, emoji=emoji, category=category, brand=brand,
        model=model, serialNumber=serial_number, purchaseDate=purchase_date,
        purchasePrice=purchase_price, warrantyExpiryDate=warranty_expiry_date, notes=notes,
    )


@mcp.tool()
async def delete_inventory_item(ctx: Context, item_id: str, home_id: str | None = None) -> dict:
    """Delete an inventory item."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_inventory_item_impl(home_id, item_id)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_mcp_tools_inventory.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_inventory.py packages/backend/tests/test_mcp_tools_inventory.py
git commit -m "feat: add MCP tools for inventory"
```

---

## Task 9: `mcp_tools_consumables.py`

**Files:**
- Create: `packages/backend/src/myhome/mcp_tools_consumables.py`
- Test: `packages/backend/tests/test_mcp_tools_consumables.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_mcp_tools_consumables.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_consumable(home_id):
    from myhome.mcp_tools_consumables import _create_consumable_impl, _list_consumables_impl
    item = _create_consumable_impl(home_id, "AA Batteries", unit="packs", quantity=5.0)
    doc = _list_consumables_impl(home_id)
    assert doc["consumables"][0]["id"] == item["id"]
    assert doc["consumables"][0]["quantity"] == 5.0


def test_update_consumable(home_id):
    from myhome.mcp_tools_consumables import _create_consumable_impl, _update_consumable_impl
    item = _create_consumable_impl(home_id, "Detergent")
    updated = _update_consumable_impl(home_id, item["id"], name="Laundry Detergent")
    assert updated["name"] == "Laundry Detergent"


def test_delete_consumable(home_id):
    from myhome.mcp_tools_consumables import (
        _create_consumable_impl, _delete_consumable_impl, _list_consumables_impl,
    )
    item = _create_consumable_impl(home_id, "Old Item")
    _delete_consumable_impl(home_id, item["id"])
    assert _list_consumables_impl(home_id)["consumables"] == []


def test_delete_consumable_unknown_id_raises(home_id):
    from myhome.mcp_tools_consumables import _delete_consumable_impl
    with pytest.raises(ValueError):
        _delete_consumable_impl(home_id, "nonexistent")


def test_adjust_stock_sets_absolute_quantity_and_logs_transaction(home_id):
    from myhome.mcp_tools_consumables import _adjust_consumable_stock_impl, _create_consumable_impl, _list_consumables_impl
    item = _create_consumable_impl(home_id, "Batteries", quantity=10.0)
    result = _adjust_consumable_stock_impl(home_id, item["id"], 8.0, note="used 2")
    assert result["quantity"] == 8.0
    doc = _list_consumables_impl(home_id)
    assert len(doc["transactions"]) == 1
    assert doc["transactions"][0]["delta"] == -2.0
    assert doc["transactions"][0]["note"] == "used 2"


def test_adjust_stock_unknown_id_raises(home_id):
    from myhome.mcp_tools_consumables import _adjust_consumable_stock_impl
    with pytest.raises(ValueError):
        _adjust_consumable_stock_impl(home_id, "nonexistent", 5.0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_mcp_tools_consumables.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.mcp_tools_consumables'`

- [ ] **Step 3: Write `mcp_tools_consumables.py`**

Create `packages/backend/src/myhome/mcp_tools_consumables.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_consumables import Consumable, ConsumableTransaction
from .persistence_consumables import load_consumables, save_consumables


def _list_consumables_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_consumables(resolved).model_dump()


def _create_consumable_impl(
    home_id: str | None,
    name: str,
    emoji: str = "🛒",
    unit: str = "count",
    quantity: float = 0.0,
    min_quantity: float = 1.0,
    category_id: str | None = None,
    description: str = "",
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_consumables(resolved)
    item = Consumable(
        id=str(uuid.uuid4()), name=name, emoji=emoji, unit=unit, quantity=quantity,
        minQuantity=min_quantity, categoryId=category_id, description=description,
    )
    doc.consumables.append(item)
    save_consumables(resolved, doc)
    return item.model_dump()


def _update_consumable_impl(home_id: str | None, consumable_id: str, **fields) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_consumables(resolved)
    item = next((c for c in doc.consumables if c.id == consumable_id), None)
    if item is None:
        raise ValueError(f"Unknown consumable_id {consumable_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(item, field, value)
    save_consumables(resolved, doc)
    return item.model_dump()


def _delete_consumable_impl(home_id: str | None, consumable_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_consumables(resolved)
    before = len(doc.consumables)
    doc.consumables = [c for c in doc.consumables if c.id != consumable_id]
    if len(doc.consumables) == before:
        raise ValueError(f"Unknown consumable_id {consumable_id!r}")
    doc.transactions = [t for t in doc.transactions if t.consumableId != consumable_id]
    save_consumables(resolved, doc)
    return {"deleted": consumable_id}


def _adjust_consumable_stock_impl(home_id: str | None, consumable_id: str, quantity: float, note: str = "") -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_consumables(resolved)
    item = next((c for c in doc.consumables if c.id == consumable_id), None)
    if item is None:
        raise ValueError(f"Unknown consumable_id {consumable_id!r}")
    delta = quantity - item.quantity
    item.quantity = quantity
    tx = ConsumableTransaction(
        id=str(uuid.uuid4()), consumableId=consumable_id, delta=delta,
        quantityAfter=quantity, note=note, timestamp=datetime.now(timezone.utc).isoformat(),
    )
    doc.transactions.append(tx)
    save_consumables(resolved, doc)
    return item.model_dump()


@mcp.tool()
async def list_consumables(ctx: Context, home_id: str | None = None) -> dict:
    """List consumable stock items and their transaction history for a home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_consumables_impl(home_id)


@mcp.tool()
async def create_consumable(
    ctx: Context,
    name: str,
    home_id: str | None = None,
    emoji: str = "🛒",
    unit: str = "count",
    quantity: float = 0.0,
    min_quantity: float = 1.0,
    category_id: str | None = None,
    description: str = "",
) -> dict:
    """Add a consumable stock item (e.g. batteries, detergent). unit and category_id
    should match values from get_settings (consumableUnits / consumableCategories)."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_consumable_impl(home_id, name, emoji, unit, quantity, min_quantity, category_id, description)


@mcp.tool()
async def update_consumable(
    ctx: Context,
    consumable_id: str,
    home_id: str | None = None,
    name: str | None = None,
    emoji: str | None = None,
    unit: str | None = None,
    min_quantity: float | None = None,
    category_id: str | None = None,
    description: str | None = None,
) -> dict:
    """Update fields on a consumable. To change the quantity itself, use
    adjust_consumable_stock instead (it also records a transaction)."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_consumable_impl(
        home_id, consumable_id, name=name, emoji=emoji, unit=unit,
        minQuantity=min_quantity, categoryId=category_id, description=description,
    )


@mcp.tool()
async def delete_consumable(ctx: Context, consumable_id: str, home_id: str | None = None) -> dict:
    """Delete a consumable and its transaction history."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_consumable_impl(home_id, consumable_id)


@mcp.tool()
async def adjust_consumable_stock(
    ctx: Context, consumable_id: str, quantity: float, home_id: str | None = None, note: str = "",
) -> dict:
    """Set a consumable's ABSOLUTE quantity (not a delta) and record a stock
    transaction. E.g. to record using 2 units from a stock of 10, pass quantity=8."""
    await _require_role(ctx.request_context.request, "normal")
    return _adjust_consumable_stock_impl(home_id, consumable_id, quantity, note)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_mcp_tools_consumables.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_consumables.py packages/backend/tests/test_mcp_tools_consumables.py
git commit -m "feat: add MCP tools for consumables"
```

---

## Task 10: `mcp_tools_costs.py`

**Files:**
- Create: `packages/backend/src/myhome/mcp_tools_costs.py`
- Test: `packages/backend/tests/test_mcp_tools_costs.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_mcp_tools_costs.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_entry(home_id):
    from myhome.mcp_tools_costs import _create_cost_entry_impl, _list_cost_entries_impl
    entry = _create_cost_entry_impl(home_id, "cat-electricity", "2026-07-01", 45.50)
    doc = _list_cost_entries_impl(home_id)
    assert doc["entries"][0]["id"] == entry["id"]
    assert doc["entries"][0]["totalAmount"] == 45.50


def test_update_entry(home_id):
    from myhome.mcp_tools_costs import _create_cost_entry_impl, _update_cost_entry_impl
    entry = _create_cost_entry_impl(home_id, "cat-water", "2026-07-01", 20.0)
    updated = _update_cost_entry_impl(home_id, entry["id"], notes="corrected reading")
    assert updated["notes"] == "corrected reading"


def test_update_entry_unknown_id_raises(home_id):
    from myhome.mcp_tools_costs import _update_cost_entry_impl
    with pytest.raises(ValueError):
        _update_cost_entry_impl(home_id, "nonexistent", notes="x")


def test_delete_entry(home_id):
    from myhome.mcp_tools_costs import _create_cost_entry_impl, _delete_cost_entry_impl, _list_cost_entries_impl
    entry = _create_cost_entry_impl(home_id, "cat-fuel", "2026-07-01", 60.0)
    _delete_cost_entry_impl(home_id, entry["id"])
    assert _list_cost_entries_impl(home_id)["entries"] == []


def test_delete_entry_unknown_id_raises(home_id):
    from myhome.mcp_tools_costs import _delete_cost_entry_impl
    with pytest.raises(ValueError):
        _delete_cost_entry_impl(home_id, "nonexistent")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_mcp_tools_costs.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.mcp_tools_costs'`

- [ ] **Step 3: Write `mcp_tools_costs.py`**

Create `packages/backend/src/myhome/mcp_tools_costs.py`:

```python
from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_costs import CostEntry
from .persistence_costs import load_costs, save_costs


def _list_cost_entries_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_costs(resolved).model_dump()


def _create_cost_entry_impl(
    home_id: str | None,
    category_id: str,
    date: str,
    total_amount: float,
    quantity: float | None = None,
    unit_price: float | None = None,
    supplier_id: str | None = None,
    notes: str = "",
    room_id: str | None = None,
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_costs(resolved)
    entry = CostEntry(
        id=str(uuid.uuid4()), categoryId=category_id, date=date, totalAmount=total_amount,
        quantity=quantity, unitPrice=unit_price, supplierId=supplier_id, notes=notes, roomId=room_id,
    )
    doc.entries.append(entry)
    save_costs(resolved, doc)
    return entry.model_dump()


def _update_cost_entry_impl(home_id: str | None, entry_id: str, **fields) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_costs(resolved)
    entry = next((e for e in doc.entries if e.id == entry_id), None)
    if entry is None:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(entry, field, value)
    save_costs(resolved, doc)
    return entry.model_dump()


def _delete_cost_entry_impl(home_id: str | None, entry_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_costs(resolved)
    before = len(doc.entries)
    doc.entries = [e for e in doc.entries if e.id != entry_id]
    if len(doc.entries) == before:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    save_costs(resolved, doc)
    return {"deleted": entry_id}


@mcp.tool()
async def list_cost_entries(ctx: Context, home_id: str | None = None) -> dict:
    """List all cost/expense entries for a home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_cost_entries_impl(home_id)


@mcp.tool()
async def create_cost_entry(
    ctx: Context,
    category_id: str,
    date: str,
    total_amount: float,
    home_id: str | None = None,
    quantity: float | None = None,
    unit_price: float | None = None,
    supplier_id: str | None = None,
    notes: str = "",
    room_id: str | None = None,
) -> dict:
    """Log a cost entry. category_id and supplier_id should match ids from
    get_settings (costCategories / suppliers). date is ISO-8601."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_cost_entry_impl(
        home_id, category_id, date, total_amount, quantity, unit_price, supplier_id, notes, room_id,
    )


@mcp.tool()
async def update_cost_entry(
    ctx: Context,
    entry_id: str,
    home_id: str | None = None,
    category_id: str | None = None,
    date: str | None = None,
    total_amount: float | None = None,
    quantity: float | None = None,
    unit_price: float | None = None,
    supplier_id: str | None = None,
    notes: str | None = None,
    room_id: str | None = None,
) -> dict:
    """Update fields on an existing cost entry. Only pass the fields you want to change."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_cost_entry_impl(
        home_id, entry_id, categoryId=category_id, date=date, totalAmount=total_amount,
        quantity=quantity, unitPrice=unit_price, supplierId=supplier_id, notes=notes, roomId=room_id,
    )


@mcp.tool()
async def delete_cost_entry(ctx: Context, entry_id: str, home_id: str | None = None) -> dict:
    """Delete a cost entry."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_cost_entry_impl(home_id, entry_id)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_mcp_tools_costs.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_costs.py packages/backend/tests/test_mcp_tools_costs.py
git commit -m "feat: add MCP tools for costs"
```

---

## Task 11: `mcp_tools_works.py`

**Files:**
- Create: `packages/backend/src/myhome/mcp_tools_works.py`
- Test: `packages/backend/tests/test_mcp_tools_works.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_mcp_tools_works.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_work(home_id):
    from myhome.mcp_tools_works import _create_work_impl, _list_works_impl
    work = _create_work_impl(home_id, "Repaint fence", "2026-08-01")
    doc = _list_works_impl(home_id)
    assert doc["works"][0]["id"] == work["id"]
    assert doc["works"][0]["status"] == "planned"


def test_create_work_rejects_invalid_status(home_id):
    from myhome.mcp_tools_works import _create_work_impl
    with pytest.raises(ValueError):
        _create_work_impl(home_id, "Bad", "2026-08-01", status="nope")


def test_update_work_transitions_status(home_id):
    from myhome.mcp_tools_works import _create_work_impl, _update_work_impl
    work = _create_work_impl(home_id, "Replace gutters", "2026-08-01")
    updated = _update_work_impl(home_id, work["id"], status="in_progress")
    assert updated["status"] == "in_progress"


def test_update_work_rejects_invalid_status(home_id):
    from myhome.mcp_tools_works import _create_work_impl, _update_work_impl
    work = _create_work_impl(home_id, "Repaint fence", "2026-08-01")
    with pytest.raises(ValueError):
        _update_work_impl(home_id, work["id"], status="nope")


def test_delete_work(home_id):
    from myhome.mcp_tools_works import _create_work_impl, _delete_work_impl, _list_works_impl
    work = _create_work_impl(home_id, "Old Project", "2026-08-01")
    _delete_work_impl(home_id, work["id"])
    assert _list_works_impl(home_id)["works"] == []


def test_delete_work_unknown_id_raises(home_id):
    from myhome.mcp_tools_works import _delete_work_impl
    with pytest.raises(ValueError):
        _delete_work_impl(home_id, "nonexistent")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_mcp_tools_works.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.mcp_tools_works'`

- [ ] **Step 3: Write `mcp_tools_works.py`**

Create `packages/backend/src/myhome/mcp_tools_works.py`:

```python
from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_works import Work
from .persistence_works import load_works, save_works

_VALID_STATUSES = ("planned", "in_progress", "done")


def _list_works_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_works(resolved).model_dump()


def _create_work_impl(
    home_id: str | None,
    title: str,
    date: str,
    description: str = "",
    status: str = "planned",
    category_id: str | None = None,
    total_cost: float | None = None,
    supplier_id: str | None = None,
    notes: str = "",
) -> dict:
    if status not in _VALID_STATUSES:
        raise ValueError(f"status must be one of {_VALID_STATUSES}")
    resolved = _resolve_home_id(home_id)
    doc = load_works(resolved)
    work = Work(
        id=str(uuid.uuid4()), title=title, description=description, status=status,
        categoryId=category_id, date=date, totalCost=total_cost, supplierId=supplier_id, notes=notes,
    )
    doc.works.append(work)
    save_works(resolved, doc)
    return work.model_dump()


def _update_work_impl(home_id: str | None, work_id: str, **fields) -> dict:
    if fields.get("status") is not None and fields["status"] not in _VALID_STATUSES:
        raise ValueError(f"status must be one of {_VALID_STATUSES}")
    resolved = _resolve_home_id(home_id)
    doc = load_works(resolved)
    work = next((w for w in doc.works if w.id == work_id), None)
    if work is None:
        raise ValueError(f"Unknown work_id {work_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(work, field, value)
    save_works(resolved, doc)
    return work.model_dump()


def _delete_work_impl(home_id: str | None, work_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_works(resolved)
    before = len(doc.works)
    doc.works = [w for w in doc.works if w.id != work_id]
    if len(doc.works) == before:
        raise ValueError(f"Unknown work_id {work_id!r}")
    save_works(resolved, doc)
    return {"deleted": work_id}


@mcp.tool()
async def list_works(ctx: Context, home_id: str | None = None) -> dict:
    """List home improvement/renovation works for a home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_works_impl(home_id)


@mcp.tool()
async def create_work(
    ctx: Context,
    title: str,
    date: str,
    home_id: str | None = None,
    description: str = "",
    status: str = "planned",
    category_id: str | None = None,
    total_cost: float | None = None,
    supplier_id: str | None = None,
    notes: str = "",
) -> dict:
    """Create a home improvement/work project entry. status is 'planned', 'in_progress',
    or 'done'. category_id and supplier_id should match ids from get_settings."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_work_impl(home_id, title, date, description, status, category_id, total_cost, supplier_id, notes)


@mcp.tool()
async def update_work(
    ctx: Context,
    work_id: str,
    home_id: str | None = None,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    category_id: str | None = None,
    date: str | None = None,
    total_cost: float | None = None,
    supplier_id: str | None = None,
    notes: str | None = None,
) -> dict:
    """Update fields on an existing work, including transitioning its status."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_work_impl(
        home_id, work_id, title=title, description=description, status=status,
        categoryId=category_id, date=date, totalCost=total_cost, supplierId=supplier_id, notes=notes,
    )


@mcp.tool()
async def delete_work(ctx: Context, work_id: str, home_id: str | None = None) -> dict:
    """Delete a work entry."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_work_impl(home_id, work_id)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_mcp_tools_works.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_works.py packages/backend/tests/test_mcp_tools_works.py
git commit -m "feat: add MCP tools for works"
```

---

## Task 12: `mcp_tools_kb.py`

**Files:**
- Create: `packages/backend/src/myhome/mcp_tools_kb.py`
- Test: `packages/backend/tests/test_mcp_tools_kb.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_mcp_tools_kb.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


@pytest.fixture()
def home_id():
    from myhome.persistence_homes import create_home
    return create_home("Test Home", "existing").id


def test_create_and_list_entry(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _list_kb_entries_impl
    entry = _create_kb_entry_impl(home_id, "Wifi Password", content="It's on the router")
    doc = _list_kb_entries_impl(home_id)
    assert doc["entries"][0]["id"] == entry["id"]
    assert doc["entries"][0]["title"] == "Wifi Password"


def test_update_entry_bumps_updated_at(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _update_kb_entry_impl
    entry = _create_kb_entry_impl(home_id, "Boiler Manual")
    updated = _update_kb_entry_impl(home_id, entry["id"], content="Reset button is on the side")
    assert updated["content"] == "Reset button is on the side"
    assert updated["updatedAt"] >= entry["updatedAt"]


def test_update_entry_unknown_id_raises(home_id):
    from myhome.mcp_tools_kb import _update_kb_entry_impl
    with pytest.raises(ValueError):
        _update_kb_entry_impl(home_id, "nonexistent", title="X")


def test_delete_entry(home_id):
    from myhome.mcp_tools_kb import _create_kb_entry_impl, _delete_kb_entry_impl, _list_kb_entries_impl
    entry = _create_kb_entry_impl(home_id, "Old Note")
    _delete_kb_entry_impl(home_id, entry["id"])
    assert _list_kb_entries_impl(home_id)["entries"] == []


def test_delete_entry_unknown_id_raises(home_id):
    from myhome.mcp_tools_kb import _delete_kb_entry_impl
    with pytest.raises(ValueError):
        _delete_kb_entry_impl(home_id, "nonexistent")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_mcp_tools_kb.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myhome.mcp_tools_kb'`

- [ ] **Step 3: Write `mcp_tools_kb.py`**

Create `packages/backend/src/myhome/mcp_tools_kb.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_kb import KBEntry
from .persistence_kb import delete_entry, load_all, load_entry, save_entry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _list_kb_entries_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return {"entries": [e.model_dump() for e in load_all(resolved)]}


def _create_kb_entry_impl(home_id: str | None, title: str, content: str = "") -> dict:
    resolved = _resolve_home_id(home_id)
    now = _now()
    entry = KBEntry(id=str(uuid.uuid4()), title=title, content=content, createdAt=now, updatedAt=now)
    save_entry(resolved, entry)
    return entry.model_dump()


def _update_kb_entry_impl(
    home_id: str | None, entry_id: str, title: str | None = None, content: str | None = None,
) -> dict:
    resolved = _resolve_home_id(home_id)
    entry = load_entry(resolved, entry_id)
    if entry is None:
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    if title is not None:
        entry.title = title
    if content is not None:
        entry.content = content
    entry.updatedAt = _now()
    save_entry(resolved, entry)
    return entry.model_dump()


def _delete_kb_entry_impl(home_id: str | None, entry_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    if not delete_entry(resolved, entry_id):
        raise ValueError(f"Unknown entry_id {entry_id!r}")
    return {"deleted": entry_id}


@mcp.tool()
async def list_kb_entries(ctx: Context, home_id: str | None = None) -> dict:
    """List all knowledge base articles for a home. There is no server-side search --
    fetch the list and filter/search over titles and content yourself."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_kb_entries_impl(home_id)


@mcp.tool()
async def create_kb_entry(ctx: Context, title: str, home_id: str | None = None, content: str = "") -> dict:
    """Create a knowledge base article. content supports Markdown."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_kb_entry_impl(home_id, title, content)


@mcp.tool()
async def update_kb_entry(
    ctx: Context, entry_id: str, home_id: str | None = None, title: str | None = None, content: str | None = None,
) -> dict:
    """Update the title and/or content of a knowledge base article."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_kb_entry_impl(home_id, entry_id, title, content)


@mcp.tool()
async def delete_kb_entry(ctx: Context, entry_id: str, home_id: str | None = None) -> dict:
    """Delete a knowledge base article."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_kb_entry_impl(home_id, entry_id)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_mcp_tools_kb.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/mcp_tools_kb.py packages/backend/tests/test_mcp_tools_kb.py
git commit -m "feat: add MCP tools for knowledge base"
```

---

## Task 13: Wire it all together — mount, lifespan, gating, auth exemption

This is where `/mcp` actually becomes reachable. Three things happen together: (1) a small `mcp_app.py` registers all eight tool modules and builds the Streamable HTTP ASGI app exactly once; (2) `main.py` gains a combined lifespan (so the MCP session manager's background task actually starts), the `/mcp` mount (gated by the on/off flag from Task 2), and an exemption from the existing blanket "POST/PUT/DELETE/PATCH needs normal+" middleware rule — MCP multiplexes both reads and writes over POST to one endpoint, so that per-method floor has to be replaced by the per-tool `_require_role` checks already written into every tool.

**Files:**
- Create: `packages/backend/src/myhome/mcp_app.py`
- Modify: `packages/backend/src/myhome/main.py`
- Test: `packages/backend/tests/test_mcp_integration.py`

- [ ] **Step 1: Write `mcp_app.py`**

Create `packages/backend/src/myhome/mcp_app.py`:

```python
"""Registers all MCP tool modules on the shared FastMCP instance (mcp_server.mcp)
and builds the Streamable HTTP ASGI app. Imported exactly once, from main.py, so
tool registration happens before the app is built."""
from . import (  # noqa: F401 - imported for the side effect of registering tools
    mcp_tools_chores,
    mcp_tools_consumables,
    mcp_tools_costs,
    mcp_tools_homes,
    mcp_tools_inventory,
    mcp_tools_kb,
    mcp_tools_settings,
    mcp_tools_works,
)
from .mcp_server import mcp

mcp_asgi_app = mcp.streamable_http_app()
```

- [ ] **Step 2: Update `main.py`**

Edit `packages/backend/src/myhome/main.py`. The full file, with new pieces marked, should read:

```python
# packages/backend/src/myhome/main.py
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .deps import ROLE_ORDER, get_user_from_request
from .mcp_app import mcp_asgi_app
from .mcp_server import mcp
from .persistence_mcp import load_mcp_config
from .routes import auth, backup, chores, consumables, costs, ha, homes, house, inventory, kb, mcp_config, settings, svg, works


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # The MCP session manager's background task group is NOT started just by
    # mounting mcp_asgi_app -- Starlette never forwards ASGI lifespan events into
    # mounted sub-apps, so it must be entered here explicitly.
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="MyHome Backend", version="0.1.0", lifespan=_lifespan)


# ── First boot ────────────────────────────────────────────────────────────

def _first_boot() -> None:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    if not data_dir.exists():
        return  # DATA_DIR not yet mounted (CI/test import without fixture)
    if (data_dir / "users.json").exists():
        return
    from passlib.context import CryptContext

    from .models_auth import User, UserDocument
    from .persistence_auth import save_users

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    password = secrets.token_urlsafe(12)
    admin = User(
        id=secrets.token_hex(8),
        username="admin",
        password_hash=pwd_ctx.hash(password),
        role="admin",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    save_users(UserDocument(users=[admin]))
    print(f"[myhome] First boot — admin password: {password}", flush=True)


_first_boot()

from .persistence_homes import migrate_legacy_if_needed
migrate_legacy_if_needed()


# ── Auth middleware ────────────────────────────────────────────────────────

_EXEMPT_PATHS = {"/api/auth/login", "/api/auth/refresh"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path in _EXEMPT_PATHS:
        return await call_next(request)
    user = await get_user_from_request(request)
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
    return await call_next(request)


# ── MCP gate ──────────────────────────────────────────────────────────────
# The MCP tool surface is always mounted, but only reachable while enabled in
# Settings. Authentication still applies either way (auth_middleware above runs
# first) -- this only controls whether an *authenticated* request gets a real
# response or a 404.

async def _gated_mcp_app(scope, receive, send):
    if scope["type"] == "http" and not load_mcp_config().enabled:
        response = JSONResponse({"detail": "MCP server is disabled"}, status_code=404)
        await response(scope, receive, send)
        return
    await mcp_asgi_app(scope, receive, send)


# ── Routers ───────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(homes.router)
app.include_router(house.router)
app.include_router(svg.router)
app.include_router(ha.router)
app.include_router(chores.router)
app.include_router(inventory.router)
app.include_router(settings.router)
app.include_router(costs.router)
app.include_router(works.router)
app.include_router(kb.router)
app.include_router(backup.router)
app.include_router(consumables.router)
app.include_router(mcp_config.router)

app.mount("/mcp", _gated_mcp_app)


# ── Static files ──────────────────────────────────────────────────────────

_static_dir = Path(os.environ.get("STATIC_DIR", "/app/static"))
if _static_dir.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
```

- [ ] **Step 3: Run the full backend suite to confirm nothing regressed**

Run: `pytest -q`
Expected: all tests pass, including every `test_mcp_*` file from Tasks 2–12 (the middleware/lifespan changes don't touch any existing route's behavior — the only change to a pre-existing code path is the new `not request.url.path.startswith("/mcp")` clause, which is a no-op for every path that isn't `/mcp`)

- [ ] **Step 4: Write the integration tests**

Create `packages/backend/tests/test_mcp_integration.py`:

```python
import httpx
import pytest
from fastapi.testclient import TestClient
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from myhome.main import app
from myhome.models_auth import User, UserDocument
from myhome.models_mcp import McpConfig
from myhome.persistence_auth import save_users
from myhome.persistence_mcp import save_mcp_config


def _seed_admin_and_token(role: str = "admin") -> str:
    from passlib.context import CryptContext

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    save_users(UserDocument(users=[
        User(id="u-admin", username="admin", password_hash=pwd_ctx.hash("admin123"),
             role="admin", created_at="2026-01-01T00:00:00+00:00"),
    ]))
    tc = TestClient(app)
    tc.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token_resp = tc.post("/api/auth/tokens", json={"name": "MCP Test", "role": role})
    return token_resp.json()["token"]


async def _call_tool(headers: dict, tool_name: str, arguments: dict):
    transport = httpx.ASGITransport(app=app)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver", headers=headers)
    async with app.router.lifespan_context(app):
        async with streamable_http_client("http://testserver/mcp", http_client=http_client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(tool_name, arguments)


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-mcp-integration")


def test_mcp_disabled_returns_404_even_when_authenticated():
    token = _seed_admin_and_token()
    tc = TestClient(app)
    resp = tc.post("/mcp", headers={"Authorization": f"Bearer {token}"}, json={})
    assert resp.status_code == 404


def test_mcp_unauthenticated_request_returns_401():
    tc = TestClient(app)
    resp = tc.post("/mcp", json={})
    assert resp.status_code == 401


async def test_mcp_admin_token_can_list_and_create_home():
    token = _seed_admin_and_token()
    save_mcp_config(McpConfig(enabled=True))

    read_result = await _call_tool({"Authorization": f"Bearer {token}"}, "list_homes", {})
    assert read_result.isError is not True

    write_result = await _call_tool(
        {"Authorization": f"Bearer {token}"}, "create_home", {"name": "New Home", "type": "existing"},
    )
    assert write_result.isError is not True


async def test_mcp_ro_token_can_read_but_not_write():
    token = _seed_admin_and_token(role="ro")
    save_mcp_config(McpConfig(enabled=True))

    read_result = await _call_tool({"Authorization": f"Bearer {token}"}, "list_homes", {})
    assert read_result.isError is not True

    write_result = await _call_tool(
        {"Authorization": f"Bearer {token}"}, "create_home", {"name": "Nope", "type": "existing"},
    )
    assert write_result.isError is True
```

- [ ] **Step 5: Run the integration tests**

Run: `pytest tests/test_mcp_integration.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Run the full backend suite one more time**

Run: `pytest -q`
Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add packages/backend/src/myhome/mcp_app.py packages/backend/src/myhome/main.py \
        packages/backend/tests/test_mcp_integration.py
git commit -m "feat: mount and gate the MCP server in the FastAPI app"
```

---

## Task 14: Settings UI — MCP Server card

**Files:**
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte`
- Test: `packages/editor/test/SettingsPage.test.ts`

- [ ] **Step 1: Write the failing tests**

Add a new `describe` block to `packages/editor/test/SettingsPage.test.ts` (append at the end of the file, after the "Users tab" block):

```ts
describe("SettingsPage — MCP Server (admin only)", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("shows the MCP Server card for admin", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    flushSync();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("MCP Server");
    unmount(app);
  });

  it("hides the MCP Server card for non-admin", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("normal") } });
    flushSync();
    const cards = [...target.querySelectorAll(".ui-card")].map((c) => c.textContent);
    expect(cards.some((t) => t?.includes("MCP Server"))).toBe(false);
    unmount(app);
  });

  it("does not show the connection URL while disabled", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    flushSync();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).not.toContain("Connection URL");
    unmount(app);
  });

  it("shows the connection URL once enabled", async () => {
    fetchMock = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      if (url === "/api/auth/tokens") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/auth/users") return Promise.resolve({ ok: true, json: async () => [] });
      if (url === "/api/mcp/config" && opts?.method === "PUT") {
        return Promise.resolve({ ok: true, json: async () => ({ enabled: true }) });
      }
      if (url === "/api/mcp/config") return Promise.resolve({ ok: true, json: async () => ({ enabled: false }) });
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;

    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    flushSync();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    const checkbox = [...target.querySelectorAll('input[type="checkbox"]')].find(
      (el) => el.closest(".ui-card")?.textContent?.includes("MCP Server"),
    ) as HTMLInputElement;
    checkbox.click();
    await new Promise((r) => setTimeout(r, 0));
    flushSync();

    expect(target.textContent).toContain("Connection URL");
    unmount(app);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npx vitest run test/SettingsPage.test.ts`
Expected: FAIL — the new `describe` block's assertions fail (no "MCP Server" text exists yet)

- [ ] **Step 3: Add the script logic**

In `packages/editor/src/lib/components/SettingsPage.svelte`, add this block in the `<script>` section, right after the "Users (admin only)" `deleteUser` function and before the `// --- Backup & Restore ---` comment (i.e. right before `let downloadingBackup = $state(false);`):

```ts
  // --- MCP Server (admin only) ---
  let mcpEnabled = $state(false);
  let mcpConfigLoaded = $state(false);
  let mcpError = $state<string | null>(null);

  async function loadMcpConfig(): Promise<void> {
    if (authStore.user?.role !== "admin") return;
    try {
      const resp = await fetch("/api/mcp/config");
      if (!resp.ok) return;
      const data = await resp.json();
      mcpEnabled = data.enabled;
    } finally {
      mcpConfigLoaded = true;
    }
  }

  async function toggleMcpEnabled(): Promise<void> {
    const next = !mcpEnabled;
    mcpError = null;
    const resp = await fetch("/api/mcp/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: next }),
    });
    if (!resp.ok) { mcpError = `Error ${resp.status}`; return; }
    mcpEnabled = next;
  }

  loadMcpConfig();
```

- [ ] **Step 4: Add the markup**

In the same file, add a new `<Card>` block right after the "Users (admin only)" `{/if}` (i.e. right after the closing of the Users card block, before the `<!-- Backup & Restore -->` comment):

```svelte
    <!-- MCP Server (admin only) -->
    {#if authStore.user?.role === "admin"}
      <Card>
        <div class="section-header">
          <h2>MCP Server</h2>
        </div>
        <p class="section-desc">
          Lets an MCP client (Claude Desktop, claude.ai, Claude Code, or Home Assistant's
          Assist) query and act on this home's data. Create an API token above with the
          access level you want the assistant to have, then use it as the Bearer token
          when connecting.
        </p>
        {#if mcpConfigLoaded}
          <label class="module-row">
            <input type="checkbox" checked={mcpEnabled} onchange={toggleMcpEnabled} />
            <span class="mod-label">Enable MCP Server</span>
          </label>
          {#if mcpEnabled}
            <p class="empty-hint">Connection URL: <code>{window.location.origin}/mcp</code></p>
          {/if}
        {/if}
        {#if mcpError}<div class="error">{mcpError}</div>{/if}
      </Card>
    {/if}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `npx vitest run test/SettingsPage.test.ts`
Expected: PASS (all tests in the file, including the 4 new ones)

- [ ] **Step 6: Run the full frontend suite to check for regressions**

Run: `npm test`
Expected: all tests pass

- [ ] **Step 7: Run the typecheck**

Run: `npm run typecheck`
Expected: no errors

- [ ] **Step 8: Commit**

```bash
git add packages/editor/src/lib/components/SettingsPage.svelte packages/editor/test/SettingsPage.test.ts
git commit -m "feat: add MCP Server toggle to Settings (admin only)"
```

---

## Task 15: Manual end-to-end verification

Automated tests cover the tool logic, the auth/permission wiring, and the on/off gate. They do not exercise the real Streamable HTTP handshake against a real MCP client over the network — do that once here before considering this done.

- [ ] **Step 1: Start the dev backend with a real DATA_DIR**

Run: `cd packages/backend && DATA_DIR=/tmp/myhome-mcp-verify uvicorn myhome.main:app --reload --port 8000`
Expected: server starts; console prints `[myhome] First boot — admin password: <password>` (copy it)

- [ ] **Step 2: Log in and enable MCP + create a token**

```bash
curl -s -c /tmp/myhome-cookies.txt -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' -d '{"username":"admin","password":"<password from step 1>"}'

curl -s -b /tmp/myhome-cookies.txt -X PUT http://localhost:8000/api/mcp/config \
  -H 'Content-Type: application/json' -d '{"enabled": true}'

curl -s -b /tmp/myhome-cookies.txt -X POST http://localhost:8000/api/auth/tokens \
  -H 'Content-Type: application/json' -d '{"name":"Manual Verify","role":"admin"}'
```

Expected: last response includes a `"token"` field — copy the raw token string.

- [ ] **Step 3: Drive the server with the MCP Inspector**

Run: `npx @modelcontextprotocol/inspector`
In the Inspector UI: set Transport to "Streamable HTTP", URL to `http://localhost:8000/mcp`, and add a header `Authorization: Bearer <token from step 2>`. Connect.
Expected: the Inspector's tool list shows all ~26 tools across homes/settings/chores/inventory/consumables/costs/works/kb.

- [ ] **Step 4: Exercise one read and one write tool**

In the Inspector, call `list_homes` with no arguments — expect an empty list (or your test homes if any exist). Then call `create_home` with `{"name": "Verify Home", "type": "existing"}` — expect a success result containing the new home's `id`. Call `list_homes` again and confirm the new home appears.

- [ ] **Step 5: Confirm the disable switch actually blocks it**

```bash
curl -s -b /tmp/myhome-cookies.txt -X PUT http://localhost:8000/api/mcp/config \
  -H 'Content-Type: application/json' -d '{"enabled": false}'
```

In the Inspector, try calling `list_homes` again.
Expected: the connection/request fails (404) — the Inspector should surface this as a transport-level error.

- [ ] **Step 6: Clean up**

Stop the dev server (Ctrl-C) and remove the scratch data dir: `rm -rf /tmp/myhome-mcp-verify`

No commit for this task — it's verification only, not a code change.

---

## Summary of new/changed files

**New:**
- `packages/backend/src/myhome/models_mcp.py`
- `packages/backend/src/myhome/persistence_mcp.py`
- `packages/backend/src/myhome/routes/mcp_config.py`
- `packages/backend/src/myhome/chore_scheduling.py`
- `packages/backend/src/myhome/mcp_server.py`
- `packages/backend/src/myhome/mcp_tools_homes.py`
- `packages/backend/src/myhome/mcp_tools_settings.py`
- `packages/backend/src/myhome/mcp_tools_chores.py`
- `packages/backend/src/myhome/mcp_tools_inventory.py`
- `packages/backend/src/myhome/mcp_tools_consumables.py`
- `packages/backend/src/myhome/mcp_tools_costs.py`
- `packages/backend/src/myhome/mcp_tools_works.py`
- `packages/backend/src/myhome/mcp_tools_kb.py`
- `packages/backend/src/myhome/mcp_app.py`
- 12 new backend test files, 1 new frontend `describe` block

**Modified:**
- `packages/backend/pyproject.toml` (new dependency)
- `packages/backend/src/myhome/routes/chores.py` (scheduling logic extracted)
- `packages/backend/src/myhome/main.py` (lifespan, mount, gate, middleware exemption, new router)
- `packages/editor/src/lib/components/SettingsPage.svelte` (new admin-only card)

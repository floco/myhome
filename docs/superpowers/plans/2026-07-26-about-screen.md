# About Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an About tab to Settings showing the running app version, deployment/runtime system info, and whether a newer version is available, and fix a likely contributor to "the UI still looks stale after an update" by adding correct cache headers to the served frontend assets.

**Architecture:** One new backend endpoint (`GET /api/system/info`) aggregates static system facts plus a GitHub-tags-based update check (cached in-process for 1 hour). One new frontend Settings tab (`SettingsAbout.svelte`) fetches and renders it. A small `StaticFiles` subclass fixes cache headers on the existing static-file mount.

**Tech Stack:** FastAPI/Starlette + httpx (backend), Svelte 5 + svelte-i18n (frontend), pytest + respx (backend tests), vitest (frontend tests).

## Global Constraints

- Version strings are plain `X.Y.Z` (no `v` prefix, no pre-release suffixes) — matches `addon/config.yaml`'s existing `version:` field, which the release workflow already validates against the git tag.
- **JSON API fields are camelCase, not snake_case** — this codebase's existing models define fields directly as camelCase in Python (e.g. `ActivityEntry.userId`, `ActivityEntry.entityLabel` in `models_activity.py`; `ScheduledBackupConfig`'s `dayOfWeek`/`retentionCount` on the frontend). Every new dict key returned from `/api/system/info` must follow this, even though it's a plain dict rather than a Pydantic model.
- `require_auth()` with no argument defaults to `min_role="ro"` — the lowest role. Use it bare for anything all logged-in users should see (matches this feature's "all logged-in users" access decision from the design spec).
- Every user-facing string needs a key in **both** `packages/editor/src/lib/locales/en.json` and `fr.json` — the app is fully i18n'd and a missing French key is a real gap, not a follow-up.
- Outbound network calls (the GitHub tags check) must never turn into a page-level error — degrade to `"unknown"` on any failure.
- New backend modules follow the codebase's existing per-module `_data_dir()` helper convention (`Path(os.environ.get("DATA_DIR", "/data"))`) rather than importing another module's private helper.

---

### Task 1: Version baking + static system-info fields

**Files:**
- Modify: `Dockerfile`
- Create: `packages/backend/src/myhome/system_info.py`
- Test: `packages/backend/tests/test_system_info.py`

**Interfaces:**
- Produces: `system_info.get_app_version() -> str`, `system_info.get_deployment_mode() -> str`, `system_info.get_uptime_seconds() -> int`, `system_info.get_home_count() -> int`, `system_info.get_database_size_bytes() -> int`, `system_info.get_static_system_info() -> dict` (keys: `version`, `deploymentMode`, `pythonVersion`, `arch`, `dbSchemaVersion`, `homeCount`, `databaseSizeBytes`, `uptimeSeconds`).

- [ ] **Step 1: Bake the version into the image**

Modify `Dockerfile` — in Stage 2, insert this right before the existing `COPY addon/run.sh /run.sh` line:

```dockerfile
COPY addon/config.yaml /tmp/addon-config.yaml
RUN grep '^version:' /tmp/addon-config.yaml | sed 's/version: *"\(.*\)"/\1/' > /app/VERSION \
    && rm /tmp/addon-config.yaml
```

So the relevant section of `Dockerfile` reads:

```dockerfile
COPY --from=frontend-build /build/packages/editor/dist ./static
COPY addon/config.yaml /tmp/addon-config.yaml
RUN grep '^version:' /tmp/addon-config.yaml | sed 's/version: *"\(.*\)"/\1/' > /app/VERSION \
    && rm /tmp/addon-config.yaml
COPY addon/run.sh /run.sh
RUN chmod +x /run.sh
ENV STATIC_DIR=/app/static
EXPOSE 8000
CMD ["/run.sh"]
```

- [ ] **Step 2: Write the failing tests**

Create `packages/backend/tests/test_system_info.py`:

```python
from myhome import system_info


def test_get_app_version_reads_version_file(tmp_path, monkeypatch):
    version_file = tmp_path / "VERSION"
    version_file.write_text("1.2.3\n")
    monkeypatch.setenv("APP_VERSION_FILE", str(version_file))
    assert system_info.get_app_version() == "1.2.3"


def test_get_app_version_returns_unknown_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_VERSION_FILE", str(tmp_path / "does-not-exist"))
    assert system_info.get_app_version() == "unknown"


def test_get_deployment_mode_detects_home_assistant(monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "abc")
    assert system_info.get_deployment_mode() == "home_assistant"


def test_get_deployment_mode_detects_standalone(monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    assert system_info.get_deployment_mode() == "standalone"


def test_get_home_count_reflects_created_homes(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from myhome.persistence_homes import create_home
    assert system_info.get_home_count() == 0
    create_home("Test Home", "existing")
    assert system_info.get_home_count() == 1


def test_get_database_size_bytes_zero_when_no_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert system_info.get_database_size_bytes() == 0


def test_get_database_size_bytes_positive_once_db_created(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from myhome.persistence_homes import create_home
    create_home("Test Home", "existing")
    assert system_info.get_database_size_bytes() > 0


def test_get_uptime_seconds_is_nonnegative():
    assert system_info.get_uptime_seconds() >= 0


def test_get_static_system_info_shape(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    version_file = tmp_path / "VERSION"
    version_file.write_text("0.8.0")
    monkeypatch.setenv("APP_VERSION_FILE", str(version_file))
    info = system_info.get_static_system_info()
    assert info["version"] == "0.8.0"
    assert info["deploymentMode"] == "standalone"
    assert info["dbSchemaVersion"] == 6
    assert info["homeCount"] == 0
    assert info["databaseSizeBytes"] == 0
    assert info["uptimeSeconds"] >= 0
    assert isinstance(info["pythonVersion"], str)
    assert isinstance(info["arch"], str)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest packages/backend/tests/test_system_info.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.system_info'`

- [ ] **Step 4: Implement `system_info.py`**

Create `packages/backend/src/myhome/system_info.py`:

```python
# packages/backend/src/myhome/system_info.py
from __future__ import annotations

import os
import platform
from datetime import datetime, timezone
from pathlib import Path

from .migrations import CURRENT_VERSION as DB_SCHEMA_VERSION
from .persistence_homes import load_homes

_START_TIME = datetime.now(timezone.utc)


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data"))


def _db_path() -> Path:
    return _data_dir() / "myhome.db"


def get_app_version() -> str:
    version_file = Path(os.environ.get("APP_VERSION_FILE", "/app/VERSION"))
    if not version_file.exists():
        return "unknown"
    return version_file.read_text().strip()


def get_deployment_mode() -> str:
    return "home_assistant" if os.environ.get("SUPERVISOR_TOKEN") else "standalone"


def get_uptime_seconds() -> int:
    return int((datetime.now(timezone.utc) - _START_TIME).total_seconds())


def get_home_count() -> int:
    return len(load_homes().homes)


def get_database_size_bytes() -> int:
    db_path = _db_path()
    if not db_path.exists():
        return 0
    return db_path.stat().st_size


def get_static_system_info() -> dict:
    return {
        "version": get_app_version(),
        "deploymentMode": get_deployment_mode(),
        "pythonVersion": platform.python_version(),
        "arch": platform.machine(),
        "dbSchemaVersion": DB_SCHEMA_VERSION,
        "homeCount": get_home_count(),
        "databaseSizeBytes": get_database_size_bytes(),
        "uptimeSeconds": get_uptime_seconds(),
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest packages/backend/tests/test_system_info.py -v`
Expected: PASS (9 tests)

- [ ] **Step 6: Commit**

```bash
git add Dockerfile packages/backend/src/myhome/system_info.py packages/backend/tests/test_system_info.py
git commit -m "feat(about): bake app version into image, add static system-info fields"
```

---

### Task 2: Update-check against GitHub tags

**Files:**
- Modify: `packages/backend/src/myhome/system_info.py`
- Test: `packages/backend/tests/test_system_info.py`

**Interfaces:**
- Consumes: nothing new from Task 1 besides the same module.
- Produces: `system_info.check_for_update(current_version: str) -> dict` (keys: `status` — `"up_to_date" | "update_available" | "unknown"`, `latestVersion: str | None`, `checkedAt: str | None` ISO-8601), `system_info.reset_update_cache() -> None` (test helper), module constant `system_info._GITHUB_TAGS_URL`.

- [ ] **Step 1: Write the failing tests**

Append to `packages/backend/tests/test_system_info.py`:

```python
import httpx
import pytest
import respx
from httpx import Response

from myhome import system_info


@pytest.fixture(autouse=True)
def _reset_update_cache():
    system_info.reset_update_cache()
    yield
    system_info.reset_update_cache()


async def test_check_for_update_detects_update_available():
    with respx.mock:
        respx.get(system_info._GITHUB_TAGS_URL).mock(
            return_value=Response(200, json=[{"name": "v0.9.0"}, {"name": "v0.8.0"}])
        )
        result = await system_info.check_for_update("0.8.0")
    assert result["status"] == "update_available"
    assert result["latestVersion"] == "0.9.0"
    assert result["checkedAt"] is not None


async def test_check_for_update_detects_up_to_date():
    with respx.mock:
        respx.get(system_info._GITHUB_TAGS_URL).mock(
            return_value=Response(200, json=[{"name": "v0.8.0"}, {"name": "v0.7.1"}])
        )
        result = await system_info.check_for_update("0.8.0")
    assert result["status"] == "up_to_date"
    assert result["latestVersion"] == "0.8.0"


async def test_check_for_update_returns_unknown_on_network_failure():
    with respx.mock:
        respx.get(system_info._GITHUB_TAGS_URL).mock(side_effect=httpx.ConnectError("boom"))
        result = await system_info.check_for_update("0.8.0")
    assert result["status"] == "unknown"
    assert result["latestVersion"] is None


async def test_check_for_update_handles_unparseable_current_version():
    with respx.mock:
        respx.get(system_info._GITHUB_TAGS_URL).mock(
            return_value=Response(200, json=[{"name": "v0.8.0"}])
        )
        result = await system_info.check_for_update("unknown")
    assert result["status"] == "unknown"


async def test_check_for_update_falls_back_to_cached_result_on_later_failure():
    with respx.mock:
        respx.get(system_info._GITHUB_TAGS_URL).mock(
            return_value=Response(200, json=[{"name": "v0.8.0"}])
        )
        first = await system_info.check_for_update("0.8.0")
    assert first["status"] == "up_to_date"

    # Force the cache to look stale so the next call re-fetches.
    system_info._update_cache["checkedAt"] = "2000-01-01T00:00:00+00:00"

    with respx.mock:
        respx.get(system_info._GITHUB_TAGS_URL).mock(side_effect=httpx.ConnectError("boom"))
        second = await system_info.check_for_update("0.8.0")
    assert second["status"] == "up_to_date"
    assert second["latestVersion"] == "0.8.0"


async def test_check_for_update_uses_cache_within_ttl():
    with respx.mock:
        route = respx.get(system_info._GITHUB_TAGS_URL).mock(
            return_value=Response(200, json=[{"name": "v0.8.0"}])
        )
        await system_info.check_for_update("0.8.0")
        await system_info.check_for_update("0.8.0")
    assert route.call_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest packages/backend/tests/test_system_info.py -v -k check_for_update`
Expected: FAIL with `AttributeError: module 'myhome.system_info' has no attribute '_GITHUB_TAGS_URL'`

- [ ] **Step 3: Implement the update check**

Modify `packages/backend/src/myhome/system_info.py` — add `import re` and `import httpx` to the top-of-file imports alongside the existing ones, so the import block reads:

```python
import os
import platform
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .migrations import CURRENT_VERSION as DB_SCHEMA_VERSION
from .persistence_homes import load_homes
```

Then append at the bottom of the file:

```python
_GITHUB_TAGS_URL = "https://api.github.com/repos/floco/myhome/tags"
_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
_UPDATE_CACHE_TTL_SECONDS = 3600

_update_cache: dict[str, object] = {"status": "unknown", "latestVersion": None, "checkedAt": None}


def reset_update_cache() -> None:
    """Test helper -- clears the module-level update-check cache."""
    _update_cache.update({"status": "unknown", "latestVersion": None, "checkedAt": None})


def _version_tuple(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


async def _fetch_latest_tag_version() -> str | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(_GITHUB_TAGS_URL, headers={"User-Agent": "myhome-app"}, timeout=5.0)
        resp.raise_for_status()
        tags = resp.json()
    versions: list[tuple[int, int, int]] = []
    for tag in tags:
        match = _TAG_RE.match(tag.get("name", ""))
        if match:
            versions.append(tuple(int(g) for g in match.groups()))
    if not versions:
        return None
    latest = max(versions)
    return ".".join(str(part) for part in latest)


async def check_for_update(current_version: str) -> dict:
    now = datetime.now(timezone.utc)
    checked_at = _update_cache["checkedAt"]
    if checked_at is not None:
        age = (now - datetime.fromisoformat(checked_at)).total_seconds()
        if age < _UPDATE_CACHE_TTL_SECONDS:
            return dict(_update_cache)

    try:
        latest = await _fetch_latest_tag_version()
    except httpx.HTTPError:
        if checked_at is not None:
            return dict(_update_cache)
        return {"status": "unknown", "latestVersion": None, "checkedAt": None}

    if latest is None:
        status = "unknown"
    else:
        try:
            status = "update_available" if _version_tuple(latest) > _version_tuple(current_version) else "up_to_date"
        except ValueError:
            status = "unknown"

    _update_cache.update({
        "status": status,
        "latestVersion": latest,
        "checkedAt": now.isoformat(),
    })
    return dict(_update_cache)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest packages/backend/tests/test_system_info.py -v`
Expected: PASS (15 tests total)

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/system_info.py packages/backend/tests/test_system_info.py
git commit -m "feat(about): check GitHub tags for a newer version, with 1h cache"
```

---

### Task 3: `/api/system/info` endpoint

**Files:**
- Create: `packages/backend/src/myhome/routes/system.py`
- Modify: `packages/backend/src/myhome/main.py`
- Test: `packages/backend/tests/test_system_route.py`

**Interfaces:**
- Consumes: `system_info.get_static_system_info()`, `system_info.check_for_update(current_version)`, `system_info.reset_update_cache()`, `system_info._GITHUB_TAGS_URL` (Task 1 & 2), `deps.require_auth()` (existing).
- Produces: `GET /api/system/info` — same shape as `get_static_system_info()` plus an `updateCheck` key (`{status, latestVersion, checkedAt}`).

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_system_route.py`:

```python
import respx
from fastapi.testclient import TestClient
from httpx import Response

from myhome import system_info
from myhome.main import app


def test_get_system_info_requires_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    tc = TestClient(app)
    resp = tc.get("/api/system/info")
    assert resp.status_code == 401


def test_get_system_info_returns_full_shape(client, tmp_path, monkeypatch):
    version_file = tmp_path / "VERSION"
    version_file.write_text("0.8.0")
    monkeypatch.setenv("APP_VERSION_FILE", str(version_file))
    system_info.reset_update_cache()
    with respx.mock:
        respx.get(system_info._GITHUB_TAGS_URL).mock(
            return_value=Response(200, json=[{"name": "v0.9.0"}])
        )
        resp = client.get("/api/system/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "0.8.0"
    assert data["deploymentMode"] == "standalone"
    assert data["dbSchemaVersion"] == 6
    assert isinstance(data["pythonVersion"], str)
    assert isinstance(data["arch"], str)
    assert data["uptimeSeconds"] >= 0
    assert data["homeCount"] == 0
    assert data["databaseSizeBytes"] >= 0
    assert data["updateCheck"]["status"] == "update_available"
    assert data["updateCheck"]["latestVersion"] == "0.9.0"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest packages/backend/tests/test_system_route.py -v`
Expected: FAIL with 404 (route doesn't exist yet)

- [ ] **Step 3: Implement the route**

Create `packages/backend/src/myhome/routes/system.py`:

```python
from fastapi import APIRouter

from ..deps import require_auth
from ..system_info import check_for_update, get_static_system_info

router = APIRouter()


@router.get("/api/system/info")
async def get_system_info(current_user: tuple[str, str] = require_auth()) -> dict:
    info = get_static_system_info()
    info["updateCheck"] = await check_for_update(info["version"])
    return info
```

Modify `packages/backend/src/myhome/main.py`:

Change:
```python
from .routes import activity, auth, backup, build, chores, consumables, contacts, costs, ha, homes, house, insurance, inventory, kb, locations, mcp_config, notifications, properties, settings, svg, works
```
to:
```python
from .routes import activity, auth, backup, build, chores, consumables, contacts, costs, ha, homes, house, insurance, inventory, kb, locations, mcp_config, notifications, properties, settings, svg, system, works
```

Change:
```python
app.include_router(activity.router)
```
to:
```python
app.include_router(activity.router)
app.include_router(system.router)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest packages/backend/tests/test_system_route.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full backend suite**

Run: `pytest packages/backend -q`
Expected: all tests pass (no regressions from the router registration change)

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/routes/system.py packages/backend/src/myhome/main.py packages/backend/tests/test_system_route.py
git commit -m "feat(about): add GET /api/system/info endpoint"
```

---

### Task 4: Cache-Control headers on static files

**Files:**
- Create: `packages/backend/src/myhome/caching_static.py`
- Modify: `packages/backend/src/myhome/main.py`
- Test: `packages/backend/tests/test_caching_static.py`

**Interfaces:**
- Produces: `caching_static.CachingStaticFiles` (drop-in subclass of `starlette.staticfiles.StaticFiles`).

- [ ] **Step 1: Write the failing tests**

Create `packages/backend/tests/test_caching_static.py`:

```python
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.testclient import TestClient

from myhome.caching_static import CachingStaticFiles


def _make_client(tmp_path):
    (tmp_path / "index.html").write_text("<html>shell</html>")
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "app-abc123.js").write_text("console.log(1)")
    app = Starlette(routes=[Mount("/", app=CachingStaticFiles(directory=str(tmp_path), html=True))])
    return TestClient(app)


def test_index_html_is_not_cached(tmp_path):
    client = _make_client(tmp_path)
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "no-cache"


def test_hashed_asset_is_cached_immutably(tmp_path):
    client = _make_client(tmp_path)
    resp = client.get("/assets/app-abc123.js")
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "public, max-age=31536000, immutable"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest packages/backend/tests/test_caching_static.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'myhome.caching_static'`

- [ ] **Step 3: Implement `CachingStaticFiles`**

Create `packages/backend/src/myhome/caching_static.py`:

```python
# packages/backend/src/myhome/caching_static.py
"""A StaticFiles variant that sets sane Cache-Control headers.

Plain Starlette StaticFiles sends only Last-Modified/ETag with no explicit
Cache-Control, which lets browsers apply their own caching heuristics to
index.html -- so after a fresh deploy, a client can keep rendering the old
UI until something forces a revalidation. index.html is tiny, so we just
disable caching on it outright; everything else (Vite's content-hashed
JS/CSS/asset files) is safe to cache for a long time, since a new build
always produces new filenames.
"""
from __future__ import annotations

import os

from starlette.staticfiles import FileResponse, Headers, NotModifiedResponse, StaticFiles


class CachingStaticFiles(StaticFiles):
    def file_response(self, full_path, stat_result, scope, status_code=200):
        request_headers = Headers(scope=scope)
        response = FileResponse(full_path, status_code=status_code, stat_result=stat_result)
        if os.path.basename(str(full_path)) == "index.html":
            response.headers["cache-control"] = "no-cache"
        else:
            response.headers["cache-control"] = "public, max-age=31536000, immutable"
        if self.is_not_modified(response.headers, request_headers):
            return NotModifiedResponse(response.headers)
        return response
```

Modify `packages/backend/src/myhome/main.py` — change:
```python
_static_dir = Path(os.environ.get("STATIC_DIR", "/app/static"))
if _static_dir.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
```
to:
```python
_static_dir = Path(os.environ.get("STATIC_DIR", "/app/static"))
if _static_dir.exists():
    from .caching_static import CachingStaticFiles

    app.mount("/", CachingStaticFiles(directory=str(_static_dir), html=True), name="static")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest packages/backend/tests/test_caching_static.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full backend suite**

Run: `pytest packages/backend -q`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add packages/backend/src/myhome/caching_static.py packages/backend/src/myhome/main.py packages/backend/tests/test_caching_static.py
git commit -m "fix(static): set explicit Cache-Control headers (no-cache shell, immutable assets)"
```

---

### Task 5: `SettingsAbout.svelte` component

**Files:**
- Create: `packages/editor/src/lib/components/settings/SettingsAbout.svelte`
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`
- Test: `packages/editor/test/SettingsAbout.test.ts`

**Interfaces:**
- Consumes: `GET /api/system/info` (Task 3's response shape: `{version, deploymentMode, pythonVersion, arch, dbSchemaVersion, homeCount, databaseSizeBytes, uptimeSeconds, updateCheck: {status, latestVersion, checkedAt}}`) via plain `fetch()` (the app's `ingressFetchShim` already rewrites `/api/...` paths, so no `apiUrl()` wrapper is needed — same pattern as `SettingsBackup.svelte`).
- Produces: `SettingsAbout.svelte` (no props).

- [ ] **Step 1: Add locale keys**

In `packages/editor/src/lib/locales/en.json`, change:
```json
    "nav": {
      "general": "General",
      "categories": "Categories",
      "notifications": "Notifications",
      "security": "Security & Access",
      "integrations": "Integrations",
      "backup": "Backup & Restore",
      "activity": "Activity Log"
    },
```
to:
```json
    "nav": {
      "general": "General",
      "categories": "Categories",
      "notifications": "Notifications",
      "security": "Security & Access",
      "integrations": "Integrations",
      "backup": "Backup & Restore",
      "activity": "Activity Log",
      "about": "About"
    },
```

And change:
```json
    "notifications": {
      "desc": "Surface chores due soon, low-stock consumables, and expiring warranties in one place, with an optional daily summary pushed to Home Assistant.",
      "enable": "Enable notification center",
      "choresThreshold": "Chores \"due soon\" threshold (fraction of period remaining)",
      "warrantyWindow": "Warranty \"expiring soon\" window (days)",
      "haDigest": "Send a daily digest via Home Assistant",
      "haNotifyService": "HA notify service",
      "haNotifyServicePlaceholder": "e.g. notify.mobile_app_pixel",
      "digestTime": "Digest time (UTC, HH:MM)"
    }
  },
```
to:
```json
    "notifications": {
      "desc": "Surface chores due soon, low-stock consumables, and expiring warranties in one place, with an optional daily summary pushed to Home Assistant.",
      "enable": "Enable notification center",
      "choresThreshold": "Chores \"due soon\" threshold (fraction of period remaining)",
      "warrantyWindow": "Warranty \"expiring soon\" window (days)",
      "haDigest": "Send a daily digest via Home Assistant",
      "haNotifyService": "HA notify service",
      "haNotifyServicePlaceholder": "e.g. notify.mobile_app_pixel",
      "digestTime": "Digest time (UTC, HH:MM)"
    },
    "about": {
      "appName": "My Home",
      "updateAvailable": "Update available: v{version}",
      "upToDate": "You're up to date",
      "updateUnknown": "Unable to check for updates",
      "deploymentMode": "Deployment",
      "deploymentHa": "Home Assistant add-on",
      "deploymentStandalone": "Standalone Docker",
      "pythonVersion": "Backend runtime",
      "architecture": "Architecture",
      "dbSchemaVersion": "Database schema version",
      "homeCount": "Homes",
      "databaseSize": "Database size",
      "uptime": "Uptime",
      "loadFailed": "Unable to load system information."
    }
  },
```

In `packages/editor/src/lib/locales/fr.json`, change:
```json
    "nav": {
      "general": "Général",
      "categories": "Catégories",
      "notifications": "Notifications",
      "security": "Sécurité et accès",
      "integrations": "Intégrations",
      "backup": "Sauvegarde et restauration",
      "activity": "Journal d'activité"
    },
```
to:
```json
    "nav": {
      "general": "Général",
      "categories": "Catégories",
      "notifications": "Notifications",
      "security": "Sécurité et accès",
      "integrations": "Intégrations",
      "backup": "Sauvegarde et restauration",
      "activity": "Journal d'activité",
      "about": "À propos"
    },
```

And change:
```json
    "notifications": {
      "desc": "Regroupez les corvées bientôt dues, les consommables à stock faible et les garanties expirant, avec un résumé quotidien optionnel envoyé à Home Assistant.",
      "enable": "Activer le centre de notifications",
      "choresThreshold": "Seuil « bientôt dû » des corvées (fraction de la période restante)",
      "warrantyWindow": "Fenêtre « expire bientôt » des garanties (jours)",
      "haDigest": "Envoyer un résumé quotidien via Home Assistant",
      "haNotifyService": "Service de notification HA",
      "haNotifyServicePlaceholder": "ex. notify.mobile_app_pixel",
      "digestTime": "Heure du résumé (UTC, HH:MM)"
    }
  },
```
to:
```json
    "notifications": {
      "desc": "Regroupez les corvées bientôt dues, les consommables à stock faible et les garanties expirant, avec un résumé quotidien optionnel envoyé à Home Assistant.",
      "enable": "Activer le centre de notifications",
      "choresThreshold": "Seuil « bientôt dû » des corvées (fraction de la période restante)",
      "warrantyWindow": "Fenêtre « expire bientôt » des garanties (jours)",
      "haDigest": "Envoyer un résumé quotidien via Home Assistant",
      "haNotifyService": "Service de notification HA",
      "haNotifyServicePlaceholder": "ex. notify.mobile_app_pixel",
      "digestTime": "Heure du résumé (UTC, HH:MM)"
    },
    "about": {
      "appName": "My Home",
      "updateAvailable": "Mise à jour disponible : v{version}",
      "upToDate": "Vous êtes à jour",
      "updateUnknown": "Impossible de vérifier les mises à jour",
      "deploymentMode": "Déploiement",
      "deploymentHa": "Module complémentaire Home Assistant",
      "deploymentStandalone": "Docker autonome",
      "pythonVersion": "Moteur backend",
      "architecture": "Architecture",
      "dbSchemaVersion": "Version du schéma de base de données",
      "homeCount": "Logements",
      "databaseSize": "Taille de la base de données",
      "uptime": "Disponibilité",
      "loadFailed": "Impossible de charger les informations système."
    }
  },
```

- [ ] **Step 2: Write the failing component test**

Create `packages/editor/test/SettingsAbout.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsAbout from "../src/lib/components/settings/SettingsAbout.svelte";

describe("SettingsAbout", () => {
  let target: HTMLDivElement;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  async function mountWith(info: object) {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => info });
    const app = mount(SettingsAbout, { target });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    return app;
  }

  it("shows the version and an up-to-date badge", async () => {
    const app = await mountWith({
      version: "0.8.0", deploymentMode: "standalone", pythonVersion: "3.12.3",
      arch: "x86_64", dbSchemaVersion: 6, homeCount: 1, databaseSizeBytes: 2048,
      uptimeSeconds: 3661,
      updateCheck: { status: "up_to_date", latestVersion: "0.8.0", checkedAt: "2026-07-26T18:00:00Z" },
    });
    expect(target.textContent).toContain("0.8.0");
    expect(target.textContent).toContain("up to date");
    unmount(app);
  });

  it("shows an update-available link with the latest version", async () => {
    const app = await mountWith({
      version: "0.8.0", deploymentMode: "home_assistant", pythonVersion: "3.12.3",
      arch: "aarch64", dbSchemaVersion: 6, homeCount: 2, databaseSizeBytes: 4096,
      uptimeSeconds: 60,
      updateCheck: { status: "update_available", latestVersion: "0.9.0", checkedAt: "2026-07-26T18:00:00Z" },
    });
    expect(target.textContent).toContain("0.9.0");
    unmount(app);
  });

  it("shows a neutral message when the update check is unknown", async () => {
    const app = await mountWith({
      version: "0.8.0", deploymentMode: "standalone", pythonVersion: "3.12.3",
      arch: "x86_64", dbSchemaVersion: 6, homeCount: 0, databaseSizeBytes: 0,
      uptimeSeconds: 5,
      updateCheck: { status: "unknown", latestVersion: null, checkedAt: null },
    });
    expect(target.textContent).toContain("Unable to check for updates");
    unmount(app);
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `npm test -w @myhome/editor -- SettingsAbout --run`
Expected: FAIL (module `../src/lib/components/settings/SettingsAbout.svelte` doesn't exist)

- [ ] **Step 4: Implement `SettingsAbout.svelte`**

Create `packages/editor/src/lib/components/settings/SettingsAbout.svelte`:

```svelte
<!-- packages/editor/src/lib/components/settings/SettingsAbout.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import Card from "../ui/Card.svelte";

  interface UpdateCheck {
    status: "up_to_date" | "update_available" | "unknown";
    latestVersion: string | null;
    checkedAt: string | null;
  }
  interface SystemInfo {
    version: string;
    deploymentMode: string;
    pythonVersion: string;
    arch: string;
    dbSchemaVersion: number;
    homeCount: number;
    databaseSizeBytes: number;
    uptimeSeconds: number;
    updateCheck: UpdateCheck;
  }

  let info = $state<SystemInfo | null>(null);
  let loadError = $state<string | null>(null);

  async function load(): Promise<void> {
    try {
      const resp = await fetch("/api/system/info");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      info = await resp.json();
    } catch {
      loadError = $_('settings.about.loadFailed');
    }
  }

  load();

  function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function formatUptime(seconds: number): string {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  }
</script>

<Card>
  <div class="section-header">
    <h2>{$_('settings.nav.about')}</h2>
  </div>

  {#if loadError}
    <div class="error">{loadError}</div>
  {:else if info}
    <div class="version-headline">{$_('settings.about.appName')} v{info.version}</div>

    {#if info.updateCheck.status === "update_available"}
      <a
        class="update-status available"
        href="https://github.com/floco/myhome/tags"
        target="_blank"
        rel="noopener noreferrer"
      >
        {$_('settings.about.updateAvailable', { values: { version: info.updateCheck.latestVersion } })}
      </a>
    {:else if info.updateCheck.status === "up_to_date"}
      <div class="update-status uptodate">{$_('settings.about.upToDate')}</div>
    {:else}
      <div class="update-status unknown">{$_('settings.about.updateUnknown')}</div>
    {/if}

    <dl class="info-list">
      <div class="info-row">
        <dt>{$_('settings.about.deploymentMode')}</dt>
        <dd>{info.deploymentMode === "home_assistant" ? $_('settings.about.deploymentHa') : $_('settings.about.deploymentStandalone')}</dd>
      </div>
      <div class="info-row">
        <dt>{$_('settings.about.pythonVersion')}</dt>
        <dd>{info.pythonVersion}</dd>
      </div>
      <div class="info-row">
        <dt>{$_('settings.about.architecture')}</dt>
        <dd>{info.arch}</dd>
      </div>
      <div class="info-row">
        <dt>{$_('settings.about.dbSchemaVersion')}</dt>
        <dd>{info.dbSchemaVersion}</dd>
      </div>
      <div class="info-row">
        <dt>{$_('settings.about.homeCount')}</dt>
        <dd>{info.homeCount}</dd>
      </div>
      <div class="info-row">
        <dt>{$_('settings.about.databaseSize')}</dt>
        <dd>{formatBytes(info.databaseSizeBytes)}</dd>
      </div>
      <div class="info-row">
        <dt>{$_('settings.about.uptime')}</dt>
        <dd>{formatUptime(info.uptimeSeconds)}</dd>
      </div>
    </dl>
  {/if}
</Card>

<style>
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
  .error { color: var(--danger); font-size: 11px; margin-top: 6px; }

  .version-headline { font-size: 20px; font-weight: 700; color: var(--text); margin: var(--space-2) 0; }

  .update-status { display: inline-block; font-size: 12px; padding: 4px 10px; border-radius: 999px; margin-bottom: var(--space-3); text-decoration: none; }
  .update-status.uptodate { background: color-mix(in srgb, var(--success) 15%, transparent); color: var(--success); }
  .update-status.available { background: color-mix(in srgb, var(--accent) 15%, transparent); color: var(--accent); cursor: pointer; }
  .update-status.unknown { background: var(--surface-hover); color: var(--text-faint); }

  .info-list { display: flex; flex-direction: column; gap: 8px; margin: 0; }
  .info-row { display: flex; justify-content: space-between; gap: var(--space-3); padding: 6px 0; border-bottom: 1px solid var(--border); }
  .info-row dt { font-size: 12px; color: var(--text-muted); }
  .info-row dd { margin: 0; font-size: 12px; color: var(--text); font-weight: 600; }
</style>
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test -w @myhome/editor -- SettingsAbout --run`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsAbout.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/SettingsAbout.test.ts
git commit -m "feat(about): add SettingsAbout component and locale keys"
```

---

### Task 6: Wire the About tab into Settings

**Files:**
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte`
- Modify: `packages/editor/test/SettingsPage.test.ts`

**Interfaces:**
- Consumes: `SettingsAbout.svelte` (Task 5, no props).

- [ ] **Step 1: Write the failing test**

In `packages/editor/test/SettingsPage.test.ts`, extend the existing "shows all 7 groups" test to expect 8 groups and add "About". Change:
```ts
  it("shows all 7 groups for an admin, including Integrations and Activity Log", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin"), importFromDonetick: vi.fn(async () => 0) } });
    flushSync();
    const labels = [...target.querySelectorAll(".nav-item")].map((b) => b.textContent);
    expect(labels.some((l) => l?.includes("General"))).toBe(true);
    expect(labels.some((l) => l?.includes("Categories"))).toBe(true);
    expect(labels.some((l) => l?.includes("Notifications"))).toBe(true);
    expect(labels.some((l) => l?.includes("Security & Access"))).toBe(true);
    expect(labels.some((l) => l?.includes("Integrations"))).toBe(true);
    expect(labels.some((l) => l?.includes("Backup & Restore"))).toBe(true);
    expect(labels.some((l) => l?.includes("Activity Log"))).toBe(true);
    unmount(app);
  });
```
to:
```ts
  it("shows all 8 groups for an admin, including Integrations, Activity Log, and About", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin"), importFromDonetick: vi.fn(async () => 0) } });
    flushSync();
    const labels = [...target.querySelectorAll(".nav-item")].map((b) => b.textContent);
    expect(labels.some((l) => l?.includes("General"))).toBe(true);
    expect(labels.some((l) => l?.includes("Categories"))).toBe(true);
    expect(labels.some((l) => l?.includes("Notifications"))).toBe(true);
    expect(labels.some((l) => l?.includes("Security & Access"))).toBe(true);
    expect(labels.some((l) => l?.includes("Integrations"))).toBe(true);
    expect(labels.some((l) => l?.includes("Backup & Restore"))).toBe(true);
    expect(labels.some((l) => l?.includes("Activity Log"))).toBe(true);
    expect(labels.some((l) => l?.includes("About"))).toBe(true);
    unmount(app);
  });

  it("shows About for a non-admin too", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("normal"), importFromDonetick: vi.fn(async () => 0) } });
    flushSync();
    const labels = [...target.querySelectorAll(".nav-item")].map((b) => b.textContent);
    expect(labels.some((l) => l?.includes("About"))).toBe(true);
    unmount(app);
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -w @myhome/editor -- SettingsPage --run`
Expected: FAIL (only 7 groups render, "About" not found)

- [ ] **Step 3: Wire in the new tab**

In `packages/editor/src/lib/components/SettingsPage.svelte`, change:
```svelte
  import SettingsBackup from "./settings/SettingsBackup.svelte";
  import SettingsActivityLog from "./settings/SettingsActivityLog.svelte";
```
to:
```svelte
  import SettingsBackup from "./settings/SettingsBackup.svelte";
  import SettingsActivityLog from "./settings/SettingsActivityLog.svelte";
  import SettingsAbout from "./settings/SettingsAbout.svelte";
```

Change:
```svelte
  const ALL_GROUPS: SettingsGroupDef[] = [
    { id: "general", icon: "⚙️" },
    { id: "categories", icon: "🏷️" },
    { id: "notifications", icon: "🔔" },
    { id: "security", icon: "🔐" },
    { id: "integrations", icon: "🔌", adminOnly: true },
    { id: "backup", icon: "💾" },
    { id: "activity", icon: "📜" },
  ];
```
to:
```svelte
  const ALL_GROUPS: SettingsGroupDef[] = [
    { id: "general", icon: "⚙️" },
    { id: "categories", icon: "🏷️" },
    { id: "notifications", icon: "🔔" },
    { id: "security", icon: "🔐" },
    { id: "integrations", icon: "🔌", adminOnly: true },
    { id: "backup", icon: "💾" },
    { id: "activity", icon: "📜" },
    { id: "about", icon: "ℹ️" },
  ];
```

Change:
```svelte
      {:else if activeGroup === "activity"}
        <SettingsActivityLog />
      {/if}
```
to:
```svelte
      {:else if activeGroup === "activity"}
        <SettingsActivityLog />
      {:else if activeGroup === "about"}
        <SettingsAbout />
      {/if}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -w @myhome/editor -- SettingsPage --run`
Expected: PASS

- [ ] **Step 5: Run the full frontend suite**

Run: `npm test -w @myhome/editor -- --run`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/SettingsPage.svelte packages/editor/test/SettingsPage.test.ts
git commit -m "feat(about): wire About tab into Settings nav"
```

---

### Task 7: Full verification

- [ ] **Step 1: Run the full backend suite**

Run: `pytest packages/backend -q`
Expected: all tests pass, no regressions

- [ ] **Step 2: Run the full frontend suite**

Run: `npm test -w @myhome/editor -- --run`
Expected: all tests pass, no regressions

- [ ] **Step 3: Manual smoke check**

Use the `run` skill (or start the dev server directly) and, in a browser, log into Settings → About and confirm: the version renders, the update-status line renders one of the three states without throwing, and the system-info list renders all seven fields with sane values.

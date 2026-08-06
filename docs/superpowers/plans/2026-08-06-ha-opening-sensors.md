# HA window/door sensors + roller shutters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let windows/doors link to HA `binary_sensor` entities (color-coded open/closed/unavailable on the floor plan) and windows additionally link a roller shutter `cover` entity (position overlay + open/close/stop controls), all delivered near-real-time over a new backend WebSocket proxy, behind a toggleable "ha" map layer that's on by default.

**Architecture:** Backend gets two new REST endpoints (entity picker listing, cover control) plus a per-connection WebSocket proxy (`/api/ha/ws`) that authenticates the browser client itself (not covered by the existing HTTP-only auth middleware), opens its own upstream connection to HA's websocket API, and forwards filtered `state_changed` events. Frontend gets a new geometry utility (room-adjacency-to-opening, for scoping entity pickers), a WebSocket-backed reactive store, a new `OpeningPanel` side panel (mirroring the existing `RoomPanel`), and rendering changes in `OpeningShape.svelte` gated on the new layer toggle.

**Tech Stack:** FastAPI + Pydantic + httpx + `websockets` (backend), Svelte 5 runes + TypeScript (frontend), pytest/respx (backend tests), Vitest (frontend tests).

## Global Constraints

- Backend: Python 3.12, existing route files use `from ..module import name` relative imports; new backend dependency `websockets>=12` must be declared explicitly in `pyproject.toml` (currently only present transitively via `uvicorn[standard]`).
- All new/changed strings visible in the UI need both `en.json` and `fr.json` entries — this codebase is fully bilingual (see `floorPlan.roomPanel.*` / `common.modules.*` for the existing pattern).
- Frontend components read design tokens from CSS custom properties in `packages/editor/src/lib/theme.css`, defined once in `:root` (light) and once in `[data-theme="dark"]`. Never hardcode colors in component `<style>` blocks.
- Svelte 5 runes only (`$state`, `$derived`, `$effect`, `$props`) — no Svelte 4 patterns (`export let`, stores via `writable`, etc.) in new code.
- Component tests use `mount`/`unmount`/`flushSync` from `"svelte"` directly, target element attached to `document.body`, and dispatched events use `{ bubbles: true }` — required for Svelte 5 event delegation to fire in jsdom.
- **Security-critical:** `/api/ha/ws` is a WebSocket route. FastAPI's `@app.middleware("http")` in `main.py` (the `auth_middleware` function, lines ~107-140) only wraps HTTP-scope requests — it does **not** run for WebSocket connections. The new WS route must perform its own authentication check (reusing `get_user_from_request`/`resolve_ha_ingress_user` from `deps.py`/`ha_ingress.py`) or it will be reachable without login. This is called out explicitly in Task 4 — do not skip it.

---

### Task 1: Backend `Opening` model — HA sensor/shutter fields

**Files:**
- Modify: `packages/backend/src/myhome/models.py:19-25` (the `Opening` class)
- Test: `packages/backend/tests/test_persistence.py`

**Interfaces:**
- Produces: `Opening.haEntityId: str | None`, `Opening.hasShutter: bool`, `Opening.shutterEntityId: str | None`, all defaulting so existing saved houses (missing these keys) still load.

- [ ] **Step 1: Write the failing test**

Add to `packages/backend/tests/test_persistence.py`:

```python
from myhome.models import Opening, Wall


def make_doc_with_opening() -> HouseDocument:
    doc = make_doc()
    doc.floors[0].walls = [
        Wall(id="w1", type="wall", start={"x": 0, "y": 0}, end={"x": 4, "y": 0}, thickness=0.1)
    ]
    doc.floors[0].openings = [
        Opening(
            id="o1", wallId="w1", type="window", offset=1, width=1,
            haEntityId="binary_sensor.front_window", hasShutter=True,
            shutterEntityId="cover.front_window_shutter",
        )
    ]
    return doc


def test_round_trip_preserves_opening_ha_fields(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    save_house(HOME_ID, make_doc_with_opening())
    loaded = load_house(HOME_ID)
    opening = loaded.floors[0].openings[0]
    assert opening.haEntityId == "binary_sensor.front_window"
    assert opening.hasShutter is True
    assert opening.shutterEntityId == "cover.front_window_shutter"


def test_opening_ha_fields_default_when_absent():
    opening = Opening(id="o2", wallId="w1", type="door", offset=0, width=0.9)
    assert opening.haEntityId is None
    assert opening.hasShutter is False
    assert opening.shutterEntityId is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_persistence.py -v`
Expected: FAIL — `Opening() got unexpected keyword arguments 'haEntityId', 'hasShutter', 'shutterEntityId'` (Pydantic rejects unknown kwargs by default).

- [ ] **Step 3: Implement**

In `packages/backend/src/myhome/models.py`, change the `Opening` class:

```python
class Opening(BaseModel):
    id: str
    wallId: str
    type: Literal["door", "window"]
    offset: float
    width: float
    swing: Literal["left-in", "right-in", "left-out", "right-out"] | None = None
    haEntityId: str | None = None
    hasShutter: bool = False
    shutterEntityId: str | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_persistence.py -v`
Expected: PASS (all tests in the file, including the pre-existing ones).

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/models.py packages/backend/tests/test_persistence.py
git commit -m "feat(backend): add HA sensor/shutter fields to Opening model"
```

---

### Task 2: Backend `GET /api/ha/entities` endpoint

**Files:**
- Modify: `packages/backend/src/myhome/routes/ha.py`
- Test: `packages/backend/tests/test_ha.py`

**Interfaces:**
- Consumes: `_HA_BASE`, `_auth_headers` (existing module-level constant/function in `ha.py`).
- Produces: `GET /api/ha/entities?area_id=<str>&domain=<binary_sensor|cover>` → `list[{"entity_id": str, "name": str}]`. `400` if `domain` isn't `binary_sensor` or `cover`.

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_ha.py`:

```python
def test_get_ha_entities_returns_empty_without_token(client, monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    resp = client.get("/api/ha/entities", params={"area_id": "entryway", "domain": "binary_sensor"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_ha_entities_rejects_unsupported_domain(client, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    resp = client.get("/api/ha/entities", params={"area_id": "entryway", "domain": "light"})
    assert resp.status_code == 400


def test_get_ha_entities_lists_matching_domain(client, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    with respx.mock:
        route = respx.post("http://supervisor/core/api/template").mock(
            return_value=Response(200, text=json.dumps([
                {"entity_id": "binary_sensor.front_door", "name": "Front Door"},
            ]))
        )
        resp = client.get("/api/ha/entities", params={"area_id": "entryway", "domain": "binary_sensor"})
    assert resp.status_code == 200
    assert resp.json() == [{"entity_id": "binary_sensor.front_door", "name": "Front Door"}]
    body = json.loads(route.calls[0].request.content)
    assert body["variables"] == {"area_id": "entryway", "domain": "binary_sensor"}


def test_get_ha_entities_returns_empty_on_ha_error(client, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    with respx.mock:
        respx.post("http://supervisor/core/api/template").mock(return_value=Response(500))
        resp = client.get("/api/ha/entities", params={"area_id": "entryway", "domain": "cover"})
    assert resp.status_code == 200
    assert resp.json() == []
```

`client` is the existing authenticated-`TestClient` fixture from `conftest.py`. Need `respx` and `Response`/`json` already imported at the top of `test_ha.py` (add `import json`, `import respx`, `from httpx import Response` if not already present from Task work — `test_ha.py` currently imports `json`, `pytest`, `respx`, `Response`, so these already exist).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_ha.py -v`
Expected: FAIL with 404 (route doesn't exist yet).

- [ ] **Step 3: Implement**

In `packages/backend/src/myhome/routes/ha.py`, add near the top (after the `_auth_headers` function) and register the new route:

```python
from fastapi import APIRouter, HTTPException  # extend existing "from fastapi import APIRouter"

_ALLOWED_ENTITY_DOMAINS = {"binary_sensor", "cover"}


@router.get("/api/ha/entities")
async def get_ha_entities(area_id: str, domain: str) -> list[dict]:
    if domain not in _ALLOWED_ENTITY_DOMAINS:
        raise HTTPException(status_code=400, detail="unsupported domain")
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return []
    # area_id/domain are passed as Jinja `variables`, not string-interpolated into
    # the template source -- interpolating user-controlled query params directly
    # into the template text would be a server-side template injection hole.
    template = (
        "[{%- for e in area_entities(area_id) if e.startswith(domain + '.') -%}"
        "{%- if not loop.first -%},{%- endif -%}"
        '{"entity_id":"{{ e }}","name":"{{ (state_attr(e, \'friendly_name\') or e) '
        "| replace('\"', '\\\\\"') }}\"}"
        "{%- endfor -%}]"
    )
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_HA_BASE}/template",
                headers=_auth_headers(token),
                json={"template": template, "variables": {"area_id": area_id, "domain": domain}},
                timeout=5.0,
            )
            if resp.status_code == 200:
                return json.loads(resp.text)
    except Exception:
        pass
    return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_ha.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/ha.py packages/backend/tests/test_ha.py
git commit -m "feat(backend): add GET /api/ha/entities for scoped entity pickers"
```

---

### Task 3: Backend `POST /api/ha/cover/{entity_id}/{action}` endpoint

**Files:**
- Modify: `packages/backend/src/myhome/routes/ha.py`
- Test: `packages/backend/tests/test_ha.py`

**Interfaces:**
- Consumes: `call_ha_service(domain, service, data)` (existing function in `ha.py`, unchanged).
- Produces: `POST /api/ha/cover/{entity_id}/{action}` (`action` ∈ `open`/`close`/`stop`) → `{"ok": true}`. `400` for an unrecognized action, `502` if `call_ha_service` raises (no token, or HA returned an error).

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_ha.py`:

```python
def test_post_ha_cover_action_calls_service(client, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    with respx.mock:
        route = respx.post("http://supervisor/core/api/services/cover/open_cover").mock(
            return_value=Response(200, json={"ok": True})
        )
        resp = client.post("/api/ha/cover/cover.bedroom_shutter/open")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert route.called
    assert json.loads(route.calls[0].request.content) == {"entity_id": "cover.bedroom_shutter"}


def test_post_ha_cover_action_rejects_invalid_action(client, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    resp = client.post("/api/ha/cover/cover.bedroom_shutter/toggle")
    assert resp.status_code == 400


def test_post_ha_cover_action_502_without_token(client, monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    resp = client.post("/api/ha/cover/cover.bedroom_shutter/open")
    assert resp.status_code == 502
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_ha.py -v`
Expected: FAIL with 404 (route doesn't exist).

- [ ] **Step 3: Implement**

In `packages/backend/src/myhome/routes/ha.py`, add:

```python
_ALLOWED_COVER_ACTIONS = {"open", "close", "stop"}


@router.post("/api/ha/cover/{entity_id}/{action}")
async def post_ha_cover_action(entity_id: str, action: str) -> dict:
    if action not in _ALLOWED_COVER_ACTIONS:
        raise HTTPException(status_code=400, detail="invalid action")
    try:
        await call_ha_service("cover", f"{action}_cover", {"entity_id": entity_id})
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"ok": True}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_ha.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/ha.py packages/backend/tests/test_ha.py
git commit -m "feat(backend): add POST /api/ha/cover/{entity_id}/{action} for shutter control"
```

---

### Task 4: Backend `/api/ha/ws` WebSocket proxy

**Files:**
- Modify: `packages/backend/pyproject.toml` (add `websockets` dependency)
- Modify: `packages/backend/src/myhome/routes/ha.py`
- Test: `packages/backend/tests/test_ha.py`

**Interfaces:**
- Consumes: `get_user_from_request` (from `myhome.deps`), `resolve_ha_ingress_user` (from `myhome.ha_ingress`), `_HA_BASE`, `_auth_headers`.
- Produces: WebSocket route `/api/ha/ws`. Protocol: client sends `{"entity_ids": [str, ...]}`; server replies with one `{"entity_id": str, "state": str, "attributes": dict}` message per entity (initial snapshot for newly-added ids), then a message per subsequent matching `state_changed` event. Also produces `_connect_upstream_ws()` — an injectable module-level async factory (tests monkeypatch this) returning an object with `async def recv()`, `async def send(str)`, `async def close()`.

**⚠️ This route does its own auth check** — see the Global Constraints note above. Do not rely on `main.py`'s `@app.middleware("http")` auth_middleware; it does not run for WebSocket connections.

- [ ] **Step 1: Add the `websockets` dependency**

In `packages/backend/pyproject.toml`, add to the `dependencies` list (after `"sqlalchemy>=2.0",`):

```toml
    "websockets>=12",
```

Run: `cd packages/backend && pip install -e ".[dev]"`
Expected: succeeds (the package is already present transitively via `uvicorn[standard]`, so this just makes the constraint explicit).

- [ ] **Step 2: Write the failing tests**

Add to `packages/backend/tests/test_ha.py` (needs `import asyncio` and `import myhome.routes.ha as ha_module` added to the file's imports):

```python
import asyncio
import myhome.routes.ha as ha_module


class FakeUpstream:
    """Stand-in for the websockets.ClientConnection returned by _connect_upstream_ws."""

    def __init__(self, initial_messages):
        self._queue: asyncio.Queue = asyncio.Queue()
        for m in initial_messages:
            self._queue.put_nowait(json.dumps(m))
        self.sent: list[dict] = []
        self.closed = False

    async def recv(self):
        return await self._queue.get()

    async def send(self, msg: str):
        self.sent.append(json.loads(msg))

    async def close(self):
        self.closed = True

    def push_event(self, entity_id: str, state: str, attributes: dict | None = None):
        self._queue.put_nowait(json.dumps({
            "type": "event",
            "event": {"data": {"entity_id": entity_id, "new_state": {
                "state": state, "attributes": attributes or {},
            }}},
        }))


def _handshake_messages():
    return [
        {"type": "auth_required"},
        {"type": "auth_ok"},
        {"id": 1, "type": "result", "success": True},
    ]


def test_ha_ws_rejects_unauthenticated_connection():
    from fastapi.testclient import TestClient
    from myhome.main import app
    anonymous_client = TestClient(app)
    with anonymous_client.websocket_connect("/api/ha/ws") as ws:
        with pytest.raises(Exception):
            ws.receive_json()


def test_ha_ws_closes_without_token(client, monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    with client.websocket_connect("/api/ha/ws") as ws:
        with pytest.raises(Exception):
            ws.receive_json()


def test_ha_ws_sends_snapshot_and_forwards_live_updates(client, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    fake = FakeUpstream(_handshake_messages())

    async def fake_connect():
        return fake

    monkeypatch.setattr(ha_module, "_connect_upstream_ws", fake_connect)

    with respx.mock:
        respx.get("http://supervisor/core/api/states/binary_sensor.front_door").mock(
            return_value=Response(200, json={
                "entity_id": "binary_sensor.front_door", "state": "off", "attributes": {},
            })
        )
        with client.websocket_connect("/api/ha/ws") as ws:
            ws.send_json({"entity_ids": ["binary_sensor.front_door"]})
            snapshot = ws.receive_json()
            assert snapshot == {
                "entity_id": "binary_sensor.front_door", "state": "off", "attributes": {},
            }

            fake.push_event("binary_sensor.front_door", "on", {"device_class": "door"})
            update = ws.receive_json()
            assert update == {
                "entity_id": "binary_sensor.front_door", "state": "on",
                "attributes": {"device_class": "door"},
            }


def test_ha_ws_ignores_events_for_unsubscribed_entities(client, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    fake = FakeUpstream(_handshake_messages())

    async def fake_connect():
        return fake

    monkeypatch.setattr(ha_module, "_connect_upstream_ws", fake_connect)

    with respx.mock:
        respx.get("http://supervisor/core/api/states/binary_sensor.front_door").mock(
            return_value=Response(200, json={
                "entity_id": "binary_sensor.front_door", "state": "off", "attributes": {},
            })
        )
        with client.websocket_connect("/api/ha/ws") as ws:
            ws.send_json({"entity_ids": ["binary_sensor.front_door"]})
            ws.receive_json()  # snapshot

            fake.push_event("binary_sensor.back_door", "on")  # not subscribed
            fake.push_event("binary_sensor.front_door", "on")  # subscribed
            update = ws.receive_json()
            assert update["entity_id"] == "binary_sensor.front_door"


def test_ha_ws_updates_subscription_and_sends_snapshot_for_new_ids(client, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    fake = FakeUpstream(_handshake_messages())

    async def fake_connect():
        return fake

    monkeypatch.setattr(ha_module, "_connect_upstream_ws", fake_connect)

    with respx.mock:
        respx.get("http://supervisor/core/api/states/binary_sensor.front_door").mock(
            return_value=Response(200, json={
                "entity_id": "binary_sensor.front_door", "state": "off", "attributes": {},
            })
        )
        respx.get("http://supervisor/core/api/states/cover.bedroom_shutter").mock(
            return_value=Response(200, json={
                "entity_id": "cover.bedroom_shutter", "state": "open",
                "attributes": {"current_position": 100},
            })
        )
        with client.websocket_connect("/api/ha/ws") as ws:
            ws.send_json({"entity_ids": ["binary_sensor.front_door"]})
            ws.receive_json()  # snapshot for front_door

            ws.send_json({"entity_ids": ["binary_sensor.front_door", "cover.bedroom_shutter"]})
            snapshot2 = ws.receive_json()
            assert snapshot2["entity_id"] == "cover.bedroom_shutter"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_ha.py -v -k ha_ws`
Expected: FAIL — route doesn't exist / `_connect_upstream_ws` doesn't exist.

- [ ] **Step 4: Implement**

In `packages/backend/src/myhome/routes/ha.py`, update the imports at the top of the file and add the route:

```python
import asyncio
import json
import os

import httpx
import websockets
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed

from ..deps import get_user_from_request
from ..ha_ingress import resolve_ha_ingress_user

router = APIRouter()

_HA_BASE = "http://supervisor/core/api"
_HA_WS_URL = "ws://supervisor/core/websocket"
```

(Keep the existing `_auth_headers`, `get_ha_areas`, `call_ha_service`, and the Task 2/3 routes below this — only the import block and constants change here.)

Then add, near the bottom of the file:

```python
async def _connect_upstream_ws():
    """Injectable seam -- tests monkeypatch this to avoid a real HA connection."""
    return await websockets.connect(_HA_WS_URL)


async def _authenticate_ws(websocket: WebSocket) -> tuple[str, str] | None:
    """Mirrors main.py's auth_middleware, which does not run for WebSocket scope."""
    user = await get_user_from_request(websocket)
    if user is not None:
        return user
    return await resolve_ha_ingress_user(websocket)


async def _fetch_state(client: httpx.AsyncClient, token: str, entity_id: str) -> dict | None:
    resp = await client.get(f"{_HA_BASE}/states/{entity_id}", headers=_auth_headers(token), timeout=5.0)
    if resp.status_code != 200:
        return None
    data = resp.json()
    return {"entity_id": data["entity_id"], "state": data["state"], "attributes": data.get("attributes", {})}


@router.websocket("/api/ha/ws")
async def ha_ws(websocket: WebSocket) -> None:
    await websocket.accept()

    user = await _authenticate_ws(websocket)
    if user is None:
        await websocket.close(code=4401)
        return

    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        await websocket.close(code=4501)
        return

    try:
        upstream = await _connect_upstream_ws()
    except Exception:
        await websocket.close(code=4502)
        return

    try:
        auth_required = json.loads(await upstream.recv())
        if auth_required.get("type") != "auth_required":
            await websocket.close(code=4503)
            return
        await upstream.send(json.dumps({"type": "auth", "access_token": token}))
        auth_result = json.loads(await upstream.recv())
        if auth_result.get("type") != "auth_ok":
            await websocket.close(code=4503)
            return

        await upstream.send(json.dumps({"id": 1, "type": "subscribe_events", "event_type": "state_changed"}))
        await upstream.recv()  # subscription result ack, discarded

        entity_ids: set[str] = set()

        async def send_snapshot(ids: set[str]) -> None:
            async with httpx.AsyncClient() as http_client:
                for entity_id in ids:
                    state = await _fetch_state(http_client, token, entity_id)
                    if state is not None:
                        await websocket.send_json(state)

        async def handle_frontend_messages() -> None:
            nonlocal entity_ids
            while True:
                data = await websocket.receive_json()
                new_ids = set(data.get("entity_ids", []))
                added = new_ids - entity_ids
                entity_ids = new_ids
                if added:
                    await send_snapshot(added)

        async def handle_upstream_events() -> None:
            while True:
                raw = await upstream.recv()
                event = json.loads(raw)
                if event.get("type") != "event":
                    continue
                event_data = event.get("event", {}).get("data", {})
                entity_id = event_data.get("entity_id")
                new_state = event_data.get("new_state")
                if entity_id in entity_ids and new_state is not None:
                    await websocket.send_json({
                        "entity_id": entity_id,
                        "state": new_state.get("state"),
                        "attributes": new_state.get("attributes", {}),
                    })

        async with asyncio.TaskGroup() as tg:
            tg.create_task(handle_frontend_messages())
            tg.create_task(handle_upstream_events())
    except* (WebSocketDisconnect, ConnectionClosed):
        pass
    finally:
        await upstream.close()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_ha.py -v`
Expected: PASS — all tests in the file, including Tasks 1-3's tests (no regressions).

- [ ] **Step 6: Run the full backend suite**

Run: `cd packages/backend && python -m pytest`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/backend/pyproject.toml packages/backend/src/myhome/routes/ha.py packages/backend/tests/test_ha.py
git commit -m "feat(backend): add /api/ha/ws WebSocket proxy for live entity state"
```

---

### Task 5: Geometry package — `Opening` type HA fields

**Files:**
- Modify: `packages/geometry/src/types.ts:27-37` (the `Opening` interface)
- Test: `packages/geometry/test/types.test.ts`

**Interfaces:**
- Produces: `Opening.haEntityId?: string | null`, `Opening.hasShutter?: boolean`, `Opening.shutterEntityId?: string | null` — mirrors Task 1's backend fields exactly.

- [ ] **Step 1: Write the failing test**

Add to `packages/geometry/test/types.test.ts`:

```ts
import type { Opening } from "../src/types";

describe("Opening HA fields", () => {
  it("allows an opening with HA sensor and shutter links", () => {
    const opening: Opening = {
      id: "o1", wallId: "w1", type: "window", offset: 1, width: 1,
      haEntityId: "binary_sensor.front_window",
      hasShutter: true,
      shutterEntityId: "cover.front_window_shutter",
    };
    expect(opening.hasShutter).toBe(true);
  });

  it("allows an opening with the HA fields omitted", () => {
    const opening: Opening = { id: "o2", wallId: "w1", type: "door", offset: 0, width: 0.9 };
    expect(opening.haEntityId).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/geometry && npx tsc --noEmit`
Expected: FAIL — `Object literal may only specify known properties, and 'haEntityId' does not exist in type 'Opening'.`

- [ ] **Step 3: Implement**

In `packages/geometry/src/types.ts`, update the `Opening` interface:

```ts
export interface Opening {
  id: string;
  wallId: string;
  type: OpeningType;
  /** Distance in meters along the wall from `wall.start`, clamped to the wall's length. */
  offset: number;
  /** Meters. */
  width: number;
  /** Only meaningful for type "door". */
  swing?: DoorSwing;
  /** Linked HA binary_sensor entity id (door/window contact sensor). */
  haEntityId?: string | null;
  /** Whether this window has a roller shutter. Only meaningful for type "window". */
  hasShutter?: boolean;
  /** Linked HA cover entity id for the roller shutter. */
  shutterEntityId?: string | null;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/geometry && npx tsc --noEmit && npx vitest run test/types.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/geometry/src/types.ts packages/geometry/test/types.test.ts
git commit -m "feat(geometry): add HA sensor/shutter fields to Opening type"
```

---

### Task 6: Geometry package — `findAdjacentRooms` utility

**Files:**
- Create: `packages/geometry/src/openingAdjacency.ts`
- Modify: `packages/geometry/src/index.ts` (add export)
- Test: `packages/geometry/test/openingAdjacency.test.ts`

**Interfaces:**
- Consumes: `Point`, `Room`, `Wall`, `Opening` (from `./types`), `pointInPolygon` (from `./geometry`).
- Produces: `findAdjacentRooms(opening: Opening, wall: Wall, rooms: Room[]): Room[]` — 0, 1, or 2 rooms whose polygon contains a point just off either side of the opening's midpoint on the wall.

- [ ] **Step 1: Write the failing test**

Create `packages/geometry/test/openingAdjacency.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { findAdjacentRooms } from "../src/openingAdjacency";
import type { Opening, Room, Wall } from "../src/types";

describe("findAdjacentRooms", () => {
  const exteriorWall: Wall = { id: "w1", type: "wall", start: { x: 0, y: 0 }, end: { x: 4, y: 0 }, thickness: 0.1 };
  const interiorWall: Wall = { id: "w2", type: "wall", start: { x: 2, y: 0 }, end: { x: 2, y: 4 }, thickness: 0.1 };
  const windowOpening: Opening = { id: "o1", wallId: "w1", type: "window", offset: 1, width: 1 };
  const doorOpening: Opening = { id: "o2", wallId: "w2", type: "door", offset: 1, width: 0.9 };

  const roomBelow: Room = {
    id: "r1", label: "Living Room", haAreaId: "living_room", areaM2: 12,
    polygon: [{ x: 0, y: 0 }, { x: 4, y: 0 }, { x: 4, y: 3 }, { x: 0, y: 3 }],
  };
  const roomLeft: Room = {
    id: "r2", label: "Kitchen", haAreaId: "kitchen", areaM2: 8,
    polygon: [{ x: 0, y: 0 }, { x: 2, y: 0 }, { x: 2, y: 4 }, { x: 0, y: 4 }],
  };
  const roomRight: Room = {
    id: "r3", label: "Hallway", haAreaId: "hallway", areaM2: 8,
    polygon: [{ x: 2, y: 0 }, { x: 4, y: 0 }, { x: 4, y: 4 }, { x: 2, y: 4 }],
  };

  it("finds exactly one room for a window on an exterior wall", () => {
    const found = findAdjacentRooms(windowOpening, exteriorWall, [roomBelow]);
    expect(found.map((r) => r.id)).toEqual(["r1"]);
  });

  it("finds both rooms for a door on an interior wall shared by two rooms", () => {
    const found = findAdjacentRooms(doorOpening, interiorWall, [roomLeft, roomRight]);
    expect(found.map((r) => r.id).sort()).toEqual(["r2", "r3"]);
  });

  it("finds no rooms when neither side is enclosed", () => {
    const found = findAdjacentRooms(windowOpening, exteriorWall, []);
    expect(found).toEqual([]);
  });

  it("skips rooms with a null (unresolved) polygon", () => {
    const unresolved: Room = { ...roomBelow, polygon: null };
    const found = findAdjacentRooms(windowOpening, exteriorWall, [unresolved]);
    expect(found).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/geometry && npx vitest run test/openingAdjacency.test.ts`
Expected: FAIL — cannot find module `../src/openingAdjacency`.

- [ ] **Step 3: Implement**

Create `packages/geometry/src/openingAdjacency.ts`:

```ts
import type { Opening, Room, Wall } from "./types";
import { pointInPolygon } from "./geometry";

/** How far (meters) to offset from the wall centerline when probing which room an opening borders. */
const ADJACENCY_EPSILON = 0.05;

/**
 * Finds the room(s) adjacent to an opening's position on its wall, by testing
 * points just off each side of the opening's midpoint against every room's
 * polygon. Returns 0 rooms for an opening on an unenclosed wall, 1 for the
 * common case (e.g. an exterior window), or 2 for an interior door shared by
 * two rooms.
 */
export function findAdjacentRooms(opening: Opening, wall: Wall, rooms: Room[]): Room[] {
  const dx = wall.end.x - wall.start.x;
  const dy = wall.end.y - wall.start.y;
  const length = Math.hypot(dx, dy);
  if (length < 1e-9) return [];
  const dirX = dx / length;
  const dirY = dy / length;

  const midAlongWall = opening.offset + opening.width / 2;
  const midWorld = { x: wall.start.x + dirX * midAlongWall, y: wall.start.y + dirY * midAlongWall };

  const perpX = -dirY * ADJACENCY_EPSILON;
  const perpY = dirX * ADJACENCY_EPSILON;
  const sideA = { x: midWorld.x + perpX, y: midWorld.y + perpY };
  const sideB = { x: midWorld.x - perpX, y: midWorld.y - perpY };

  const found: Room[] = [];
  for (const room of rooms) {
    if (!room.polygon) continue;
    if (pointInPolygon(sideA, room.polygon) || pointInPolygon(sideB, room.polygon)) {
      found.push(room);
    }
  }
  return found;
}
```

Add to `packages/geometry/src/index.ts`:

```ts
export * from "./openingAdjacency";
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/geometry && npx vitest run test/openingAdjacency.test.ts`
Expected: PASS.

- [ ] **Step 5: Run the full geometry suite**

Run: `cd packages/geometry && npx vitest run`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/geometry/src/openingAdjacency.ts packages/geometry/src/index.ts packages/geometry/test/openingAdjacency.test.ts
git commit -m "feat(geometry): add findAdjacentRooms for opening-to-room HA area scoping"
```

---

### Task 7: `houseStore.updateOpening` — accept HA patch fields

**Files:**
- Modify: `packages/editor/src/lib/houseStore.svelte.ts:170-182`
- Test: `packages/editor/test/houseStore.test.ts`

**Interfaces:**
- Consumes: `Opening` type from `@myhome/geometry` (Task 5); `store.addOpening(opening: Opening): void` (existing, exported by `createHouseStore`).
- Produces: `updateOpening(id, patch: Partial<Pick<Opening, "offset" | "width" | "swing" | "haEntityId" | "hasShutter" | "shutterEntityId">>, opts?)` — unchanged signature shape, just a wider patch type.

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/houseStore.test.ts` (this file already defines `HOME`/`getHomeId`, `makeFetchStub`, and an `async function tick()` helper at the top — reuse them):

```ts
describe("houseStore — updateOpening HA fields", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", makeFetchStub(404));
  });

  it("persists HA sensor and shutter fields", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    store.addOpening({ id: "o1", wallId: "w1", type: "window", offset: 0, width: 1 });
    store.updateOpening("o1", {
      haEntityId: "binary_sensor.front_window",
      hasShutter: true,
      shutterEntityId: "cover.front_window_shutter",
    });
    const opening = store.floor.openings[0];
    expect(opening.haEntityId).toBe("binary_sensor.front_window");
    expect(opening.hasShutter).toBe(true);
    expect(opening.shutterEntityId).toBe("cover.front_window_shutter");
  });

  it("can clear a previously-set shutter link", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    store.addOpening({
      id: "o1", wallId: "w1", type: "window", offset: 0, width: 1,
      hasShutter: true, shutterEntityId: "cover.front_window_shutter",
    });
    store.updateOpening("o1", { hasShutter: false, shutterEntityId: null });
    const opening = store.floor.openings[0];
    expect(opening.hasShutter).toBe(false);
    expect(opening.shutterEntityId).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx tsc --noEmit`
Expected: FAIL — `Object literal may only specify known properties...` / patch type error, since `haEntityId` etc. aren't in the current `Pick<...>`.

- [ ] **Step 3: Implement**

In `packages/editor/src/lib/houseStore.svelte.ts`, update `updateOpening`:

```ts
function updateOpening(
  id: string,
  patch: Partial<Pick<Opening, "offset" | "width" | "swing" | "haEntityId" | "hasShutter" | "shutterEntityId">>,
  opts?: { skipHistory?: boolean }
): void {
  const opening = currentFloor().openings.find((o) => o.id === id);
  if (!opening) return;
  if (!opts?.skipHistory) saveSnapshot();
  else generation++;
  if (patch.offset !== undefined) opening.offset = patch.offset;
  if (patch.width !== undefined) opening.width = patch.width;
  if (patch.swing !== undefined) opening.swing = patch.swing;
  if (patch.haEntityId !== undefined) opening.haEntityId = patch.haEntityId;
  if (patch.hasShutter !== undefined) opening.hasShutter = patch.hasShutter;
  if (patch.shutterEntityId !== undefined) opening.shutterEntityId = patch.shutterEntityId;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/houseStore.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/houseStore.svelte.ts packages/editor/test/houseStore.test.ts
git commit -m "feat(editor): let updateOpening patch HA sensor/shutter fields"
```

---

### Task 8: `wsUrl()` helper for ingress-safe WebSocket URLs

**Files:**
- Modify: `packages/editor/src/lib/apiUrl.ts`
- Test: `packages/editor/test/apiUrl.test.ts`

**Interfaces:**
- Consumes: `apiUrl(path)` (existing function in the same file).
- Produces: `wsUrl(path: string): string` — same ingress-prefix rewriting as `apiUrl`, plus an `http(s):` → `ws(s):` protocol swap.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/apiUrl.test.ts`:

```ts
import { apiUrl, wsUrl } from "../src/lib/apiUrl";

describe("wsUrl", () => {
  it("converts http to ws at domain root", () => {
    setBaseURI("http://localhost:3000/");
    expect(wsUrl("/api/ha/ws")).toBe("ws://localhost:3000/api/ha/ws");
  });

  it("converts https to wss under an ingress path prefix", () => {
    setBaseURI("https://localhost:3000/api/hassio_ingress/abc123/");
    expect(wsUrl("/api/ha/ws")).toBe("wss://localhost:3000/api/hassio_ingress/abc123/api/ha/ws");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/apiUrl.test.ts`
Expected: FAIL — `wsUrl is not exported`.

- [ ] **Step 3: Implement**

In `packages/editor/src/lib/apiUrl.ts`, add:

```ts
/**
 * Same ingress-prefix rewriting as apiUrl(), for WebSocket connections --
 * `new WebSocket(...)` needs a ws(s):// URL, not http(s)://.
 */
export function wsUrl(path: string): string {
  const url = new URL(apiUrl(path), location.href);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/apiUrl.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/apiUrl.ts packages/editor/test/apiUrl.test.ts
git commit -m "feat(editor): add wsUrl() ingress-safe WebSocket URL helper"
```

---

### Task 9: "ha" map layer — toggle entry + default-on seeding

**Files:**
- Modify: `packages/editor/src/lib/components/LayersDropdown.svelte`
- Modify: `packages/editor/src/App.svelte:188` (the `activeLayers` seed)
- Modify: `packages/editor/src/lib/locales/en.json`, `packages/editor/src/lib/locales/fr.json`
- Test: `packages/editor/test/LayersDropdown.test.ts` (new file), `packages/editor/test/App.test.ts` (add one test)

**Interfaces:**
- Produces: a `"ha"` entry in `LayersDropdown`'s layer list; `App.svelte`'s `activeLayers` now seeds as `new Set(["ha"])` instead of `new Set()`.

- [ ] **Step 1: Write the failing LayersDropdown test**

Create `packages/editor/test/LayersDropdown.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import LayersDropdown from "../src/lib/components/LayersDropdown.svelte";

function setup(activeLayers: Set<string>, ontoggle = vi.fn()) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const comp = mount(LayersDropdown, { target, props: { activeLayers, ontoggle } });
  flushSync();
  return { target, comp, ontoggle };
}

describe("LayersDropdown — ha layer", () => {
  it("renders a checked 'ha' row when the layer is active", () => {
    const { target, comp } = setup(new Set(["ha"]));
    (target.querySelector(".layers-btn") as HTMLButtonElement).click();
    flushSync();
    const haRow = Array.from(target.querySelectorAll(".layer-row")).find(
      (r) => r.textContent?.includes("Home Assistant"),
    ) as HTMLElement;
    expect(haRow).not.toBeUndefined();
    expect((haRow.querySelector('input[type="checkbox"]') as HTMLInputElement).checked).toBe(true);
    unmount(comp); target.remove();
  });

  it("calls ontoggle('ha') when the row is clicked", () => {
    const { target, comp, ontoggle } = setup(new Set(["ha"]));
    (target.querySelector(".layers-btn") as HTMLButtonElement).click();
    flushSync();
    const haRow = Array.from(target.querySelectorAll(".layer-row")).find(
      (r) => r.textContent?.includes("Home Assistant"),
    ) as HTMLElement;
    (haRow.querySelector('input[type="checkbox"]') as HTMLInputElement).dispatchEvent(
      new Event("change", { bubbles: true }),
    );
    expect(ontoggle).toHaveBeenCalledWith("ha");
    unmount(comp); target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/LayersDropdown.test.ts`
Expected: FAIL — no row contains "Home Assistant".

- [ ] **Step 3: Implement — i18n keys**

In `packages/editor/src/lib/locales/en.json`, inside `"common"."modules"`, add:

```json
"ha": "Home Assistant"
```

In `packages/editor/src/lib/locales/fr.json`, inside `"common"."modules"`, add:

```json
"ha": "Home Assistant"
```

- [ ] **Step 4: Implement — LayersDropdown entry**

In `packages/editor/src/lib/components/LayersDropdown.svelte`, add to the `layers` array:

```ts
const layers = [
  { id: "chores",      icon: "✅" },
  { id: "inventory",   icon: "📦" },
  { id: "consumables", icon: "🛒" },
  { id: "costs",       icon: "💰" },
  { id: "works",       icon: "🔧" },
  { id: "ha",          icon: "📡" },
];
```

- [ ] **Step 5: Run LayersDropdown tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/LayersDropdown.test.ts`
Expected: PASS.

- [ ] **Step 6: Write the failing App-level default-on test**

Add to `packages/editor/test/App.test.ts`, inside a `describe("App — HA layer")` block (see existing `stubFetch`/`mountAndLoad` helpers already in this file):

```ts
describe("App — HA layer", () => {
  it("is active by default without the user toggling it", async () => {
    stubFetch();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = await mountAndLoad(target);

    (target.querySelector('button[title="Toggle map layers"]') as HTMLButtonElement).click();
    await tick();
    flushSync();
    const haRow = Array.from(target.querySelectorAll(".layer-row")).find(
      (r) => r.textContent?.includes("Home Assistant"),
    ) as HTMLElement;
    expect((haRow.querySelector('input[type="checkbox"]') as HTMLInputElement).checked).toBe(true);

    unmount(app);
    target.remove();
  });
});
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "HA layer"`
Expected: FAIL — checkbox is unchecked (default `activeLayers` is empty).

- [ ] **Step 8: Implement**

In `packages/editor/src/App.svelte`, change line ~188:

```ts
let activeLayers = $state(new Set<string>(["ha"]));
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "HA layer"`
Expected: PASS.

- [ ] **Step 10: Run the full editor suite to check for regressions**

Run: `cd packages/editor && npx vitest run`
Expected: PASS — in particular, re-check any existing test that asserts on the *count* of layer rows or the exact contents of `activeLayers` right after mount, since the default set is no longer empty.

- [ ] **Step 11: Commit**

```bash
git add packages/editor/src/lib/components/LayersDropdown.svelte packages/editor/src/App.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/LayersDropdown.test.ts packages/editor/test/App.test.ts
git commit -m "feat(editor): add default-on 'ha' map layer toggle"
```

---

### Task 10: `haStateStore` — WebSocket-backed live state store

**Files:**
- Create: `packages/editor/src/lib/haStateStore.svelte.ts`
- Test: `packages/editor/test/haStateStore.test.ts`

**Interfaces:**
- Consumes: `wsUrl` (from `./apiUrl`, Task 8).
- Produces: `createHaStateStore()` → `{ states: Map<string, HaEntityState>, setActive(boolean), setEntityIds(Iterable<string>), disconnect() }`, plus the exported type `HaEntityState { state: string; attributes: Record<string, unknown> }`.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/haStateStore.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createHaStateStore } from "../src/lib/haStateStore.svelte";

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 3;

  url: string;
  readyState = FakeWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }
  send(data: string): void { this.sent.push(data); }
  close(): void {
    this.closed = true;
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.();
  }
  open(): void {
    this.readyState = FakeWebSocket.OPEN;
    this.onopen?.();
  }
  receive(data: unknown): void {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeWebSocket);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("createHaStateStore", () => {
  it("does not connect until both active and entityIds are set", () => {
    const store = createHaStateStore();
    store.setEntityIds(["binary_sensor.front_door"]);
    expect(FakeWebSocket.instances).toHaveLength(0);
    store.setActive(true);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it("sends entity_ids on open and merges incoming state updates", () => {
    const store = createHaStateStore();
    store.setEntityIds(["binary_sensor.front_door"]);
    store.setActive(true);
    const ws = FakeWebSocket.instances[0];
    ws.open();
    expect(JSON.parse(ws.sent[0])).toEqual({ entity_ids: ["binary_sensor.front_door"] });

    ws.receive({ entity_id: "binary_sensor.front_door", state: "on", attributes: { device_class: "door" } });
    expect(store.states.get("binary_sensor.front_door")).toEqual({ state: "on", attributes: { device_class: "door" } });
  });

  it("closes the socket when entityIds becomes empty", () => {
    const store = createHaStateStore();
    store.setEntityIds(["binary_sensor.front_door"]);
    store.setActive(true);
    const ws = FakeWebSocket.instances[0];
    ws.open();
    store.setEntityIds([]);
    expect(ws.closed).toBe(true);
  });

  it("closes the socket when set inactive, and does not reconnect", () => {
    vi.useFakeTimers();
    const store = createHaStateStore();
    store.setEntityIds(["binary_sensor.front_door"]);
    store.setActive(true);
    const ws = FakeWebSocket.instances[0];
    ws.open();
    store.setActive(false);
    expect(ws.closed).toBe(true);
    vi.advanceTimersByTime(20000);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it("reconnects with backoff after the socket drops while still active", () => {
    vi.useFakeTimers();
    const store = createHaStateStore();
    store.setEntityIds(["binary_sensor.front_door"]);
    store.setActive(true);
    FakeWebSocket.instances[0].open();
    FakeWebSocket.instances[0].close();
    expect(FakeWebSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(1000);
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it("preserves last-known state across a reconnect", () => {
    vi.useFakeTimers();
    const store = createHaStateStore();
    store.setEntityIds(["binary_sensor.front_door"]);
    store.setActive(true);
    const ws = FakeWebSocket.instances[0];
    ws.open();
    ws.receive({ entity_id: "binary_sensor.front_door", state: "on", attributes: {} });
    ws.close();
    vi.advanceTimersByTime(1000);
    expect(store.states.get("binary_sensor.front_door")).toEqual({ state: "on", attributes: {} });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/haStateStore.test.ts`
Expected: FAIL — cannot find module `../src/lib/haStateStore.svelte`.

- [ ] **Step 3: Implement**

Create `packages/editor/src/lib/haStateStore.svelte.ts`:

```ts
import { wsUrl } from "./apiUrl";

export interface HaEntityState {
  state: string;
  attributes: Record<string, unknown>;
}

const RECONNECT_DELAYS_MS = [1000, 2000, 4000, 8000, 15000];

export function createHaStateStore() {
  let states = $state(new Map<string, HaEntityState>());
  let active = false;
  let entityIds = new Set<string>();
  let socket: WebSocket | null = null;
  let reconnectAttempt = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  function clearReconnectTimer(): void {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  }

  function connect(): void {
    if (!active || entityIds.size === 0 || socket) return;
    const ws = new WebSocket(wsUrl("/api/ha/ws"));
    socket = ws;
    ws.onopen = () => {
      reconnectAttempt = 0;
      ws.send(JSON.stringify({ entity_ids: [...entityIds] }));
    };
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data as string) as {
        entity_id: string; state: string; attributes: Record<string, unknown>;
      };
      const next = new Map(states);
      next.set(data.entity_id, { state: data.state, attributes: data.attributes });
      states = next;
    };
    ws.onclose = () => {
      socket = null;
      scheduleReconnect();
    };
    ws.onerror = () => {
      ws.close();
    };
  }

  function scheduleReconnect(): void {
    clearReconnectTimer();
    if (!active || entityIds.size === 0) return;
    const delay = RECONNECT_DELAYS_MS[Math.min(reconnectAttempt, RECONNECT_DELAYS_MS.length - 1)];
    reconnectAttempt += 1;
    reconnectTimer = setTimeout(connect, delay);
  }

  function disconnect(): void {
    clearReconnectTimer();
    reconnectAttempt = 0;
    if (socket) {
      const ws = socket;
      socket = null;
      ws.onclose = null;
      ws.close();
    }
  }

  function setActive(next: boolean): void {
    if (active === next) return;
    active = next;
    if (active) connect();
    else disconnect();
  }

  function setEntityIds(ids: Iterable<string>): void {
    entityIds = new Set(ids);
    if (entityIds.size === 0) {
      disconnect();
      return;
    }
    if (!active) return;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ entity_ids: [...entityIds] }));
    } else if (!socket) {
      connect();
    }
  }

  return {
    get states() { return states; },
    setActive,
    setEntityIds,
    disconnect,
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/haStateStore.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/haStateStore.svelte.ts packages/editor/test/haStateStore.test.ts
git commit -m "feat(editor): add haStateStore, a WebSocket-backed live HA state store"
```

---

### Task 11: `OpeningShape.svelte` — sensor color + shutter overlay

**Files:**
- Modify: `packages/editor/src/lib/theme.css` (new CSS vars, light + dark)
- Modify: `packages/editor/src/lib/components/OpeningShape.svelte`
- Modify: `packages/editor/src/lib/locales/en.json`, `fr.json`
- Test: `packages/editor/test/OpeningShape.test.ts` (new file)

**Interfaces:**
- Consumes: `HaEntityState` type (from `../haStateStore.svelte`, Task 10).
- Produces: `OpeningShape` gains three new optional props: `haLayerActive?: boolean` (default `false`), `haState?: HaEntityState | null` (default `null`, the sensor's state), `shutterState?: HaEntityState | null` (default `null`, the cover's state). Rendering only changes when `haLayerActive` is true.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/OpeningShape.test.ts`:

```ts
import { describe, it, expect, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import OpeningShape from "../src/lib/components/OpeningShape.svelte";
import { DEFAULT_VIEWPORT } from "../src/lib/viewportStore.svelte";
import type { Wall, Opening } from "@myhome/geometry";

const wall: Wall = { id: "w1", type: "wall", start: { x: 0, y: 0 }, end: { x: 4, y: 0 }, thickness: 0.1 };

function makeWindow(overrides: Partial<Opening> = {}): Opening {
  return { id: "o1", wallId: "w1", type: "window", offset: 1, width: 1, ...overrides };
}

let target: HTMLElement;
let app: ReturnType<typeof mount> | undefined;

function setup(props: Record<string, unknown>) {
  target = document.createElement("div");
  document.body.appendChild(target);
  app = mount(OpeningShape, {
    target,
    props: { wall, viewport: { ...DEFAULT_VIEWPORT }, ...props },
  });
  flushSync();
}

afterEach(() => {
  if (app) { unmount(app); app = undefined; }
  target?.remove();
});

describe("OpeningShape — HA sensor color", () => {
  it("renders the default color when the ha layer is off, even if linked", () => {
    setup({
      opening: makeWindow({ haEntityId: "binary_sensor.front_window" }),
      haLayerActive: false,
      haState: { state: "on", attributes: {} },
    });
    const line = target.querySelector("line.window-sym") as SVGLineElement;
    expect(line.getAttribute("stroke")).toBe("var(--canvas-opening-window)");
  });

  it("renders open color when the sensor state is 'on'", () => {
    setup({
      opening: makeWindow({ haEntityId: "binary_sensor.front_window" }),
      haLayerActive: true,
      haState: { state: "on", attributes: {} },
    });
    const line = target.querySelector("line.window-sym") as SVGLineElement;
    expect(line.getAttribute("stroke")).toBe("var(--canvas-opening-open)");
  });

  it("renders default color when the sensor state is 'off'", () => {
    setup({
      opening: makeWindow({ haEntityId: "binary_sensor.front_window" }),
      haLayerActive: true,
      haState: { state: "off", attributes: {} },
    });
    const line = target.querySelector("line.window-sym") as SVGLineElement;
    expect(line.getAttribute("stroke")).toBe("var(--canvas-opening-window)");
  });

  it("renders unavailable color when state is missing", () => {
    setup({
      opening: makeWindow({ haEntityId: "binary_sensor.front_window" }),
      haLayerActive: true,
      haState: null,
    });
    const line = target.querySelector("line.window-sym") as SVGLineElement;
    expect(line.getAttribute("stroke")).toBe("var(--canvas-opening-unavailable)");
  });

  it("renders the default color for an unlinked opening even with the layer on", () => {
    setup({ opening: makeWindow(), haLayerActive: true });
    const line = target.querySelector("line.window-sym") as SVGLineElement;
    expect(line.getAttribute("stroke")).toBe("var(--canvas-opening-window)");
  });
});

describe("OpeningShape — shutter overlay", () => {
  it("renders no overlay when hasShutter is false", () => {
    setup({
      opening: makeWindow({ hasShutter: false }),
      haLayerActive: true,
    });
    expect(target.querySelector(".shutter-overlay")).toBeNull();
  });

  it("renders an overlay proportional to the closed fraction via current_position", () => {
    setup({
      opening: makeWindow({ hasShutter: true, shutterEntityId: "cover.front_window_shutter" }),
      haLayerActive: true,
      shutterState: { state: "open", attributes: { current_position: 50 } },
    });
    const overlay = target.querySelector(".shutter-overlay");
    expect(overlay).not.toBeNull();
  });

  it("renders a full overlay when current_position is absent and state is 'closed'", () => {
    setup({
      opening: makeWindow({ hasShutter: true, shutterEntityId: "cover.front_window_shutter" }),
      haLayerActive: true,
      shutterState: { state: "closed", attributes: {} },
    });
    expect(target.querySelector(".shutter-overlay")).not.toBeNull();
  });

  it("renders no overlay when current_position is 100 (fully open)", () => {
    setup({
      opening: makeWindow({ hasShutter: true, shutterEntityId: "cover.front_window_shutter" }),
      haLayerActive: true,
      shutterState: { state: "open", attributes: { current_position: 100 } },
    });
    expect(target.querySelector(".shutter-overlay")).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/OpeningShape.test.ts`
Expected: FAIL — new props ignored, colors/overlay don't match.

- [ ] **Step 3: Implement — theme tokens**

In `packages/editor/src/lib/theme.css`, add to the `:root` block (after `--canvas-opening-window: #3b7dd8;`):

```css
  --canvas-opening-open: #d97706;
  --canvas-opening-unavailable: #9a9aa5;
  --canvas-shutter-fill: rgba(20, 20, 24, 0.45);
```

Add to the `[data-theme="dark"]` block (after `--canvas-opening-window: #88ccff;`):

```css
  --canvas-opening-open: #fbbf24;
  --canvas-opening-unavailable: #6b6b75;
  --canvas-shutter-fill: rgba(255, 255, 255, 0.4);
```

- [ ] **Step 4: Implement — i18n key**

Add to `packages/editor/src/lib/locales/en.json` under `floorPlan` (new `openingPanel` object, also used by Task 13):

```json
"openingPanel": {
  "sensorUnavailable": "Sensor unavailable"
}
```

Add to `packages/editor/src/lib/locales/fr.json` under `floorPlan`:

```json
"openingPanel": {
  "sensorUnavailable": "Capteur indisponible"
}
```

- [ ] **Step 5: Implement — OpeningShape.svelte**

In `packages/editor/src/lib/components/OpeningShape.svelte`, update the script block: add the import, new props, and derived color/overlay logic.

```svelte
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { Wall, Opening } from "@myhome/geometry";
  import { chooseSweepFlag } from "@myhome/geometry";
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte.ts";
  import type { ToolType } from "../toolStore.svelte";
  import type { HaEntityState } from "../haStateStore.svelte";

  let {
    wall,
    opening,
    viewport,
    tool = "select",
    selected = false,
    haLayerActive = false,
    haState = null,
    shutterState = null,
    onselect,
    ondraghandlestart,
  }: {
    wall: Wall;
    opening: Opening;
    viewport: ViewportState;
    tool?: ToolType;
    selected?: boolean;
    haLayerActive?: boolean;
    haState?: HaEntityState | null;
    shutterState?: HaEntityState | null;
    onselect?: (id: string) => void;
    ondraghandlestart?: (openingId: string, side: "start" | "end", event: PointerEvent) => void;
  } = $props();
```

After the existing `thickness` derived value, add:

```ts
  const sensorStatus = $derived.by((): "open" | "closed" | "unavailable" | null => {
    if (!haLayerActive || !opening.haEntityId) return null;
    if (!haState || haState.state === "unavailable" || haState.state === "unknown") return "unavailable";
    return haState.state === "on" ? "open" : "closed";
  });

  const strokeColor = $derived.by(() => {
    if (selected) return "var(--canvas-wall-selected)";
    if (sensorStatus === "open") return "var(--canvas-opening-open)";
    if (sensorStatus === "unavailable") return "var(--canvas-opening-unavailable)";
    return opening.type === "window" ? "var(--canvas-opening-window)" : "var(--canvas-opening-door)";
  });

  const shutterClosedFraction = $derived.by(() => {
    if (!haLayerActive || opening.type !== "window" || !opening.hasShutter || !shutterState) return 0;
    const pos = shutterState.attributes?.current_position;
    if (typeof pos === "number") return Math.max(0, Math.min(1, (100 - pos) / 100));
    return shutterState.state === "closed" ? 1 : 0;
  });

  const shutterOverlayPoints = $derived.by(() => {
    if (shutterClosedFraction <= 0) return null;
    const closedTo = clampedFrom + (clampedTo - clampedFrom) * shutterClosedFraction;
    const perpX = -dir.y * (thickness / 2);
    const perpY = dir.x * (thickness / 2);
    const startWorld = { x: wall.start.x + dir.x * clampedFrom, y: wall.start.y + dir.y * clampedFrom };
    const endWorld = { x: wall.start.x + dir.x * closedTo, y: wall.start.y + dir.y * closedTo };
    const c1 = worldToScreen({ x: startWorld.x + perpX, y: startWorld.y + perpY }, viewport);
    const c2 = worldToScreen({ x: endWorld.x + perpX, y: endWorld.y + perpY }, viewport);
    const c3 = worldToScreen({ x: endWorld.x - perpX, y: endWorld.y - perpY }, viewport);
    const c4 = worldToScreen({ x: startWorld.x - perpX, y: startWorld.y - perpY }, viewport);
    return `${c1.x},${c1.y} ${c2.x},${c2.y} ${c3.x},${c3.y} ${c4.x},${c4.y}`;
  });
```

Replace the window/door stroke colors in the markup (the `stroke={selected ? "var(--canvas-wall-selected)" : "var(--canvas-opening-window)"}` line and its door/arc equivalents) with `stroke={strokeColor}`, and add a `<title>` + the shutter overlay polygon:

```svelte
  {#if opening.type === "window"}
    <line
      class="window-sym"
      x1={sp1.x}
      y1={sp1.y}
      x2={sp2.x}
      y2={sp2.y}
      stroke={strokeColor}
      stroke-width="3"
      onclick={handleClick}
      role="button"
      tabindex="0"
    >
      {#if sensorStatus === "unavailable"}<title>{$_('floorPlan.openingPanel.sensorUnavailable')}</title>{/if}
    </line>
    {#if shutterOverlayPoints}
      <polygon points={shutterOverlayPoints} fill="var(--canvas-shutter-fill)" class="shutter-overlay" />
    {/if}
  {:else if opening.type === "door" && doorData}
    <line
      class="door-leaf"
      x1={doorData.hinge.x}
      y1={doorData.hinge.y}
      x2={doorData.openEnd.x}
      y2={doorData.openEnd.y}
      stroke={strokeColor}
      stroke-width="2"
      onclick={handleClick}
      role="button"
      tabindex="0"
    >
      {#if sensorStatus === "unavailable"}<title>{$_('floorPlan.openingPanel.sensorUnavailable')}</title>{/if}
    </line>
    <path
      class="door-arc"
      d="M {doorData.other.x} {doorData.other.y} A {doorData.radius} {doorData.radius} 0 0 {doorData.sweep} {doorData.openEnd.x} {doorData.openEnd.y}"
      fill="none"
      stroke={strokeColor}
      stroke-width="1"
      stroke-dasharray="4 2"
      onclick={handleClick}
      role="button"
      tabindex="0"
    />
  {/if}
```

(Everything else in the file — `handleClick`, the gap polygon, the selection handles, the `<style>` block — is unchanged.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/OpeningShape.test.ts`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/theme.css packages/editor/src/lib/components/OpeningShape.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/OpeningShape.test.ts
git commit -m "feat(editor): render HA sensor color and shutter position on openings"
```

---

### Task 12: `Canvas.svelte` — thread `haLayerActive`/`haStates` to openings

**Files:**
- Modify: `packages/editor/src/lib/components/Canvas.svelte`
- Test: `packages/editor/test/Canvas.test.ts`

**Interfaces:**
- Consumes: `HaEntityState` (from `../haStateStore.svelte`, Task 10); `OpeningShape`'s `haLayerActive`/`haState`/`shutterState` props (Task 11).
- Produces: `Canvas` gains `haLayerActive?: boolean` (default `false`) and `haStates?: Map<string, HaEntityState>` (default `new Map()`) props, resolved per-opening and passed to each `OpeningShape`.

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/Canvas.test.ts` (reuse `createSampleFloor`-style fixtures already in the file, adding an opening with `haEntityId` set):

```ts
it("passes resolved HA state through to the linked opening", () => {
  target = document.createElement("div");
  document.body.appendChild(target);

  const floor = createSampleFloor();
  floor.openings = [
    { id: "op1", wallId: "wall-1", type: "window", offset: 1, width: 1, haEntityId: "binary_sensor.front_window" },
  ];

  const haStates = new Map([
    ["binary_sensor.front_window", { state: "on", attributes: {} }],
  ]);

  app = mount(Canvas, {
    target,
    props: {
      floor, viewport: { ...DEFAULT_VIEWPORT }, width: 800, height: 600,
      haLayerActive: true, haStates,
    },
  });
  flushSync();

  const line = target.querySelector("line.window-sym") as SVGLineElement;
  expect(line.getAttribute("stroke")).toBe("var(--canvas-opening-open)");
});

it("does not apply HA coloring when haLayerActive is false", () => {
  target = document.createElement("div");
  document.body.appendChild(target);

  const floor = createSampleFloor();
  floor.openings = [
    { id: "op1", wallId: "wall-1", type: "window", offset: 1, width: 1, haEntityId: "binary_sensor.front_window" },
  ];
  const haStates = new Map([["binary_sensor.front_window", { state: "on", attributes: {} }]]);

  app = mount(Canvas, {
    target,
    props: { floor, viewport: { ...DEFAULT_VIEWPORT }, width: 800, height: 600, haStates },
  });
  flushSync();

  const line = target.querySelector("line.window-sym") as SVGLineElement;
  expect(line.getAttribute("stroke")).toBe("var(--canvas-opening-window)");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/Canvas.test.ts`
Expected: FAIL — `Canvas` doesn't forward the props yet (color stays default in both cases, so the first test fails).

- [ ] **Step 3: Implement**

In `packages/editor/src/lib/components/Canvas.svelte`, add to the props destructure and type block:

```ts
  import type { HaEntityState } from "../haStateStore.svelte";

  let {
    // ...existing props...
    haLayerActive = false,
    haStates = new Map<string, HaEntityState>(),
  }: {
    // ...existing prop types...
    haLayerActive?: boolean;
    haStates?: Map<string, HaEntityState>;
  } = $props();
```

In the `{#each floor.openings as opening (opening.id)}` block, pass the resolved states down to `<OpeningShape>`:

```svelte
      <OpeningShape
        {wall}
        {opening}
        {viewport}
        {tool}
        selected={opening.id === selectedOpeningId}
        haLayerActive={haLayerActive}
        haState={opening.haEntityId ? (haStates.get(opening.haEntityId) ?? null) : null}
        shutterState={opening.hasShutter && opening.shutterEntityId ? (haStates.get(opening.shutterEntityId) ?? null) : null}
        onselect={(id) => onselectopening?.(id)}
        ondraghandlestart={(openingId, side, event) => {
          event.stopPropagation();
          ondragopeninghandlestart?.(openingId, side);
        }}
      />
```

(Keep the existing prop bindings on that element — only add the three new ones.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/Canvas.test.ts`
Expected: PASS.

- [ ] **Step 5: Run the full editor suite**

Run: `cd packages/editor && npx vitest run`
Expected: PASS — no regressions in other Canvas tests.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/Canvas.svelte packages/editor/test/Canvas.test.ts
git commit -m "feat(editor): thread HA layer state from Canvas to OpeningShape"
```

---

### Task 13: `OpeningPanel.svelte` — sensor/shutter linking UI

**Files:**
- Create: `packages/editor/src/lib/components/OpeningPanel.svelte`
- Modify: `packages/editor/src/lib/locales/en.json`, `fr.json`
- Test: `packages/editor/test/OpeningPanel.test.ts` (new file)

**Interfaces:**
- Consumes: `Opening` type (from `@myhome/geometry`).
- Produces: `OpeningPanel` component with props `{ opening: Opening, areaIds?: string[], onupdate: (patch) => void, onstartdrag?, ondismiss? }`, structurally mirroring `RoomPanel.svelte`.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/OpeningPanel.test.ts`:

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import OpeningPanel from "../src/lib/components/OpeningPanel.svelte";
import type { Opening } from "@myhome/geometry";

function makeWindow(overrides: Partial<Opening> = {}): Opening {
  return { id: "o1", wallId: "w1", type: "window", offset: 0, width: 1, ...overrides };
}

function makeDoor(overrides: Partial<Opening> = {}): Opening {
  return { id: "o2", wallId: "w1", type: "door", offset: 0, width: 0.9, ...overrides };
}

let target: HTMLElement;
let app: ReturnType<typeof mount> | undefined;

function setup(overrides: Record<string, unknown> = {}) {
  target = document.createElement("div");
  document.body.appendChild(target);
  const props = { opening: makeWindow(), areaIds: ["living_room"], onupdate: vi.fn(), ...overrides };
  app = mount(OpeningPanel, { target, props });
  flushSync();
  return { props };
}

afterEach(() => {
  if (app) { unmount(app); app = undefined; }
  target?.remove();
});

describe("OpeningPanel — sensor picker", () => {
  it("fetches binary_sensor entities scoped to the given area(s)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ entity_id: "binary_sensor.front_window", name: "Front Window" }],
    }));
    setup();
    await Promise.resolve();
    await Promise.resolve();
    flushSync();
    const options = Array.from(target.querySelectorAll("select")[0].querySelectorAll("option"));
    expect(options.some((o) => o.textContent === "Front Window")).toBe(true);
    expect((fetch as ReturnType<typeof vi.fn>).mock.calls[0][0]).toContain("domain=binary_sensor");
  });

  it("shows a hint and disables pickers when there is no linked area", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ areaIds: [] });
    expect(target.querySelector(".hint")).not.toBeNull();
    expect((target.querySelectorAll("select")[0] as HTMLSelectElement).disabled).toBe(true);
  });

  it("calls onupdate with the selected entity id", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    const onupdate = vi.fn();
    setup({ onupdate });
    const select = target.querySelectorAll("select")[0] as HTMLSelectElement;
    select.value = "";
    const opt = document.createElement("option");
    opt.value = "binary_sensor.front_window";
    select.appendChild(opt);
    select.value = "binary_sensor.front_window";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ haEntityId: "binary_sensor.front_window" });
  });
});

describe("OpeningPanel — shutter fields", () => {
  it("shows shutter fields for a window", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeWindow() });
    expect(target.querySelector('input[type="checkbox"]')).not.toBeNull();
  });

  it("does not show shutter fields for a door", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor() });
    expect(target.querySelector('input[type="checkbox"]')).toBeNull();
  });

  it("clears shutterEntityId when hasShutter is unchecked", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    const onupdate = vi.fn();
    setup({
      opening: makeWindow({ hasShutter: true, shutterEntityId: "cover.front_window_shutter" }),
      onupdate,
    });
    const checkbox = target.querySelector('input[type="checkbox"]') as HTMLInputElement;
    checkbox.checked = false;
    checkbox.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ hasShutter: false, shutterEntityId: null });
  });

  it("shows open/close/stop controls once a shutter entity is linked", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeWindow({ hasShutter: true, shutterEntityId: "cover.front_window_shutter" }) });
    expect(target.querySelector(".shutter-controls")).not.toBeNull();
    expect(target.querySelectorAll(".shutter-controls button")).toHaveLength(3);
  });

  it("posts the cover action when a control button is clicked", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });
    vi.stubGlobal("fetch", fetchMock);
    setup({ opening: makeWindow({ hasShutter: true, shutterEntityId: "cover.front_window_shutter" }) });
    fetchMock.mockClear();
    const openBtn = target.querySelectorAll(".shutter-controls button")[0] as HTMLButtonElement;
    openBtn.click();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/ha/cover/cover.front_window_shutter/open",
      { method: "POST" },
    );
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/OpeningPanel.test.ts`
Expected: FAIL — cannot find module `../src/lib/components/OpeningPanel.svelte`.

- [ ] **Step 3: Implement — i18n keys**

Extend `packages/editor/src/lib/locales/en.json`'s `floorPlan.openingPanel` (created in Task 11) with:

```json
"openingPanel": {
  "sensorUnavailable": "Sensor unavailable",
  "title": "Opening",
  "sensor": "Sensor",
  "none": "(none)",
  "unknownSuffix": "{id} (unknown)",
  "hasShutter": "Has roller shutter",
  "shutter": "Shutter",
  "noArea": "Assign this room to an HA Area first",
  "open": "Open",
  "close": "Close",
  "stop": "Stop"
}
```

Extend `packages/editor/src/lib/locales/fr.json`'s `floorPlan.openingPanel`:

```json
"openingPanel": {
  "sensorUnavailable": "Capteur indisponible",
  "title": "Ouverture",
  "sensor": "Capteur",
  "none": "(aucun)",
  "unknownSuffix": "{id} (inconnu)",
  "hasShutter": "Volet roulant",
  "shutter": "Volet",
  "noArea": "Associez d'abord cette pièce à une zone HA",
  "open": "Ouvrir",
  "close": "Fermer",
  "stop": "Stop"
}
```

- [ ] **Step 4: Implement — OpeningPanel.svelte**

Create `packages/editor/src/lib/components/OpeningPanel.svelte`:

```svelte
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { Opening } from "@myhome/geometry";

  interface HaEntity { entity_id: string; name: string }

  let {
    opening,
    areaIds = [],
    onupdate,
    onstartdrag,
    ondismiss,
  }: {
    opening: Opening;
    areaIds?: string[];
    onupdate: (patch: { haEntityId?: string | null; hasShutter?: boolean; shutterEntityId?: string | null }) => void;
    onstartdrag?: (e: PointerEvent) => void;
    ondismiss?: () => void;
  } = $props();

  let sensorEntities = $state<HaEntity[]>([]);
  let coverEntities = $state<HaEntity[]>([]);
  let controlInFlight = $state(false);

  async function fetchEntities(domain: string): Promise<HaEntity[]> {
    if (areaIds.length === 0) return [];
    const lists = await Promise.all(
      areaIds.map((areaId) =>
        fetch(`/api/ha/entities?area_id=${encodeURIComponent(areaId)}&domain=${domain}`)
          .then((r) => (r.ok ? r.json() : []))
          .catch(() => [] as HaEntity[])
      )
    );
    const byId = new Map<string, HaEntity>();
    for (const list of lists as HaEntity[][]) for (const e of list) byId.set(e.entity_id, e);
    return [...byId.values()];
  }

  $effect(() => {
    fetchEntities("binary_sensor").then((list) => { sensorEntities = list; });
  });

  $effect(() => {
    if (opening.type !== "window") { coverEntities = []; return; }
    fetchEntities("cover").then((list) => { coverEntities = list; });
  });

  function handleSensorChange(e: Event): void {
    const val = (e.target as HTMLSelectElement).value;
    onupdate({ haEntityId: val === "" ? null : val });
  }

  function handleHasShutterChange(e: Event): void {
    const checked = (e.target as HTMLInputElement).checked;
    onupdate(checked ? { hasShutter: true } : { hasShutter: false, shutterEntityId: null });
  }

  function handleShutterEntityChange(e: Event): void {
    const val = (e.target as HTMLSelectElement).value;
    onupdate({ shutterEntityId: val === "" ? null : val });
  }

  async function sendCoverAction(action: "open" | "close" | "stop"): Promise<void> {
    if (!opening.shutterEntityId || controlInFlight) return;
    controlInFlight = true;
    try {
      await fetch(`/api/ha/cover/${encodeURIComponent(opening.shutterEntityId)}/${action}`, { method: "POST" });
    } finally {
      controlInFlight = false;
    }
  }
</script>

<aside class="opening-panel">
  <div class="panel-header">
    {#if onstartdrag}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="drag-handle" onpointerdown={onstartdrag} title={$_('floorPlan.itemPicker.dragToReposition')}>⠿</div>
    {/if}
    <h2>{$_('floorPlan.openingPanel.title')}</h2>
    {#if ondismiss}
      <button class="dismiss-btn" onclick={ondismiss} title={$_('common.close')}>✕</button>
    {/if}
  </div>

  <label>
    <span>{$_('floorPlan.openingPanel.sensor')}</span>
    <select value={opening.haEntityId ?? ""} onchange={handleSensorChange} disabled={areaIds.length === 0}>
      <option value="">{$_('floorPlan.openingPanel.none')}</option>
      {#each sensorEntities as entity (entity.entity_id)}
        <option value={entity.entity_id}>{entity.name}</option>
      {/each}
      {#if opening.haEntityId && !sensorEntities.some((e) => e.entity_id === opening.haEntityId)}
        <option value={opening.haEntityId}>{$_('floorPlan.openingPanel.unknownSuffix', { values: { id: opening.haEntityId } })}</option>
      {/if}
    </select>
    {#if areaIds.length === 0}
      <p class="hint">{$_('floorPlan.openingPanel.noArea')}</p>
    {/if}
  </label>

  {#if opening.type === "window"}
    <label class="checkbox-row">
      <input type="checkbox" checked={opening.hasShutter ?? false} onchange={handleHasShutterChange} />
      <span>{$_('floorPlan.openingPanel.hasShutter')}</span>
    </label>

    {#if opening.hasShutter}
      <label>
        <span>{$_('floorPlan.openingPanel.shutter')}</span>
        <select value={opening.shutterEntityId ?? ""} onchange={handleShutterEntityChange} disabled={areaIds.length === 0}>
          <option value="">{$_('floorPlan.openingPanel.none')}</option>
          {#each coverEntities as entity (entity.entity_id)}
            <option value={entity.entity_id}>{entity.name}</option>
          {/each}
          {#if opening.shutterEntityId && !coverEntities.some((e) => e.entity_id === opening.shutterEntityId)}
            <option value={opening.shutterEntityId}>{$_('floorPlan.openingPanel.unknownSuffix', { values: { id: opening.shutterEntityId } })}</option>
          {/if}
        </select>
      </label>

      {#if opening.shutterEntityId}
        <div class="shutter-controls">
          <button disabled={controlInFlight} onclick={() => sendCoverAction("open")}>{$_('floorPlan.openingPanel.open')}</button>
          <button disabled={controlInFlight} onclick={() => sendCoverAction("close")}>{$_('floorPlan.openingPanel.close')}</button>
          <button disabled={controlInFlight} onclick={() => sendCoverAction("stop")}>{$_('floorPlan.openingPanel.stop')}</button>
        </div>
      {/if}
    {/if}
  {/if}
</aside>

<style>
  .opening-panel {
    width: 200px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
    padding: var(--space-3);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    overflow-y: auto;
  }

  @media (max-width: 480px) {
    .opening-panel {
      width: 100%;
      height: 100%;
      border-radius: 0;
      border-left: none; border-right: none; border-bottom: none;
    }
  }

  .panel-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }
  h2 {
    flex: 1;
    min-width: 0;
    margin: 0;
    font-size: 13px;
    color: var(--text);
    font-weight: 600;
  }
  .drag-handle {
    cursor: grab;
    color: var(--text-muted);
    font-size: 14px;
    letter-spacing: 3px;
    opacity: 0.5;
    padding: 2px 0;
    flex-shrink: 0;
    border-radius: var(--radius-sm);
    user-select: none;
  }
  .drag-handle:hover { opacity: 1; background: var(--surface-hover); }
  .drag-handle:active { cursor: grabbing; }
  .dismiss-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-muted);
    flex-shrink: 0;
    padding: 2px 4px;
    border-radius: var(--radius-sm);
  }
  .dismiss-btn:hover { background: var(--surface-hover); color: var(--text); }
  label {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  .checkbox-row {
    flex-direction: row;
    align-items: center;
    gap: var(--space-2);
  }
  span {
    font-size: 11px;
    color: var(--text-muted);
  }
  input,
  select {
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text);
    padding: 4px 6px;
    font-size: 12px;
    font-family: inherit;
  }
  input[type="checkbox"] { width: auto; }
  input:focus,
  select:focus {
    outline: none;
    border-color: var(--accent);
  }
  .hint {
    margin: 0;
    font-size: 10px;
    color: var(--text-faint);
  }
  .shutter-controls {
    display: flex;
    gap: var(--space-2);
  }
  .shutter-controls button {
    flex: 1;
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text);
    padding: 4px 6px;
    font-size: 11px;
    cursor: pointer;
  }
  .shutter-controls button:hover:not(:disabled) { background: var(--surface-hover); }
  .shutter-controls button:disabled { opacity: 0.5; cursor: default; }
</style>
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/OpeningPanel.test.ts`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/OpeningPanel.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/OpeningPanel.test.ts
git commit -m "feat(editor): add OpeningPanel for HA sensor/shutter linking"
```

---

### Task 14: `App.svelte` — final wiring

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Test: `packages/editor/test/App.test.ts`

**Interfaces:**
- Consumes: `findAdjacentRooms` (Task 6), `createHaStateStore` (Task 10), `OpeningPanel` (Task 13), `Canvas`'s `haLayerActive`/`haStates` props (Task 12), `createFloatingDrag` (existing).

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/App.test.ts` (new `describe` block, using the file's existing `drawWalls` helper and the `toolbarBtn(target, "Window")` pattern — the floating toolbar has a button titled exactly `"Window"`, confirmed via the existing toolbar-titles assertion in this file):

```ts
describe("App — OpeningPanel wiring", () => {
  it("shows the OpeningPanel when a window is selected, with no area hint when its room has no HA area", async () => {
    stubFetch();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = await mountAndLoad(target);

    drawWalls(target, [
      { x: 0, y: 0 }, { x: 4, y: 0 }, { x: 4, y: 3 }, { x: 0, y: 3 }, { x: 0, y: 0 },
    ]);

    toolbarBtn(target, "Window").click();
    flushSync();
    const svg = target.querySelector("svg.canvas")!;
    // Click near the middle of the bottom wall (world (2,0) -> screen (600,300)).
    svg.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, pointerId: 1, clientX: 600, clientY: 300 }));
    flushSync();
    svg.dispatchEvent(new MouseEvent("click", { bubbles: true, clientX: 600, clientY: 300 }));
    flushSync();
    toolbarBtn(target, "Select").click();
    flushSync();

    const windowLine = target.querySelector("line.window-sym") as SVGLineElement;
    windowLine.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".opening-panel-float")).not.toBeNull();
    expect(target.querySelector(".opening-panel .hint")).not.toBeNull();

    unmount(app);
    target.remove();
  });
});
```

(This test only needs to prove the panel mounts and reads the no-area hint correctly — it doesn't need to exercise the full HA area chain, which Task 6's and Task 13's own tests already cover directly. If the exact click coordinates above don't land the window selection in practice, adjust them to match wherever `drawWalls`'s coordinate mapping — `screen = world*100 + (400,300)` per the existing helper's doc comment — places the bottom wall's midpoint.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "OpeningPanel wiring"`
Expected: FAIL — no `.opening-panel-float` in the DOM.

- [ ] **Step 3: Implement**

In `packages/editor/src/App.svelte`:

Add imports:

```ts
import OpeningPanel from "./lib/components/OpeningPanel.svelte";
import { createHaStateStore } from "./lib/haStateStore.svelte";
import { findAdjacentRooms } from "@myhome/geometry";
```

(`findAdjacentRooms` joins whatever existing `@myhome/geometry` import line already exists in `App.svelte` — add it to that import's named list rather than a new import statement, if one already exists.)

Near the other `createFloatingDrag(...)` calls (around line 296):

```ts
const opDrag = createFloatingDrag(".opening-panel-float");
```

Near `haAreas` (around line 380), instantiate the store:

```ts
const haStateStore = createHaStateStore();
```

Near `selectedRoom` (around line 339), add:

```ts
const selectedOpening = $derived(
  toolStore.state.selectedOpeningId
    ? (floorStore.floor.openings.find((o) => o.id === toolStore.state.selectedOpeningId) ?? null)
    : null
);
const selectedOpeningWall = $derived(
  selectedOpening
    ? (floorStore.floor.walls.find((w) => w.id === selectedOpening.wallId) ?? null)
    : null
);
const selectedOpeningAreaIds = $derived.by(() => {
  if (!selectedOpening || !selectedOpeningWall) return [];
  const rooms = findAdjacentRooms(selectedOpening, selectedOpeningWall, floorStore.floor.rooms);
  return [...new Set(rooms.map((r) => r.haAreaId).filter((id): id is string => id !== null))];
});

const haLayerActive = $derived(activeLayers.has("ha"));
```

Add two effects (near the existing `haAreas`-fetching `$effect`, around line 423) to drive the store's lifecycle:

```ts
$effect(() => {
  haStateStore.setActive(isFloorPlan && haLayerActive);
});

$effect(() => {
  const ids = new Set<string>();
  for (const opening of floorStore.floor.openings) {
    if (opening.haEntityId) ids.add(opening.haEntityId);
    if (opening.hasShutter && opening.shutterEntityId) ids.add(opening.shutterEntityId);
  }
  haStateStore.setEntityIds(ids);
});
```

In the template, pass the two new props to `<Canvas>` (in the block around line 880-908):

```svelte
              haLayerActive={haLayerActive}
              haStates={haStateStore.states}
```

Add the `OpeningPanel` render block right after the existing `{#if selectedRoom}...{/if}` block (around line 919):

```svelte
            {#if selectedOpening}
              <div class="opening-panel-float" style={opDrag.pos ? `left:${opDrag.pos.x}px;top:${opDrag.pos.y}px;right:auto;transform:none` : ''}>
                <OpeningPanel
                  opening={selectedOpening}
                  areaIds={selectedOpeningAreaIds}
                  onupdate={(patch) => floorStore.updateOpening(selectedOpening.id, patch)}
                  onstartdrag={opDrag.startDrag}
                  ondismiss={() => toolStore.selectOpening(null)}
                />
              </div>
            {/if}
```

In `App.svelte`'s `<style>` block, right after the existing `.room-panel-float` rule and its mobile media-query override (around line 1513-1527), add the equivalent rule for the new panel:

```css
  .opening-panel-float {
    position: absolute; right: 120px; top: 50%; transform: translateY(-50%);
    z-index: 21;
  }

  @media (max-width: 480px) { /* --bp-mobile */
    .opening-panel-float {
      position: fixed;
      left: 0; right: 0; bottom: 48px; top: auto;
      transform: none !important;
      width: 100%;
      max-height: 45vh;
      z-index: 26;
    }
  }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/App.test.ts -t "OpeningPanel wiring"`
Expected: PASS.

- [ ] **Step 5: Run the full editor suite**

Run: `cd packages/editor && npx vitest run`
Expected: PASS — no regressions. In particular confirm no test unexpectedly triggers a real `new WebSocket(...)` call (jsdom has no native WebSocket): this only happens if `haStateStore.setEntityIds` is ever called with a non-empty set while `isFloorPlan && haLayerActive` is true in some *other* existing test's fixture. Since the "ha" layer defaults on (Task 9) but no other test's fixture openings carry `haEntityId`/`shutterEntityId`, `entityIds` stays empty everywhere except this task's own test, so `connect()` no-ops.

- [ ] **Step 6: Run the geometry and backend suites once more for a full cross-package check**

Run: `cd packages/geometry && npx vitest run && cd ../backend && python -m pytest && cd ../editor && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.test.ts
git commit -m "feat(editor): wire OpeningPanel and live HA state into the floor plan editor"
```

- [ ] **Step 8: Manual smoke test**

Since this feature can't be fully exercised without a real Home Assistant instance, do a manual pass with the dev server running against a standalone (non-HA) backend to confirm graceful degradation: the "ha" layer toggle appears and defaults on, selecting a window/door shows the `OpeningPanel` with the "assign this room to an HA Area first" hint (no `SUPERVISOR_TOKEN` in this dev environment), and nothing throws in the browser console. A full end-to-end check against a real HA instance (sensor color change, shutter overlay, open/close/stop) is out of scope for this environment and should be done once deployed as an add-on.

---

## Post-plan check

After Task 14, re-read `docs/superpowers/specs/2026-08-06-ha-opening-sensors-design.md` end to end and confirm every Goal has a corresponding task:

- Sensor linking + color → Tasks 1, 2, 5, 7, 11, 13, 14.
- Shutter linking + overlay + controls → Tasks 1, 2, 3, 5, 7, 11, 13, 14.
- Near-real-time delivery → Tasks 4, 8, 10, 12, 14.
- Default-on toggleable layer → Task 9.
- Area-scoped pickers → Tasks 6, 13, 14.

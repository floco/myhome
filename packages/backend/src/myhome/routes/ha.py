import asyncio
import json
import os
import re
from urllib.parse import quote

import httpx
import websockets
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed

from ..deps import get_user_from_request
from ..ha_ingress import resolve_ha_ingress_user

router = APIRouter()

_HA_BASE = "http://supervisor/core/api"
_HA_WS_URL = "ws://supervisor/core/websocket"

_ALLOWED_ENTITY_DOMAINS = {"binary_sensor", "cover"}
_ENTITY_ID_RE = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")


def _is_allowed_entity_id(entity_id: object) -> bool:
    """Restricts WS state subscriptions to the same binary_sensor/cover scope
    that /api/ha/entities enforces -- without this, an authenticated client
    could request live state for *any* HA entity (locks, cameras, alarm
    panels, ...) via the WS channel, bypassing that domain restriction."""
    if not isinstance(entity_id, str) or not _ENTITY_ID_RE.match(entity_id):
        return False
    domain = entity_id.split(".", 1)[0]
    return domain in _ALLOWED_ENTITY_DOMAINS


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@router.get("/api/ha/areas")
async def get_ha_areas() -> list[dict]:
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return []
    try:
        async with httpx.AsyncClient() as client:
            # Try the area registry list endpoint (HA 2023.x+)
            resp = await client.get(
                f"{_HA_BASE}/config/area_registry/list",
                headers=_auth_headers(token),
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {"area_id": a.get("area_id", a.get("id", "")), "name": a.get("name", "")}
                    for a in data
                    if a.get("area_id") or a.get("id")
                ]
            # Fallback: template API works in all HA versions
            template = (
                "[{%- for a in areas() -%}"
                "{%- if not loop.first -%},{%- endif -%}"
                '{\"area_id\":\"{{ a }}\",\"name\":\"{{ area_name(a) | replace(\'\"\', \'\\\\"\') }}\"}'
                "{%- endfor -%}]"
            )
            resp2 = await client.post(
                f"{_HA_BASE}/template",
                headers=_auth_headers(token),
                json={"template": template},
                timeout=5.0,
            )
            if resp2.status_code == 200:
                return json.loads(resp2.text)
    except Exception:
        pass
    return []


@router.get("/api/ha/entities")
async def get_ha_entities(area_id: str, domain: str, device_classes: str | None = None) -> list[dict]:
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
        "| replace('\"', '\\\\\"') }}\",\"device_class\":\"{{ (state_attr(e, 'device_class') or '') "
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
                entities = json.loads(resp.text)
                if device_classes:
                    allowed = {d.strip() for d in device_classes.split(",") if d.strip()}
                    entities = [e for e in entities if e.get("device_class") in allowed]
                return [{"entity_id": e["entity_id"], "name": e["name"]} for e in entities]
    except Exception:
        pass
    return []


async def call_ha_service(domain: str, service: str, data: dict) -> None:
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise RuntimeError("SUPERVISOR_TOKEN not set")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_HA_BASE}/services/{domain}/{service}",
            headers=_auth_headers(token),
            json=data,
            timeout=5.0,
        )
        resp.raise_for_status()


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
    resp = await client.get(
        f"{_HA_BASE}/states/{quote(entity_id, safe='')}", headers=_auth_headers(token), timeout=5.0
    )
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
                requested_ids = data.get("entity_ids", [])
                new_ids = {e for e in requested_ids if _is_allowed_entity_id(e)}
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

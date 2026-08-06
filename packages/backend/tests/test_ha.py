import asyncio
import json

import pytest
import respx
from httpx import Response

import myhome.routes.ha as ha_module
from myhome.routes.ha import call_ha_service


async def test_call_ha_service_posts_to_correct_url_and_payload(monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    with respx.mock:
        route = respx.post("http://supervisor/core/api/services/notify/mobile_app_pixel").mock(
            return_value=Response(200, json={"ok": True})
        )
        await call_ha_service("notify", "mobile_app_pixel", {"message": "hello"})
        assert route.called
        request = route.calls[0].request
        assert request.headers["Authorization"] == "Bearer test-token"
        assert json.loads(request.content) == {"message": "hello"}


async def test_call_ha_service_raises_without_token(monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        await call_ha_service("notify", "mobile_app_pixel", {"message": "hello"})


async def test_call_ha_service_raises_on_http_error(monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    with respx.mock:
        respx.post("http://supervisor/core/api/services/notify/mobile_app_pixel").mock(
            return_value=Response(500)
        )
        with pytest.raises(Exception):
            await call_ha_service("notify", "mobile_app_pixel", {"message": "hello"})


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

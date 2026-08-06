import json

import pytest
import respx
from httpx import Response

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

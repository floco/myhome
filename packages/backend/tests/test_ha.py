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

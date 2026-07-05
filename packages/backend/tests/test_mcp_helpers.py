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

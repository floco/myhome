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


async def _call_tool_over_new_session(headers: dict, tool_name: str, arguments: dict):
    """Open a fresh MCP client session against the already-running app and call one
    tool. Must be invoked from *inside* an `async with app.router.lifespan_context(app):`
    block -- the FastMCP session manager's `.run()` can only be entered once per
    process, so every test in this module shares a single lifespan entry rather than
    each opening its own."""
    transport = httpx.ASGITransport(app=app)
    # follow_redirects=True matches the MCP SDK's own default http client
    # (mcp.shared._httpx_utils.create_mcp_http_client) -- FastMCP's internal
    # Starlette sub-app redirects a bare "/mcp" to "/mcp/", and every real MCP
    # client follows that transparently.
    http_client = httpx.AsyncClient(
        transport=transport, base_url="http://testserver", headers=headers, follow_redirects=True,
    )
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


async def test_mcp_admin_and_ro_tokens_via_real_protocol():
    """A single lifespan entry covering both scenarios -- the FastMCP session
    manager's `.run()` can only be called once per process, so admin and ro
    coverage must share one `async with app.router.lifespan_context(app):` block
    rather than each living in its own test function."""
    admin_token = _seed_admin_and_token(role="admin")
    ro_token = _seed_admin_and_token(role="ro")
    save_mcp_config(McpConfig(enabled=True))

    async with app.router.lifespan_context(app):
        admin_read = await _call_tool_over_new_session(
            {"Authorization": f"Bearer {admin_token}"}, "list_homes", {},
        )
        assert admin_read.isError is not True

        admin_write = await _call_tool_over_new_session(
            {"Authorization": f"Bearer {admin_token}"}, "create_home", {"name": "New Home", "type": "existing"},
        )
        assert admin_write.isError is not True

        ro_read = await _call_tool_over_new_session(
            {"Authorization": f"Bearer {ro_token}"}, "list_homes", {},
        )
        assert ro_read.isError is not True

        ro_write = await _call_tool_over_new_session(
            {"Authorization": f"Bearer {ro_token}"}, "create_home", {"name": "Nope", "type": "existing"},
        )
        assert ro_write.isError is True

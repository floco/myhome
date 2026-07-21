import pytest
from starlette.requests import Request

from myhome.ha_ingress import _ingress_trust_satisfied, resolve_ha_ingress_user
from myhome.models_auth import User, UserDocument
from myhome.persistence_auth import initial_admin_password_file, load_users, save_users


def _make_request(headers: dict[str, str], client_host: str = "172.30.32.2") -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (client_host, 12345),
        "method": "GET",
        "path": "/api/homes",
    }
    return Request(scope)


def _headers_for(user_id: str, username: str, display_name: str) -> dict[str, str]:
    return {
        "X-Remote-User-Id": user_id,
        "X-Remote-User-Name": username,
        "X-Remote-User-Display-Name": display_name,
    }


_FULL_HEADERS = _headers_for("ha-abc123", "jane", "Jane Doe")


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


@pytest.fixture()
def ingress_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    return tmp_path


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

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from myhome import oidc as oidc_module
from myhome.main import app
from myhome.models_auth import OidcConfig
from myhome.persistence_auth import load_oidc_config, save_oidc_config


@pytest.fixture()
def fresh(tmp_path, monkeypatch):
    """Unauthenticated client, no users/config seeded."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture(autouse=True)
def _clear_discovery_cache():
    oidc_module.clear_discovery_cache()
    yield
    oidc_module.clear_discovery_cache()


def test_oidc_status_reachable_without_auth(fresh):
    resp = fresh.get("/api/auth/oidc/status")
    assert resp.status_code == 200


def test_oidc_status_reflects_saved_config(fresh, tmp_path, monkeypatch):
    save_oidc_config(OidcConfig(enabled=True, provider_name="Keycloak", issuer="https://x.test"))
    resp = fresh.get("/api/auth/oidc/status")
    assert resp.status_code == 200
    assert resp.json() == {"enabled": True, "provider_name": "Keycloak"}


def test_oidc_status_defaults_to_disabled(fresh):
    resp = fresh.get("/api/auth/oidc/status")
    assert resp.json() == {"enabled": False, "provider_name": ""}


def test_get_oidc_config_requires_admin(client, ro_client):
    resp = ro_client.get("/api/auth/oidc/config")
    assert resp.status_code == 403
    resp = client.get("/api/auth/oidc/config")
    assert resp.status_code == 200


def test_get_oidc_config_masks_secret(client):
    save_oidc_config(OidcConfig(enabled=True, provider_name="Keycloak", issuer="https://x.test", client_secret="realsecret"))
    resp = client.get("/api/auth/oidc/config")
    data = resp.json()
    assert data["client_secret"] == "••••••••"
    assert "realsecret" not in resp.text


def test_get_oidc_config_empty_secret_shows_empty(client):
    resp = client.get("/api/auth/oidc/config")
    assert resp.json()["client_secret"] == ""


def test_put_oidc_config_disabled_skips_discovery_check(client):
    resp = client.put("/api/auth/oidc/config", json={
        "enabled": False, "provider_name": "Keycloak", "issuer": "https://unreachable.invalid",
        "client_id": "cid", "default_role": "normal", "scopes": ["openid", "profile", "email"],
    })
    assert resp.status_code == 200


def test_put_oidc_config_enabled_validates_discovery(client):
    with respx.mock:
        respx.get("https://good.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json={
                "authorization_endpoint": "https://good.test/authorize",
                "token_endpoint": "https://good.test/token",
                "jwks_uri": "https://good.test/jwks",
            })
        )
        resp = client.put("/api/auth/oidc/config", json={
            "enabled": True, "provider_name": "Good", "issuer": "https://good.test",
            "client_id": "cid", "client_secret": "s3cret", "default_role": "normal",
            "scopes": ["openid", "profile", "email"],
        })
    assert resp.status_code == 200
    assert resp.json()["client_secret"] == "••••••••"


def test_put_oidc_config_enabled_rejects_unreachable_issuer(client):
    with respx.mock:
        respx.get("https://bad.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(500)
        )
        resp = client.put("/api/auth/oidc/config", json={
            "enabled": True, "provider_name": "Bad", "issuer": "https://bad.test",
            "client_id": "cid", "client_secret": "s3cret", "default_role": "normal",
            "scopes": ["openid", "profile", "email"],
        })
    assert resp.status_code == 422


def test_put_oidc_config_keeps_existing_secret_when_omitted(client):
    client.put("/api/auth/oidc/config", json={
        "enabled": False, "provider_name": "Keycloak", "issuer": "https://x.test",
        "client_id": "cid", "client_secret": "s3cret", "default_role": "normal",
        "scopes": ["openid", "profile", "email"],
    })
    resp = client.put("/api/auth/oidc/config", json={
        "enabled": False, "provider_name": "Keycloak Renamed", "issuer": "https://x.test",
        "client_id": "cid", "default_role": "normal", "scopes": ["openid", "profile", "email"],
    })
    assert resp.status_code == 200
    assert load_oidc_config().client_secret == "s3cret"
    assert load_oidc_config().provider_name == "Keycloak Renamed"


def test_put_oidc_config_clears_discovery_cache(client):
    with respx.mock:
        route = respx.get("https://good.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json={
                "authorization_endpoint": "https://good.test/authorize",
                "token_endpoint": "https://good.test/token",
                "jwks_uri": "https://good.test/jwks",
            })
        )
        client.put("/api/auth/oidc/config", json={
            "enabled": True, "provider_name": "Good", "issuer": "https://good.test",
            "client_id": "cid", "client_secret": "s3cret", "default_role": "normal",
            "scopes": ["openid", "profile", "email"],
        })
        client.put("/api/auth/oidc/config", json={
            "enabled": True, "provider_name": "Good Renamed", "issuer": "https://good.test",
            "client_id": "cid", "default_role": "normal", "scopes": ["openid", "profile", "email"],
        })
    assert route.call_count == 2  # second PUT re-fetches instead of using the cached doc

import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx
from authlib.jose import JsonWebKey
from authlib.jose import jwt as authlib_jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from myhome import oidc as oidc_module
from myhome.main import app
from myhome.models_auth import OidcConfig
from myhome.persistence_auth import load_oidc_config, load_users, save_oidc_config, save_users


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


@pytest.fixture(autouse=True)
def _resolve_test_hostnames_to_public_ip(monkeypatch):
    """Test hostnames (*.test) don't resolve via real DNS. Pin every hostname
    to a public IP so SSRF host-validation doesn't reject mocked requests."""
    monkeypatch.setattr(oidc_module, "_resolve_hostname", lambda hostname: ["1.1.1.1"])


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


DISCOVERY = {
    "authorization_endpoint": "https://idp.example.test/authorize",
    "token_endpoint": "https://idp.example.test/token",
    "jwks_uri": "https://idp.example.test/jwks",
}


def _generate_rsa_keypair() -> tuple[bytes, bytes]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def _make_jwks(public_pem: bytes, kid: str) -> dict:
    jwk = JsonWebKey.import_key(public_pem, {"kid": kid})
    return {"keys": [jwk.as_dict()]}


def _make_id_token(private_pem: bytes, kid: str, claims: dict) -> str:
    header = {"alg": "RS256", "kid": kid}
    return authlib_jwt.encode(header, claims, private_pem).decode("utf-8")


def test_oidc_login_redirects_to_authorization_endpoint(fresh):
    save_oidc_config(OidcConfig(
        enabled=True, provider_name="TestIdP", issuer="https://idp.example.test",
        client_id="cid", client_secret="csecret", default_role="normal",
        scopes=["openid", "profile", "email"],
    ))
    with respx.mock:
        respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=DISCOVERY)
        )
        resp = fresh.get("/api/auth/oidc/login", follow_redirects=False)
    assert resp.status_code == 307
    location = resp.headers["location"]
    assert location.startswith("https://idp.example.test/authorize")
    assert "code_challenge=" in location
    assert "oidc_flow" in resp.cookies


def test_oidc_login_404s_when_disabled(fresh):
    resp = fresh.get("/api/auth/oidc/login", follow_redirects=False)
    assert resp.status_code == 404


def test_oidc_callback_creates_new_user_and_sets_session(fresh):
    private_pem, public_pem = _generate_rsa_keypair()
    kid = "test-key-1"
    save_oidc_config(OidcConfig(
        enabled=True, provider_name="TestIdP", issuer="https://idp.example.test",
        client_id="cid", client_secret="csecret", default_role="normal",
        scopes=["openid", "profile", "email"],
    ))
    with respx.mock:
        respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=DISCOVERY)
        )
        login_resp = fresh.get("/api/auth/oidc/login", follow_redirects=False)
        qs = parse_qs(urlparse(login_resp.headers["location"]).query)
        state, nonce = qs["state"][0], qs["nonce"][0]

        claims_in = {
            "iss": "https://idp.example.test", "aud": "cid", "sub": "sub-123",
            "exp": int(time.time()) + 3600, "nonce": nonce,
            "preferred_username": "newoidcuser", "email": "newoidcuser@example.test",
        }
        id_token = _make_id_token(private_pem, kid, claims_in)
        respx.get("https://idp.example.test/jwks").mock(
            return_value=httpx.Response(200, json=_make_jwks(public_pem, kid))
        )
        respx.post("https://idp.example.test/token").mock(
            return_value=httpx.Response(200, json={
                "access_token": "at-1", "id_token": id_token, "token_type": "Bearer",
            })
        )
        callback_resp = fresh.get(
            "/api/auth/oidc/callback", params={"code": "authcode123", "state": state},
            follow_redirects=False,
        )
    assert callback_resp.status_code == 307
    assert callback_resp.headers["location"] == "/"
    assert "myhome_access" in callback_resp.cookies

    users = load_users().users
    created = next(u for u in users if u.username == "newoidcuser")
    assert created.role == "normal"
    assert created.auth_provider == "oidc"
    assert created.password_hash is None
    assert created.oidc_sub == "sub-123"


def test_oidc_callback_rejects_conflicting_local_username(fresh):
    from datetime import datetime, timezone
    from myhome.models_auth import User, UserDocument
    save_users(UserDocument(users=[
        User(id="existing-1", username="alice", password_hash="somehash", role="admin",
             created_at=datetime.now(timezone.utc).isoformat(), auth_provider="local"),
    ]))
    private_pem, public_pem = _generate_rsa_keypair()
    kid = "test-key-1"
    save_oidc_config(OidcConfig(
        enabled=True, provider_name="TestIdP", issuer="https://idp.example.test",
        client_id="cid", client_secret="csecret", default_role="ro",
        scopes=["openid", "profile", "email"],
    ))
    with respx.mock:
        respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=DISCOVERY)
        )
        login_resp = fresh.get("/api/auth/oidc/login", follow_redirects=False)
        qs = parse_qs(urlparse(login_resp.headers["location"]).query)
        state, nonce = qs["state"][0], qs["nonce"][0]

        claims_in = {
            "iss": "https://idp.example.test", "aud": "cid", "sub": "sub-999",
            "exp": int(time.time()) + 3600, "nonce": nonce, "preferred_username": "Alice",
        }
        id_token = _make_id_token(private_pem, kid, claims_in)
        respx.get("https://idp.example.test/jwks").mock(
            return_value=httpx.Response(200, json=_make_jwks(public_pem, kid))
        )
        respx.post("https://idp.example.test/token").mock(
            return_value=httpx.Response(200, json={
                "access_token": "at-1", "id_token": id_token, "token_type": "Bearer",
            })
        )
        callback_resp = fresh.get(
            "/api/auth/oidc/callback", params={"code": "authcode123", "state": state},
            follow_redirects=False,
        )
    assert callback_resp.status_code == 307
    assert callback_resp.headers["location"] == "/?error=oidc_account_conflict"
    assert "myhome_access" not in callback_resp.cookies
    users = load_users().users
    assert len(users) == 1
    assert users[0].auth_provider == "local"  # untouched


def test_oidc_callback_relogin_matches_by_sub_even_if_username_changed(fresh):
    private_pem, public_pem = _generate_rsa_keypair()
    kid = "test-key-1"
    save_oidc_config(OidcConfig(
        enabled=True, provider_name="TestIdP", issuer="https://idp.example.test",
        client_id="cid", client_secret="csecret", default_role="normal",
        scopes=["openid", "profile", "email"],
    ))

    def _do_login(username: str, sub: str):
        with respx.mock:
            respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
                return_value=httpx.Response(200, json=DISCOVERY)
            )
            login_resp = fresh.get("/api/auth/oidc/login", follow_redirects=False)
            qs = parse_qs(urlparse(login_resp.headers["location"]).query)
            state, nonce = qs["state"][0], qs["nonce"][0]
            claims_in = {
                "iss": "https://idp.example.test", "aud": "cid", "sub": sub,
                "exp": int(time.time()) + 3600, "nonce": nonce, "preferred_username": username,
            }
            id_token = _make_id_token(private_pem, kid, claims_in)
            respx.get("https://idp.example.test/jwks").mock(
                return_value=httpx.Response(200, json=_make_jwks(public_pem, kid))
            )
            respx.post("https://idp.example.test/token").mock(
                return_value=httpx.Response(200, json={
                    "access_token": "at-1", "id_token": id_token, "token_type": "Bearer",
                })
            )
            return fresh.get(
                "/api/auth/oidc/callback", params={"code": "authcode123", "state": state},
                follow_redirects=False,
            )

    first = _do_login("dave", "sub-abc")
    assert "myhome_access" in first.cookies
    second = _do_login("dave-renamed", "sub-abc")  # same sub, IdP-side username changed
    assert "myhome_access" in second.cookies

    users = load_users().users
    assert len(users) == 1  # re-login matched by sub, no duplicate created
    assert users[0].oidc_sub == "sub-abc"


def test_oidc_callback_backfills_legacy_oidc_user_missing_sub(fresh):
    from datetime import datetime, timezone
    from myhome.models_auth import User, UserDocument
    save_users(UserDocument(users=[
        User(id="legacy-1", username="erin", password_hash=None, role="normal",
             created_at=datetime.now(timezone.utc).isoformat(), auth_provider="oidc", oidc_sub=None),
    ]))
    private_pem, public_pem = _generate_rsa_keypair()
    kid = "test-key-1"
    save_oidc_config(OidcConfig(
        enabled=True, provider_name="TestIdP", issuer="https://idp.example.test",
        client_id="cid", client_secret="csecret", default_role="ro",
        scopes=["openid", "profile", "email"],
    ))
    with respx.mock:
        respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=DISCOVERY)
        )
        login_resp = fresh.get("/api/auth/oidc/login", follow_redirects=False)
        qs = parse_qs(urlparse(login_resp.headers["location"]).query)
        state, nonce = qs["state"][0], qs["nonce"][0]
        claims_in = {
            "iss": "https://idp.example.test", "aud": "cid", "sub": "sub-erin-1",
            "exp": int(time.time()) + 3600, "nonce": nonce, "preferred_username": "erin",
        }
        id_token = _make_id_token(private_pem, kid, claims_in)
        respx.get("https://idp.example.test/jwks").mock(
            return_value=httpx.Response(200, json=_make_jwks(public_pem, kid))
        )
        respx.post("https://idp.example.test/token").mock(
            return_value=httpx.Response(200, json={
                "access_token": "at-1", "id_token": id_token, "token_type": "Bearer",
            })
        )
        callback_resp = fresh.get(
            "/api/auth/oidc/callback", params={"code": "authcode123", "state": state},
            follow_redirects=False,
        )
    assert "myhome_access" in callback_resp.cookies
    users = load_users().users
    assert len(users) == 1
    assert users[0].id == "legacy-1"
    assert users[0].oidc_sub == "sub-erin-1"  # backfilled


def test_oidc_callback_rejects_mismatched_state(fresh):
    save_oidc_config(OidcConfig(
        enabled=True, provider_name="TestIdP", issuer="https://idp.example.test",
        client_id="cid", client_secret="csecret", default_role="normal",
    ))
    with respx.mock:
        respx.get("https://idp.example.test/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=DISCOVERY)
        )
        fresh.get("/api/auth/oidc/login", follow_redirects=False)
        resp = fresh.get(
            "/api/auth/oidc/callback", params={"code": "x", "state": "wrong-state"},
            follow_redirects=False,
        )
    assert resp.status_code == 307
    assert resp.headers["location"] == "/?error=oidc_failed"


def test_oidc_callback_rejects_missing_flow_cookie(fresh):
    resp = fresh.get(
        "/api/auth/oidc/callback", params={"code": "x", "state": "some-state"},
        follow_redirects=False,
    )
    assert resp.status_code == 307
    assert resp.headers["location"] == "/?error=oidc_failed"


def test_oidc_callback_passes_through_idp_error_param(fresh):
    resp = fresh.get(
        "/api/auth/oidc/callback", params={"error": "access_denied"},
        follow_redirects=False,
    )
    assert resp.status_code == 307
    assert resp.headers["location"] == "/?error=oidc_failed"

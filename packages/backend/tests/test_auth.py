from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from myhome.main import app
from myhome.models_auth import User, UserDocument
from myhome.persistence_auth import load_users, save_users


@pytest.fixture()
def fresh(tmp_path, monkeypatch):
    """Unauthenticated client with admin user already seeded."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    save_users(UserDocument(users=[
        User(id="u1", username="admin", password_hash=pwd_ctx.hash("admin123"),
             role="admin", created_at="2026-01-01T00:00:00+00:00")
    ]))
    return TestClient(app, raise_server_exceptions=True)


def test_unauthenticated_request_returns_401(fresh):
    resp = fresh.get("/api/settings")
    assert resp.status_code == 401


def test_login_happy_path(fresh):
    resp = fresh.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"
    assert "myhome_access" in resp.cookies
    assert "myhome_refresh" in resp.cookies


def test_login_wrong_password_returns_401(fresh):
    resp = fresh.post("/api/auth/login", json={"username": "admin", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_unknown_user_returns_401(fresh):
    resp = fresh.post("/api/auth/login", json={"username": "nobody", "password": "admin123"})
    assert resp.status_code == 401


def test_me_returns_current_user(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"


def test_me_returns_401_when_not_logged_in(fresh):
    resp = fresh.get("/api/auth/me")
    assert resp.status_code == 401


def test_logout_clears_cookies(client):
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 204
    assert resp.cookies.get("myhome_access") is None or resp.cookies.get("myhome_access") == ""


def test_refresh_issues_new_access_token(fresh):
    login_resp = fresh.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_resp.status_code == 200
    # TestClient preserves cookies; refresh uses the myhome_refresh cookie
    resp = fresh.post("/api/auth/refresh")
    assert resp.status_code == 204
    assert "myhome_access" in resp.cookies


def test_refresh_fails_without_cookie(fresh):
    resp = fresh.post("/api/auth/refresh")
    assert resp.status_code == 401


def test_change_password_succeeds(client):
    resp = client.put("/api/auth/me/password", json={
        "current_password": "admin123",
        "new_password": "newpassword99",
    })
    assert resp.status_code == 204


def test_change_password_wrong_current_returns_400(client):
    resp = client.put("/api/auth/me/password", json={
        "current_password": "wrongpass",
        "new_password": "newpassword99",
    })
    assert resp.status_code == 400


def test_change_password_too_short_returns_422(client):
    resp = client.put("/api/auth/me/password", json={
        "current_password": "admin123",
        "new_password": "short",
    })
    assert resp.status_code == 422


def test_login_against_oidc_only_user_returns_401(fresh):
    doc = load_users()
    doc.users.append(User(
        id="u-oidc", username="oidcuser", password_hash=None, role="normal",
        created_at=datetime.now(timezone.utc).isoformat(), auth_provider="oidc",
    ))
    save_users(doc)
    resp = fresh.post("/api/auth/login", json={"username": "oidcuser", "password": "anything"})
    assert resp.status_code == 401


def test_change_password_sets_password_when_none_exists(fresh):
    doc = load_users()
    doc.users.append(User(
        id="u-oidc2", username="oidcuser2", password_hash=None, role="normal",
        created_at=datetime.now(timezone.utc).isoformat(), auth_provider="oidc",
    ))
    save_users(doc)
    from myhome.deps import create_access_token
    fresh.cookies.set("myhome_access", create_access_token("u-oidc2", "normal"))
    resp = fresh.put("/api/auth/me/password", json={
        "current_password": "",
        "new_password": "newpassword99",
    })
    assert resp.status_code == 204
    reloaded = next(u for u in load_users().users if u.id == "u-oidc2")
    from myhome.deps import pwd_ctx
    assert pwd_ctx.verify("newpassword99", reloaded.password_hash)

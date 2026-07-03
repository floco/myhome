import pytest


def test_list_tokens_initially_empty(client):
    resp = client.get("/api/auth/tokens")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_token(client):
    resp = client.post("/api/auth/tokens", json={"name": "My Script", "role": "ro"})
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert len(data["token"]) == 64  # 32 bytes hex
    assert data["info"]["name"] == "My Script"
    assert data["info"]["role"] == "ro"


def test_created_token_appears_in_list(client):
    client.post("/api/auth/tokens", json={"name": "Listed", "role": "ro"})
    resp = client.get("/api/auth/tokens")
    tokens = resp.json()
    assert any(t["name"] == "Listed" for t in tokens)


def test_token_list_does_not_expose_raw_token(client):
    client.post("/api/auth/tokens", json={"name": "Secret", "role": "ro"})
    tokens = client.get("/api/auth/tokens").json()
    for t in tokens:
        assert "token_hash" not in t
        assert len(t.get("id", "")) < 32  # id is short, not the raw 64-char token


def test_create_token_scope_ceiling_enforced(ro_client):
    # ro user cannot create an admin-scoped token
    resp = ro_client.post("/api/auth/tokens", json={"name": "Escalation", "role": "admin"})
    assert resp.status_code == 422


def test_create_token_invalid_role_returns_422(client):
    resp = client.post("/api/auth/tokens", json={"name": "Bad", "role": "superuser"})
    assert resp.status_code == 422


def test_revoke_token(client):
    create_resp = client.post("/api/auth/tokens", json={"name": "ToRevoke", "role": "ro"})
    tid = create_resp.json()["info"]["id"]
    resp = client.delete(f"/api/auth/tokens/{tid}")
    assert resp.status_code == 204
    tokens = client.get("/api/auth/tokens").json()
    assert not any(t["id"] == tid for t in tokens)


def test_revoke_nonexistent_token_returns_404(client):
    resp = client.delete("/api/auth/tokens/nonexistent")
    assert resp.status_code == 404


def test_bearer_token_authenticates_request(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    from passlib.context import CryptContext
    from myhome.models_auth import User, UserDocument
    from myhome.persistence_auth import save_users
    from fastapi.testclient import TestClient
    from myhome.main import app
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    save_users(UserDocument(users=[
        User(id="u1", username="admin", password_hash=pwd_ctx.hash("admin123"),
             role="admin", created_at="2026-01-01T00:00:00+00:00")
    ]))
    tc = TestClient(app)
    # Login to get a session, then create a token
    tc.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    hid = tc.post("/api/homes", json={"name": "Test Home", "type": "existing"}).json()["id"]
    create_resp = tc.post("/api/auth/tokens", json={"name": "Automation", "role": "normal"})
    raw_token = create_resp.json()["token"]
    # Now use the raw token as a Bearer token on a fresh (cookieless) client
    bare = TestClient(app)
    resp = bare.get(f"/api/homes/{hid}/settings", headers={"Authorization": f"Bearer {raw_token}"})
    assert resp.status_code == 200


def test_bearer_token_updates_last_used_at(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    from passlib.context import CryptContext
    from myhome.models_auth import User, UserDocument
    from myhome.persistence_auth import load_tokens, save_users
    from fastapi.testclient import TestClient
    from myhome.main import app
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    save_users(UserDocument(users=[
        User(id="u1", username="admin", password_hash=pwd_ctx.hash("admin123"),
             role="admin", created_at="2026-01-01T00:00:00+00:00")
    ]))
    tc = TestClient(app)
    tc.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    hid = tc.post("/api/homes", json={"name": "Test Home", "type": "existing"}).json()["id"]
    create_resp = tc.post("/api/auth/tokens", json={"name": "Tracker", "role": "ro"})
    raw_token = create_resp.json()["token"]
    bare = TestClient(app)
    bare.get(f"/api/homes/{hid}/settings", headers={"Authorization": f"Bearer {raw_token}"})
    doc = load_tokens()
    used = next(t for t in doc.tokens if t.name == "Tracker")
    assert used.last_used_at is not None

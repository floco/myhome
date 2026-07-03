import pytest


def test_ro_user_can_read_settings(client, ro_client, home_id):
    resp = ro_client.get(f"/api/homes/{home_id}/settings")
    assert resp.status_code == 200


def test_ro_user_blocked_from_writing_settings(client, ro_client, home_id):
    resp = ro_client.put(f"/api/homes/{home_id}/settings/suppliers", json=[{"id": "s1", "name": "Acme"}])
    assert resp.status_code == 403


def test_ro_user_blocked_from_creating_chore(client, ro_client, home_id):
    resp = ro_client.post(f"/api/homes/{home_id}/chores", json={
        "name": "Clean", "emoji": "🧹", "frequencyDays": 7,
        "nextDueDate": "2026-07-10", "categoryId": None,
    })
    assert resp.status_code == 403


def test_normal_user_can_write_data(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    from passlib.context import CryptContext
    from myhome.models_auth import User, UserDocument
    from myhome.persistence_auth import save_users
    from fastapi.testclient import TestClient
    from myhome.main import app
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    save_users(UserDocument(users=[
        User(id="u1", username="normal", password_hash=pwd_ctx.hash("normal123"),
             role="normal", created_at="2026-01-01T00:00:00+00:00")
    ]))
    tc = TestClient(app)
    tc.post("/api/auth/login", json={"username": "normal", "password": "normal123"})
    home_resp = tc.post("/api/homes", json={"name": "Test Home", "type": "existing"})
    hid = home_resp.json()["id"]
    resp = tc.put(f"/api/homes/{hid}/settings/suppliers", json=[{"id": "s1", "name": "Plumbers"}])
    assert resp.status_code == 204


def test_normal_user_blocked_from_user_management(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    from passlib.context import CryptContext
    from myhome.models_auth import User, UserDocument
    from myhome.persistence_auth import save_users
    from fastapi.testclient import TestClient
    from myhome.main import app
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    save_users(UserDocument(users=[
        User(id="u1", username="normal", password_hash=pwd_ctx.hash("normal123"),
             role="normal", created_at="2026-01-01T00:00:00+00:00")
    ]))
    tc = TestClient(app)
    tc.post("/api/auth/login", json={"username": "normal", "password": "normal123"})
    resp = tc.get("/api/auth/users")
    assert resp.status_code == 403


def test_ro_bearer_token_blocked_on_write(tmp_path, monkeypatch):
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
    tc.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    home_resp = tc.post("/api/homes", json={"name": "Test Home", "type": "existing"})
    hid = home_resp.json()["id"]
    create_resp = tc.post("/api/auth/tokens", json={"name": "ReadOnly", "role": "ro"})
    raw_token = create_resp.json()["token"]
    bare = TestClient(app)
    resp = bare.put(f"/api/homes/{hid}/settings/suppliers",
                    json=[{"id": "s1", "name": "X"}],
                    headers={"Authorization": f"Bearer {raw_token}"})
    assert resp.status_code == 403

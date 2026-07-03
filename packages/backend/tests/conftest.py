# packages/backend/tests/conftest.py
import sys
from pathlib import Path

src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

import pytest
from fastapi.testclient import TestClient
from myhome.main import app
from myhome.models_auth import User, UserDocument
from myhome.persistence_auth import save_users


def _make_users(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    from passlib.context import CryptContext

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    save_users(UserDocument(users=[
        User(
            id="u-admin", username="admin",
            password_hash=pwd_ctx.hash("admin123"),
            role="admin", created_at="2026-01-01T00:00:00+00:00",
        ),
        User(
            id="u-normal", username="normaluser",
            password_hash=pwd_ctx.hash("normal123"),
            role="normal", created_at="2026-01-01T00:00:00+00:00",
        ),
        User(
            id="u-ro", username="rouser",
            password_hash=pwd_ctx.hash("ro123456"),
            role="ro", created_at="2026-01-01T00:00:00+00:00",
        ),
    ]))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    _make_users(tmp_path, monkeypatch)
    tc = TestClient(app)
    resp = tc.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return tc


@pytest.fixture()
def home_id(client) -> str:
    resp = client.post("/api/homes", json={"name": "Test Home", "type": "existing"})
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture()
def ro_client(tmp_path, monkeypatch):
    _make_users(tmp_path, monkeypatch)
    tc = TestClient(app)
    resp = tc.post("/api/auth/login", json={"username": "rouser", "password": "ro123456"})
    assert resp.status_code == 200
    return tc

import pytest
from fastapi.testclient import TestClient
from myhome.main import app


@pytest.fixture()
def fresh(tmp_path, monkeypatch):
    """Unauthenticated client, no users/config seeded."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    return TestClient(app, raise_server_exceptions=True)


def test_oidc_status_reachable_without_auth(fresh):
    resp = fresh.get("/api/auth/oidc/status")
    assert resp.status_code == 200

import respx
from fastapi.testclient import TestClient
from httpx import Response

from myhome import system_info
from myhome.main import app


def test_get_system_info_requires_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-tests-only")
    tc = TestClient(app)
    resp = tc.get("/api/system/info")
    assert resp.status_code == 401


def test_get_system_info_returns_full_shape(client, tmp_path, monkeypatch):
    version_file = tmp_path / "VERSION"
    version_file.write_text("0.8.0")
    monkeypatch.setenv("APP_VERSION_FILE", str(version_file))
    system_info.reset_update_cache()
    with respx.mock:
        respx.get(system_info._GITHUB_TAGS_URL).mock(
            return_value=Response(200, json=[{"name": "v0.9.0"}])
        )
        resp = client.get("/api/system/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "0.8.0"
    assert data["deploymentMode"] == "standalone"
    assert data["dbSchemaVersion"] == 8
    assert isinstance(data["pythonVersion"], str)
    assert isinstance(data["arch"], str)
    assert data["uptimeSeconds"] >= 0
    assert data["homeCount"] == 0
    assert data["databaseSizeBytes"] >= 0
    assert data["updateCheck"]["status"] == "update_available"
    assert data["updateCheck"]["latestVersion"] == "0.9.0"

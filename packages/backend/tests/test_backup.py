import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from myhome.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app)


def test_download_backup_returns_zip_with_expected_files(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "house.json").write_text('{"floors": []}')
    (tmp_path / "settings.json").write_text('{"version": 1}')
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    (kb_dir / "e1.md").write_text("# Article")

    resp = TestClient(app).get("/api/backup/download")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    cd = resp.headers["content-disposition"]
    assert "myhome-backup-" in cd
    assert ".zip" in cd

    names = zipfile.ZipFile(io.BytesIO(resp.content)).namelist()
    assert "house.json" in names
    assert "settings.json" in names
    assert "kb/e1.md" in names


def test_download_backup_empty_data_dir(client):
    resp = client.get("/api/backup/download")
    assert resp.status_code == 200
    assert zipfile.ZipFile(io.BytesIO(resp.content)).namelist() == []

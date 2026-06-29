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


def test_restore_replaces_data_dir_contents(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "old.json").write_text('{"old": true}')

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("house.json", '{"floors": []}')
        zf.writestr("settings.json", '{"version": 1}')
    buf.seek(0)

    resp = TestClient(app).post(
        "/api/backup/restore",
        files={"file": ("backup.zip", buf.read(), "application/zip")},
    )

    assert resp.status_code == 204
    assert not (tmp_path / "old.json").exists()
    assert (tmp_path / "house.json").read_text() == '{"floors": []}'
    assert (tmp_path / "settings.json").read_text() == '{"version": 1}'


def test_restore_handles_subdirectories(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("kb/e1.md", "# Article")
        zf.writestr("inventory-attachments/i1/photo.jpg", b"fake-jpeg")
    buf.seek(0)

    resp = TestClient(app).post(
        "/api/backup/restore",
        files={"file": ("backup.zip", buf.read(), "application/zip")},
    )

    assert resp.status_code == 204
    assert (tmp_path / "kb" / "e1.md").read_text() == "# Article"
    assert (tmp_path / "inventory-attachments" / "i1" / "photo.jpg").exists()


def test_restore_rejects_non_zip(client):
    resp = client.post(
        "/api/backup/restore",
        files={"file": ("data.json", b'{"not": "a zip"}', "application/json")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid backup file"


def test_restore_rejects_zip_slip(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../evil.txt", "pwned")
    buf.seek(0)
    resp = TestClient(app).post(
        "/api/backup/restore",
        files={"file": ("backup.zip", buf.read(), "application/zip")},
    )
    assert resp.status_code == 400
    assert not (tmp_path.parent / "evil.txt").exists()


def test_download_skips_symlinks(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "real.json").write_text('{"ok": true}')
    link = tmp_path / "link.json"
    link.symlink_to(tmp_path / "real.json")

    resp = TestClient(app).get("/api/backup/download")

    names = zipfile.ZipFile(io.BytesIO(resp.content)).namelist()
    assert "real.json" in names
    assert "link.json" not in names

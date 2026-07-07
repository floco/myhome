import io
import zipfile

import pytest


def test_download_backup_returns_zip_with_expected_files(client, tmp_path):
    (tmp_path / "house.json").write_text('{"floors": []}')
    (tmp_path / "settings.json").write_text('{"version": 1}')
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    (kb_dir / "e1.md").write_text("# Article")

    resp = client.get("/api/backup/download")

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
    zip_names = zipfile.ZipFile(io.BytesIO(resp.content)).namelist()
    # users.json is in data dir from fixture; filter it out
    non_auth_files = [n for n in zip_names if n not in ("users.json",)]
    assert non_auth_files == []


def test_restore_replaces_data_dir_contents(client, tmp_path):
    (tmp_path / "old.json").write_text('{"old": true}')

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("house.json", '{"floors": []}')
        zf.writestr("settings.json", '{"version": 1}')
    buf.seek(0)

    resp = client.post(
        "/api/backup/restore",
        files={"file": ("backup.zip", buf.read(), "application/zip")},
    )

    assert resp.status_code == 204
    assert not (tmp_path / "old.json").exists()
    assert (tmp_path / "house.json").read_text() == '{"floors": []}'
    assert (tmp_path / "settings.json").read_text() == '{"version": 1}'


def test_restore_handles_subdirectories(client, tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("kb/e1.md", "# Article")
        zf.writestr("inventory-attachments/i1/photo.jpg", b"fake-jpeg")
    buf.seek(0)

    resp = client.post(
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


def test_restore_rejects_zip_slip(client, tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../evil.txt", "pwned")
    buf.seek(0)
    resp = client.post(
        "/api/backup/restore",
        files={"file": ("backup.zip", buf.read(), "application/zip")},
    )
    assert resp.status_code == 400
    assert not (tmp_path.parent / "evil.txt").exists()


def test_download_skips_symlinks(client, tmp_path):
    (tmp_path / "real.json").write_text('{"ok": true}')
    link = tmp_path / "link.json"
    link.symlink_to(tmp_path / "real.json")

    resp = client.get("/api/backup/download")

    names = zipfile.ZipFile(io.BytesIO(resp.content)).namelist()
    assert "real.json" in names
    assert "link.json" not in names


def test_download_backup_excludes_scheduled_backups_directory(client, tmp_path):
    (tmp_path / "house.json").write_text('{"floors": []}')
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    (backups_dir / "myhome-backup-20260101-000000.zip").write_bytes(b"old-backup-content")

    resp = client.get("/api/backup/download")

    names = zipfile.ZipFile(io.BytesIO(resp.content)).namelist()
    assert "house.json" in names
    assert not any(n.startswith("backups/") for n in names)

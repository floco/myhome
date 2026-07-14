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
    # myhome.db (+ its WAL/SHM sidecar files) is in the data dir from the
    # fixture's save_users() call; filter it out.
    non_auth_files = [n for n in zip_names if not n.startswith("myhome.db")]
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


def test_get_backup_config_returns_defaults(client):
    resp = client.get("/api/backup/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["frequency"] == "daily"


def test_put_backup_config_round_trips(client):
    resp = client.put("/api/backup/config", json={
        "enabled": True, "frequency": "monthly", "time": "04:30",
        "dayOfWeek": 7, "dayOfMonth": 15, "retentionCount": 10,
    })
    assert resp.status_code == 200
    data = client.get("/api/backup/config").json()
    assert data["frequency"] == "monthly"
    assert data["dayOfMonth"] == 15
    assert data["retentionCount"] == 10


def test_run_backup_now_creates_entry_and_appears_in_list(client, tmp_path):
    (tmp_path / "house.json").write_text("{}")
    resp = client.post("/api/backup/scheduled/run")
    assert resp.status_code == 200
    entry = resp.json()
    assert entry["filename"].startswith("myhome-backup-")

    list_resp = client.get("/api/backup/scheduled")
    filenames = [e["filename"] for e in list_resp.json()]
    assert entry["filename"] in filenames


def test_download_scheduled_backup_returns_the_file(client, tmp_path):
    (tmp_path / "house.json").write_text('{"marker": true}')
    entry = client.post("/api/backup/scheduled/run").json()

    resp = client.get(f"/api/backup/scheduled/{entry['filename']}/download")
    assert resp.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(resp.content)).namelist()
    assert "house.json" in names


def test_download_scheduled_backup_404_for_unknown_filename(client):
    resp = client.get("/api/backup/scheduled/myhome-backup-20260101-000000.zip/download")
    assert resp.status_code == 404


def test_download_scheduled_backup_404_for_invalid_filename(client):
    resp = client.get("/api/backup/scheduled/not-a-backup.zip/download")
    assert resp.status_code == 404


def test_delete_scheduled_backup(client, tmp_path):
    (tmp_path / "house.json").write_text("{}")
    entry = client.post("/api/backup/scheduled/run").json()

    resp = client.delete(f"/api/backup/scheduled/{entry['filename']}")
    assert resp.status_code == 204

    filenames = [e["filename"] for e in client.get("/api/backup/scheduled").json()]
    assert entry["filename"] not in filenames


def test_delete_scheduled_backup_404_for_unknown_filename(client):
    resp = client.delete("/api/backup/scheduled/myhome-backup-20260101-000000.zip")
    assert resp.status_code == 404

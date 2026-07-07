import zipfile

from myhome.models_backup import BackupConfig, BackupEntry, BackupState
from myhome.persistence_backup import (
    create_backup,
    list_backups,
    load_backup_config,
    load_backup_state,
    save_backup_config,
    save_backup_state,
)


def test_backup_config_defaults():
    config = BackupConfig()
    assert config.enabled is False
    assert config.frequency == "daily"
    assert config.time == "03:00"
    assert config.dayOfWeek == 7
    assert config.dayOfMonth == 1
    assert config.retentionCount == 7


def test_backup_entry_requires_fields():
    entry = BackupEntry(filename="myhome-backup-20260707-030000.zip", createdAt="2026-07-07T03:00:00+00:00", sizeBytes=1024)
    assert entry.sizeBytes == 1024


def test_backup_state_defaults():
    assert BackupState().lastRunDate is None


def test_load_backup_config_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    config = load_backup_config()
    assert config.enabled is False
    assert config.retentionCount == 7


def test_save_and_load_backup_config_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_backup_config(BackupConfig(enabled=True, frequency="weekly", dayOfWeek=3, retentionCount=14))
    config = load_backup_config()
    assert config.enabled is True
    assert config.frequency == "weekly"
    assert config.dayOfWeek == 3
    assert config.retentionCount == 14


def test_load_backup_state_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert load_backup_state().lastRunDate is None


def test_save_and_load_backup_state_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_backup_state(BackupState(lastRunDate="2026-07-07"))
    assert load_backup_state().lastRunDate == "2026-07-07"


def test_create_backup_writes_zip_and_excludes_backups_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "house.json").write_text('{"floors": []}')

    entry = create_backup()

    assert entry.filename.startswith("myhome-backup-")
    assert entry.filename.endswith(".zip")
    assert entry.sizeBytes > 0

    backup_path = tmp_path / "backups" / entry.filename
    assert backup_path.exists()
    names = zipfile.ZipFile(backup_path).namelist()
    assert "house.json" in names
    assert not any(n.startswith("backups/") for n in names)


def test_create_backup_prunes_to_retention_count(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_backup_config(BackupConfig(retentionCount=2))
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    (backups_dir / "myhome-backup-20260101-000000.zip").write_bytes(b"a")
    (backups_dir / "myhome-backup-20260102-000000.zip").write_bytes(b"b")
    (backups_dir / "myhome-backup-20260103-000000.zip").write_bytes(b"c")

    create_backup()  # 4th backup, timestamped "now" -- definitely the newest

    entries = list_backups()
    assert len(entries) == 2
    filenames = {e.filename for e in entries}
    assert "myhome-backup-20260101-000000.zip" not in filenames
    assert "myhome-backup-20260102-000000.zip" not in filenames
    assert "myhome-backup-20260103-000000.zip" in filenames  # 2nd-newest survives


def test_list_backups_sorted_newest_first(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    (backups_dir / "myhome-backup-20260101-000000.zip").write_bytes(b"a")
    (backups_dir / "myhome-backup-20260301-000000.zip").write_bytes(b"b")
    (backups_dir / "myhome-backup-20260201-000000.zip").write_bytes(b"c")

    entries = list_backups()
    assert [e.filename for e in entries] == [
        "myhome-backup-20260301-000000.zip",
        "myhome-backup-20260201-000000.zip",
        "myhome-backup-20260101-000000.zip",
    ]


def test_list_backups_empty_when_no_backups_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert list_backups() == []

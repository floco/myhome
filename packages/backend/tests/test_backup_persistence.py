from myhome.models_backup import BackupConfig, BackupEntry, BackupState
from myhome.persistence_backup import (
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

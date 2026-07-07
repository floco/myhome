from myhome.models_backup import BackupConfig, BackupEntry, BackupState


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

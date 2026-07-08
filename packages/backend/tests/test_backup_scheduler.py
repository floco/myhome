from datetime import datetime, timezone

from myhome.backup_scheduler import _should_run_today, check_and_run_scheduled_backup
from myhome.models_backup import BackupConfig, BackupState
from myhome.persistence_backup import list_backups, load_backup_state, save_backup_config, save_backup_state


def test_should_run_today_daily_always_true():
    now = datetime(2026, 7, 7, tzinfo=timezone.utc)
    assert _should_run_today("daily", day_of_week=1, day_of_month=1, now=now) is True


def test_should_run_today_weekly_matches_configured_day():
    # 2026-07-07 is a Tuesday (isoweekday 2)
    now = datetime(2026, 7, 7, tzinfo=timezone.utc)
    assert _should_run_today("weekly", day_of_week=2, day_of_month=1, now=now) is True
    assert _should_run_today("weekly", day_of_week=3, day_of_month=1, now=now) is False


def test_should_run_today_monthly_matches_configured_day():
    now = datetime(2026, 7, 15, tzinfo=timezone.utc)
    assert _should_run_today("monthly", day_of_week=1, day_of_month=15, now=now) is True
    assert _should_run_today("monthly", day_of_week=1, day_of_month=16, now=now) is False


def test_should_run_today_monthly_clamps_to_last_day_of_short_month():
    # February 2026 (not a leap year) has 28 days
    now = datetime(2026, 2, 28, tzinfo=timezone.utc)
    assert _should_run_today("monthly", day_of_week=1, day_of_month=31, now=now) is True


async def test_check_and_run_scheduled_backup_skips_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    await check_and_run_scheduled_backup(now=datetime.now(timezone.utc))
    assert list_backups() == []


async def test_check_and_run_scheduled_backup_skips_before_configured_time(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_backup_config(BackupConfig(enabled=True, time="20:00"))
    now = datetime(2026, 7, 7, 9, 0, tzinfo=timezone.utc)
    await check_and_run_scheduled_backup(now=now)
    assert list_backups() == []


async def test_check_and_run_scheduled_backup_skips_wrong_day_for_weekly(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_backup_config(BackupConfig(enabled=True, frequency="weekly", dayOfWeek=1, time="00:00"))
    now = datetime(2026, 7, 7, 9, 0, tzinfo=timezone.utc)  # Tuesday; configured for Monday
    await check_and_run_scheduled_backup(now=now)
    assert list_backups() == []


async def test_check_and_run_scheduled_backup_skips_if_already_run_today(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    save_backup_config(BackupConfig(enabled=True, time="00:00"))
    save_backup_state(BackupState(lastRunDate="2026-07-07"))
    now = datetime(2026, 7, 7, 9, 0, tzinfo=timezone.utc)
    await check_and_run_scheduled_backup(now=now)
    assert list_backups() == []


async def test_check_and_run_scheduled_backup_runs_and_marks_state(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    (tmp_path / "house.json").write_text("{}")
    save_backup_config(BackupConfig(enabled=True, time="00:00"))
    now = datetime(2026, 7, 7, 9, 0, tzinfo=timezone.utc)

    await check_and_run_scheduled_backup(now=now)

    assert len(list_backups()) == 1
    assert load_backup_state().lastRunDate == "2026-07-07"

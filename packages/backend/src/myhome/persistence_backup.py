import os
import re
import zipfile
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import get_engine
from .models_backup import BackupConfig, BackupEntry, BackupState
from .schema import backup_config as backup_config_table, backup_state as backup_state_table

_FILENAME_RE = re.compile(r"^myhome-backup-(\d{8})-(\d{6})\.zip$")


def _parse_backup_filename(filename: str) -> datetime | None:
    m = _FILENAME_RE.match(filename)
    if not m:
        return None
    date_part, time_part = m.groups()
    return datetime.strptime(date_part + time_part, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data"))


def _backups_dir() -> Path:
    return _data_dir() / "backups"


_BACKUP_EXCLUDED_FILES = frozenset({".initial-admin-password"})


def iter_backup_files(data_dir: Path, exclude_dirs: frozenset[str] = frozenset()) -> Iterator[tuple[Path, Path]]:
    if not data_dir.exists():
        return
    resolved_root = data_dir.resolve()
    for path in data_dir.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        if not path.resolve().is_relative_to(resolved_root):
            continue
        rel = path.relative_to(data_dir)
        if rel.parts and rel.parts[0] in exclude_dirs:
            continue
        if len(rel.parts) == 1 and rel.parts[0] in _BACKUP_EXCLUDED_FILES:
            continue
        yield path, rel


def load_backup_config() -> BackupConfig:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(select(backup_config_table).where(backup_config_table.c.id == 1)).mappings().first()
    if row is None:
        return BackupConfig()
    return BackupConfig(
        enabled=bool(row["enabled"]), frequency=row["frequency"], time=row["time"],
        dayOfWeek=row["day_of_week"], dayOfMonth=row["day_of_month"], retentionCount=row["retention_count"],
    )


def save_backup_config(config: BackupConfig) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        stmt = sqlite_insert(backup_config_table).values(
            id=1, enabled=config.enabled, frequency=config.frequency, time=config.time,
            day_of_week=config.dayOfWeek, day_of_month=config.dayOfMonth, retention_count=config.retentionCount,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[backup_config_table.c.id],
            set_={
                "enabled": stmt.excluded.enabled, "frequency": stmt.excluded.frequency, "time": stmt.excluded.time,
                "day_of_week": stmt.excluded.day_of_week, "day_of_month": stmt.excluded.day_of_month,
                "retention_count": stmt.excluded.retention_count,
            },
        )
        conn.execute(stmt)


def load_backup_state() -> BackupState:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(select(backup_state_table).where(backup_state_table.c.id == 1)).mappings().first()
    if row is None:
        return BackupState()
    return BackupState(lastRunDate=row["last_run_date"])


def save_backup_state(state: BackupState) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        stmt = sqlite_insert(backup_state_table).values(id=1, last_run_date=state.lastRunDate)
        stmt = stmt.on_conflict_do_update(
            index_elements=[backup_state_table.c.id], set_={"last_run_date": stmt.excluded.last_run_date},
        )
        conn.execute(stmt)


def list_backups() -> list[BackupEntry]:
    backups_dir = _backups_dir()
    if not backups_dir.exists():
        return []
    entries: list[BackupEntry] = []
    for path in backups_dir.glob("myhome-backup-*.zip"):
        dt = _parse_backup_filename(path.name)
        if dt is None:
            continue
        entries.append(BackupEntry(filename=path.name, createdAt=dt.isoformat(), sizeBytes=path.stat().st_size))
    entries.sort(key=lambda e: e.filename, reverse=True)
    return entries


def _prune_backups(retention_count: int) -> None:
    for entry in list_backups()[retention_count:]:
        (_backups_dir() / entry.filename).unlink(missing_ok=True)


def create_backup() -> BackupEntry:
    data_dir = _data_dir()
    backups_dir = _backups_dir()
    backups_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"myhome-backup-{timestamp}.zip"
    path = backups_dir / filename
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path, rel in iter_backup_files(data_dir, exclude_dirs=frozenset({"backups"})):
            zf.write(file_path, rel)
    entry = BackupEntry(
        filename=filename,
        createdAt=datetime.now(timezone.utc).isoformat(),
        sizeBytes=path.stat().st_size,
    )
    config = load_backup_config()
    _prune_backups(config.retentionCount)
    return entry


def get_backup_path(filename: str) -> Path | None:
    if not _FILENAME_RE.fullmatch(filename):
        return None
    # Lexical normalize-then-verify-containment, same shape used for home_id
    # elsewhere -- CodeQL's py/path-injection taint tracker doesn't credit
    # the anchored regex check above as sanitizing the value used here.
    backups_root = os.path.normpath(str(_backups_dir()))
    candidate = os.path.normpath(os.path.join(backups_root, filename))
    if not candidate.startswith(backups_root + os.sep):
        return None
    path = Path(candidate)
    if not path.exists():
        return None
    return path


def delete_backup(filename: str) -> bool:
    path = get_backup_path(filename)
    if path is None:
        return False
    path.unlink()
    return True

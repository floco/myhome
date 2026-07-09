import json
import os
import re
import zipfile
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from .models_backup import BackupConfig, BackupEntry, BackupState

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


def _config_file() -> Path:
    return _data_dir() / "backup_config.json"


def _state_file() -> Path:
    return _data_dir() / "backup_state.json"


def load_backup_config() -> BackupConfig:
    path = _config_file()
    if not path.exists():
        return BackupConfig()
    with path.open() as f:
        return BackupConfig.model_validate(json.load(f))


def save_backup_config(config: BackupConfig) -> None:
    path = _config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(config.model_dump(), f, indent=2)
    tmp.replace(path)


def load_backup_state() -> BackupState:
    path = _state_file()
    if not path.exists():
        return BackupState()
    with path.open() as f:
        return BackupState.model_validate(json.load(f))


def save_backup_state(state: BackupState) -> None:
    path = _state_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(state.model_dump(), f, indent=2)
    tmp.replace(path)


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

import json
import os
from pathlib import Path

from .models_backup import BackupConfig, BackupState


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data"))


def _backups_dir() -> Path:
    return _data_dir() / "backups"


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

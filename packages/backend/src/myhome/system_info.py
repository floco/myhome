# packages/backend/src/myhome/system_info.py
from __future__ import annotations

import os
import platform
from datetime import datetime, timezone
from pathlib import Path

from .migrations import CURRENT_VERSION as DB_SCHEMA_VERSION
from .persistence_homes import load_homes

_START_TIME = datetime.now(timezone.utc)


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data"))


def _db_path() -> Path:
    return _data_dir() / "myhome.db"


def get_app_version() -> str:
    version_file = Path(os.environ.get("APP_VERSION_FILE", "/app/VERSION"))
    if not version_file.exists():
        return "unknown"
    return version_file.read_text().strip()


def get_deployment_mode() -> str:
    return "home_assistant" if os.environ.get("SUPERVISOR_TOKEN") else "standalone"


def get_uptime_seconds() -> int:
    return int((datetime.now(timezone.utc) - _START_TIME).total_seconds())


def get_home_count() -> int:
    return len(load_homes().homes)


def get_database_size_bytes() -> int:
    db_path = _db_path()
    if not db_path.exists():
        return 0
    return db_path.stat().st_size


def get_static_system_info() -> dict:
    return {
        "version": get_app_version(),
        "deploymentMode": get_deployment_mode(),
        "pythonVersion": platform.python_version(),
        "arch": platform.machine(),
        "dbSchemaVersion": DB_SCHEMA_VERSION,
        "homeCount": get_home_count(),
        "databaseSizeBytes": get_database_size_bytes(),
        "uptimeSeconds": get_uptime_seconds(),
    }

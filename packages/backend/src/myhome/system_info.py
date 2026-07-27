# packages/backend/src/myhome/system_info.py
from __future__ import annotations

import os
import platform
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx

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
        return "dev"
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


_GITHUB_TAGS_URL = "https://api.github.com/repos/floco/myhome/tags"
_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
_UPDATE_CACHE_TTL_SECONDS = 3600

_update_cache: dict[str, object] = {"status": "unknown", "latestVersion": None, "checkedAt": None}


def reset_update_cache() -> None:
    """Test helper -- clears the module-level update-check cache."""
    _update_cache.update({"status": "unknown", "latestVersion": None, "checkedAt": None})


def _version_tuple(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


async def _fetch_latest_tag_version() -> str | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(_GITHUB_TAGS_URL, headers={"User-Agent": "myhome-app"}, timeout=5.0)
        resp.raise_for_status()
        tags = resp.json()
    versions: list[tuple[int, int, int]] = []
    for tag in tags:
        match = _TAG_RE.match(tag.get("name", ""))
        if match:
            versions.append(tuple(int(g) for g in match.groups()))
    if not versions:
        return None
    latest = max(versions)
    return ".".join(str(part) for part in latest)


async def check_for_update(current_version: str) -> dict:
    now = datetime.now(timezone.utc)
    checked_at = _update_cache["checkedAt"]
    if checked_at is not None:
        age = (now - datetime.fromisoformat(checked_at)).total_seconds()
        if age < _UPDATE_CACHE_TTL_SECONDS:
            return dict(_update_cache)

    try:
        latest = await _fetch_latest_tag_version()
    except httpx.HTTPError:
        if checked_at is not None:
            return dict(_update_cache)
        return {"status": "unknown", "latestVersion": None, "checkedAt": None}

    if latest is None:
        status = "unknown"
    else:
        try:
            status = "update_available" if _version_tuple(latest) > _version_tuple(current_version) else "up_to_date"
        except ValueError:
            status = "unknown"

    _update_cache.update({
        "status": status,
        "latestVersion": latest,
        "checkedAt": now.isoformat(),
    })
    return dict(_update_cache)

# packages/backend/src/myhome/persistence_homes.py
from __future__ import annotations

import json
import os
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .ids import InvalidIdError
from .models_homes import (
    Home,
    HomesDocument,
    DEFAULT_EXISTING_MODULES,
    DEFAULT_PROJECT_MODULES,
    DEFAULT_DEMO_MODULES,
)

_LEGACY_FILES = [
    "house.json", "chores.json", "costs.json", "inventory.json",
    "works.json", "kb.json", "consumables.json", "settings.json",
]
_LEGACY_ATTACHMENT_DIRS = [
    "chores-attachments", "costs-attachments", "inventory-attachments",
    "works-attachments", "kb-attachments",
]


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data"))


def _homes_file() -> Path:
    return _data_dir() / "homes.json"


def _home_dir(home_id: str) -> Path:
    # Normalize lexically (no filesystem access -- Path.resolve() follows
    # symlinks and touches disk, which CodeQL's own path-injection sink set
    # flags even before any check runs) then verify containment within
    # homes_root. This is CodeQL's own recommended py/path-injection
    # sanitizer shape: os.path.normpath + startswith against a safe root.
    homes_root = os.path.normpath(os.path.join(str(_data_dir()), "homes"))
    candidate = os.path.normpath(os.path.join(homes_root, home_id))
    if not candidate.startswith(homes_root + os.sep):
        raise InvalidIdError(f"Invalid home_id: {home_id!r}")
    return Path(candidate)


def load_homes() -> HomesDocument:
    path = _homes_file()
    if not path.exists():
        return HomesDocument()
    with path.open() as f:
        return HomesDocument.model_validate(json.load(f))


def save_homes(doc: HomesDocument) -> None:
    path = _homes_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def create_home(name: str, home_type: str) -> Home:
    if home_type == "existing":
        modules = DEFAULT_EXISTING_MODULES[:]
    elif home_type == "demo":
        modules = DEFAULT_DEMO_MODULES[:]
    else:
        modules = DEFAULT_PROJECT_MODULES[:]
    home = Home(
        id=secrets.token_hex(8),
        name=name,
        type=home_type,
        enabledModules=modules,
        createdAt=datetime.now(timezone.utc).isoformat(),
    )
    _home_dir(home.id).mkdir(parents=True, exist_ok=True)
    doc = load_homes()
    doc.homes.append(home)
    save_homes(doc)
    return home


def patch_home(
    home_id: str,
    name: str | None,
    home_type: str | None,
    enabled_modules: list[str] | None,
) -> Home | None:
    doc = load_homes()
    home = next((h for h in doc.homes if h.id == home_id), None)
    if home is None:
        return None
    if name is not None:
        home.name = name
    if home_type is not None:
        home.type = home_type
    if enabled_modules is not None:
        home.enabledModules = enabled_modules
    save_homes(doc)
    return home


def delete_home(home_id: str) -> bool:
    doc = load_homes()
    before = len(doc.homes)
    doc.homes = [h for h in doc.homes if h.id != home_id]
    if len(doc.homes) == before:
        return False
    save_homes(doc)
    home_dir = _home_dir(home_id)
    if home_dir.exists():
        shutil.rmtree(home_dir)
    return True


def migrate_legacy_if_needed() -> None:
    data_dir = _data_dir()
    if _homes_file().exists():
        return
    has_legacy = any((data_dir / f).exists() for f in _LEGACY_FILES)
    if not has_legacy:
        return
    default_id = "default"
    home_dir = _home_dir(default_id)
    home_dir.mkdir(parents=True, exist_ok=True)
    for fname in _LEGACY_FILES:
        src = data_dir / fname
        if src.exists():
            shutil.move(str(src), str(home_dir / fname))
    for dir_name in _LEGACY_ATTACHMENT_DIRS:
        src = data_dir / dir_name
        if src.exists():
            shutil.move(str(src), str(home_dir / dir_name))
    home = Home(
        id=default_id,
        name="My Home",
        type="existing",
        enabledModules=DEFAULT_EXISTING_MODULES[:],
        createdAt=datetime.now(timezone.utc).isoformat(),
    )
    save_homes(HomesDocument(homes=[home]))

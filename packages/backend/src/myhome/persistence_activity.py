import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .ids import InvalidIdError
from .models_activity import ActivityEntry, ActivityLogDocument

RETENTION_DAYS = 90

ACTION_VERBS = {"create": "added", "update": "updated", "delete": "deleted", "complete": "completed"}
MODULE_NOUNS = {
    "chores": "chore", "works": "work", "costs": "cost entry",
    "inventory": "inventory item", "consumables": "consumable", "kb": "KB article",
}


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data"))


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


def _activity_file(home_id: str) -> Path:
    return _home_dir(home_id) / "activity_log.json"


def load_activity_log(home_id: str) -> ActivityLogDocument:
    path = _activity_file(home_id)
    if not path.exists():
        return ActivityLogDocument()
    with path.open() as f:
        return ActivityLogDocument.model_validate(json.load(f))


def save_activity_log(home_id: str, doc: ActivityLogDocument) -> None:
    path = _activity_file(home_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def _resolve_username(user_id: str) -> str:
    from .persistence_auth import load_users
    user = next((u for u in load_users().users if u.id == user_id), None)
    return user.username if user else "unknown"


def log_activity(
    home_id: str, user_id: str, module: str, action: str,
    entity_label: str, ref_id: str | None = None,
) -> None:
    doc = load_activity_log(home_id)
    doc.entries.append(ActivityEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        userId=user_id,
        username=_resolve_username(user_id),
        module=module,
        action=action,
        entityLabel=entity_label,
        refId=ref_id,
    ))
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    doc.entries = [e for e in doc.entries if datetime.fromisoformat(e.timestamp) >= cutoff]
    save_activity_log(home_id, doc)


def describe(entry: ActivityEntry) -> str:
    return f"{ACTION_VERBS[entry.action]} {MODULE_NOUNS[entry.module]} '{entry.entityLabel}'"

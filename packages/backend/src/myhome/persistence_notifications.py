import json
import os
from pathlib import Path

from .ids import InvalidIdError
from .models_notifications import NotificationState


def _home_dir(home_id: str) -> Path:
    # Normalize lexically (no filesystem access -- Path.resolve() follows
    # symlinks and touches disk, which CodeQL's own path-injection sink set
    # flags even before any check runs) then verify containment within
    # homes_root. This is CodeQL's own recommended py/path-injection
    # sanitizer shape: os.path.normpath + startswith against a safe root.
    homes_root = os.path.normpath(os.path.join(os.environ.get("DATA_DIR", "/data"), "homes"))
    candidate = os.path.normpath(os.path.join(homes_root, home_id))
    if not candidate.startswith(homes_root + os.sep):
        raise InvalidIdError(f"Invalid home_id: {home_id!r}")
    return Path(candidate)


def _state_file(home_id: str) -> Path:
    return _home_dir(home_id) / "notifications_state.json"


def load_notification_state(home_id: str) -> NotificationState:
    path = _state_file(home_id)
    if not path.exists():
        return NotificationState()
    with path.open() as f:
        return NotificationState.model_validate(json.load(f))


def save_notification_state(home_id: str, state: NotificationState) -> None:
    path = _state_file(home_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(state.model_dump(), f, indent=2)
    tmp.replace(path)

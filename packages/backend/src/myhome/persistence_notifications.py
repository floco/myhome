import json
import os
from pathlib import Path

from .models_notifications import NotificationState


def _home_dir(home_id: str) -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "homes" / home_id


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

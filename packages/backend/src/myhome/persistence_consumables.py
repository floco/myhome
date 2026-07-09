import json
import os
from pathlib import Path

from .ids import validate_safe_id
from .models_consumables import ConsumableDocument


def _home_dir(home_id: str) -> Path:
    validate_safe_id(home_id, label="home_id")
    return Path(os.environ.get("DATA_DIR", "/data")) / "homes" / home_id


def _consumables_file(home_id: str) -> Path:
    return _home_dir(home_id) / "consumables.json"


def load_consumables(home_id: str) -> ConsumableDocument:
    path = _consumables_file(home_id)
    if not path.exists():
        return ConsumableDocument()
    with path.open() as f:
        return ConsumableDocument.model_validate(json.load(f))


def save_consumables(home_id: str, doc: ConsumableDocument) -> None:
    path = _consumables_file(home_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)

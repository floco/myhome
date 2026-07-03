import json
import os
from pathlib import Path

from .models import HouseDocument


def _home_dir(home_id: str) -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "homes" / home_id


def _house_file(home_id: str) -> Path:
    return _home_dir(home_id) / "house.json"


def load_house(home_id: str) -> HouseDocument | None:
    path = _house_file(home_id)
    if not path.exists():
        return None
    with path.open() as f:
        return HouseDocument.model_validate(json.load(f))


def save_house(home_id: str, doc: HouseDocument) -> None:
    path = _house_file(home_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)

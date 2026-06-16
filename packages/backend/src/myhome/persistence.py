import json
import os
from pathlib import Path

from .models import HouseDocument


def _house_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "house.json"


def load_house() -> HouseDocument | None:
    path = _house_file()
    if not path.exists():
        return None
    with path.open() as f:
        return HouseDocument.model_validate(json.load(f))


def save_house(doc: HouseDocument) -> None:
    path = _house_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)

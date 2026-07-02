import json
import os
from pathlib import Path

from .models_consumables import ConsumableDocument


def _consumables_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "consumables.json"


def load_consumables() -> ConsumableDocument:
    path = _consumables_file()
    if not path.exists():
        return ConsumableDocument()
    with path.open() as f:
        return ConsumableDocument.model_validate(json.load(f))


def save_consumables(doc: ConsumableDocument) -> None:
    path = _consumables_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)

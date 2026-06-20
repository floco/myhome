import json
import os
from pathlib import Path

from .models_inventory import InventoryDocument


def _inventory_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "inventory.json"


def load_inventory() -> InventoryDocument:
    path = _inventory_file()
    if not path.exists():
        return InventoryDocument()
    with path.open() as f:
        return InventoryDocument.model_validate(json.load(f))


def save_inventory(doc: InventoryDocument) -> None:
    path = _inventory_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)

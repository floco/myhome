import json
import os
import shutil
from pathlib import Path

from .models_inventory import InventoryDocument


def _inventory_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "inventory.json"


def _attachments_dir(item_id: str) -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "inventory-attachments" / item_id


def get_attachment_path(item_id: str, filename: str) -> Path:
    return _attachments_dir(item_id) / filename


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


def save_attachment(item_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(item_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)


def delete_attachment(item_id: str, filename: str) -> bool:
    path = _attachments_dir(item_id) / filename
    if not path.exists():
        return False
    path.unlink()
    return True


def delete_all_attachments(item_id: str) -> None:
    path = _attachments_dir(item_id)
    if path.exists():
        shutil.rmtree(path)

import json
import logging
import os
import shutil
from pathlib import Path

from .ids import validate_safe_id
from .models_inventory import InventoryDocument

_log = logging.getLogger(__name__)


def _home_dir(home_id: str) -> Path:
    validate_safe_id(home_id, label="home_id")
    return Path(os.environ.get("DATA_DIR", "/data")) / "homes" / home_id


def _inventory_file(home_id: str) -> Path:
    return _home_dir(home_id) / "inventory.json"


def _attachments_dir(home_id: str, item_id: str) -> Path:
    return _home_dir(home_id) / "inventory-attachments" / item_id


def get_attachment_path(home_id: str, item_id: str, filename: str) -> Path:
    return _attachments_dir(home_id, item_id) / filename


def load_inventory(home_id: str) -> InventoryDocument:
    path = _inventory_file(home_id)
    if not path.exists():
        return InventoryDocument()
    with path.open() as f:
        return InventoryDocument.model_validate(json.load(f))


def save_inventory(home_id: str, doc: InventoryDocument) -> None:
    path = _inventory_file(home_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def save_attachment(home_id: str, item_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, item_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)


def delete_attachment(home_id: str, item_id: str, filename: str) -> bool:
    path = _attachments_dir(home_id, item_id) / filename
    if not path.exists():
        return False
    path.unlink()
    thumb = path.parent / (filename + ".thumb.jpg")
    if thumb.exists():
        thumb.unlink()
    return True


def delete_all_attachments(home_id: str, item_id: str) -> None:
    path = _attachments_dir(home_id, item_id)
    if path.exists():
        shutil.rmtree(path)


def generate_pdf_thumbnail(pdf_path: Path, thumb_path: Path) -> None:
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        pix.save(str(thumb_path))
    except Exception as exc:
        _log.warning("PDF thumbnail generation failed for %s: %s", pdf_path, exc)

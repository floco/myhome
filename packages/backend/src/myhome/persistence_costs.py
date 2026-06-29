import json
import logging
import os
import shutil
from pathlib import Path

from .models_costs import CostsDocument

_log = logging.getLogger(__name__)


def _costs_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "costs.json"


def _attachments_dir(entry_id: str) -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "costs-attachments" / entry_id


def load_costs() -> CostsDocument:
    path = _costs_file()
    if not path.exists():
        return CostsDocument()
    with path.open() as f:
        raw = json.load(f)
    # Migration: entries saved before 2026-06-21 used "supplier" (freeform string).
    # Pydantic v2 ignores unknown fields, so old entries load with supplierId=None automatically.
    return CostsDocument.model_validate(raw)


def save_costs(doc: CostsDocument) -> None:
    path = _costs_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def save_attachment(entry_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(entry_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)


def delete_attachment(entry_id: str, filename: str) -> bool:
    path = _attachments_dir(entry_id) / filename
    if not path.exists():
        return False
    path.unlink()
    thumb = path.parent / (filename + ".thumb.jpg")
    if thumb.exists():
        thumb.unlink()
    return True


def delete_all_attachments(entry_id: str) -> None:
    path = _attachments_dir(entry_id)
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

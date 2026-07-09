import json
import logging
import os
import shutil
from pathlib import Path

from .ids import InvalidIdError
from .models_costs import CostsDocument

_log = logging.getLogger(__name__)


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


def _costs_file(home_id: str) -> Path:
    return _home_dir(home_id) / "costs.json"


def _attachments_dir(home_id: str, entry_id: str) -> Path:
    return _home_dir(home_id) / "costs-attachments" / entry_id


def load_costs(home_id: str) -> CostsDocument:
    path = _costs_file(home_id)
    if not path.exists():
        return CostsDocument()
    with path.open() as f:
        raw = json.load(f)
    # Migration: entries saved before 2026-06-21 used "supplier" (freeform string).
    # Pydantic v2 ignores unknown fields, so old entries load with supplierId=None automatically.
    return CostsDocument.model_validate(raw)


def save_costs(home_id: str, doc: CostsDocument) -> None:
    path = _costs_file(home_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def save_attachment(home_id: str, entry_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, entry_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)


def delete_attachment(home_id: str, entry_id: str, filename: str) -> bool:
    path = _attachments_dir(home_id, entry_id) / filename
    if not path.exists():
        return False
    path.unlink()
    thumb = path.parent / (filename + ".thumb.jpg")
    if thumb.exists():
        thumb.unlink()
    return True


def delete_all_attachments(home_id: str, entry_id: str) -> None:
    path = _attachments_dir(home_id, entry_id)
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

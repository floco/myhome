import json
import logging
import os
import shutil
from pathlib import Path

from .ids import InvalidIdError
from .models_works import WorksDocument

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


def _works_file(home_id: str) -> Path:
    return _home_dir(home_id) / "works.json"


def _attachments_dir(home_id: str, work_id: str) -> Path:
    return _home_dir(home_id) / "works-attachments" / work_id


def load_works(home_id: str) -> WorksDocument:
    path = _works_file(home_id)
    if not path.exists():
        return WorksDocument()
    with path.open() as f:
        return WorksDocument.model_validate(json.load(f))


def save_works(home_id: str, doc: WorksDocument) -> None:
    path = _works_file(home_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def get_attachment_path(home_id: str, work_id: str, filename: str) -> Path:
    return _attachments_dir(home_id, work_id) / filename


def save_attachment(home_id: str, work_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, work_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)


def delete_attachment(home_id: str, work_id: str, filename: str) -> bool:
    path = _attachments_dir(home_id, work_id) / filename
    if not path.exists():
        return False
    path.unlink()
    thumb = path.parent / (filename + ".thumb.jpg")
    if thumb.exists():
        thumb.unlink()
    return True


def delete_all_attachments(home_id: str, work_id: str) -> None:
    path = _attachments_dir(home_id, work_id)
    if path.exists():
        shutil.rmtree(path)


def generate_pdf_thumbnail(pdf_path: Path, thumb_path: Path) -> None:
    try:
        import fitz  # pymupdf
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        pix.save(str(thumb_path))
    except Exception as exc:
        _log.warning("PDF thumbnail generation failed for %s: %s", pdf_path, exc)

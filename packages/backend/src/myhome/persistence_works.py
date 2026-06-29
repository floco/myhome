import json
import logging
import os
import shutil
from pathlib import Path

from .models_works import WorksDocument

_log = logging.getLogger(__name__)


def _works_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "works.json"


def _attachments_dir(work_id: str) -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "works-attachments" / work_id


def load_works() -> WorksDocument:
    path = _works_file()
    if not path.exists():
        return WorksDocument()
    with path.open() as f:
        return WorksDocument.model_validate(json.load(f))


def save_works(doc: WorksDocument) -> None:
    path = _works_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def get_attachment_path(work_id: str, filename: str) -> Path:
    return _attachments_dir(work_id) / filename


def save_attachment(work_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(work_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)


def delete_attachment(work_id: str, filename: str) -> bool:
    path = _attachments_dir(work_id) / filename
    if not path.exists():
        return False
    path.unlink()
    thumb = path.parent / (filename + ".thumb.jpg")
    if thumb.exists():
        thumb.unlink()
    return True


def delete_all_attachments(work_id: str) -> None:
    path = _attachments_dir(work_id)
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

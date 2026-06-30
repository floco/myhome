import json
import logging
import os
import shutil
from pathlib import Path

from .models_chores import ChoreDocument

_log = logging.getLogger(__name__)


def _chores_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "chores.json"


def _attachments_dir(chore_id: str) -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "chores-attachments" / chore_id


def load_chores() -> ChoreDocument:
    path = _chores_file()
    if not path.exists():
        return ChoreDocument()
    with path.open() as f:
        doc = ChoreDocument.model_validate(json.load(f))
    # Migration 1: fill in missing assignment nextDueDates from parent chore
    chore_map = {c.id: c for c in doc.chores}
    for a in doc.assignments:
        if not a.nextDueDate:
            parent = chore_map.get(a.choreId)
            a.nextDueDate = parent.nextDueDate if parent else ""
    # Migration 2: fill in frequency fields for chores that only have periodDays
    for c in doc.chores:
        if c.frequencyType == "interval" and not c.frequencyMetadata:
            c.frequency = max(1, round(c.periodDays))
            c.frequencyMetadata = {"unit": "days"}
    return doc


def save_chores(doc: ChoreDocument) -> None:
    path = _chores_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def save_attachment(chore_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(chore_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)


def delete_attachment(chore_id: str, filename: str) -> bool:
    path = _attachments_dir(chore_id) / filename
    if not path.exists():
        return False
    path.unlink()
    thumb = path.parent / (filename + ".thumb.jpg")
    if thumb.exists():
        thumb.unlink()
    return True


def delete_all_attachments(chore_id: str) -> None:
    att_dir = _attachments_dir(chore_id)
    if att_dir.exists():
        shutil.rmtree(att_dir)


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

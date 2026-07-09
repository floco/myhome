import json
import logging
import os
import shutil
from pathlib import Path

from .ids import InvalidIdError
from .models_chores import ChoreDocument

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


def _chores_file(home_id: str) -> Path:
    return _home_dir(home_id) / "chores.json"


def _attachments_dir(home_id: str, chore_id: str) -> Path:
    return _home_dir(home_id) / "chores-attachments" / chore_id


def load_chores(home_id: str) -> ChoreDocument:
    path = _chores_file(home_id)
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


def save_chores(home_id: str, doc: ChoreDocument) -> None:
    path = _chores_file(home_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)


def save_attachment(home_id: str, chore_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, chore_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_bytes(data)


def delete_attachment(home_id: str, chore_id: str, filename: str) -> bool:
    path = _attachments_dir(home_id, chore_id) / filename
    if not path.exists():
        return False
    path.unlink()
    thumb = path.parent / (filename + ".thumb.jpg")
    if thumb.exists():
        thumb.unlink()
    return True


def delete_all_attachments(home_id: str, chore_id: str) -> None:
    att_dir = _attachments_dir(home_id, chore_id)
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

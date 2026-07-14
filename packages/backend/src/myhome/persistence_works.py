import json
import logging
import os
import shutil
from pathlib import Path

from sqlalchemy import select

from .db import get_engine
from .ids import InvalidIdError
from .models_works import Work, WorkPlacement, WorkPosition, WorksDocument
from .schema import works as works_table

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


def _attachments_dir(home_id: str, work_id: str) -> Path:
    # Same inline lexical-normalize-then-verify-containment shape as
    # _home_dir() above -- work_id is validated at the route layer too, but
    # CodeQL's taint tracker doesn't credit a separate validator function as
    # sanitizing the value used here.
    base = os.path.normpath(str(_home_dir(home_id) / "works-attachments"))
    candidate = os.path.normpath(os.path.join(base, work_id))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid work_id: {work_id!r}")
    return Path(candidate)


def load_works(home_id: str) -> WorksDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(works_table).where(works_table.c.home_id == home_id).order_by(works_table.c.order_index)
        ).mappings().all()
    return WorksDocument(works=[
        Work(
            id=r["id"], title=r["title"], description=r["description"], status=r["status"],
            categoryId=r["category_id"], date=r["date"], totalCost=r["total_cost"],
            supplierId=r["supplier_id"], notes=r["notes"], attachments=json.loads(r["attachments"]),
            placement=(
                WorkPlacement(floorId=r["placement_floor_id"], position=WorkPosition(x=r["placement_x"], y=r["placement_y"]))
                if r["placement_floor_id"] is not None else None
            ),
        )
        for r in rows
    ])


def save_works(home_id: str, doc: WorksDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(works_table.delete().where(works_table.c.home_id == home_id))
        if doc.works:
            conn.execute(works_table.insert(), [
                {
                    "id": w.id, "home_id": home_id, "order_index": i, "title": w.title,
                    "description": w.description, "status": w.status, "category_id": w.categoryId,
                    "date": w.date, "total_cost": w.totalCost, "supplier_id": w.supplierId,
                    "notes": w.notes, "attachments": json.dumps(w.attachments),
                    "placement_floor_id": w.placement.floorId if w.placement else None,
                    "placement_x": w.placement.position.x if w.placement else None,
                    "placement_y": w.placement.position.y if w.placement else None,
                }
                for i, w in enumerate(doc.works)
            ])


def get_attachment_path(home_id: str, work_id: str, filename: str) -> Path:
    base = os.path.normpath(str(_attachments_dir(home_id, work_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    return Path(candidate)


def save_attachment(home_id: str, work_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, work_id)
    base = os.path.normpath(str(path))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path.mkdir(parents=True, exist_ok=True)
    Path(candidate).write_bytes(data)


def delete_attachment(home_id: str, work_id: str, filename: str) -> bool:
    base = os.path.normpath(str(_attachments_dir(home_id, work_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path = Path(candidate)
    if not path.exists():
        return False
    path.unlink()
    thumb = path.with_name(path.name + ".thumb.jpg")
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

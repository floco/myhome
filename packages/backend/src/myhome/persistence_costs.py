import json
import logging
import os
import shutil
from pathlib import Path

from sqlalchemy import select

from .db import get_engine
from .ids import InvalidIdError
from .models_costs import CostEntry, CostsDocument
from .schema import cost_entries as cost_entries_table

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


def _attachments_dir(home_id: str, entry_id: str) -> Path:
    # Same inline lexical-normalize-then-verify-containment shape as
    # _home_dir() above -- entry_id is validated at the route layer too, but
    # CodeQL's taint tracker doesn't credit a separate validator function as
    # sanitizing the value used here.
    base = os.path.normpath(str(_home_dir(home_id) / "costs-attachments"))
    candidate = os.path.normpath(os.path.join(base, entry_id))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid entry_id: {entry_id!r}")
    return Path(candidate)


def load_costs(home_id: str) -> CostsDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(cost_entries_table).where(cost_entries_table.c.home_id == home_id)
            .order_by(cost_entries_table.c.order_index)
        ).mappings().all()
    return CostsDocument(entries=[
        CostEntry(
            id=r["id"], categoryId=r["category_id"], date=r["date"], totalAmount=r["total_amount"],
            quantity=r["quantity"], unitPrice=r["unit_price"], supplierId=r["supplier_id"],
            notes=r["notes"], roomId=r["room_id"], attachments=json.loads(r["attachments"]),
        )
        for r in rows
    ])


def save_costs(home_id: str, doc: CostsDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(cost_entries_table.delete().where(cost_entries_table.c.home_id == home_id))
        if doc.entries:
            conn.execute(cost_entries_table.insert(), [
                {
                    "id": e.id, "home_id": home_id, "order_index": i, "category_id": e.categoryId,
                    "date": e.date, "total_amount": e.totalAmount, "quantity": e.quantity,
                    "unit_price": e.unitPrice, "supplier_id": e.supplierId, "notes": e.notes,
                    "room_id": e.roomId, "attachments": json.dumps(e.attachments),
                }
                for i, e in enumerate(doc.entries)
            ])


def get_attachment_path(home_id: str, entry_id: str, filename: str) -> Path:
    base = os.path.normpath(str(_attachments_dir(home_id, entry_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    return Path(candidate)


def save_attachment(home_id: str, entry_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, entry_id)
    base = os.path.normpath(str(path))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path.mkdir(parents=True, exist_ok=True)
    Path(candidate).write_bytes(data)


def delete_attachment(home_id: str, entry_id: str, filename: str) -> bool:
    base = os.path.normpath(str(_attachments_dir(home_id, entry_id)))
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

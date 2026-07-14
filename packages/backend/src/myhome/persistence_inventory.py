import json
import logging
import os
import shutil
from pathlib import Path

from sqlalchemy import select

from .db import get_engine
from .ids import InvalidIdError
from .models_inventory import InventoryDocument, InventoryItem, InventoryPlacement, InventoryPosition
from .schema import inventory_items as inventory_items_table

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


def _attachments_dir(home_id: str, item_id: str) -> Path:
    # Same inline lexical-normalize-then-verify-containment shape as
    # _home_dir() above -- item_id is validated at the route layer too, but
    # CodeQL's taint tracker doesn't credit a separate validator function as
    # sanitizing the value used here.
    base = os.path.normpath(str(_home_dir(home_id) / "inventory-attachments"))
    candidate = os.path.normpath(os.path.join(base, item_id))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid item_id: {item_id!r}")
    return Path(candidate)


def get_attachment_path(home_id: str, item_id: str, filename: str) -> Path:
    base = os.path.normpath(str(_attachments_dir(home_id, item_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    return Path(candidate)


def load_inventory(home_id: str) -> InventoryDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(inventory_items_table).where(inventory_items_table.c.home_id == home_id)
            .order_by(inventory_items_table.c.order_index)
        ).mappings().all()
    return InventoryDocument(items=[
        InventoryItem(
            id=r["id"], name=r["name"], emoji=r["emoji"], category=r["category"], brand=r["brand"],
            model=r["model"], serialNumber=r["serial_number"], purchaseDate=r["purchase_date"],
            purchasePrice=r["purchase_price"], warrantyExpiryDate=r["warranty_expiry_date"],
            notes=r["notes"], attachments=json.loads(r["attachments"]),
            placement=(
                InventoryPlacement(
                    floorId=r["placement_floor_id"], roomId=r["placement_room_id"],
                    position=InventoryPosition(x=r["placement_x"], y=r["placement_y"]),
                )
                if r["placement_floor_id"] is not None else None
            ),
        )
        for r in rows
    ])


def save_inventory(home_id: str, doc: InventoryDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(inventory_items_table.delete().where(inventory_items_table.c.home_id == home_id))
        if doc.items:
            conn.execute(inventory_items_table.insert(), [
                {
                    "id": it.id, "home_id": home_id, "order_index": i, "name": it.name, "emoji": it.emoji,
                    "category": it.category, "brand": it.brand, "model": it.model,
                    "serial_number": it.serialNumber, "purchase_date": it.purchaseDate,
                    "purchase_price": it.purchasePrice, "warranty_expiry_date": it.warrantyExpiryDate,
                    "notes": it.notes, "attachments": json.dumps(it.attachments),
                    "placement_floor_id": it.placement.floorId if it.placement else None,
                    "placement_room_id": it.placement.roomId if it.placement else None,
                    "placement_x": it.placement.position.x if it.placement else None,
                    "placement_y": it.placement.position.y if it.placement else None,
                }
                for i, it in enumerate(doc.items)
            ])


def save_attachment(home_id: str, item_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, item_id)
    base = os.path.normpath(str(path))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path.mkdir(parents=True, exist_ok=True)
    Path(candidate).write_bytes(data)


def delete_attachment(home_id: str, item_id: str, filename: str) -> bool:
    base = os.path.normpath(str(_attachments_dir(home_id, item_id)))
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

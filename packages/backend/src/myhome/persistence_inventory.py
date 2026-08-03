import json
from pathlib import Path

from sqlalchemy import select

from . import attachment_storage
from .attachment_storage import generate_pdf_thumbnail
from .db import get_engine
from .models_inventory import InventoryDocument, InventoryItem, InventoryPlacement, InventoryPosition
from .schema import inventory_items as inventory_items_table

_MODULE = "inventory"


def get_attachment_path(home_id: str, item_id: str, filename: str) -> Path:
    return attachment_storage.get_attachment_path(home_id, _MODULE, item_id, filename)


def load_inventory(home_id: str) -> InventoryDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(inventory_items_table).where(inventory_items_table.c.home_id == home_id)
            .order_by(inventory_items_table.c.order_index)
        ).mappings().all()
    return InventoryDocument(items=[
        InventoryItem(
            id=r["id"], name=r["name"], emoji=r["emoji"], categoryId=r["category_id"],
            ownerId=r["owner_id"], storeId=r["store_id"], brand=r["brand"],
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
                    "category_id": it.categoryId, "owner_id": it.ownerId, "store_id": it.storeId,
                    "brand": it.brand, "model": it.model,
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
    attachment_storage.save_attachment(home_id, _MODULE, item_id, filename, data)


def delete_attachment(home_id: str, item_id: str, filename: str) -> bool:
    return attachment_storage.delete_attachment(home_id, _MODULE, item_id, filename)


def delete_all_attachments(home_id: str, item_id: str) -> None:
    attachment_storage.delete_all_attachments(home_id, _MODULE, item_id)


def reset_inventory(home_id: str) -> None:
    save_inventory(home_id, InventoryDocument())
    attachment_storage.delete_all_module_attachments(home_id, _MODULE)

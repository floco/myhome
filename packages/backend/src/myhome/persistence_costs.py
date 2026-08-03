import json
from pathlib import Path

from sqlalchemy import select

from . import attachment_storage
from .attachment_storage import generate_pdf_thumbnail
from .db import get_engine
from .models_costs import CostEntry, CostsDocument
from .schema import cost_entries as cost_entries_table

_MODULE = "costs"


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
            quantity=r["quantity"], unitPrice=r["unit_price"], contactId=r["contact_id"],
            notes=r["notes"], roomId=r["room_id"], attachments=json.loads(r["attachments"]),
            sourceModule=r["source_module"], sourceId=r["source_id"],
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
                    "unit_price": e.unitPrice, "contact_id": e.contactId, "notes": e.notes,
                    "room_id": e.roomId, "attachments": json.dumps(e.attachments),
                    "source_module": e.sourceModule, "source_id": e.sourceId,
                }
                for i, e in enumerate(doc.entries)
            ])


def get_attachment_path(home_id: str, entry_id: str, filename: str) -> Path:
    return attachment_storage.get_attachment_path(home_id, _MODULE, entry_id, filename)


def save_attachment(home_id: str, entry_id: str, filename: str, data: bytes) -> None:
    attachment_storage.save_attachment(home_id, _MODULE, entry_id, filename, data)


def delete_attachment(home_id: str, entry_id: str, filename: str) -> bool:
    return attachment_storage.delete_attachment(home_id, _MODULE, entry_id, filename)


def delete_all_attachments(home_id: str, entry_id: str) -> None:
    attachment_storage.delete_all_attachments(home_id, _MODULE, entry_id)


def reset_costs(home_id: str) -> None:
    save_costs(home_id, CostsDocument())
    attachment_storage.delete_all_module_attachments(home_id, _MODULE)

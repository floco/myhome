import json
from pathlib import Path

from sqlalchemy import select

from . import attachment_storage
from .attachment_storage import generate_pdf_thumbnail
from .db import get_engine
from .models_works import Work, WorkPlacement, WorkPosition, WorksDocument
from .schema import works as works_table

_MODULE = "works"


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
            contactId=r["contact_id"], notes=r["notes"], attachments=json.loads(r["attachments"]),
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
                    "date": w.date, "total_cost": w.totalCost, "contact_id": w.contactId,
                    "notes": w.notes, "attachments": json.dumps(w.attachments),
                    "placement_floor_id": w.placement.floorId if w.placement else None,
                    "placement_x": w.placement.position.x if w.placement else None,
                    "placement_y": w.placement.position.y if w.placement else None,
                }
                for i, w in enumerate(doc.works)
            ])


def get_attachment_path(home_id: str, work_id: str, filename: str) -> Path:
    return attachment_storage.get_attachment_path(home_id, _MODULE, work_id, filename)


def save_attachment(home_id: str, work_id: str, filename: str, data: bytes) -> None:
    attachment_storage.save_attachment(home_id, _MODULE, work_id, filename, data)


def delete_attachment(home_id: str, work_id: str, filename: str) -> bool:
    return attachment_storage.delete_attachment(home_id, _MODULE, work_id, filename)


def delete_all_attachments(home_id: str, work_id: str) -> None:
    attachment_storage.delete_all_attachments(home_id, _MODULE, work_id)


def reset_works(home_id: str) -> None:
    save_works(home_id, WorksDocument())
    attachment_storage.delete_all_module_attachments(home_id, _MODULE)

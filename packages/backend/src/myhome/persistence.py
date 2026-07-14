import json

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import get_engine
from .models import HouseDocument
from .schema import house_documents as house_documents_table


def load_house(home_id: str) -> HouseDocument | None:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            select(house_documents_table.c.doc).where(house_documents_table.c.home_id == home_id)
        ).first()
    if row is None:
        return None
    return HouseDocument.model_validate(json.loads(row[0]))


def save_house(home_id: str, doc: HouseDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        stmt = sqlite_insert(house_documents_table).values(home_id=home_id, doc=json.dumps(doc.model_dump()))
        stmt = stmt.on_conflict_do_update(
            index_elements=[house_documents_table.c.home_id], set_={"doc": stmt.excluded.doc},
        )
        conn.execute(stmt)

# packages/backend/src/myhome/persistence_properties.py
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from . import attachment_storage
from .attachment_storage import generate_pdf_thumbnail
from .db import get_engine
from .models_properties import Property, PropertiesDocument
from .schema import properties as properties_table

_MODULE = "properties"


def load_properties(home_id: str) -> PropertiesDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(properties_table).where(properties_table.c.home_id == home_id)
            .order_by(properties_table.c.order_index)
        ).mappings().all()
    return PropertiesDocument(properties=[
        Property(
            id=r["id"], name=r["name"], emoji=r["emoji"], type=r["type"], status=r["status"],
            locationId=r["location_id"], address=r["address"], price=r["price"],
            landSize=r["land_size"], builtSize=r["built_size"], bedrooms=r["bedrooms"], bathrooms=r["bathrooms"],
            listingUrl=r["listing_url"], contact=r["contact"], pros=json.loads(r["pros"]), cons=json.loads(r["cons"]),
            notes=r["notes"], attachments=json.loads(r["attachments"]),
        )
        for r in rows
    ])


def save_properties(home_id: str, doc: PropertiesDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(properties_table.delete().where(properties_table.c.home_id == home_id))
        if doc.properties:
            conn.execute(properties_table.insert(), [
                {
                    "id": p.id, "home_id": home_id, "order_index": i, "name": p.name, "emoji": p.emoji,
                    "type": p.type, "status": p.status, "location_id": p.locationId, "address": p.address,
                    "price": p.price, "land_size": p.landSize, "built_size": p.builtSize,
                    "bedrooms": p.bedrooms, "bathrooms": p.bathrooms, "listing_url": p.listingUrl,
                    "contact": p.contact, "pros": json.dumps(p.pros), "cons": json.dumps(p.cons),
                    "notes": p.notes, "attachments": json.dumps(p.attachments),
                }
                for i, p in enumerate(doc.properties)
            ])


def get_attachment_path(home_id: str, property_id: str, filename: str) -> Path:
    return attachment_storage.get_attachment_path(home_id, _MODULE, property_id, filename)


def save_attachment(home_id: str, property_id: str, filename: str, data: bytes) -> None:
    attachment_storage.save_attachment(home_id, _MODULE, property_id, filename, data)


def delete_attachment(home_id: str, property_id: str, filename: str) -> bool:
    return attachment_storage.delete_attachment(home_id, _MODULE, property_id, filename)


def delete_all_attachments(home_id: str, property_id: str) -> None:
    attachment_storage.delete_all_attachments(home_id, _MODULE, property_id)


def reset_properties(home_id: str) -> None:
    save_properties(home_id, PropertiesDocument())
    attachment_storage.delete_all_module_attachments(home_id, _MODULE)

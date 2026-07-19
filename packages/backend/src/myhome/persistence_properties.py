# packages/backend/src/myhome/persistence_properties.py
from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from sqlalchemy import select

from .db import get_engine
from .ids import InvalidIdError
from .models_properties import Property, PropertiesDocument
from .schema import properties as properties_table

_log = logging.getLogger(__name__)


def _home_dir(home_id: str) -> Path:
    # Normalize lexically (no filesystem access) then verify containment
    # within homes_root -- same shape as persistence_works.py's _home_dir,
    # which documents why this is CodeQL's own recommended sanitizer form.
    homes_root = os.path.normpath(os.path.join(os.environ.get("DATA_DIR", "/data"), "homes"))
    candidate = os.path.normpath(os.path.join(homes_root, home_id))
    if not candidate.startswith(homes_root + os.sep):
        raise InvalidIdError(f"Invalid home_id: {home_id!r}")
    return Path(candidate)


def _attachments_dir(home_id: str, property_id: str) -> Path:
    base = os.path.normpath(str(_home_dir(home_id) / "properties-attachments"))
    candidate = os.path.normpath(os.path.join(base, property_id))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid property_id: {property_id!r}")
    return Path(candidate)


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
    base = os.path.normpath(str(_attachments_dir(home_id, property_id)))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    return Path(candidate)


def save_attachment(home_id: str, property_id: str, filename: str, data: bytes) -> None:
    path = _attachments_dir(home_id, property_id)
    base = os.path.normpath(str(path))
    candidate = os.path.normpath(os.path.join(base, filename))
    if not candidate.startswith(base + os.sep):
        raise InvalidIdError(f"Invalid filename: {filename!r}")
    path.mkdir(parents=True, exist_ok=True)
    Path(candidate).write_bytes(data)


def delete_attachment(home_id: str, property_id: str, filename: str) -> bool:
    base = os.path.normpath(str(_attachments_dir(home_id, property_id)))
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


def delete_all_attachments(home_id: str, property_id: str) -> None:
    path = _attachments_dir(home_id, property_id)
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

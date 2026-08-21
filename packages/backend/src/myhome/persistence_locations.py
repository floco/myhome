# packages/backend/src/myhome/persistence_locations.py
from __future__ import annotations

import json
import uuid
from pathlib import Path

from sqlalchemy import select

from . import attachment_storage
from .attachment_storage import generate_pdf_thumbnail
from .db import get_engine
from .models_locations import Location, LocationCriterion, LocationRating, LocationsDocument
from .schema import (
    location_criteria as location_criteria_table,
    location_ratings as location_ratings_table,
    locations as locations_table,
)

_MODULE = "locations"

DEFAULT_CRITERIA: list[tuple[str, str]] = [
    ("Geography & Climate", "Geographic location, climate patterns, seasonal temperatures."),
    ("Cost of Living", "Cost of land, construction, everyday goods and services relative to your budget."),
    ("Healthcare", "Quality and accessibility of the healthcare system, especially for retirement."),
    ("Taxation", "Tax rules and residency implications for foreign residents."),
    ("Language & Culture", "Local language and your comfort with it; familiarity and appeal of the local culture."),
    ("Social Network & Community", "Presence of an existing community/family nearby and opportunities for social integration."),
    ("Safety", "Personal and property safety in the area."),
    ("Access to Services", "Proximity to essential services: hospitals, shops, etc."),
    ("Mobility & Transport", "Airports, roads, and public transport connections."),
    ("Real Estate Regulations", "Building and zoning regulations that would apply."),
    ("Quality of Life", "Overall subjective quality of life in the area."),
]


def load_locations(home_id: str) -> LocationsDocument:
    engine = get_engine()
    with engine.connect() as conn:
        criterion_rows = conn.execute(
            select(location_criteria_table).where(location_criteria_table.c.home_id == home_id)
            .order_by(location_criteria_table.c.order_index)
        ).mappings().all()
        location_rows = conn.execute(
            select(locations_table).where(locations_table.c.home_id == home_id)
            .order_by(locations_table.c.order_index)
        ).mappings().all()
        rating_rows = conn.execute(
            select(location_ratings_table).where(location_ratings_table.c.home_id == home_id)
        ).mappings().all()

    criteria = [
        LocationCriterion(id=r["id"], name=r["name"], description=r["description"], weight=r["weight"])
        for r in criterion_rows
    ]
    locations = [
        Location(
            id=r["id"], name=r["name"], emoji=r["emoji"],
            notes=r["notes"], attachments=json.loads(r["attachments"]),
        )
        for r in location_rows
    ]
    ratings = [
        LocationRating(locationId=r["location_id"], criterionId=r["criterion_id"], score=r["score"], note=r["note"])
        for r in rating_rows
    ]
    return LocationsDocument(criteria=criteria, locations=locations, ratings=ratings)


def save_locations(home_id: str, doc: LocationsDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(location_ratings_table.delete().where(location_ratings_table.c.home_id == home_id))
        conn.execute(locations_table.delete().where(locations_table.c.home_id == home_id))
        conn.execute(location_criteria_table.delete().where(location_criteria_table.c.home_id == home_id))
        if doc.criteria:
            conn.execute(location_criteria_table.insert(), [
                {
                    "id": c.id, "home_id": home_id, "order_index": i,
                    "name": c.name, "description": c.description, "weight": c.weight,
                }
                for i, c in enumerate(doc.criteria)
            ])
        if doc.locations:
            conn.execute(locations_table.insert(), [
                {
                    "id": l.id, "home_id": home_id, "order_index": i, "name": l.name, "emoji": l.emoji,
                    "notes": l.notes, "attachments": json.dumps(l.attachments),
                }
                for i, l in enumerate(doc.locations)
            ])
        if doc.ratings:
            conn.execute(location_ratings_table.insert(), [
                {
                    "location_id": r.locationId, "criterion_id": r.criterionId, "home_id": home_id,
                    "score": r.score, "note": r.note,
                }
                for r in doc.ratings
            ])


def seed_default_criteria(home_id: str) -> None:
    doc = LocationsDocument(
        criteria=[
            LocationCriterion(id=str(uuid.uuid4()), name=name, description=description)
            for name, description in DEFAULT_CRITERIA
        ],
    )
    save_locations(home_id, doc)


def reset_locations(home_id: str) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(location_ratings_table.delete().where(location_ratings_table.c.home_id == home_id))
        conn.execute(locations_table.delete().where(locations_table.c.home_id == home_id))
    attachment_storage.delete_all_module_attachments(home_id, _MODULE)


def get_attachment_path(home_id: str, location_id: str, filename: str) -> Path:
    return attachment_storage.get_attachment_path(home_id, _MODULE, location_id, filename)


def save_attachment(home_id: str, location_id: str, filename: str, data: bytes) -> None:
    attachment_storage.save_attachment(home_id, _MODULE, location_id, filename, data)


def delete_attachment(home_id: str, location_id: str, filename: str) -> bool:
    return attachment_storage.delete_attachment(home_id, _MODULE, location_id, filename)


def delete_all_attachments(home_id: str, location_id: str) -> None:
    attachment_storage.delete_all_attachments(home_id, _MODULE, location_id)

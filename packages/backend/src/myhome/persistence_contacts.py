# packages/backend/src/myhome/persistence_contacts.py
from sqlalchemy import select

from .db import get_engine
from .models_contacts import Contact, ContactsDocument
from .schema import (
    build_tasks as build_tasks_table,
    contacts as contacts_table,
    cost_entries as cost_entries_table,
    works as works_table,
)


def load_contacts(home_id: str) -> ContactsDocument:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(contacts_table).where(contacts_table.c.home_id == home_id)
            .order_by(contacts_table.c.order_index)
        ).mappings().all()
    return ContactsDocument(contacts=[
        Contact(
            id=r["id"], name=r["name"], companyName=r["company_name"], typeId=r["type_id"],
            phone=r["phone"], email=r["email"], address=r["address"], website=r["website"],
            notes=r["notes"],
        )
        for r in rows
    ])


def save_contacts(home_id: str, doc: ContactsDocument) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(contacts_table.delete().where(contacts_table.c.home_id == home_id))
        if doc.contacts:
            conn.execute(contacts_table.insert(), [
                {
                    "id": c.id, "home_id": home_id, "order_index": i, "name": c.name,
                    "company_name": c.companyName, "type_id": c.typeId, "phone": c.phone,
                    "email": c.email, "address": c.address, "website": c.website,
                    "notes": c.notes,
                }
                for i, c in enumerate(doc.contacts)
            ])


def get_contact_usage(home_id: str, contact_id: str) -> list[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        # build_tasks has no home_id column of its own (only reachable via
        # phase_id -> build_projects.home_id); contact_id values are UUIDs
        # generated per-record and never reused across homes, so matching
        # on contractor_id alone can't cross into another home's data.
        build_rows = conn.execute(
            select(build_tasks_table.c.id, build_tasks_table.c.title_override, build_tasks_table.c.title_key)
            .where(build_tasks_table.c.contractor_id == contact_id)
        ).mappings().all()
        work_rows = conn.execute(
            select(works_table.c.id, works_table.c.title)
            .where(works_table.c.home_id == home_id, works_table.c.contact_id == contact_id)
        ).mappings().all()
        cost_rows = conn.execute(
            select(cost_entries_table.c.id, cost_entries_table.c.notes, cost_entries_table.c.total_amount)
            .where(cost_entries_table.c.home_id == home_id, cost_entries_table.c.contact_id == contact_id)
        ).mappings().all()

    references: list[dict] = []
    for r in build_rows:
        # The backend has no locale awareness (see house-build-tracking
        # design's name_key/title_key mechanics) -- a seeded, never-edited
        # task falls back to its raw title_key string here rather than a
        # translated title. This is a display-only reference list, not
        # something requiring localization.
        label = r["title_override"] or r["title_key"] or "(untitled task)"
        references.append({"module": "build", "id": r["id"], "label": label})
    for r in work_rows:
        references.append({"module": "works", "id": r["id"], "label": r["title"]})
    for r in cost_rows:
        label = r["notes"] or f"{r['total_amount']:g}"
        references.append({"module": "costs", "id": r["id"], "label": label})
    return references


def reset_contacts(home_id: str) -> None:
    save_contacts(home_id, ContactsDocument())

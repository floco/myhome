# packages/backend/src/myhome/routes/contacts.py
import uuid

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user_id
from ..models_contacts import Contact, ContactCreate, ContactsDocument, ContactUpdate
from ..persistence_activity import log_activity
from ..persistence_contacts import get_contact_usage, load_contacts, save_contacts

router = APIRouter()


@router.get("/api/homes/{home_id}/contacts", response_model=ContactsDocument)
def get_contacts(home_id: str) -> ContactsDocument:
    return load_contacts(home_id)


@router.post("/api/homes/{home_id}/contacts", response_model=Contact, status_code=201)
def create_contact(
    home_id: str, body: ContactCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Contact:
    doc = load_contacts(home_id)
    contact = Contact(id=str(uuid.uuid4()), **body.model_dump())
    doc.contacts.append(contact)
    save_contacts(home_id, doc)
    log_activity(home_id, current_user_id, "contacts", "create", contact.name, contact.id)
    return contact


@router.put("/api/homes/{home_id}/contacts/{id}", status_code=204)
def update_contact(
    home_id: str, id: str, body: ContactUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_contacts(home_id)
    contact = next((c for c in doc.contacts if c.id == id), None)
    if not contact:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    save_contacts(home_id, doc)
    log_activity(home_id, current_user_id, "contacts", "update", contact.name, id)


@router.get("/api/homes/{home_id}/contacts/{id}/usage")
def get_contact_usage_route(home_id: str, id: str) -> dict:
    return {"references": get_contact_usage(home_id, id)}


@router.delete("/api/homes/{home_id}/contacts/{id}", status_code=204)
def delete_contact(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_contacts(home_id)
    contact = next((c for c in doc.contacts if c.id == id), None)
    if contact is None:
        raise HTTPException(status_code=404)
    usage = get_contact_usage(home_id, id)
    if usage:
        raise HTTPException(status_code=409, detail={"references": usage})
    doc.contacts = [c for c in doc.contacts if c.id != id]
    save_contacts(home_id, doc)
    log_activity(home_id, current_user_id, "contacts", "delete", contact.name, id)

# packages/backend/src/myhome/models_contacts.py
from __future__ import annotations
from pydantic import BaseModel


class Contact(BaseModel):
    id: str
    name: str
    companyName: str | None = None
    typeId: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    website: str | None = None
    notes: str = ""


class ContactsDocument(BaseModel):
    version: int = 1
    contacts: list[Contact] = []


class ContactCreate(BaseModel):
    name: str
    companyName: str | None = None
    typeId: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    website: str | None = None
    notes: str = ""


class ContactUpdate(BaseModel):
    name: str | None = None
    companyName: str | None = None
    typeId: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    website: str | None = None
    notes: str | None = None

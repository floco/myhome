# packages/backend/src/myhome/mcp_tools_contacts.py
from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context

from .mcp_server import _require_role, _resolve_home_id, mcp
from .models_contacts import Contact
from .persistence_contacts import get_contact_usage, load_contacts, save_contacts


def _list_contacts_impl(home_id: str | None) -> dict:
    resolved = _resolve_home_id(home_id)
    return load_contacts(resolved).model_dump()


def _create_contact_impl(
    home_id: str | None, name: str, type_id: str,
    company_name: str | None = None, phone: str | None = None,
    email: str | None = None, address: str | None = None,
    website: str | None = None, notes: str = "",
) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_contacts(resolved)
    contact = Contact(
        id=str(uuid.uuid4()), name=name, typeId=type_id, companyName=company_name,
        phone=phone, email=email, address=address, website=website, notes=notes,
    )
    doc.contacts.append(contact)
    save_contacts(resolved, doc)
    return contact.model_dump()


def _update_contact_impl(home_id: str | None, contact_id: str, **fields) -> dict:
    resolved = _resolve_home_id(home_id)
    doc = load_contacts(resolved)
    contact = next((c for c in doc.contacts if c.id == contact_id), None)
    if contact is None:
        raise ValueError(f"Unknown contact_id {contact_id!r}")
    for field, value in fields.items():
        if value is not None:
            setattr(contact, field, value)
    save_contacts(resolved, doc)
    return contact.model_dump()


def _delete_contact_impl(home_id: str | None, contact_id: str) -> dict:
    resolved = _resolve_home_id(home_id)
    usage = get_contact_usage(resolved, contact_id)
    if usage:
        raise ValueError(f"Contact {contact_id!r} is still referenced by: {usage}")
    doc = load_contacts(resolved)
    before = len(doc.contacts)
    doc.contacts = [c for c in doc.contacts if c.id != contact_id]
    if len(doc.contacts) == before:
        raise ValueError(f"Unknown contact_id {contact_id!r}")
    save_contacts(resolved, doc)
    return {"deleted": contact_id}


@mcp.tool()
async def list_contacts(ctx: Context, home_id: str | None = None) -> dict:
    """List contacts (contractors, suppliers, service providers, agents, notaries) for a home."""
    await _require_role(ctx.request_context.request, "ro")
    return _list_contacts_impl(home_id)


@mcp.tool()
async def create_contact(
    ctx: Context, name: str, type_id: str, home_id: str | None = None,
    company_name: str | None = None, phone: str | None = None,
    email: str | None = None, address: str | None = None,
    website: str | None = None, notes: str = "",
) -> dict:
    """Create a contact. type_id should match an id from get_settings' contactTypes."""
    await _require_role(ctx.request_context.request, "normal")
    return _create_contact_impl(home_id, name, type_id, company_name, phone, email, address, website, notes)


@mcp.tool()
async def update_contact(
    ctx: Context, contact_id: str, home_id: str | None = None,
    name: str | None = None, type_id: str | None = None,
    company_name: str | None = None, phone: str | None = None,
    email: str | None = None, address: str | None = None,
    website: str | None = None, notes: str | None = None,
) -> dict:
    """Update fields on an existing contact."""
    await _require_role(ctx.request_context.request, "normal")
    return _update_contact_impl(
        home_id, contact_id, name=name, typeId=type_id, companyName=company_name,
        phone=phone, email=email, address=address, website=website, notes=notes,
    )


@mcp.tool()
async def delete_contact(ctx: Context, contact_id: str, home_id: str | None = None) -> dict:
    """Delete a contact. Fails if the contact is still referenced by a build task, work, or cost entry."""
    await _require_role(ctx.request_context.request, "normal")
    return _delete_contact_impl(home_id, contact_id)

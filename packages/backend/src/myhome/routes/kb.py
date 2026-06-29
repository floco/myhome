import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from ..models_kb import KBCreate, KBDocument, KBEntry, KBUpdate
from ..persistence_kb import load_kb, save_kb

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/api/kb", response_model=KBDocument)
def get_kb() -> KBDocument:
    return load_kb()


@router.post("/api/kb", response_model=KBEntry, status_code=201)
def create_entry(body: KBCreate) -> KBEntry:
    doc = load_kb()
    now = _now()
    entry = KBEntry(
        id=str(uuid.uuid4()),
        title=body.title,
        content=body.content,
        createdAt=now,
        updatedAt=now,
    )
    doc.entries.append(entry)
    save_kb(doc)
    return entry


@router.put("/api/kb/{id}", status_code=204)
def update_entry(id: str, body: KBUpdate) -> None:
    doc = load_kb()
    entry = next((e for e in doc.entries if e.id == id), None)
    if not entry:
        raise HTTPException(status_code=404)
    if body.title is not None:
        entry.title = body.title
    if body.content is not None:
        entry.content = body.content
    entry.updatedAt = _now()
    save_kb(doc)


@router.delete("/api/kb/{id}", status_code=204)
def delete_entry(id: str) -> None:
    doc = load_kb()
    before = len(doc.entries)
    doc.entries = [e for e in doc.entries if e.id != id]
    if len(doc.entries) == before:
        raise HTTPException(status_code=404)
    save_kb(doc)

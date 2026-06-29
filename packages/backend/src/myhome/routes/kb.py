import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from ..models_kb import KBCreate, KBDocument, KBEntry, KBUpdate
from ..persistence_kb import delete_entry, load_all, load_entry, save_entry

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/api/kb", response_model=KBDocument)
def get_kb() -> KBDocument:
    return KBDocument(entries=load_all())


@router.post("/api/kb", response_model=KBEntry, status_code=201)
def create_entry(body: KBCreate) -> KBEntry:
    now = _now()
    entry = KBEntry(
        id=str(uuid.uuid4()),
        title=body.title,
        content=body.content,
        createdAt=now,
        updatedAt=now,
    )
    save_entry(entry)
    return entry


@router.put("/api/kb/{id}", status_code=204)
def update_entry(id: str, body: KBUpdate) -> None:
    entry = load_entry(id)
    if not entry:
        raise HTTPException(status_code=404)
    if body.title is not None:
        entry.title = body.title
    if body.content is not None:
        entry.content = body.content
    entry.updatedAt = _now()
    save_entry(entry)


@router.delete("/api/kb/{id}", status_code=204)
def delete_kb_entry(id: str) -> None:
    if not delete_entry(id):
        raise HTTPException(status_code=404)

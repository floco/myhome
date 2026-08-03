import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user_id
from ..link_preview import fetch_link_preview, render_bookmark_html
from ..models_kb import (
    KBCreate, KBDocument, KBEntry, KBLinkPreviewRequest, KBReorder, KBTrashDocument, KBUpdate,
)
from ..persistence_activity import log_activity
from ..persistence_kb import (
    delete_entry,
    empty_trash,
    list_trash,
    load_all,
    load_entry,
    next_order,
    reorder_siblings,
    restore_subtree,
    save_entry,
    soft_delete_subtree,
    would_create_cycle,
)

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _live_entry(home_id: str, id: str) -> KBEntry | None:
    entry = load_entry(home_id, id)
    if entry is None or entry.deletedAt is not None:
        return None
    return entry


@router.get("/api/homes/{home_id}/kb", response_model=KBDocument)
def get_kb(home_id: str) -> KBDocument:
    return KBDocument(entries=load_all(home_id))


@router.post("/api/homes/{home_id}/kb", response_model=KBEntry, status_code=201)
def create_entry(
    home_id: str, body: KBCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> KBEntry:
    if body.parentId is not None and _live_entry(home_id, body.parentId) is None:
        raise HTTPException(status_code=404, detail="Parent page not found")
    now = _now()
    entry = KBEntry(
        id=str(uuid.uuid4()),
        title=body.title,
        content=body.content,
        parentId=body.parentId,
        icon=body.icon,
        order=next_order(home_id, body.parentId),
        createdAt=now,
        updatedAt=now,
    )
    save_entry(home_id, entry)
    log_activity(home_id, current_user_id, "kb", "create", entry.title, entry.id)
    return entry


@router.put("/api/homes/{home_id}/kb/reorder", status_code=204)
def reorder_kb_entries(
    home_id: str, body: KBReorder,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    siblings = [e for e in load_all(home_id) if e.parentId == body.parentId]
    if {e.id for e in siblings} != set(body.orderedIds):
        raise HTTPException(status_code=400, detail="orderedIds must match current siblings exactly")
    reorder_siblings(home_id, body.parentId, body.orderedIds)


@router.put("/api/homes/{home_id}/kb/{id}", status_code=204)
def update_entry(
    home_id: str, id: str, body: KBUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    entry = _live_entry(home_id, id)
    if not entry:
        raise HTTPException(status_code=404)
    if body.title is not None:
        entry.title = body.title
    if body.content is not None:
        entry.content = body.content
    if body.icon is not None:
        entry.icon = body.icon
    if "parentId" in body.model_fields_set:
        if body.parentId is not None:
            if _live_entry(home_id, body.parentId) is None:
                raise HTTPException(status_code=404, detail="Parent page not found")
            if would_create_cycle(home_id, id, body.parentId):
                raise HTTPException(status_code=400, detail="Cannot move a page into itself or a descendant")
        entry.parentId = body.parentId
        entry.order = next_order(home_id, body.parentId)
    entry.updatedAt = _now()
    save_entry(home_id, entry)
    log_activity(home_id, current_user_id, "kb", "update", entry.title, id)


@router.delete("/api/homes/{home_id}/kb/{id}", status_code=200)
def delete_kb_entry(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    entry = _live_entry(home_id, id)
    if not entry:
        raise HTTPException(status_code=404)
    deleted_ids = soft_delete_subtree(home_id, id)
    log_activity(home_id, current_user_id, "kb", "delete", entry.title, id)
    return {"deletedCount": len(deleted_ids)}


@router.get("/api/homes/{home_id}/kb/trash", response_model=KBTrashDocument)
def get_kb_trash(home_id: str) -> KBTrashDocument:
    return KBTrashDocument(entries=list_trash(home_id))


@router.post("/api/homes/{home_id}/kb/trash/{id}/restore", status_code=200)
def restore_kb_entry(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    entry = load_entry(home_id, id)
    if entry is None or entry.deletedAt is None:
        raise HTTPException(status_code=404)
    restored_ids = restore_subtree(home_id, id)
    log_activity(home_id, current_user_id, "kb", "restore", entry.title, id)
    return {"restoredCount": len(restored_ids)}


@router.delete("/api/homes/{home_id}/kb/trash/{id}", status_code=204)
def permanently_delete_kb_entry(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    entry = load_entry(home_id, id)
    if entry is None or entry.deletedAt is None:
        raise HTTPException(status_code=404)
    delete_entry(home_id, id)
    log_activity(home_id, current_user_id, "kb", "delete_forever", entry.title, id)


@router.post("/api/homes/{home_id}/kb/trash/empty", status_code=200)
def empty_kb_trash(
    home_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    deleted_ids = empty_trash(home_id)
    log_activity(home_id, current_user_id, "kb", "empty_trash", f"{len(deleted_ids)} pages", None)
    return {"deletedCount": len(deleted_ids)}


@router.post("/api/homes/{home_id}/kb/link-preview")
def get_kb_link_preview(home_id: str, body: KBLinkPreviewRequest) -> dict:
    # home_id is unused -- kept for URL-namespace consistency with the rest of this
    # router; this endpoint isn't entry- or home-scoped, it's a stateless URL lookup.
    try:
        preview = fetch_link_preview(body.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "html": render_bookmark_html(preview),
        "title": preview.title,
        "description": preview.description,
        "image": preview.image,
    }

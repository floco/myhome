import mimetypes
import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..deps import get_current_user_id
from ..models_kb import KBCreate, KBDocument, KBEntry, KBReorder, KBTrashDocument, KBUpdate
from ..persistence_activity import log_activity
from ..persistence_kb import (
    delete_attachment,
    delete_entry,
    empty_trash,
    generate_pdf_thumbnail,
    get_attachment_path,
    list_trash,
    load_all,
    load_entry,
    next_order,
    reorder_siblings,
    restore_subtree,
    save_attachment,
    save_entry,
    soft_delete_subtree,
    would_create_cycle,
)

router = APIRouter()

_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_id(entry_id: str) -> None:
    if not _ID_RE.fullmatch(entry_id):
        raise HTTPException(status_code=400, detail="Invalid id")


def _validate_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"


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


@router.post("/api/homes/{home_id}/kb/{id}/attachments", status_code=201)
async def upload_kb_attachment(home_id: str, id: str, file: UploadFile) -> dict:
    _validate_id(id)
    entry = load_entry(home_id, id)
    if not entry:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    ext = os.path.splitext(original.lower())[1]
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not supported")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(home_id, id, filename, data)
    if ext == ".pdf":
        pdf_path = get_attachment_path(home_id, id, filename)
        thumb_path = pdf_path.with_name(pdf_path.name + ".thumb.jpg")
        generate_pdf_thumbnail(pdf_path, thumb_path)
    if filename not in entry.attachments:
        entry.attachments.append(filename)
    entry.updatedAt = _now()
    save_entry(home_id, entry)
    return {"filename": filename}


@router.get("/api/homes/{home_id}/kb/{id}/attachments/{filename}")
def get_kb_attachment(home_id: str, id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    path = get_attachment_path(home_id, id, filename)
    if not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")


@router.delete("/api/homes/{home_id}/kb/{id}/attachments/{filename}", status_code=204)
def delete_kb_attachment(home_id: str, id: str, filename: str) -> None:
    _validate_id(id)
    _validate_filename(filename)
    entry = load_entry(home_id, id)
    if not entry:
        raise HTTPException(status_code=404)
    if not delete_attachment(home_id, id, filename):
        raise HTTPException(status_code=404)
    entry.attachments = [a for a in entry.attachments if a != filename]
    entry.updatedAt = _now()
    save_entry(home_id, entry)

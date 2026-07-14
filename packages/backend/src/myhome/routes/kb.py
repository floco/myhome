import mimetypes
import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..deps import get_current_user_id
from ..models_kb import KBCreate, KBDocument, KBEntry, KBFolder, KBFolderCreate, KBFolderUpdate, KBUpdate
from ..persistence_activity import log_activity
from ..persistence_kb import (
    get_attachment_path,
    delete_attachment,
    delete_entry,
    generate_pdf_thumbnail,
    load_all,
    load_entry,
    save_attachment,
    save_entry,
)
from ..persistence_kb_folders import (
    create_folder,
    delete_folder,
    get_folder,
    list_folders,
    move_folder,
    rename_folder,
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


@router.get("/api/homes/{home_id}/kb", response_model=KBDocument)
def get_kb(home_id: str) -> KBDocument:
    return KBDocument(entries=load_all(home_id), folders=list_folders(home_id))


@router.post("/api/homes/{home_id}/kb", response_model=KBEntry, status_code=201)
def create_entry(
    home_id: str, body: KBCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> KBEntry:
    if body.folderId is not None and get_folder(home_id, body.folderId) is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    now = _now()
    entry = KBEntry(
        id=str(uuid.uuid4()),
        title=body.title,
        content=body.content,
        folderId=body.folderId,
        createdAt=now,
        updatedAt=now,
    )
    save_entry(home_id, entry)
    log_activity(home_id, current_user_id, "kb", "create", entry.title, entry.id)
    return entry


@router.put("/api/homes/{home_id}/kb/{id}", status_code=204)
def update_entry(
    home_id: str, id: str, body: KBUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    entry = load_entry(home_id, id)
    if not entry:
        raise HTTPException(status_code=404)
    if body.title is not None:
        entry.title = body.title
    if body.content is not None:
        entry.content = body.content
    if "folderId" in body.model_fields_set:
        if body.folderId is not None and get_folder(home_id, body.folderId) is None:
            raise HTTPException(status_code=404, detail="Folder not found")
        entry.folderId = body.folderId
    entry.updatedAt = _now()
    save_entry(home_id, entry)
    log_activity(home_id, current_user_id, "kb", "update", entry.title, id)


@router.delete("/api/homes/{home_id}/kb/{id}", status_code=204)
def delete_kb_entry(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    entry = load_entry(home_id, id)
    if not entry:
        raise HTTPException(status_code=404)
    if not delete_entry(home_id, id):
        raise HTTPException(status_code=404)
    log_activity(home_id, current_user_id, "kb", "delete", entry.title, id)


@router.post("/api/homes/{home_id}/kb/folders", response_model=KBFolder, status_code=201)
def create_kb_folder(home_id: str, body: KBFolderCreate) -> KBFolder:
    if body.parentId is not None and get_folder(home_id, body.parentId) is None:
        raise HTTPException(status_code=404, detail="Parent folder not found")
    return create_folder(home_id, body.name, body.parentId)


@router.put("/api/homes/{home_id}/kb/folders/{id}", status_code=204)
def update_kb_folder(home_id: str, id: str, body: KBFolderUpdate) -> None:
    if get_folder(home_id, id) is None:
        raise HTTPException(status_code=404)
    fields = body.model_fields_set
    if "name" in fields and body.name is not None:
        rename_folder(home_id, id, body.name)
    if "parentId" in fields:
        if body.parentId is not None:
            if get_folder(home_id, body.parentId) is None:
                raise HTTPException(status_code=404, detail="Parent folder not found")
            if would_create_cycle(home_id, id, body.parentId):
                raise HTTPException(status_code=400, detail="Cannot move a folder into itself or a descendant")
        move_folder(home_id, id, body.parentId)


@router.delete("/api/homes/{home_id}/kb/folders/{id}", status_code=204)
def delete_kb_folder(home_id: str, id: str) -> None:
    if get_folder(home_id, id) is None:
        raise HTTPException(status_code=404)
    has_subfolders = any(f.parentId == id for f in list_folders(home_id))
    has_entries = any(e.folderId == id for e in load_all(home_id))
    if has_subfolders or has_entries:
        raise HTTPException(status_code=400, detail="Folder must be empty before it can be deleted")
    delete_folder(home_id, id)


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

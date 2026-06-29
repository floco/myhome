import mimetypes
import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..models_kb import KBCreate, KBDocument, KBEntry, KBUpdate
from ..persistence_kb import (
    _attachments_dir,
    delete_attachment,
    delete_entry,
    generate_pdf_thumbnail,
    load_all,
    load_entry,
    save_attachment,
    save_entry,
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


@router.post("/api/kb/{id}/attachments", status_code=201)
async def upload_kb_attachment(id: str, file: UploadFile) -> dict:
    _validate_id(id)
    entry = load_entry(id)
    if not entry:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    ext = os.path.splitext(original.lower())[1]
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not supported")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(id, filename, data)
    if ext == ".pdf":
        generate_pdf_thumbnail(
            _attachments_dir(id) / filename,
            _attachments_dir(id) / (filename + ".thumb.jpg"),
        )
    if filename not in entry.attachments:
        entry.attachments.append(filename)
    entry.updatedAt = _now()
    save_entry(entry)
    return {"filename": filename}


@router.get("/api/kb/{id}/attachments/{filename}")
def get_kb_attachment(id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    base = _attachments_dir(id).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base) + "/") or not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")


@router.delete("/api/kb/{id}/attachments/{filename}", status_code=204)
def delete_kb_attachment(id: str, filename: str) -> None:
    _validate_id(id)
    _validate_filename(filename)
    entry = load_entry(id)
    if not entry:
        raise HTTPException(status_code=404)
    if not delete_attachment(id, filename):
        raise HTTPException(status_code=404)
    entry.attachments = [a for a in entry.attachments if a != filename]
    entry.updatedAt = _now()
    save_entry(entry)

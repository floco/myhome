import mimetypes
import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..deps import get_current_user_id
from ..models_costs import CostEntry, CostEntryCreate, CostEntryUpdate, CostsDocument
from ..persistence_activity import log_activity
from ..persistence_costs import (
    _attachments_dir,
    delete_all_attachments,
    delete_attachment,
    generate_pdf_thumbnail,
    load_costs,
    save_attachment,
    save_costs,
)

router = APIRouter()

_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"


def _validate_id(entry_id: str) -> None:
    if not _ID_RE.fullmatch(entry_id):
        raise HTTPException(status_code=400, detail="Invalid id")


def _validate_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


def _cost_label(entry: CostEntry) -> str:
    return entry.notes if entry.notes else f"{entry.totalAmount:g}"


@router.get("/api/homes/{home_id}/costs", response_model=CostsDocument)
def get_costs(home_id: str) -> CostsDocument:
    return load_costs(home_id)


@router.post("/api/homes/{home_id}/costs/entries", response_model=CostEntry, status_code=201)
def create_entry(
    home_id: str, body: CostEntryCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> CostEntry:
    doc = load_costs(home_id)
    entry = CostEntry(id=str(uuid.uuid4()), **body.model_dump())
    doc.entries.append(entry)
    save_costs(home_id, doc)
    log_activity(home_id, current_user_id, "costs", "create", _cost_label(entry), entry.id)
    return entry


@router.put("/api/homes/{home_id}/costs/entries/{id}", status_code=204)
def update_entry(
    home_id: str, id: str, body: CostEntryUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_costs(home_id)
    entry = next((e for e in doc.entries if e.id == id), None)
    if not entry:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    save_costs(home_id, doc)
    log_activity(home_id, current_user_id, "costs", "update", _cost_label(entry), id)


@router.delete("/api/homes/{home_id}/costs/entries/{id}", status_code=204)
def delete_entry(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_costs(home_id)
    entry = next((e for e in doc.entries if e.id == id), None)
    if entry is None:
        raise HTTPException(status_code=404)
    doc.entries = [e for e in doc.entries if e.id != id]
    save_costs(home_id, doc)
    delete_all_attachments(home_id, id)
    log_activity(home_id, current_user_id, "costs", "delete", _cost_label(entry), id)


@router.post("/api/homes/{home_id}/costs/entries/{id}/attachments", status_code=201)
async def upload_cost_attachment(home_id: str, id: str, file: UploadFile) -> dict:
    _validate_id(id)
    doc = load_costs(home_id)
    entry = next((e for e in doc.entries if e.id == id), None)
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
        generate_pdf_thumbnail(
            _attachments_dir(home_id, id) / filename,
            _attachments_dir(home_id, id) / (filename + ".thumb.jpg"),
        )
    if filename not in entry.attachments:
        entry.attachments.append(filename)
    save_costs(home_id, doc)
    return {"filename": filename}


@router.get("/api/homes/{home_id}/costs/entries/{id}/attachments/{filename}")
def get_cost_attachment(home_id: str, id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    base = _attachments_dir(home_id, id).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base) + "/") or not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")


@router.delete("/api/homes/{home_id}/costs/entries/{id}/attachments/{filename}", status_code=204)
def remove_cost_attachment(home_id: str, id: str, filename: str) -> None:
    _validate_id(id)
    _validate_filename(filename)
    doc = load_costs(home_id)
    entry = next((e for e in doc.entries if e.id == id), None)
    if not entry:
        raise HTTPException(status_code=404)
    if not delete_attachment(home_id, id, filename):
        raise HTTPException(status_code=404)
    entry.attachments = [a for a in entry.attachments if a != filename]
    save_costs(home_id, doc)

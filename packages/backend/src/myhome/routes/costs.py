import mimetypes
import os
import re
import uuid

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..models_costs import CostEntry, CostEntryCreate, CostEntryUpdate, CostsDocument
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


@router.get("/api/costs", response_model=CostsDocument)
def get_costs() -> CostsDocument:
    return load_costs()


@router.post("/api/costs/entries", response_model=CostEntry, status_code=201)
def create_entry(body: CostEntryCreate) -> CostEntry:
    doc = load_costs()
    entry = CostEntry(id=str(uuid.uuid4()), **body.model_dump())
    doc.entries.append(entry)
    save_costs(doc)
    return entry


@router.put("/api/costs/entries/{id}", status_code=204)
def update_entry(id: str, body: CostEntryUpdate) -> None:
    doc = load_costs()
    entry = next((e for e in doc.entries if e.id == id), None)
    if not entry:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    save_costs(doc)


@router.delete("/api/costs/entries/{id}", status_code=204)
def delete_entry(id: str) -> None:
    doc = load_costs()
    before = len(doc.entries)
    doc.entries = [e for e in doc.entries if e.id != id]
    if len(doc.entries) == before:
        raise HTTPException(status_code=404)
    save_costs(doc)
    delete_all_attachments(id)


@router.post("/api/costs/entries/{id}/attachments", status_code=201)
async def upload_cost_attachment(id: str, file: UploadFile) -> dict:
    _validate_id(id)
    doc = load_costs()
    entry = next((e for e in doc.entries if e.id == id), None)
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
    save_costs(doc)
    return {"filename": filename}


@router.get("/api/costs/entries/{id}/attachments/{filename}")
def get_cost_attachment(id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    base = _attachments_dir(id).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base) + "/") or not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")


@router.delete("/api/costs/entries/{id}/attachments/{filename}", status_code=204)
def remove_cost_attachment(id: str, filename: str) -> None:
    _validate_id(id)
    _validate_filename(filename)
    doc = load_costs()
    entry = next((e for e in doc.entries if e.id == id), None)
    if not entry:
        raise HTTPException(status_code=404)
    if not delete_attachment(id, filename):
        raise HTTPException(status_code=404)
    entry.attachments = [a for a in entry.attachments if a != filename]
    save_costs(doc)

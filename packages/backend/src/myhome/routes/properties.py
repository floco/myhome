import mimetypes
import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..deps import get_current_user_id
from ..models_properties import PropertiesDocument, Property, PropertyCreate, PropertyUpdate
from ..persistence_activity import log_activity
from ..persistence_properties import (
    delete_all_attachments,
    delete_attachment,
    generate_pdf_thumbnail,
    get_attachment_path,
    load_properties,
    save_attachment,
    save_properties,
)

router = APIRouter()

_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"


def _validate_id(property_id: str) -> None:
    if not _ID_RE.fullmatch(property_id):
        raise HTTPException(status_code=400, detail="Invalid id")


def _validate_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


@router.get("/api/homes/{home_id}/properties", response_model=PropertiesDocument)
def get_properties(home_id: str) -> PropertiesDocument:
    return load_properties(home_id)


@router.post("/api/homes/{home_id}/properties", response_model=Property, status_code=201)
def create_property(
    home_id: str, body: PropertyCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Property:
    doc = load_properties(home_id)
    item = Property(id=str(uuid.uuid4()), **body.model_dump())
    doc.properties.append(item)
    save_properties(home_id, doc)
    log_activity(home_id, current_user_id, "properties", "create", item.name, item.id)
    return item


@router.put("/api/homes/{home_id}/properties/{id}", status_code=204)
def update_property(
    home_id: str, id: str, body: PropertyUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_properties(home_id)
    item = next((p for p in doc.properties if p.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    save_properties(home_id, doc)
    log_activity(home_id, current_user_id, "properties", "update", item.name, id)


@router.delete("/api/homes/{home_id}/properties/{id}", status_code=204)
def delete_property(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_properties(home_id)
    item = next((p for p in doc.properties if p.id == id), None)
    if item is None:
        raise HTTPException(status_code=404)
    doc.properties = [p for p in doc.properties if p.id != id]
    save_properties(home_id, doc)
    delete_all_attachments(home_id, id)
    log_activity(home_id, current_user_id, "properties", "delete", item.name, id)


@router.post("/api/homes/{home_id}/properties/{id}/attachments", status_code=201)
async def upload_property_attachment(home_id: str, id: str, file: UploadFile) -> dict:
    _validate_id(id)
    doc = load_properties(home_id)
    item = next((p for p in doc.properties if p.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    ext = os.path.splitext(original)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(home_id, id, filename, data)
    if ext == ".pdf":
        pdf_path = get_attachment_path(home_id, id, filename)
        thumb_path = pdf_path.with_name(pdf_path.name + ".thumb.jpg")
        generate_pdf_thumbnail(pdf_path, thumb_path)
    if filename not in item.attachments:
        item.attachments.append(filename)
    save_properties(home_id, doc)
    return {"filename": filename}


@router.get("/api/homes/{home_id}/properties/{id}/attachments/{filename}")
def get_property_attachment(home_id: str, id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    path = get_attachment_path(home_id, id, filename)
    if not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")


@router.delete("/api/homes/{home_id}/properties/{id}/attachments/{filename}", status_code=204)
def remove_property_attachment(home_id: str, id: str, filename: str) -> None:
    _validate_id(id)
    _validate_filename(filename)
    doc = load_properties(home_id)
    item = next((p for p in doc.properties if p.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    if not delete_attachment(home_id, id, filename):
        raise HTTPException(status_code=404)
    item.attachments = [a for a in item.attachments if a != filename]
    save_properties(home_id, doc)

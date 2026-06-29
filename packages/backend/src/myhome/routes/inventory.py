import mimetypes
import os
import re
import uuid

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..models_inventory import (
    InventoryDocument,
    InventoryItem,
    InventoryItemCreate,
    InventoryItemUpdate,
    PlacementUpdate,
)
from ..persistence_inventory import (
    _attachments_dir,
    delete_all_attachments,
    delete_attachment,
    generate_pdf_thumbnail,
    load_inventory,
    save_attachment,
    save_inventory,
)

router = APIRouter()


@router.get("/api/inventory", response_model=InventoryDocument)
def get_inventory() -> InventoryDocument:
    return load_inventory()


@router.post("/api/inventory/items", response_model=InventoryItem, status_code=201)
def create_item(body: InventoryItemCreate) -> InventoryItem:
    doc = load_inventory()
    item = InventoryItem(id=str(uuid.uuid4()), **body.model_dump())
    doc.items.append(item)
    save_inventory(doc)
    return item


@router.put("/api/inventory/items/{id}", status_code=204)
def update_item(id: str, body: InventoryItemUpdate) -> None:
    doc = load_inventory()
    item = next((i for i in doc.items if i.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    save_inventory(doc)


@router.delete("/api/inventory/items/{id}", status_code=204)
def delete_item(id: str) -> None:
    doc = load_inventory()
    before = len(doc.items)
    doc.items = [i for i in doc.items if i.id != id]
    if len(doc.items) == before:
        raise HTTPException(status_code=404)
    save_inventory(doc)
    delete_all_attachments(id)


@router.put("/api/inventory/items/{id}/placement", status_code=204)
def update_placement(id: str, body: PlacementUpdate) -> None:
    doc = load_inventory()
    item = next((i for i in doc.items if i.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    item.placement = body.placement
    save_inventory(doc)


_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"


_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _validate_id(item_id: str) -> None:
    if not _ID_RE.fullmatch(item_id):
        raise HTTPException(status_code=400, detail="Invalid id")


def _validate_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


@router.post("/api/inventory/items/{id}/attachments", status_code=201)
async def upload_attachment(id: str, file: UploadFile) -> dict:
    _validate_id(id)
    doc = load_inventory()
    item = next((i for i in doc.items if i.id == id), None)
    if not item:
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
    if filename not in item.attachments:
        item.attachments.append(filename)
    save_inventory(doc)
    return {"filename": filename}


@router.get("/api/inventory/items/{id}/attachments/{filename}")
def get_attachment(id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    base = _attachments_dir(id).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base) + "/") or not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")


@router.delete("/api/inventory/items/{id}/attachments/{filename}", status_code=204)
def remove_attachment(id: str, filename: str) -> None:
    _validate_id(id)
    _validate_filename(filename)
    doc = load_inventory()
    item = next((i for i in doc.items if i.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    if not delete_attachment(id, filename):
        raise HTTPException(status_code=404)
    item.attachments = [a for a in item.attachments if a != filename]
    save_inventory(doc)

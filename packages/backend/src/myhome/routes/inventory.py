import mimetypes
import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..deps import get_current_user_id
from ..models_inventory import (
    InventoryDocument,
    InventoryItem,
    InventoryItemCreate,
    InventoryItemUpdate,
    PlacementUpdate,
)
from ..persistence_activity import log_activity
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


@router.get("/api/homes/{home_id}/inventory", response_model=InventoryDocument)
def get_inventory(home_id: str) -> InventoryDocument:
    return load_inventory(home_id)


@router.post("/api/homes/{home_id}/inventory/items", response_model=InventoryItem, status_code=201)
def create_item(
    home_id: str, body: InventoryItemCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> InventoryItem:
    doc = load_inventory(home_id)
    item = InventoryItem(id=str(uuid.uuid4()), **body.model_dump())
    doc.items.append(item)
    save_inventory(home_id, doc)
    log_activity(home_id, current_user_id, "inventory", "create", item.name, item.id)
    return item


@router.put("/api/homes/{home_id}/inventory/items/{id}", status_code=204)
def update_item(
    home_id: str, id: str, body: InventoryItemUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_inventory(home_id)
    item = next((i for i in doc.items if i.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    save_inventory(home_id, doc)
    log_activity(home_id, current_user_id, "inventory", "update", item.name, id)


@router.delete("/api/homes/{home_id}/inventory/items/{id}", status_code=204)
def delete_item(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_inventory(home_id)
    item = next((i for i in doc.items if i.id == id), None)
    if item is None:
        raise HTTPException(status_code=404)
    doc.items = [i for i in doc.items if i.id != id]
    save_inventory(home_id, doc)
    delete_all_attachments(home_id, id)
    log_activity(home_id, current_user_id, "inventory", "delete", item.name, id)


@router.put("/api/homes/{home_id}/inventory/items/{id}/placement", status_code=204)
def update_placement(home_id: str, id: str, body: PlacementUpdate) -> None:
    doc = load_inventory(home_id)
    item = next((i for i in doc.items if i.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    item.placement = body.placement
    save_inventory(home_id, doc)


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


@router.post("/api/homes/{home_id}/inventory/items/{id}/attachments", status_code=201)
async def upload_attachment(home_id: str, id: str, file: UploadFile) -> dict:
    _validate_id(id)
    doc = load_inventory(home_id)
    item = next((i for i in doc.items if i.id == id), None)
    if not item:
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
    if filename not in item.attachments:
        item.attachments.append(filename)
    save_inventory(home_id, doc)
    return {"filename": filename}


@router.get("/api/homes/{home_id}/inventory/items/{id}/attachments/{filename}")
def get_attachment(home_id: str, id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    base = _attachments_dir(home_id, id).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base) + "/") or not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")


@router.delete("/api/homes/{home_id}/inventory/items/{id}/attachments/{filename}", status_code=204)
def remove_attachment(home_id: str, id: str, filename: str) -> None:
    _validate_id(id)
    _validate_filename(filename)
    doc = load_inventory(home_id)
    item = next((i for i in doc.items if i.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    if not delete_attachment(home_id, id, filename):
        raise HTTPException(status_code=404)
    item.attachments = [a for a in item.attachments if a != filename]
    save_inventory(home_id, doc)

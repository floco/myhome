import uuid

from fastapi import APIRouter, Depends, HTTPException

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
    delete_all_attachments,
    load_inventory,
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

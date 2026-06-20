import uuid

from fastapi import APIRouter, HTTPException

from ..models_inventory import (
    InventoryDocument,
    InventoryItem,
    InventoryItemCreate,
    InventoryItemUpdate,
    PlacementUpdate,
)
from ..persistence_inventory import load_inventory, save_inventory

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


@router.put("/api/inventory/items/{id}/placement", status_code=204)
def update_placement(id: str, body: PlacementUpdate) -> None:
    doc = load_inventory()
    item = next((i for i in doc.items if i.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    item.placement = body.placement
    save_inventory(doc)

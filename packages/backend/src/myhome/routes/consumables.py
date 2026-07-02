import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from ..models_consumables import (
    Consumable,
    ConsumableCreate,
    ConsumablePlacementUpdate,
    ConsumableUpdate,
    ConsumableTransaction,
    StockUpdate,
)
from ..persistence_consumables import load_consumables, save_consumables

router = APIRouter()


@router.get("/api/consumables")
def get_consumables():
    return load_consumables()


@router.post("/api/consumables", response_model=Consumable, status_code=201)
def create_consumable(body: ConsumableCreate) -> Consumable:
    doc = load_consumables()
    item = Consumable(id=str(uuid.uuid4()), **body.model_dump())
    doc.consumables.append(item)
    save_consumables(doc)
    return item


@router.put("/api/consumables/{id}", status_code=204)
def update_consumable(id: str, body: ConsumableUpdate) -> None:
    doc = load_consumables()
    item = next((c for c in doc.consumables if c.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    save_consumables(doc)


@router.delete("/api/consumables/{id}", status_code=204)
def delete_consumable(id: str) -> None:
    doc = load_consumables()
    before = len(doc.consumables)
    doc.consumables = [c for c in doc.consumables if c.id != id]
    if len(doc.consumables) == before:
        raise HTTPException(status_code=404)
    doc.transactions = [t for t in doc.transactions if t.consumableId != id]
    save_consumables(doc)


@router.put("/api/consumables/{id}/placement", status_code=204)
def update_placement(id: str, body: ConsumablePlacementUpdate) -> None:
    doc = load_consumables()
    item = next((c for c in doc.consumables if c.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    item.placement = body.placement
    save_consumables(doc)


@router.post("/api/consumables/{id}/stock", status_code=204)
def update_stock(id: str, body: StockUpdate) -> None:
    doc = load_consumables()
    item = next((c for c in doc.consumables if c.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    delta = body.quantity - item.quantity
    item.quantity = body.quantity
    tx = ConsumableTransaction(
        id=str(uuid.uuid4()),
        consumableId=id,
        delta=delta,
        quantityAfter=body.quantity,
        note=body.note,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    doc.transactions.append(tx)
    save_consumables(doc)


@router.delete("/api/consumable-transactions/{id}", status_code=204)
def delete_transaction(id: str) -> None:
    doc = load_consumables()
    before = len(doc.transactions)
    doc.transactions = [t for t in doc.transactions if t.id != id]
    if len(doc.transactions) == before:
        raise HTTPException(status_code=404)
    save_consumables(doc)

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


@router.get("/api/homes/{home_id}/consumables")
def get_consumables(home_id: str):
    return load_consumables(home_id)


@router.post("/api/homes/{home_id}/consumables", response_model=Consumable, status_code=201)
def create_consumable(home_id: str, body: ConsumableCreate) -> Consumable:
    doc = load_consumables(home_id)
    item = Consumable(id=str(uuid.uuid4()), **body.model_dump())
    doc.consumables.append(item)
    save_consumables(home_id, doc)
    return item


@router.put("/api/homes/{home_id}/consumables/{id}", status_code=204)
def update_consumable(home_id: str, id: str, body: ConsumableUpdate) -> None:
    doc = load_consumables(home_id)
    item = next((c for c in doc.consumables if c.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    save_consumables(home_id, doc)


@router.delete("/api/homes/{home_id}/consumables/{id}", status_code=204)
def delete_consumable(home_id: str, id: str) -> None:
    doc = load_consumables(home_id)
    before = len(doc.consumables)
    doc.consumables = [c for c in doc.consumables if c.id != id]
    if len(doc.consumables) == before:
        raise HTTPException(status_code=404)
    doc.transactions = [t for t in doc.transactions if t.consumableId != id]
    save_consumables(home_id, doc)


@router.put("/api/homes/{home_id}/consumables/{id}/placement", status_code=204)
def update_placement(home_id: str, id: str, body: ConsumablePlacementUpdate) -> None:
    doc = load_consumables(home_id)
    item = next((c for c in doc.consumables if c.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    item.placement = body.placement
    save_consumables(home_id, doc)


@router.post("/api/homes/{home_id}/consumables/{id}/stock", status_code=204)
def update_stock(home_id: str, id: str, body: StockUpdate) -> None:
    doc = load_consumables(home_id)
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
    save_consumables(home_id, doc)


@router.delete("/api/homes/{home_id}/consumable-transactions/{id}", status_code=204)
def delete_transaction(home_id: str, id: str) -> None:
    doc = load_consumables(home_id)
    before = len(doc.transactions)
    doc.transactions = [t for t in doc.transactions if t.id != id]
    if len(doc.transactions) == before:
        raise HTTPException(status_code=404)
    save_consumables(home_id, doc)

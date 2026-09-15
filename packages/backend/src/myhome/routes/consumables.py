import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user_id
from ..models_consumables import (
    Consumable,
    ConsumableCreate,
    ConsumablePlacementUpdate,
    ConsumableUpdate,
    ConsumableTransaction,
    StockUpdate,
)
from ..persistence_activity import log_activity
from ..persistence_consumables import (
    load_consumables,
    recompute_consumable_transactions,
    save_consumables,
)
from ..persistence_costs import clear_linked_consumable, load_costs, save_costs

router = APIRouter()


@router.get("/api/homes/{home_id}/consumables")
def get_consumables(home_id: str):
    return load_consumables(home_id)


@router.post("/api/homes/{home_id}/consumables", response_model=Consumable, status_code=201)
def create_consumable(
    home_id: str, body: ConsumableCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Consumable:
    doc = load_consumables(home_id)
    item = Consumable(id=str(uuid.uuid4()), initialQuantity=body.quantity, **body.model_dump())
    doc.consumables.append(item)
    save_consumables(home_id, doc)
    log_activity(home_id, current_user_id, "consumables", "create", item.name, item.id)
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
def delete_consumable(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_consumables(home_id)
    item = next((c for c in doc.consumables if c.id == id), None)
    if item is None:
        raise HTTPException(status_code=404)
    doc.consumables = [c for c in doc.consumables if c.id != id]
    doc.transactions = [t for t in doc.transactions if t.consumableId != id]
    save_consumables(home_id, doc)
    costs_doc = load_costs(home_id)
    clear_linked_consumable(costs_doc, id)
    save_costs(home_id, costs_doc)
    log_activity(home_id, current_user_id, "consumables", "delete", item.name, id)


@router.put("/api/homes/{home_id}/consumables/{id}/placement", status_code=204)
def update_placement(home_id: str, id: str, body: ConsumablePlacementUpdate) -> None:
    doc = load_consumables(home_id)
    item = next((c for c in doc.consumables if c.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    item.placement = body.placement
    save_consumables(home_id, doc)


@router.post("/api/homes/{home_id}/consumables/{id}/stock", status_code=204)
def update_stock(
    home_id: str, id: str, body: StockUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_consumables(home_id)
    item = next((c for c in doc.consumables if c.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    doc.transactions.append(ConsumableTransaction(
        id=str(uuid.uuid4()),
        consumableId=id,
        delta=0.0,
        quantityAfter=body.quantity,
        note=body.note,
        timestamp=datetime.now(timezone.utc).isoformat(),
    ))
    recompute_consumable_transactions(doc, id)
    save_consumables(home_id, doc)
    log_activity(home_id, current_user_id, "consumables", "update", item.name, id)


@router.delete("/api/homes/{home_id}/consumable-transactions/{id}", status_code=204)
def delete_transaction(home_id: str, id: str) -> None:
    doc = load_consumables(home_id)
    tx = next((t for t in doc.transactions if t.id == id), None)
    if tx is None:
        raise HTTPException(status_code=404)
    consumable_id = tx.consumableId
    doc.transactions = [t for t in doc.transactions if t.id != id]
    recompute_consumable_transactions(doc, consumable_id)
    save_consumables(home_id, doc)

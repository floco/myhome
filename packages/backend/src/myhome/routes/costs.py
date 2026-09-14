import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user_id
from ..models_costs import CostEntry, CostEntryCreate, CostEntryUpdate, CostsDocument
from ..persistence_activity import log_activity
from ..persistence_consumables import (
    apply_cost_linked_delta,
    load_consumables,
    reverse_cost_linked_transactions,
    save_consumables,
)
from ..persistence_costs import (
    delete_all_attachments,
    load_costs,
    save_costs,
)

router = APIRouter()


def _cost_label(entry: CostEntry) -> str:
    return entry.notes if entry.notes else f"{entry.totalAmount:g}"


def _entry_date_timestamp(entry_date: str) -> str:
    """Turn a cost entry's `YYYY-MM-DD` date into a full UTC timestamp for its
    linked stock transaction, keeping the current time-of-day so it sorts
    sensibly against other same-day transactions (same approach as chores'
    _resolve_completed_at). Falls back to now if the date is malformed."""
    now = datetime.now(timezone.utc)
    try:
        picked = datetime.strptime(entry_date, "%Y-%m-%d").date()
    except ValueError:
        return now.isoformat()
    return now.replace(year=picked.year, month=picked.month, day=picked.day).isoformat()


def _sync_linked_stock(home_id: str, entry: CostEntry) -> None:
    """Reconcile the consumable stock transaction tied to this cost entry.

    Reverses any previous transaction for this entry, then reapplies one if
    the entry currently has a link and a quantity -- simplest way to handle
    create/update/link-change/unlink without tracking a diff.
    """
    consumables_doc = load_consumables(home_id)
    reverse_cost_linked_transactions(consumables_doc, entry.id)
    if entry.linkedConsumableId and entry.quantity:
        apply_cost_linked_delta(
            consumables_doc, entry.linkedConsumableId, entry.quantity,
            note=f"Cost entry: {_cost_label(entry)}", cost_entry_id=entry.id,
            timestamp=_entry_date_timestamp(entry.date),
        )
    save_consumables(home_id, consumables_doc)


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
    if entry.linkedConsumableId:
        _sync_linked_stock(home_id, entry)
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
    if entry.sourceModule is not None:
        raise HTTPException(status_code=400, detail=f"This entry is synced from {entry.sourceModule} — edit it there instead")
    changed_fields = body.model_dump(exclude_unset=True)
    for field, value in changed_fields.items():
        setattr(entry, field, value)
    save_costs(home_id, doc)
    if "linkedConsumableId" in changed_fields or "quantity" in changed_fields or entry.linkedConsumableId:
        _sync_linked_stock(home_id, entry)
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
    if entry.sourceModule is not None:
        raise HTTPException(status_code=400, detail=f"This entry is synced from {entry.sourceModule} — edit it there instead")
    if entry.linkedConsumableId:
        consumables_doc = load_consumables(home_id)
        reverse_cost_linked_transactions(consumables_doc, id)
        save_consumables(home_id, consumables_doc)
    doc.entries = [e for e in doc.entries if e.id != id]
    save_costs(home_id, doc)
    delete_all_attachments(home_id, id)
    log_activity(home_id, current_user_id, "costs", "delete", _cost_label(entry), id)

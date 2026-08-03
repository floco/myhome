import uuid

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user_id
from ..models_costs import CostEntry, CostEntryCreate, CostEntryUpdate, CostsDocument
from ..persistence_activity import log_activity
from ..persistence_costs import (
    delete_all_attachments,
    load_costs,
    save_costs,
)

router = APIRouter()


def _cost_label(entry: CostEntry) -> str:
    return entry.notes if entry.notes else f"{entry.totalAmount:g}"


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
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    save_costs(home_id, doc)
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
    doc.entries = [e for e in doc.entries if e.id != id]
    save_costs(home_id, doc)
    delete_all_attachments(home_id, id)
    log_activity(home_id, current_user_id, "costs", "delete", _cost_label(entry), id)

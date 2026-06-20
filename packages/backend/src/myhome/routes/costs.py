import uuid
from fastapi import APIRouter, HTTPException
from ..models_costs import CostEntry, CostEntryCreate, CostEntryUpdate, CostsDocument
from ..persistence_costs import load_costs, save_costs

router = APIRouter()


@router.get("/api/costs", response_model=CostsDocument)
def get_costs() -> CostsDocument:
    return load_costs()


@router.post("/api/costs/entries", response_model=CostEntry, status_code=201)
def create_entry(body: CostEntryCreate) -> CostEntry:
    doc = load_costs()
    entry = CostEntry(id=str(uuid.uuid4()), **body.model_dump())
    doc.entries.append(entry)
    save_costs(doc)
    return entry


@router.put("/api/costs/entries/{id}", status_code=204)
def update_entry(id: str, body: CostEntryUpdate) -> None:
    doc = load_costs()
    entry = next((e for e in doc.entries if e.id == id), None)
    if not entry:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    save_costs(doc)


@router.delete("/api/costs/entries/{id}", status_code=204)
def delete_entry(id: str) -> None:
    doc = load_costs()
    before = len(doc.entries)
    doc.entries = [e for e in doc.entries if e.id != id]
    if len(doc.entries) == before:
        raise HTTPException(status_code=404)
    save_costs(doc)

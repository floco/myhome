import uuid

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user_id
from ..models_properties import PropertiesDocument, Property, PropertyCreate, PropertyUpdate
from ..persistence_activity import log_activity
from ..persistence_properties import load_properties, save_properties

router = APIRouter()


@router.get("/api/homes/{home_id}/properties", response_model=PropertiesDocument)
def get_properties(home_id: str) -> PropertiesDocument:
    return load_properties(home_id)


@router.post("/api/homes/{home_id}/properties", response_model=Property, status_code=201)
def create_property(
    home_id: str, body: PropertyCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Property:
    doc = load_properties(home_id)
    item = Property(id=str(uuid.uuid4()), **body.model_dump())
    doc.properties.append(item)
    save_properties(home_id, doc)
    log_activity(home_id, current_user_id, "properties", "create", item.name, item.id)
    return item


@router.put("/api/homes/{home_id}/properties/{id}", status_code=204)
def update_property(
    home_id: str, id: str, body: PropertyUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_properties(home_id)
    item = next((p for p in doc.properties if p.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    save_properties(home_id, doc)
    log_activity(home_id, current_user_id, "properties", "update", item.name, id)


@router.delete("/api/homes/{home_id}/properties/{id}", status_code=204)
def delete_property(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_properties(home_id)
    item = next((p for p in doc.properties if p.id == id), None)
    if item is None:
        raise HTTPException(status_code=404)
    doc.properties = [p for p in doc.properties if p.id != id]
    save_properties(home_id, doc)
    log_activity(home_id, current_user_id, "properties", "delete", item.name, id)

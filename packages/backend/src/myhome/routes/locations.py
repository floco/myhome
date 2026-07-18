import uuid

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user_id
from ..models_locations import (
    Location,
    LocationCreate,
    LocationCriterion,
    LocationCriterionCreate,
    LocationCriterionUpdate,
    LocationRating,
    LocationUpdate,
    RatingUpdate,
    ReorderRequest,
)
from ..persistence_activity import log_activity
from ..persistence_locations import load_locations, save_locations

router = APIRouter()


@router.get("/api/homes/{home_id}/locations")
def get_locations(home_id: str):
    return load_locations(home_id)


# --- criteria ---

@router.post("/api/homes/{home_id}/locations/criteria", response_model=LocationCriterion, status_code=201)
def create_criterion(
    home_id: str, body: LocationCriterionCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> LocationCriterion:
    doc = load_locations(home_id)
    item = LocationCriterion(id=str(uuid.uuid4()), **body.model_dump())
    doc.criteria.append(item)
    save_locations(home_id, doc)
    log_activity(home_id, current_user_id, "locations", "create", item.name, item.id)
    return item


@router.put("/api/homes/{home_id}/locations/criteria/reorder", status_code=204)
def reorder_criteria(home_id: str, body: ReorderRequest) -> None:
    doc = load_locations(home_id)
    by_id = {c.id: c for c in doc.criteria}
    if set(body.orderedIds) != set(by_id.keys()):
        raise HTTPException(status_code=400, detail="orderedIds must match existing criterion ids")
    doc.criteria = [by_id[i] for i in body.orderedIds]
    save_locations(home_id, doc)


@router.put("/api/homes/{home_id}/locations/criteria/{id}", status_code=204)
def update_criterion(home_id: str, id: str, body: LocationCriterionUpdate) -> None:
    doc = load_locations(home_id)
    item = next((c for c in doc.criteria if c.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    save_locations(home_id, doc)


@router.delete("/api/homes/{home_id}/locations/criteria/{id}", status_code=204)
def delete_criterion(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_locations(home_id)
    item = next((c for c in doc.criteria if c.id == id), None)
    if item is None:
        raise HTTPException(status_code=404)
    doc.criteria = [c for c in doc.criteria if c.id != id]
    doc.ratings = [r for r in doc.ratings if r.criterionId != id]
    save_locations(home_id, doc)
    log_activity(home_id, current_user_id, "locations", "delete", item.name, id)


# --- locations ---

@router.post("/api/homes/{home_id}/locations/locations", response_model=Location, status_code=201)
def create_location(
    home_id: str, body: LocationCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Location:
    doc = load_locations(home_id)
    item = Location(id=str(uuid.uuid4()), **body.model_dump())
    doc.locations.append(item)
    save_locations(home_id, doc)
    log_activity(home_id, current_user_id, "locations", "create", item.name, item.id)
    return item


@router.put("/api/homes/{home_id}/locations/locations/reorder", status_code=204)
def reorder_locations(home_id: str, body: ReorderRequest) -> None:
    doc = load_locations(home_id)
    by_id = {l.id: l for l in doc.locations}
    if set(body.orderedIds) != set(by_id.keys()):
        raise HTTPException(status_code=400, detail="orderedIds must match existing location ids")
    doc.locations = [by_id[i] for i in body.orderedIds]
    save_locations(home_id, doc)


@router.put("/api/homes/{home_id}/locations/locations/{id}", status_code=204)
def update_location(home_id: str, id: str, body: LocationUpdate) -> None:
    doc = load_locations(home_id)
    item = next((l for l in doc.locations if l.id == id), None)
    if not item:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    save_locations(home_id, doc)


@router.delete("/api/homes/{home_id}/locations/locations/{id}", status_code=204)
def delete_location(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_locations(home_id)
    item = next((l for l in doc.locations if l.id == id), None)
    if item is None:
        raise HTTPException(status_code=404)
    doc.locations = [l for l in doc.locations if l.id != id]
    doc.ratings = [r for r in doc.ratings if r.locationId != id]
    save_locations(home_id, doc)
    log_activity(home_id, current_user_id, "locations", "delete", item.name, id)


# --- ratings ---

@router.put("/api/homes/{home_id}/locations/ratings/{location_id}/{criterion_id}", status_code=204)
def upsert_rating(home_id: str, location_id: str, criterion_id: str, body: RatingUpdate) -> None:
    doc = load_locations(home_id)
    if not any(l.id == location_id for l in doc.locations):
        raise HTTPException(status_code=404, detail="Unknown location_id")
    if not any(c.id == criterion_id for c in doc.criteria):
        raise HTTPException(status_code=404, detail="Unknown criterion_id")
    doc.ratings = [r for r in doc.ratings if not (r.locationId == location_id and r.criterionId == criterion_id)]
    doc.ratings.append(LocationRating(locationId=location_id, criterionId=criterion_id, score=body.score, note=body.note))
    save_locations(home_id, doc)


@router.delete("/api/homes/{home_id}/locations/ratings/{location_id}/{criterion_id}", status_code=204)
def clear_rating(home_id: str, location_id: str, criterion_id: str) -> None:
    doc = load_locations(home_id)
    before = len(doc.ratings)
    doc.ratings = [r for r in doc.ratings if not (r.locationId == location_id and r.criterionId == criterion_id)]
    if len(doc.ratings) == before:
        raise HTTPException(status_code=404)
    save_locations(home_id, doc)

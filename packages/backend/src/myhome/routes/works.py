import uuid

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user_id
from ..models_works import Work, WorkCreate, WorkPlacement, WorkUpdate, WorksDocument
from ..persistence_activity import log_activity
from ..persistence_works import (
    delete_all_attachments,
    load_works,
    save_works,
)

router = APIRouter()


@router.get("/api/homes/{home_id}/works", response_model=WorksDocument)
def get_works(home_id: str) -> WorksDocument:
    return load_works(home_id)


@router.post("/api/homes/{home_id}/works", response_model=Work, status_code=201)
def create_work(
    home_id: str, body: WorkCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Work:
    doc = load_works(home_id)
    work = Work(id=str(uuid.uuid4()), **body.model_dump())
    doc.works.append(work)
    save_works(home_id, doc)
    log_activity(home_id, current_user_id, "works", "create", work.title, work.id)
    return work


@router.put("/api/homes/{home_id}/works/{id}", status_code=204)
def update_work(
    home_id: str, id: str, body: WorkUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_works(home_id)
    work = next((w for w in doc.works if w.id == id), None)
    if not work:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(work, field, value)
    save_works(home_id, doc)
    log_activity(home_id, current_user_id, "works", "update", work.title, id)


@router.delete("/api/homes/{home_id}/works/{id}", status_code=204)
def delete_work(
    home_id: str, id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_works(home_id)
    work = next((w for w in doc.works if w.id == id), None)
    if work is None:
        raise HTTPException(status_code=404)
    doc.works = [w for w in doc.works if w.id != id]
    save_works(home_id, doc)
    delete_all_attachments(home_id, id)
    log_activity(home_id, current_user_id, "works", "delete", work.title, id)


@router.put("/api/homes/{home_id}/works/{id}/placement", status_code=204)
def set_placement(home_id: str, id: str, body: WorkPlacement) -> None:
    doc = load_works(home_id)
    work = next((w for w in doc.works if w.id == id), None)
    if not work:
        raise HTTPException(status_code=404)
    work.placement = body
    save_works(home_id, doc)


@router.delete("/api/homes/{home_id}/works/{id}/placement", status_code=204)
def clear_placement(home_id: str, id: str) -> None:
    doc = load_works(home_id)
    work = next((w for w in doc.works if w.id == id), None)
    if not work:
        raise HTTPException(status_code=404)
    work.placement = None
    save_works(home_id, doc)

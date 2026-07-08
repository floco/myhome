import mimetypes
import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..deps import get_current_user_id
from ..models_works import Work, WorkCreate, WorkPlacement, WorkUpdate, WorksDocument
from ..persistence_activity import log_activity
from ..persistence_works import (
    _attachments_dir,
    delete_all_attachments,
    delete_attachment,
    generate_pdf_thumbnail,
    get_attachment_path,
    load_works,
    save_attachment,
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


_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"


_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _validate_id(work_id: str) -> None:
    if not _ID_RE.fullmatch(work_id):
        raise HTTPException(status_code=400, detail="Invalid id")


def _validate_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


@router.post("/api/homes/{home_id}/works/{id}/attachments", status_code=201)
async def upload_attachment(home_id: str, id: str, file: UploadFile) -> dict:
    _validate_id(id)
    doc = load_works(home_id)
    work = next((w for w in doc.works if w.id == id), None)
    if not work:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    ext = os.path.splitext(original)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(home_id, id, filename, data)
    if ext == ".pdf":
        pdf_path = get_attachment_path(home_id, id, filename)
        thumb_path = pdf_path.parent / (filename + ".thumb.jpg")
        generate_pdf_thumbnail(pdf_path, thumb_path)
    if filename not in work.attachments:
        work.attachments.append(filename)
    save_works(home_id, doc)
    return {"filename": filename}


@router.get("/api/homes/{home_id}/works/{id}/attachments/{filename}")
def get_attachment(home_id: str, id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    base = _attachments_dir(home_id, id).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base) + "/") or not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", filename=filename)


@router.delete("/api/homes/{home_id}/works/{id}/attachments/{filename}", status_code=204)
def remove_attachment(home_id: str, id: str, filename: str) -> None:
    _validate_id(id)
    _validate_filename(filename)
    doc = load_works(home_id)
    work = next((w for w in doc.works if w.id == id), None)
    if not work:
        raise HTTPException(status_code=404)
    if not delete_attachment(home_id, id, filename):
        raise HTTPException(status_code=404)
    work.attachments = [a for a in work.attachments if a != filename]
    save_works(home_id, doc)


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

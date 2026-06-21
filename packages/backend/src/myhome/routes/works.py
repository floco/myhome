import re
import uuid

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..models_works import Work, WorkCreate, WorkPlacement, WorkUpdate, WorksDocument
from ..persistence_works import (
    _attachments_dir,
    delete_all_attachments,
    delete_attachment,
    get_attachment_path,
    load_works,
    save_attachment,
    save_works,
)

router = APIRouter()


@router.get("/api/works", response_model=WorksDocument)
def get_works() -> WorksDocument:
    return load_works()


@router.post("/api/works", response_model=Work, status_code=201)
def create_work(body: WorkCreate) -> Work:
    doc = load_works()
    work = Work(id=str(uuid.uuid4()), **body.model_dump())
    doc.works.append(work)
    save_works(doc)
    return work


@router.put("/api/works/{id}", status_code=204)
def update_work(id: str, body: WorkUpdate) -> None:
    doc = load_works()
    work = next((w for w in doc.works if w.id == id), None)
    if not work:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(work, field, value)
    save_works(doc)


@router.delete("/api/works/{id}", status_code=204)
def delete_work(id: str) -> None:
    doc = load_works()
    before = len(doc.works)
    doc.works = [w for w in doc.works if w.id != id]
    if len(doc.works) == before:
        raise HTTPException(status_code=404)
    save_works(doc)
    delete_all_attachments(id)


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    if not name.lower().endswith(".pdf"):
        name = name + ".pdf"
    return name or "attachment.pdf"


_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _validate_id(work_id: str) -> None:
    if not _ID_RE.fullmatch(work_id):
        raise HTTPException(status_code=400, detail="Invalid id")


def _validate_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


@router.post("/api/works/{id}/attachments", status_code=201)
async def upload_attachment(id: str, file: UploadFile) -> dict:
    _validate_id(id)
    doc = load_works()
    work = next((w for w in doc.works if w.id == id), None)
    if not work:
        raise HTTPException(status_code=404)
    original = file.filename or ""
    content_type = file.content_type or ""
    if content_type not in ("application/pdf", "application/octet-stream") and not original.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(id, filename, data)
    if filename not in work.attachments:
        work.attachments.append(filename)
    save_works(doc)
    return {"filename": filename}


@router.get("/api/works/{id}/attachments/{filename}")
def get_attachment(id: str, filename: str) -> FileResponse:
    _validate_id(id)
    _validate_filename(filename)
    base = _attachments_dir(id).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base) + "/") or not path.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(str(path), media_type="application/pdf", filename=filename)


@router.delete("/api/works/{id}/attachments/{filename}", status_code=204)
def remove_attachment(id: str, filename: str) -> None:
    _validate_id(id)
    _validate_filename(filename)
    doc = load_works()
    work = next((w for w in doc.works if w.id == id), None)
    if not work:
        raise HTTPException(status_code=404)
    if not delete_attachment(id, filename):
        raise HTTPException(status_code=404)
    work.attachments = [a for a in work.attachments if a != filename]
    save_works(doc)


@router.put("/api/works/{id}/placement", status_code=204)
def set_placement(id: str, body: WorkPlacement) -> None:
    doc = load_works()
    work = next((w for w in doc.works if w.id == id), None)
    if not work:
        raise HTTPException(status_code=404)
    work.placement = body
    save_works(doc)


@router.delete("/api/works/{id}/placement", status_code=204)
def clear_placement(id: str) -> None:
    doc = load_works()
    work = next((w for w in doc.works if w.id == id), None)
    if not work:
        raise HTTPException(status_code=404)
    work.placement = None
    save_works(doc)

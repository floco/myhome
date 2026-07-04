import mimetypes
import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..models_chores import (
    Assignment,
    AssignmentCreate,
    AssignmentUpdate,
    Chore,
    ChoreCreate,
    ChoreDocument,
    ChoreUpdate,
    CompleteRequest,
    CompletionRecord,
    ImportRequest,
    ImportResponse,
)
from ..chore_scheduling import next_due_from_schedule
from ..persistence_chores import (
    _attachments_dir,
    delete_all_attachments,
    delete_attachment,
    generate_pdf_thumbnail,
    load_chores,
    save_attachment,
    save_chores,
)

router = APIRouter()

_DONETICK_BASE = os.environ.get("DONETICK_URL", "https://chores.casa.mutualis.com")
_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _validate_id(chore_id: str) -> None:
    if not _ID_RE.fullmatch(chore_id):
        raise HTTPException(status_code=400, detail="Invalid id")


def _validate_filename(filename: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename) or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


def _sanitise_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "attachment"

UNIT_DAYS: dict[str, float] = {"days": 1, "weeks": 7, "months": 30, "years": 365}


def _period_days(chore: dict) -> float:
    freq: int = chore["frequency"]
    freq_type: str = chore["frequencyType"]
    meta: dict = chore.get("frequencyMetadata") or {}
    unit: str = meta.get("unit", "days")
    if freq_type == "weekly":
        return freq * 7.0
    elif freq_type == "interval":
        return freq * UNIT_DAYS.get(unit, 1)
    elif freq_type == "yearly":
        return freq * 365.0
    elif freq_type == "day_of_the_month":
        return 30.0
    return 30.0


def _extract_emoji(name: str) -> str:
    name = name.strip()
    result: list[str] = []
    for ch in name:
        cp = ord(ch)
        if (0x2600 <= cp <= 0x27BF or
                0x1F000 <= cp <= 0x1FFFF or
                cp == 0xFE0F or
                cp == 0x200D):
            result.append(ch)
        elif result:
            break
    return "".join(result).strip() or "📋"


# GET must come before /import and /{id} routes - FastAPI matches in definition order
@router.get("/api/homes/{home_id}/chores", response_model=ChoreDocument)
def get_chores(home_id: str) -> ChoreDocument:
    return load_chores(home_id)


# CRITICAL: /import MUST be defined before /{chore_id}
# so FastAPI does not try to match "import" as a chore ID.
@router.post("/api/homes/{home_id}/chores/import", response_model=ImportResponse)
async def import_from_donetick(home_id: str, body: ImportRequest) -> ImportResponse:
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            url = f"{_DONETICK_BASE}/api/v1/chores/"
            resp = await client.get(
                url,
                headers={"secretkey": body.token},
                timeout=10.0,
            )
            resp.raise_for_status()
            raw_chores: list[dict] = resp.json().get("res", [])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Donetick error: {exc}") from exc

    doc = load_chores(home_id)
    existing_ids = {c.donetickId for c in doc.chores if c.donetickId is not None}
    imported = 0

    for rc in raw_chores:
        if rc["id"] in existing_ids:
            continue
        raw_due = rc.get("nextDueDate") or ""
        next_due = raw_due if raw_due else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        doc.chores.append(
            Chore(
                id=str(uuid.uuid4()),
                donetickId=rc["id"],
                name=rc["name"].strip(),
                emoji=_extract_emoji(rc["name"]),
                periodDays=_period_days(rc),
                frequencyType=rc["frequencyType"],
                frequency=rc["frequency"],
                frequencyMetadata=rc.get("frequencyMetadata") or {},
                nextDueDate=next_due,
                description="",
            )
        )
        imported += 1

    save_chores(home_id, doc)
    return ImportResponse(imported=imported)


@router.post("/api/homes/{home_id}/chores", response_model=Chore, status_code=201)
def create_chore(home_id: str, body: ChoreCreate) -> Chore:
    doc = load_chores(home_id)
    data = body.model_dump()
    if data["frequency"] == 0:
        data["frequency"] = max(1, round(data["periodDays"]))
        data["frequencyMetadata"] = {"unit": "days"}
    chore = Chore(id=str(uuid.uuid4()), **data)
    doc.chores.append(chore)
    save_chores(home_id, doc)
    return chore


@router.put("/api/homes/{home_id}/chores/{chore_id}", status_code=204)
def update_chore(home_id: str, chore_id: str, body: ChoreUpdate) -> None:
    doc = load_chores(home_id)
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(chore, field, value)
    save_chores(home_id, doc)


@router.delete("/api/homes/{home_id}/chores/{chore_id}", status_code=204)
def delete_chore(home_id: str, chore_id: str) -> None:
    doc = load_chores(home_id)
    if not any(c.id == chore_id for c in doc.chores):
        raise HTTPException(status_code=404, detail="Chore not found")
    doc.chores = [c for c in doc.chores if c.id != chore_id]
    doc.assignments = [a for a in doc.assignments if a.choreId != chore_id]
    save_chores(home_id, doc)
    delete_all_attachments(home_id, chore_id)


@router.post("/api/homes/{home_id}/chores/{chore_id}/complete", response_model=Chore)
def complete_chore(home_id: str, chore_id: str, body: CompleteRequest | None = None) -> Chore:
    doc = load_chores(home_id)
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    notes = body.notes if body else ""
    now = datetime.now(timezone.utc)
    if chore.scheduleFromDue and chore.nextDueDate:
        try:
            from_dt = datetime.fromisoformat(chore.nextDueDate.replace("Z", "+00:00"))
        except ValueError:
            from_dt = now
    else:
        from_dt = now
    next_due = next_due_from_schedule(chore, from_dt)
    next_due_str = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    doc.completions.append(CompletionRecord(
        id=str(uuid.uuid4()),
        choreId=chore_id,
        completedAt=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        scheduledDue=chore.nextDueDate,
        notes=notes,
    ))
    for a in doc.assignments:
        if a.choreId == chore_id:
            a.nextDueDate = next_due_str
    chore.nextDueDate = next_due_str
    save_chores(home_id, doc)
    return chore


# --- Chore attachment routes ---

@router.post("/api/homes/{home_id}/chores/{chore_id}/attachments", status_code=201)
async def upload_chore_attachment(home_id: str, chore_id: str, file: UploadFile) -> dict:
    _validate_id(chore_id)
    doc = load_chores(home_id)
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    original = file.filename or ""
    ext = os.path.splitext(original.lower())[1]
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not supported")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(home_id, chore_id, filename, data)
    if ext == ".pdf":
        generate_pdf_thumbnail(
            _attachments_dir(home_id, chore_id) / filename,
            _attachments_dir(home_id, chore_id) / (filename + ".thumb.jpg"),
        )
    if filename not in chore.attachments:
        chore.attachments.append(filename)
    save_chores(home_id, doc)
    return {"filename": filename}


@router.get("/api/homes/{home_id}/chores/{chore_id}/attachments/{filename}")
def get_chore_attachment(home_id: str, chore_id: str, filename: str) -> FileResponse:
    _validate_id(chore_id)
    _validate_filename(filename)
    base = _attachments_dir(home_id, chore_id).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base) + "/") or not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")


@router.delete("/api/homes/{home_id}/chores/{chore_id}/attachments/{filename}", status_code=204)
def delete_chore_attachment(home_id: str, chore_id: str, filename: str) -> None:
    _validate_id(chore_id)
    _validate_filename(filename)
    doc = load_chores(home_id)
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    if not delete_attachment(home_id, chore_id, filename):
        raise HTTPException(status_code=404)
    chore.attachments = [a for a in chore.attachments if a != filename]
    save_chores(home_id, doc)


# --- Assignment routes ---

@router.post("/api/homes/{home_id}/assignments", response_model=Assignment, status_code=201)
def create_assignment(home_id: str, body: AssignmentCreate) -> Assignment:
    doc = load_chores(home_id)
    chore = next((c for c in doc.chores if c.id == body.choreId), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    next_due = body.nextDueDate or chore.nextDueDate
    assignment = Assignment(
        id=str(uuid.uuid4()),
        choreId=body.choreId,
        roomId=body.roomId,
        position=body.position,
        nextDueDate=next_due,
    )
    doc.assignments.append(assignment)
    save_chores(home_id, doc)
    return assignment


@router.post("/api/homes/{home_id}/assignments/{assignment_id}/complete", response_model=Assignment)
def complete_assignment(home_id: str, assignment_id: str, body: CompleteRequest | None = None) -> Assignment:
    doc = load_chores(home_id)
    assignment = next((a for a in doc.assignments if a.id == assignment_id), None)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    chore = next((c for c in doc.chores if c.id == assignment.choreId), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    notes = body.notes if body else ""
    now = datetime.now(timezone.utc)
    if chore.scheduleFromDue and assignment.nextDueDate:
        try:
            from_dt = datetime.fromisoformat(assignment.nextDueDate.replace("Z", "+00:00"))
        except ValueError:
            from_dt = now
    else:
        from_dt = now
    next_due = next_due_from_schedule(chore, from_dt)
    doc.completions.append(CompletionRecord(
        id=str(uuid.uuid4()),
        choreId=chore.id,
        assignmentId=assignment_id,
        completedAt=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        scheduledDue=assignment.nextDueDate,
        notes=notes,
    ))
    assignment.nextDueDate = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    save_chores(home_id, doc)
    return assignment


@router.put("/api/homes/{home_id}/assignments/{assignment_id}", status_code=204)
def update_assignment(home_id: str, assignment_id: str, body: AssignmentUpdate) -> None:
    doc = load_chores(home_id)
    assignment = next((a for a in doc.assignments if a.id == assignment_id), None)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if body.position is not None:
        assignment.position = body.position
    if body.nextDueDate is not None:
        assignment.nextDueDate = body.nextDueDate
    save_chores(home_id, doc)


@router.delete("/api/homes/{home_id}/assignments/{assignment_id}", status_code=204)
def delete_assignment(home_id: str, assignment_id: str) -> None:
    doc = load_chores(home_id)
    if not any(a.id == assignment_id for a in doc.assignments):
        raise HTTPException(status_code=404, detail="Assignment not found")
    doc.assignments = [a for a in doc.assignments if a.id != assignment_id]
    save_chores(home_id, doc)


@router.delete("/api/homes/{home_id}/completions/{completion_id}", status_code=204)
def delete_completion(home_id: str, completion_id: str) -> None:
    doc = load_chores(home_id)
    if not any(r.id == completion_id for r in doc.completions):
        raise HTTPException(status_code=404, detail="Completion not found")
    doc.completions = [r for r in doc.completions if r.id != completion_id]
    save_chores(home_id, doc)

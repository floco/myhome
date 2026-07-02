import calendar
import mimetypes
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

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


def _add_months(dt: datetime, months: int) -> datetime:
    total = dt.month - 1 + months
    year = dt.year + total // 12
    month = total % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _add_years(dt: datetime, years: int) -> datetime:
    try:
        return dt.replace(year=dt.year + years)
    except ValueError:
        return dt.replace(year=dt.year + years, month=3, day=1)


_WEEKDAY_NAMES: dict[str, int] = {
    "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4,
    "friday": 5, "saturday": 6, "sunday": 7,
    "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7,
}


def _to_weekday_num(d: object) -> int:
    """Convert a Donetick weekday value (int or name string) to a 1-based int."""
    if isinstance(d, str):
        name = d.lower().strip()
        if name in _WEEKDAY_NAMES:
            return _WEEKDAY_NAMES[name]
        return int(name)
    return int(d)


def _next_due_from_schedule(chore: Chore, from_dt: datetime) -> datetime:
    ft = chore.frequencyType
    freq = chore.frequency
    meta: dict = chore.frequencyMetadata or {}
    unit = meta.get("unit", "days")
    if ft == "day_of_the_month":
        allowed_months: set[int] = set(meta.get("months") or range(1, 13))
        next_m = _add_months(from_dt.replace(day=1), 1)
        for _ in range(12):
            if next_m.month in allowed_months:
                break
            next_m = _add_months(next_m, 1)
        day = min(freq, calendar.monthrange(next_m.year, next_m.month)[1])
        return next_m.replace(day=day)
    if ft == "days_of_the_week":
        days = sorted((_to_weekday_num(d) - 1) % 7 for d in (meta.get("days") or []))
        if not days:
            return from_dt + timedelta(weeks=1)
        wd = from_dt.weekday()
        for d in days:
            if d > wd:
                return from_dt + timedelta(days=d - wd)
        return from_dt + timedelta(days=7 - wd + days[0])
    if ft == "weekly":
        return from_dt + timedelta(weeks=freq)
    if ft in ("monthly", "month"):
        return _add_months(from_dt, freq)
    if ft in ("yearly", "year"):
        return _add_years(from_dt, freq)
    if ft == "interval":
        if unit == "years":
            return _add_years(from_dt, freq)
        if unit == "months":
            return _add_months(from_dt, freq)
        if unit == "weeks":
            return from_dt + timedelta(weeks=freq)
        return from_dt + timedelta(days=freq)
    return from_dt + timedelta(days=chore.periodDays)


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
@router.get("/api/chores", response_model=ChoreDocument)
def get_chores() -> ChoreDocument:
    return load_chores()


# CRITICAL: /api/chores/import MUST be defined before /api/chores/{chore_id}
# so FastAPI does not try to match "import" as a chore ID.
@router.post("/api/chores/import", response_model=ImportResponse)
async def import_from_donetick(body: ImportRequest) -> ImportResponse:
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

    doc = load_chores()
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

    save_chores(doc)
    return ImportResponse(imported=imported)


@router.post("/api/chores", response_model=Chore, status_code=201)
def create_chore(body: ChoreCreate) -> Chore:
    doc = load_chores()
    data = body.model_dump()
    if data["frequency"] == 0:
        data["frequency"] = max(1, round(data["periodDays"]))
        data["frequencyMetadata"] = {"unit": "days"}
    chore = Chore(id=str(uuid.uuid4()), **data)
    doc.chores.append(chore)
    save_chores(doc)
    return chore


@router.put("/api/chores/{chore_id}", status_code=204)
def update_chore(chore_id: str, body: ChoreUpdate) -> None:
    doc = load_chores()
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(chore, field, value)
    save_chores(doc)


@router.delete("/api/chores/{chore_id}", status_code=204)
def delete_chore(chore_id: str) -> None:
    doc = load_chores()
    if not any(c.id == chore_id for c in doc.chores):
        raise HTTPException(status_code=404, detail="Chore not found")
    doc.chores = [c for c in doc.chores if c.id != chore_id]
    doc.assignments = [a for a in doc.assignments if a.choreId != chore_id]
    save_chores(doc)
    delete_all_attachments(chore_id)


@router.post("/api/chores/{chore_id}/complete", response_model=Chore)
def complete_chore(chore_id: str, body: CompleteRequest | None = None) -> Chore:
    doc = load_chores()
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
    next_due = _next_due_from_schedule(chore, from_dt)
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
    save_chores(doc)
    return chore


# --- Chore attachment routes ---

@router.post("/api/chores/{chore_id}/attachments", status_code=201)
async def upload_chore_attachment(chore_id: str, file: UploadFile) -> dict:
    _validate_id(chore_id)
    doc = load_chores()
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    original = file.filename or ""
    ext = os.path.splitext(original.lower())[1]
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not supported")
    filename = _sanitise_filename(original)
    data = await file.read()
    save_attachment(chore_id, filename, data)
    if ext == ".pdf":
        generate_pdf_thumbnail(
            _attachments_dir(chore_id) / filename,
            _attachments_dir(chore_id) / (filename + ".thumb.jpg"),
        )
    if filename not in chore.attachments:
        chore.attachments.append(filename)
    save_chores(doc)
    return {"filename": filename}


@router.get("/api/chores/{chore_id}/attachments/{filename}")
def get_chore_attachment(chore_id: str, filename: str) -> FileResponse:
    _validate_id(chore_id)
    _validate_filename(filename)
    base = _attachments_dir(chore_id).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base) + "/") or not path.is_file():
        raise HTTPException(status_code=404)
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", content_disposition_type="inline")


@router.delete("/api/chores/{chore_id}/attachments/{filename}", status_code=204)
def delete_chore_attachment(chore_id: str, filename: str) -> None:
    _validate_id(chore_id)
    _validate_filename(filename)
    doc = load_chores()
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    if not delete_attachment(chore_id, filename):
        raise HTTPException(status_code=404)
    chore.attachments = [a for a in chore.attachments if a != filename]
    save_chores(doc)


# --- Assignment routes ---

@router.post("/api/assignments", response_model=Assignment, status_code=201)
def create_assignment(body: AssignmentCreate) -> Assignment:
    doc = load_chores()
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
    save_chores(doc)
    return assignment


@router.post("/api/assignments/{assignment_id}/complete", response_model=Assignment)
def complete_assignment(assignment_id: str, body: CompleteRequest | None = None) -> Assignment:
    doc = load_chores()
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
    next_due = _next_due_from_schedule(chore, from_dt)
    doc.completions.append(CompletionRecord(
        id=str(uuid.uuid4()),
        choreId=chore.id,
        assignmentId=assignment_id,
        completedAt=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        scheduledDue=assignment.nextDueDate,
        notes=notes,
    ))
    assignment.nextDueDate = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    save_chores(doc)
    return assignment


@router.put("/api/assignments/{assignment_id}", status_code=204)
def update_assignment(assignment_id: str, body: AssignmentUpdate) -> None:
    doc = load_chores()
    assignment = next((a for a in doc.assignments if a.id == assignment_id), None)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if body.position is not None:
        assignment.position = body.position
    if body.nextDueDate is not None:
        assignment.nextDueDate = body.nextDueDate
    save_chores(doc)


@router.delete("/api/assignments/{assignment_id}", status_code=204)
def delete_assignment(assignment_id: str) -> None:
    doc = load_chores()
    if not any(a.id == assignment_id for a in doc.assignments):
        raise HTTPException(status_code=404, detail="Assignment not found")
    doc.assignments = [a for a in doc.assignments if a.id != assignment_id]
    save_chores(doc)


@router.delete("/api/completions/{completion_id}", status_code=204)
def delete_completion(completion_id: str) -> None:
    doc = load_chores()
    if not any(r.id == completion_id for r in doc.completions):
        raise HTTPException(status_code=404, detail="Completion not found")
    doc.completions = [r for r in doc.completions if r.id != completion_id]
    save_chores(doc)

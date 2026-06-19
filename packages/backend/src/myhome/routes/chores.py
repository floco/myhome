import calendar
import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from ..models_chores import (
    Assignment,
    AssignmentCreate,
    AssignmentUpdate,
    Chore,
    ChoreCreate,
    ChoreDocument,
    ChoreUpdate,
    ImportRequest,
    ImportResponse,
)
from ..persistence_chores import load_chores, save_chores

router = APIRouter()

_DONETICK_BASE = os.environ.get("DONETICK_URL", "https://chores.casa.mutualis.com")

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


def _next_due_from_schedule(chore: Chore, from_dt: datetime) -> datetime:
    ft = chore.frequencyType
    freq = chore.frequency
    meta: dict = chore.frequencyMetadata or {}
    unit = meta.get("unit", "days")
    if ft == "day_of_the_month":
        next_m = _add_months(from_dt.replace(day=1), 1)
        day = min(freq, calendar.monthrange(next_m.year, next_m.month)[1])
        return next_m.replace(day=day)
    if ft == "days_of_the_week":
        days = sorted((d - 1) % 7 for d in (meta.get("days") or []))
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


@router.post("/api/chores/{chore_id}/complete", response_model=Chore)
def complete_chore(chore_id: str) -> Chore:
    doc = load_chores()
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    next_due = _next_due_from_schedule(chore, datetime.now(timezone.utc))
    next_due_str = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    # Advance all assignments for this chore
    for a in doc.assignments:
        if a.choreId == chore_id:
            a.nextDueDate = next_due_str
    # Also advance the chore template date
    chore.nextDueDate = next_due_str
    save_chores(doc)
    return chore


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
def complete_assignment(assignment_id: str) -> Assignment:
    doc = load_chores()
    assignment = next((a for a in doc.assignments if a.id == assignment_id), None)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    chore = next((c for c in doc.chores if c.id == assignment.choreId), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    next_due = _next_due_from_schedule(chore, datetime.now(timezone.utc))
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
    save_chores(doc)


@router.delete("/api/assignments/{assignment_id}", status_code=204)
def delete_assignment(assignment_id: str) -> None:
    doc = load_chores()
    if not any(a.id == assignment_id for a in doc.assignments):
        raise HTTPException(status_code=404, detail="Assignment not found")
    doc.assignments = [a for a in doc.assignments if a.id != assignment_id]
    save_chores(doc)

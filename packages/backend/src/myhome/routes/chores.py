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
            resp = await client.get(
                "https://chores.casa.mutualis.com/api/v1/chores/",
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
        doc.chores.append(
            Chore(
                id=str(uuid.uuid4()),
                donetickId=rc["id"],
                name=rc["name"].strip(),
                emoji=_extract_emoji(rc["name"]),
                periodDays=_period_days(rc),
                nextDueDate=rc.get("nextDueDate", ""),
                description="",
            )
        )
        imported += 1

    save_chores(doc)
    return ImportResponse(imported=imported)


@router.post("/api/chores", response_model=Chore, status_code=201)
def create_chore(body: ChoreCreate) -> Chore:
    doc = load_chores()
    chore = Chore(id=str(uuid.uuid4()), **body.model_dump())
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
    next_due = datetime.now(timezone.utc) + timedelta(days=chore.periodDays)
    chore.nextDueDate = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    save_chores(doc)
    return chore


# --- Assignment routes ---

@router.post("/api/assignments", response_model=Assignment, status_code=201)
def create_assignment(body: AssignmentCreate) -> Assignment:
    doc = load_chores()
    if not any(c.id == body.choreId for c in doc.chores):
        raise HTTPException(status_code=404, detail="Chore not found")
    assignment = Assignment(id=str(uuid.uuid4()), **body.model_dump())
    doc.assignments.append(assignment)
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

import asyncio
import ipaddress
import socket
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException

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
from ..chore_scheduling import next_due_from_schedule, adaptive_period_days
from ..deps import get_current_user_id, require_auth
from ..persistence_activity import log_activity
from ..persistence_chores import (
    delete_all_attachments,
    load_chores,
    save_chores,
)

router = APIRouter()


async def _validate_donetick_url(raw_url: str) -> str:
    """Reject anything that isn't a resolvable http(s) URL pointed at a normal
    host. RFC1918 addresses are allowed on purpose -- self-hosted Donetick
    instances normally live on the same LAN as this add-on -- but loopback,
    link-local (which covers the 169.254.169.254 cloud-metadata address), and
    other special ranges are not legitimate Donetick targets and are the
    classic SSRF probes.
    """
    parsed = urlparse(raw_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Donetick URL must be a valid http(s) URL")
    try:
        addrs = await asyncio.to_thread(socket.getaddrinfo, parsed.hostname, None)
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail=f"Could not resolve Donetick URL: {exc}") from exc
    for _family, _type, _proto, _canon, sockaddr in addrs:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise HTTPException(status_code=400, detail="Donetick URL resolves to a disallowed address")
    return raw_url.rstrip("/")


UNIT_DAYS: dict[str, float] = {"days": 1, "weeks": 7, "months": 30, "years": 365}


def _period_days(chore: dict) -> float:
    # Donetick's own scheduler always advances "daily"/"weekly"/"monthly"/"yearly"
    # chores by exactly 1 unit and ignores `frequency` for them entirely -- that
    # multiplier only applies to the "interval" type (see upstream
    # internal/chore/scheduler.go). A chore imported with a stray `frequency`
    # value on one of these literal types must not be multiplied.
    freq: int = chore["frequency"]
    freq_type: str = chore["frequencyType"]
    meta: dict = chore.get("frequencyMetadata") or {}
    unit: str = meta.get("unit", "days")
    if freq_type == "daily":
        return 1.0
    elif freq_type == "weekly":
        return 7.0
    elif freq_type == "interval":
        return freq * UNIT_DAYS.get(unit, 1)
    elif freq_type in ("monthly", "month"):
        return 30.0
    elif freq_type in ("yearly", "year"):
        return 365.0
    elif freq_type == "day_of_the_month":
        return 30.0
    elif freq_type == "days_of_the_week":
        week_pattern = meta.get("weekPattern")
        if week_pattern == "week_of_month":
            return 30.0
        if week_pattern == "week_of_quarter":
            return 91.0
        return 7.0
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


def _strip_leading_emoji(name: str, emoji: str) -> str:
    """myhome has a dedicated `emoji` field, so drop it from the Donetick name if
    it's a leading icon rather than keeping it duplicated in the title."""
    if emoji and name.startswith(emoji):
        return name[len(emoji):].strip()
    return name


# Donetick ChoreHistoryStatus: 1 = completed (see upstream internal/chore/model).
# Other statuses (started/skipped/pending-approval/rejected/missed/rescheduled)
# aren't a "this chore was done" event, so they're not imported as completions.
_DONETICK_HISTORY_STATUS_COMPLETED = 1


async def _fetch_donetick_history(client, base_url: str, token: str, donetick_chore_id: int) -> list[dict]:
    try:
        resp = await client.get(
            f"{base_url}/api/v1/chores/{donetick_chore_id}/history",
            headers={"secretkey": token},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json().get("res", []) or []
    except Exception:
        # History is a best-effort enrichment of the import -- a chore whose
        # history fetch fails should still be imported, just without history.
        return []


# GET must come before /import and /{id} routes - FastAPI matches in definition order
@router.get("/api/homes/{home_id}/chores", response_model=ChoreDocument)
def get_chores(home_id: str) -> ChoreDocument:
    return load_chores(home_id)


# CRITICAL: /import MUST be defined before /{chore_id}
# so FastAPI does not try to match "import" as a chore ID.
@router.post("/api/homes/{home_id}/chores/import", response_model=ImportResponse)
async def import_from_donetick(
    home_id: str, body: ImportRequest,
    current_user: tuple[str, str] = require_auth("admin"),
) -> ImportResponse:
    import httpx

    stripped_url = body.url.strip()
    if not stripped_url:
        raise HTTPException(status_code=400, detail="Donetick URL is required")
    base_url = await _validate_donetick_url(stripped_url)

    try:
        # httpx.AsyncClient defaults to follow_redirects=False -- a redirect
        # to an internal address would otherwise bypass the resolution check
        # above, since only the original host is validated.
        async with httpx.AsyncClient() as client:
            url = f"{base_url}/api/v1/chores/"
            resp = await client.get(
                url,
                headers={"secretkey": body.token},
                timeout=10.0,
            )
            resp.raise_for_status()
            raw_chores: list[dict] = resp.json().get("res", [])

            doc = load_chores(home_id)
            existing_ids = {c.donetickId for c in doc.chores if c.donetickId is not None}
            imported = 0

            for rc in raw_chores:
                if rc["id"] in existing_ids:
                    continue
                raw_due = rc.get("nextDueDate") or ""
                next_due = raw_due if raw_due else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                raw_name = rc["name"].strip()
                emoji = _extract_emoji(rc["name"])
                chore_id = str(uuid.uuid4())
                doc.chores.append(
                    Chore(
                        id=chore_id,
                        donetickId=rc["id"],
                        name=_strip_leading_emoji(raw_name, emoji),
                        emoji=emoji,
                        periodDays=_period_days(rc),
                        frequencyType=rc["frequencyType"],
                        frequency=rc["frequency"],
                        frequencyMetadata=rc.get("frequencyMetadata") or {},
                        nextDueDate=next_due,
                        description="",
                    )
                )
                imported += 1

                for entry in await _fetch_donetick_history(client, base_url, body.token, rc["id"]):
                    if entry.get("status") != _DONETICK_HISTORY_STATUS_COMPLETED:
                        continue
                    completed_at = entry.get("performedAt")
                    if not completed_at:
                        continue
                    doc.completions.append(
                        CompletionRecord(
                            id=str(uuid.uuid4()),
                            choreId=chore_id,
                            completedAt=completed_at,
                            scheduledDue=entry.get("dueDate") or "",
                            notes=entry.get("notes") or "",
                        )
                    )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Donetick error: {exc}") from exc

    save_chores(home_id, doc)
    return ImportResponse(imported=imported)


@router.post("/api/homes/{home_id}/chores", response_model=Chore, status_code=201)
def create_chore(
    home_id: str, body: ChoreCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Chore:
    doc = load_chores(home_id)
    data = body.model_dump()
    if data["frequency"] == 0:
        data["frequency"] = max(1, round(data["periodDays"]))
        data["frequencyMetadata"] = {"unit": "days"}
    chore = Chore(id=str(uuid.uuid4()), **data)
    doc.chores.append(chore)
    save_chores(home_id, doc)
    log_activity(home_id, current_user_id, "chores", "create", chore.name, chore.id)
    return chore


@router.put("/api/homes/{home_id}/chores/{chore_id}", status_code=204)
def update_chore(
    home_id: str, chore_id: str, body: ChoreUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_chores(home_id)
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(chore, field, value)
    save_chores(home_id, doc)
    log_activity(home_id, current_user_id, "chores", "update", chore.name, chore.id)


@router.delete("/api/homes/{home_id}/chores/{chore_id}", status_code=204)
def delete_chore(
    home_id: str, chore_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    doc = load_chores(home_id)
    chore = next((c for c in doc.chores if c.id == chore_id), None)
    if chore is None:
        raise HTTPException(status_code=404, detail="Chore not found")
    doc.chores = [c for c in doc.chores if c.id != chore_id]
    doc.assignments = [a for a in doc.assignments if a.choreId != chore_id]
    save_chores(home_id, doc)
    delete_all_attachments(home_id, chore_id)
    log_activity(home_id, current_user_id, "chores", "delete", chore.name, chore_id)


@router.post("/api/homes/{home_id}/chores/{chore_id}/complete", response_model=Chore)
def complete_chore(
    home_id: str, chore_id: str, body: CompleteRequest | None = None,
    current_user_id: str = Depends(get_current_user_id),
) -> Chore:
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
    doc.completions.append(CompletionRecord(
        id=str(uuid.uuid4()),
        choreId=chore_id,
        completedAt=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        scheduledDue=chore.nextDueDate,
        notes=notes,
    ))
    completions_for_chore = [c for c in doc.completions if c.choreId == chore_id]
    next_due = next_due_from_schedule(chore, from_dt, completions_for_chore)
    next_due_str = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    if chore.frequencyType == "adaptive":
        chore.periodDays = adaptive_period_days(chore, completions_for_chore)
    for a in doc.assignments:
        if a.choreId == chore_id:
            a.nextDueDate = next_due_str
    chore.nextDueDate = next_due_str
    save_chores(home_id, doc)
    log_activity(home_id, current_user_id, "chores", "complete", chore.name, chore_id)
    return chore


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
def complete_assignment(
    home_id: str, assignment_id: str, body: CompleteRequest | None = None,
    current_user_id: str = Depends(get_current_user_id),
) -> Assignment:
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
    doc.completions.append(CompletionRecord(
        id=str(uuid.uuid4()),
        choreId=chore.id,
        assignmentId=assignment_id,
        completedAt=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        scheduledDue=assignment.nextDueDate,
        notes=notes,
    ))
    completions_for_chore = [c for c in doc.completions if c.choreId == chore.id]
    next_due = next_due_from_schedule(chore, from_dt, completions_for_chore)
    if chore.frequencyType == "adaptive":
        chore.periodDays = adaptive_period_days(chore, completions_for_chore)
    assignment.nextDueDate = next_due.strftime("%Y-%m-%dT%H:%M:%SZ")
    save_chores(home_id, doc)
    log_activity(home_id, current_user_id, "chores", "complete", chore.name, chore.id)
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

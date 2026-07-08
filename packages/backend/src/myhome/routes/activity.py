from fastapi import APIRouter, Query

from ..deps import require_auth
from ..persistence_activity import describe, load_activity_log

router = APIRouter()


@router.get("/api/homes/{home_id}/activity")
def get_activity(
    home_id: str,
    module: str | None = Query(default=None),
    userId: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: tuple[str, str] = require_auth("admin"),
) -> dict:
    entries = load_activity_log(home_id).entries
    if module:
        entries = [e for e in entries if e.module == module]
    if userId:
        entries = [e for e in entries if e.userId == userId]
    if since:
        entries = [e for e in entries if e.timestamp >= since]
    if until:
        entries = [e for e in entries if e.timestamp <= until]
    entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)
    total = len(entries)
    page = entries[offset:offset + limit]
    return {
        "entries": [{**e.model_dump(), "description": describe(e)} for e in page],
        "total": total,
    }

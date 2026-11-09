# packages/backend/src/myhome/property_search_ingest.py
"""Runner protocol: claim a due search, then complete (ingest listings) or fail it."""
from __future__ import annotations

import logging
import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ValidationError

from . import persistence_property_search as ps
from .db import get_engine
from .models_property_search import PropertySearch, PropertySearchRun, PropertySuggestion, SearchUsage
from .persistence_homes import load_homes
from .persistence_properties import load_properties
from .property_search_dedup import fingerprint, url_key
from .property_search_email import send_digest_if_any, send_failure
from .property_search_schedule import STALE_ERROR_PREFIX, MAX_USAGE_LIMIT_RETRIES, is_due, local_now

log = logging.getLogger(__name__)

STALE_AFTER = timedelta(hours=2)
SEEN_IN_CLAIM = 300

# Claims are serialised in-process: myhome runs as a single uvicorn process,
# and SQLite's deferred transactions would otherwise let two concurrent
# claims both read "due" before either writes its running row.
_claim_lock = threading.Lock()


class RunnerComplete(BaseModel):
    listings: list = []
    sitesQueried: list[str] = []
    searchQueries: list[str] = []
    usage: SearchUsage | None = None


class RunnerFail(BaseModel):
    reason: Literal["usage_limit", "error"]
    message: str = ""
    usage: SearchUsage | None = None


class RunNotFound(Exception):
    pass


class RunNotRunning(Exception):
    pass


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None


def _expire_stale_runs(conn, now: datetime) -> None:
    for home_id, run in ps.list_running_runs(conn):
        if now - _parse_dt(run.startedAt) > STALE_AFTER:
            run.status = "failed"
            run.error = f"{STALE_ERROR_PREFIX} no result from the runner after 2 h"
            run.finishedAt = now.isoformat()
            ps.update_run(home_id, run, conn=conn)


def claim_next(now: datetime | None = None) -> dict | None:
    now = now or local_now()
    with _claim_lock, get_engine().begin() as conn:
        _expire_stale_runs(conn, now)
        for home in load_homes().homes:
            for s in ps.list_searches(home.id):
                runs = ps.list_runs(home.id, s.id, limit=50, conn=conn)
                due, slot = is_due(s, runs, now)
                if not due:
                    continue
                run = PropertySearchRun(id=str(uuid.uuid4()), searchId=s.id, slot=slot,
                                        startedAt=now.isoformat(), status="running")
                ps.insert_run(home.id, run, conn=conn)
                if slot.startswith("manual:"):
                    s.runRequestedAt = None
                    ps.update_search(home.id, s, conn=conn)
                return {
                    "runId": run.id, "homeId": home.id, "searchId": s.id, "name": s.name, "prompt": s.prompt,
                    "maxResultsPerRun": s.maxResultsPerRun, "maxListingAgeDays": s.maxListingAgeDays,
                    "language": ps.load_config(home.id).language,
                    "today": now.date().isoformat(), "seen": ps.recent_seen(home.id, SEEN_IN_CLAIM),
                }
    return None


def _load_running(run_id: str) -> tuple[str, PropertySearchRun, PropertySearch]:
    found = ps.find_run(run_id)
    if found is None:
        raise RunNotFound(run_id)
    home_id, run = found
    if run.status != "running":
        raise RunNotRunning(run_id)
    search = ps.get_search(home_id, run.searchId)
    if search is None:
        raise RunNotFound(run_id)
    return home_id, run, search


def _validate_listing(raw, search_id: str, run_id: str, created_at: str) -> PropertySuggestion | None:
    if not isinstance(raw, dict):
        return None
    url = raw.get("listingUrl")
    if not isinstance(url, str) or not url.lower().startswith(("http://", "https://")):
        return None
    data = {k: v for k, v in raw.items() if k in PropertySuggestion.model_fields}
    data.update(id=str(uuid.uuid4()), searchId=search_id, runId=run_id, status="new",
                createdAt=created_at, acceptedPropertyId=None)
    for text_field in ("location", "sourceSite", "reason"):
        if data.get(text_field) is None:
            data.pop(text_field, None)
    try:
        return PropertySuggestion.model_validate(data)
    except ValidationError:
        return None


def complete_run(run_id: str, body: RunnerComplete, now: datetime | None = None) -> dict:
    now = now or local_now()
    home_id, run, search = _load_running(run_id)

    seen_urls, seen_fps = ps.seen_keys(home_id)
    for p in load_properties(home_id).properties:
        if p.listingUrl:
            seen_urls.add(url_key(p.listingUrl))
        fp = fingerprint(p.type, p.price, p.landSize, p.builtSize, p.address)
        if fp:
            seen_fps.add(fp)

    today = _parse_date(run.startedAt) or now.date()
    oldest = today - timedelta(days=search.maxListingAgeDays)
    created_at = now.isoformat()
    fresh: list[PropertySuggestion] = []
    seen_rows: list[tuple[str, str | None]] = []
    duplicates = 0
    for raw in body.listings:
        item = _validate_listing(raw, search.id, run.id, created_at)
        if item is None:
            continue
        published = _parse_date(item.publishedAt)
        if published is not None and published < oldest:
            continue
        key = url_key(item.listingUrl)
        fp = fingerprint(item.type, item.price, item.landSize, item.builtSize, item.location)
        if key in seen_urls or (fp and fp in seen_fps):
            duplicates += 1
            continue
        seen_urls.add(key)
        if fp:
            seen_fps.add(fp)
        if len(fresh) < search.maxResultsPerRun:
            fresh.append(item)
            seen_rows.append((key, fp))

    run.status = "succeeded"
    run.finishedAt = now.isoformat()
    run.sites = body.sitesQueried
    run.searchQueries = body.searchQueries
    run.usage = body.usage
    run.receivedCount = len(body.listings)
    run.newCount = len(fresh)
    run.duplicateCount = duplicates
    search.lastRunAt, search.lastRunStatus, search.lastRunError = run.finishedAt, "succeeded", None
    search.lastRunNew, search.lastRunDuplicates, search.lastRunEmailError = run.newCount, duplicates, None
    with get_engine().begin() as conn:
        ps.insert_suggestions(home_id, fresh, conn=conn)
        ps.add_seen(home_id, seen_rows, conn=conn)
        ps.update_run(home_id, run, conn=conn)
        ps.update_search(home_id, search, conn=conn)

    send_digest_if_any(home_id, search, run, fresh)
    return {"received": run.receivedCount, "new": run.newCount, "duplicates": duplicates}


def fail_run(run_id: str, body: RunnerFail, now: datetime | None = None) -> None:
    now = now or local_now()
    home_id, run, search = _load_running(run_id)
    run.status = "usage_limited" if body.reason == "usage_limit" else "failed"
    run.error = body.message or body.reason
    run.finishedAt = now.isoformat()
    run.usage = body.usage
    search.lastRunAt, search.lastRunStatus, search.lastRunError = run.finishedAt, run.status, run.error
    search.lastRunNew, search.lastRunDuplicates, search.lastRunEmailError = None, None, None
    with get_engine().begin() as conn:
        ps.update_run(home_id, run, conn=conn)
        ps.update_search(home_id, search, conn=conn)

    notify = body.reason == "error"
    if body.reason == "usage_limit":
        limited = [r for r in ps.list_runs(home_id, search.id, limit=50)
                   if r.slot == run.slot and r.status == "usage_limited"]
        notify = len(limited) >= MAX_USAGE_LIMIT_RETRIES
    if notify:
        send_failure(home_id, search, run)

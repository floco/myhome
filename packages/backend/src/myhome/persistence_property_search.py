# packages/backend/src/myhome/persistence_property_search.py
"""DB access for the AI property search tables (all home-scoped)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import get_engine
from .models_property_search import (
    PropertySearch,
    PropertySearchConfig,
    PropertySearchRun,
    PropertySuggestion,
    SearchUsage,
)
from .schema import (
    property_search_config as config_t,
    property_search_runs as runs_t,
    property_searches as searches_t,
    property_seen as seen_t,
    property_suggestions as sugg_t,
)

# ── Searches ────────────────────────────────────────────────────────────────

_SEARCH_COLS = {
    "id": "id", "name": "name", "prompt": "prompt", "enabled": "enabled", "frequency": "frequency",
    "time": "time", "dayOfWeek": "day_of_week", "dayOfMonth": "day_of_month",
    "maxResultsPerRun": "max_results_per_run", "maxListingAgeDays": "max_listing_age_days",
    "createdAt": "created_at", "runRequestedAt": "run_requested_at", "lastRunAt": "last_run_at",
    "lastRunStatus": "last_run_status", "lastRunError": "last_run_error",
    "lastRunNew": "last_run_new", "lastRunDuplicates": "last_run_duplicates",
    "lastRunEmailError": "last_run_email_error",
}


def _search_from_row(r) -> PropertySearch:
    return PropertySearch(**{f: r[c] for f, c in _SEARCH_COLS.items()})


def _search_to_row(home_id: str, s: PropertySearch) -> dict:
    row = {c: getattr(s, f) for f, c in _SEARCH_COLS.items()}
    row["home_id"] = home_id
    return row


def list_searches(home_id: str) -> list[PropertySearch]:
    with get_engine().connect() as conn:
        rows = conn.execute(
            select(searches_t).where(searches_t.c.home_id == home_id).order_by(searches_t.c.created_at, searches_t.c.id)
        ).mappings().all()
    return [_search_from_row(r) for r in rows]


def get_search(home_id: str, search_id: str) -> PropertySearch | None:
    with get_engine().connect() as conn:
        r = conn.execute(
            select(searches_t).where(searches_t.c.home_id == home_id, searches_t.c.id == search_id)
        ).mappings().first()
    return _search_from_row(r) if r else None


def insert_search(home_id: str, s: PropertySearch) -> None:
    with get_engine().begin() as conn:
        conn.execute(searches_t.insert().values(**_search_to_row(home_id, s)))


def update_search(home_id: str, s: PropertySearch, conn=None) -> None:
    stmt = (searches_t.update()
            .where(searches_t.c.home_id == home_id, searches_t.c.id == s.id)
            .values(**_search_to_row(home_id, s)))
    if conn is not None:
        conn.execute(stmt)
        return
    with get_engine().begin() as c:
        c.execute(stmt)


def delete_search(home_id: str, search_id: str) -> bool:
    with get_engine().begin() as conn:
        conn.execute(delete(sugg_t).where(sugg_t.c.home_id == home_id, sugg_t.c.search_id == search_id))
        conn.execute(delete(runs_t).where(runs_t.c.home_id == home_id, runs_t.c.search_id == search_id))
        res = conn.execute(delete(searches_t).where(searches_t.c.home_id == home_id, searches_t.c.id == search_id))
    return res.rowcount > 0


# ── Suggestions ─────────────────────────────────────────────────────────────

_SUGG_COLS = {
    "id": "id", "searchId": "search_id", "runId": "run_id", "title": "title", "type": "type",
    "price": "price", "currency": "currency", "landSize": "land_size", "builtSize": "built_size",
    "bedrooms": "bedrooms", "bathrooms": "bathrooms", "location": "location", "country": "country",
    "region": "region", "city": "city", "sourceSite": "source_site",
    "listingUrl": "listing_url", "imageUrl": "image_url", "publishedAt": "published_at", "reason": "reason",
    "status": "status", "createdAt": "created_at", "acceptedPropertyId": "accepted_property_id",
}


def _sugg_from_row(r) -> PropertySuggestion:
    return PropertySuggestion(**{f: r[c] for f, c in _SUGG_COLS.items()})


def list_suggestions(home_id: str, status: list[str] | None = None) -> list[PropertySuggestion]:
    q = select(sugg_t).where(sugg_t.c.home_id == home_id)
    if status is not None:
        q = q.where(sugg_t.c.status.in_(status))
    q = q.order_by(sugg_t.c.created_at.desc(), sugg_t.c.id)
    with get_engine().connect() as conn:
        rows = conn.execute(q).mappings().all()
    return [_sugg_from_row(r) for r in rows]


def get_suggestion(home_id: str, suggestion_id: str) -> PropertySuggestion | None:
    with get_engine().connect() as conn:
        r = conn.execute(
            select(sugg_t).where(sugg_t.c.home_id == home_id, sugg_t.c.id == suggestion_id)
        ).mappings().first()
    return _sugg_from_row(r) if r else None


def insert_suggestions(home_id: str, items: list[PropertySuggestion], conn=None) -> None:
    if not items:
        return
    rows = [{**{c: getattr(s, f) for f, c in _SUGG_COLS.items()}, "home_id": home_id} for s in items]
    if conn is not None:
        conn.execute(sugg_t.insert(), rows)
        return
    with get_engine().begin() as c:
        c.execute(sugg_t.insert(), rows)


def set_suggestion_status(
    home_id: str, suggestion_id: str, status: str, accepted_property_id: str | None = None,
) -> bool:
    values: dict = {"status": status}
    if accepted_property_id is not None:
        values["accepted_property_id"] = accepted_property_id
    with get_engine().begin() as conn:
        res = conn.execute(
            sugg_t.update().where(sugg_t.c.home_id == home_id, sugg_t.c.id == suggestion_id).values(**values)
        )
    return res.rowcount > 0


def delete_suggestions_older_than(home_id: str, statuses: list[str], cutoff_iso: str) -> int:
    with get_engine().begin() as conn:
        res = conn.execute(delete(sugg_t).where(
            sugg_t.c.home_id == home_id, sugg_t.c.status.in_(statuses), sugg_t.c.created_at < cutoff_iso,
        ))
    return res.rowcount


# ── Seen ledger ─────────────────────────────────────────────────────────────

def seen_keys(home_id: str) -> tuple[set[str], set[str]]:
    with get_engine().connect() as conn:
        rows = conn.execute(select(seen_t.c.url_key, seen_t.c.fingerprint).where(seen_t.c.home_id == home_id)).all()
    return {r[0] for r in rows}, {r[1] for r in rows if r[1]}


def add_seen(home_id: str, rows: list[tuple[str, str | None]], conn=None) -> None:
    if not rows:
        return
    now = datetime.now(timezone.utc).isoformat()
    stmt = sqlite_insert(seen_t).values([
        {"home_id": home_id, "url_key": u, "fingerprint": fp, "first_seen_at": now} for u, fp in rows
    ]).on_conflict_do_nothing(index_elements=[seen_t.c.home_id, seen_t.c.url_key])
    if conn is not None:
        conn.execute(stmt)
        return
    with get_engine().begin() as c:
        c.execute(stmt)


def recent_seen(home_id: str, limit: int = 300) -> list[dict]:
    with get_engine().connect() as conn:
        rows = conn.execute(
            select(sugg_t.c.listing_url, sugg_t.c.title).where(sugg_t.c.home_id == home_id)
            .order_by(sugg_t.c.created_at.desc()).limit(limit)
        ).all()
    return [{"url": r[0], "title": r[1]} for r in rows]


# ── Runs ────────────────────────────────────────────────────────────────────

def _run_from_row(r) -> PropertySearchRun:
    return PropertySearchRun(
        id=r["id"], searchId=r["search_id"], slot=r["slot"], startedAt=r["started_at"],
        finishedAt=r["finished_at"], status=r["status"], error=r["error"], emailError=r["email_error"],
        sites=json.loads(r["sites"]), searchQueries=json.loads(r["search_queries"]),
        usage=SearchUsage.model_validate_json(r["usage"]) if r["usage"] else None,
        receivedCount=r["received_count"], newCount=r["new_count"], duplicateCount=r["duplicate_count"],
    )


def _run_to_row(home_id: str, run: PropertySearchRun) -> dict:
    return {
        "id": run.id, "home_id": home_id, "search_id": run.searchId, "slot": run.slot,
        "started_at": run.startedAt, "finished_at": run.finishedAt, "status": run.status,
        "error": run.error, "email_error": run.emailError, "sites": json.dumps(run.sites),
        "search_queries": json.dumps(run.searchQueries),
        "usage": run.usage.model_dump_json() if run.usage else None,
        "received_count": run.receivedCount, "new_count": run.newCount, "duplicate_count": run.duplicateCount,
    }


def insert_run(home_id: str, run: PropertySearchRun, conn=None) -> None:
    stmt = runs_t.insert().values(**_run_to_row(home_id, run))
    if conn is not None:
        conn.execute(stmt)
        return
    with get_engine().begin() as c:
        c.execute(stmt)


def update_run(home_id: str, run: PropertySearchRun, conn=None) -> None:
    stmt = (runs_t.update().where(runs_t.c.home_id == home_id, runs_t.c.id == run.id)
            .values(**_run_to_row(home_id, run)))
    if conn is not None:
        conn.execute(stmt)
        return
    with get_engine().begin() as c:
        c.execute(stmt)


def get_run(home_id: str, run_id: str) -> PropertySearchRun | None:
    with get_engine().connect() as conn:
        r = conn.execute(select(runs_t).where(runs_t.c.home_id == home_id, runs_t.c.id == run_id)).mappings().first()
    return _run_from_row(r) if r else None


def find_run(run_id: str) -> tuple[str, PropertySearchRun] | None:
    with get_engine().connect() as conn:
        r = conn.execute(select(runs_t).where(runs_t.c.id == run_id)).mappings().first()
    return (r["home_id"], _run_from_row(r)) if r else None


def list_runs(home_id: str, search_id: str, limit: int = 20, conn=None) -> list[PropertySearchRun]:
    q = (select(runs_t).where(runs_t.c.home_id == home_id, runs_t.c.search_id == search_id)
         .order_by(runs_t.c.started_at.desc()).limit(limit))
    if conn is not None:
        return [_run_from_row(r) for r in conn.execute(q).mappings().all()]
    with get_engine().connect() as c:
        return [_run_from_row(r) for r in c.execute(q).mappings().all()]


def list_running_runs(conn) -> list[tuple[str, PropertySearchRun]]:
    rows = conn.execute(select(runs_t).where(runs_t.c.status == "running")).mappings().all()
    return [(r["home_id"], _run_from_row(r)) for r in rows]


def delete_runs_older_than(home_id: str, cutoff_iso: str) -> int:
    with get_engine().begin() as conn:
        res = conn.execute(delete(runs_t).where(runs_t.c.home_id == home_id, runs_t.c.started_at < cutoff_iso))
    return res.rowcount


# ── Config ──────────────────────────────────────────────────────────────────

def load_config(home_id: str) -> PropertySearchConfig:
    with get_engine().connect() as conn:
        r = conn.execute(select(config_t).where(config_t.c.home_id == home_id)).mappings().first()
    if r is None:
        return PropertySearchConfig()
    return PropertySearchConfig(
        retentionDays=r["retention_days"], brevoApiKey=r["brevo_api_key"], senderEmail=r["sender_email"],
        senderName=r["sender_name"], recipients=json.loads(r["recipients"]), appBaseUrl=r["app_base_url"],
        language=r["language"],
    )


def save_config(home_id: str, cfg: PropertySearchConfig) -> None:
    values = {
        "retention_days": cfg.retentionDays, "brevo_api_key": cfg.brevoApiKey, "sender_email": cfg.senderEmail,
        "sender_name": cfg.senderName, "recipients": json.dumps(cfg.recipients), "app_base_url": cfg.appBaseUrl,
        "language": cfg.language,
    }
    stmt = sqlite_insert(config_t).values(home_id=home_id, **values).on_conflict_do_update(
        index_elements=[config_t.c.home_id], set_=values,
    )
    with get_engine().begin() as conn:
        conn.execute(stmt)


# ── Reset ───────────────────────────────────────────────────────────────────

def reset_property_search(home_id: str) -> None:
    with get_engine().begin() as conn:
        for t in (sugg_t, runs_t, seen_t, config_t, searches_t):
            conn.execute(delete(t).where(t.c.home_id == home_id))

# packages/backend/src/myhome/routes/property_search.py
"""AI property search: user-facing routes (searches, suggestions inbox, config)
and the provider-neutral runner API (claim / complete / fail)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ..deps import get_current_user_id, require_auth
from ..models_properties import Property
from ..models_property_search import (
    PropertySearch,
    PropertySearchConfigOut,
    PropertySearchConfigUpdate,
    PropertySearchCreate,
    PropertySearchRun,
    PropertySearchUpdate,
    PropertySuggestion,
)
from ..persistence_activity import log_activity
from ..persistence_properties import load_properties, save_properties
from .. import persistence_property_search as ps
from .. import property_search_email as email
from .. import property_search_ingest as ingest
from ..property_search_schedule import local_now

router = APIRouter()

_INBOX = ["new", "pinned"]


# ── Searches ────────────────────────────────────────────────────────────────

@router.get("/api/homes/{home_id}/property-searches", response_model=list[PropertySearch])
def list_searches(home_id: str) -> list[PropertySearch]:
    return ps.list_searches(home_id)


@router.post("/api/homes/{home_id}/property-searches", response_model=PropertySearch, status_code=201)
def create_search(home_id: str, body: PropertySearchCreate) -> PropertySearch:
    s = PropertySearch(id=str(uuid.uuid4()), createdAt=local_now().isoformat(), **body.model_dump())
    ps.insert_search(home_id, s)
    return s


def _get_search_or_404(home_id: str, search_id: str) -> PropertySearch:
    s = ps.get_search(home_id, search_id)
    if s is None:
        raise HTTPException(status_code=404)
    return s


@router.put("/api/homes/{home_id}/property-searches/{search_id}", status_code=204)
def update_search(home_id: str, search_id: str, body: PropertySearchUpdate) -> None:
    s = _get_search_or_404(home_id, search_id)
    updated = s.model_copy(update=body.model_dump(exclude_unset=True, exclude_none=True))
    ps.update_search(home_id, PropertySearch.model_validate(updated.model_dump()))


@router.delete("/api/homes/{home_id}/property-searches/{search_id}", status_code=204)
def delete_search(home_id: str, search_id: str) -> None:
    if not ps.delete_search(home_id, search_id):
        raise HTTPException(status_code=404)


@router.post("/api/homes/{home_id}/property-searches/{search_id}/run-now", status_code=204)
def run_now(home_id: str, search_id: str) -> None:
    s = _get_search_or_404(home_id, search_id)
    s.runRequestedAt = local_now().isoformat()
    ps.update_search(home_id, s)


@router.get("/api/homes/{home_id}/property-searches/{search_id}/runs", response_model=list[PropertySearchRun])
def list_runs(home_id: str, search_id: str) -> list[PropertySearchRun]:
    _get_search_or_404(home_id, search_id)
    return ps.list_runs(home_id, search_id)


# ── Suggestions ─────────────────────────────────────────────────────────────

@router.get("/api/homes/{home_id}/property-suggestions", response_model=list[PropertySuggestion])
def list_suggestions(home_id: str, status: str = Query(default="new,pinned")) -> list[PropertySuggestion]:
    return ps.list_suggestions(home_id, [x for x in status.split(",") if x])


def _get_inbox_suggestion(home_id: str, suggestion_id: str) -> PropertySuggestion:
    g = ps.get_suggestion(home_id, suggestion_id)
    if g is None:
        raise HTTPException(status_code=404)
    if g.status not in _INBOX:
        raise HTTPException(status_code=409, detail=f"Suggestion already {g.status}")
    return g


@router.post("/api/homes/{home_id}/property-suggestions/{suggestion_id}/accept", response_model=Property, status_code=201)
def accept_suggestion(
    home_id: str, suggestion_id: str, current_user_id: str = Depends(get_current_user_id),
) -> Property:
    g = _get_inbox_suggestion(home_id, suggestion_id)
    notes = f"{g.reason}\n\nSource: {g.sourceSite}" + (f"\nCurrency: {g.currency}" if g.currency else "")
    prop = Property(
        id=str(uuid.uuid4()), name=g.title, emoji="🌳" if g.type == "land" else "🏠",
        type=g.type or "land", status="watching", address=g.location, price=g.price,
        landSize=g.landSize, builtSize=g.builtSize, bedrooms=g.bedrooms, bathrooms=g.bathrooms,
        listingUrl=g.listingUrl, notes=notes.strip(),
    )
    doc = load_properties(home_id)
    doc.properties.append(prop)
    save_properties(home_id, doc)
    ps.set_suggestion_status(home_id, suggestion_id, "accepted", accepted_property_id=prop.id)
    log_activity(home_id, current_user_id, "properties", "create", prop.name, prop.id)
    return prop


@router.post("/api/homes/{home_id}/property-suggestions/{suggestion_id}/reject", status_code=204)
def reject_suggestion(home_id: str, suggestion_id: str) -> None:
    _get_inbox_suggestion(home_id, suggestion_id)
    ps.set_suggestion_status(home_id, suggestion_id, "rejected")


@router.post("/api/homes/{home_id}/property-suggestions/{suggestion_id}/pin", status_code=204)
def toggle_pin(home_id: str, suggestion_id: str) -> None:
    g = _get_inbox_suggestion(home_id, suggestion_id)
    ps.set_suggestion_status(home_id, suggestion_id, "new" if g.status == "pinned" else "pinned")


# ── Config (admin only) ─────────────────────────────────────────────────────

def _config_out(home_id: str) -> PropertySearchConfigOut:
    cfg = ps.load_config(home_id)
    data = cfg.model_dump(exclude={"brevoApiKey"})
    return PropertySearchConfigOut(brevoApiKeySet=bool(cfg.brevoApiKey), **data)


@router.get("/api/homes/{home_id}/property-search-config", response_model=PropertySearchConfigOut)
def get_config(home_id: str, current_user: tuple[str, str] = require_auth("admin")) -> PropertySearchConfigOut:
    return _config_out(home_id)


@router.put("/api/homes/{home_id}/property-search-config", response_model=PropertySearchConfigOut)
def put_config(
    home_id: str, body: PropertySearchConfigUpdate, current_user: tuple[str, str] = require_auth("admin"),
) -> PropertySearchConfigOut:
    cfg = ps.load_config(home_id)
    patch = body.model_dump(exclude_unset=True, exclude_none=True)
    if not patch.get("brevoApiKey"):
        patch.pop("brevoApiKey", None)
    if "recipients" in patch:
        recipients = [r.strip() for r in patch["recipients"] if r.strip()]
        bad = [r for r in recipients if "@" not in r]
        if bad:
            raise HTTPException(status_code=422, detail=f"Invalid recipient(s): {', '.join(bad)}")
        patch["recipients"] = recipients
    for key in ("senderEmail", "senderName", "appBaseUrl", "brevoApiKey"):
        if key in patch:
            patch[key] = patch[key].strip()
    ps.save_config(home_id, cfg.model_copy(update=patch))
    return _config_out(home_id)


@router.post("/api/homes/{home_id}/property-search-config/test-email", status_code=204)
def test_email(home_id: str, current_user: tuple[str, str] = require_auth("admin")) -> None:
    try:
        email.send_test(home_id)
    except email.EmailError as e:
        raise HTTPException(status_code=502, detail=str(e))


# ── Runner API (provider-neutral; Bearer API token with role >= normal) ──────

@router.post("/api/property-search/runner/claim")
def runner_claim(current_user: tuple[str, str] = require_auth("normal")):
    claim = ingest.claim_next()
    if claim is None:
        return Response(status_code=204)
    return claim


@router.post("/api/property-search/runner/runs/{run_id}/complete")
def runner_complete(
    run_id: str, body: ingest.RunnerComplete, current_user: tuple[str, str] = require_auth("normal"),
) -> dict:
    try:
        return ingest.complete_run(run_id, body)
    except ingest.RunNotFound:
        raise HTTPException(status_code=404)
    except ingest.RunNotRunning:
        raise HTTPException(status_code=409, detail="Run is not running")


@router.post("/api/property-search/runner/runs/{run_id}/fail", status_code=204)
def runner_fail(
    run_id: str, body: ingest.RunnerFail, current_user: tuple[str, str] = require_auth("normal"),
) -> None:
    try:
        ingest.fail_run(run_id, body)
    except ingest.RunNotFound:
        raise HTTPException(status_code=404)
    except ingest.RunNotRunning:
        raise HTTPException(status_code=409, detail="Run is not running")

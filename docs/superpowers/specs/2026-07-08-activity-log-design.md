# Unified Activity Timeline / Audit Log — Design Spec

**Date:** 2026-07-08
**Status:** Approved

---

## Overview

A per-home **activity log** capturing "who did what" across all six data
modules (Chores, Works, Costs, Inventory, Consumables, Knowledge Base),
viewable as an admin-only "Activity Log" section in Settings.

- **Actions logged**: create / update / delete for every covered module,
  plus a distinct **complete** action for chore completions.
- **Rich entries**: e.g. *"Alice completed chore 'Take out trash'"*, *"Bob
  added cost entry 'Electricity'"* — not raw request/method logs.
- **Retention**: entries older than 90 days are pruned automatically on
  each write (fixed constant, not user-configurable in v1).
- **Visibility**: admin-only, consistent with the existing Users/MCP/SSO/
  Backup sections in Settings.
- **Extensible by design**: a future module logs activity by adding one
  dependency and one `log_activity(...)` call to its route handlers — no
  changes to the log infrastructure itself.

This closes a real gap found during research: no business route handler
today (chores/works/costs/inventory/consumables/kb) has access to *who* is
calling it — user identity is resolved only in the auth middleware, purely
for permission checks, and is never passed into business logic. This spec
plumbs identity through to the handlers that need it, without re-running
authentication (the middleware has already done that work).

---

## Approach

A shared `log_activity(...)` helper, called explicitly at the end of each
mutating route handler's success path, across all six modules — no
decorator, no auto-logging wrapper, no generic job/event-bus abstraction.
This matches the codebase's existing bias toward simple, explicit,
per-feature code over shared frameworks (the same reasoning that led to two
independent background-scheduler loops for notifications and backups
rather than one generic scheduler).

---

## Data Model

New `packages/backend/src/myhome/models_activity.py`:

```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class ActivityEntry(BaseModel):
    id: str
    timestamp: str  # ISO 8601 UTC
    userId: str
    username: str    # denormalized at write time -- survives username changes or user deletion
    module: Literal["chores", "works", "costs", "inventory", "consumables", "kb"]
    action: Literal["create", "update", "delete", "complete"]
    entityLabel: str  # e.g. chore name, cost description, item name
    refId: str | None = None  # id of the underlying entity, for future deep-linking


class ActivityLogDocument(BaseModel):
    version: int = 1
    entries: list[ActivityEntry] = []
```

New `packages/backend/src/myhome/persistence_activity.py`, following the
same per-home, atomic-tmp-file-rename pattern as every other module:
`{DATA_DIR}/homes/{home_id}/activity_log.json`.

```python
RETENTION_DAYS = 90

def log_activity(
    home_id: str, user_id: str, username: str,
    module: str, action: str, entity_label: str, ref_id: str | None = None,
) -> None:
    doc = load_activity_log(home_id)
    doc.entries.append(ActivityEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        userId=user_id, username=username,
        module=module, action=action, entityLabel=entity_label, refId=ref_id,
    ))
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    doc.entries = [e for e in doc.entries if datetime.fromisoformat(e.timestamp) >= cutoff]
    save_activity_log(home_id, doc)
```

The human-readable description ("completed chore 'Take out trash'") is
**not stored** — it's computed at read time (in the `GET` route) from
`action` + `module` + `entityLabel` via a small verb/noun lookup table:

```python
ACTION_VERBS = {"create": "added", "update": "updated", "delete": "deleted", "complete": "completed"}
MODULE_NOUNS = {
    "chores": "chore", "works": "work", "costs": "cost entry",
    "inventory": "inventory item", "consumables": "consumable", "kb": "KB article",
}

def describe(entry: ActivityEntry) -> str:
    return f"{ACTION_VERBS[entry.action]} {MODULE_NOUNS[entry.module]} '{entry.entityLabel}'"
```

Keeping the stored record compact (module/action/entityLabel rather than a
frozen sentence) means phrasing can change later without rewriting history.

---

## Backend: Identity Plumbing

A lightweight dependency — **not** a re-authentication, since the auth
middleware (`main.py`) has already validated the request and stored
`request.state.user`:

```python
# deps.py
def get_current_user_id(request: Request) -> str:
    user_id, _role = request.state.user
    return user_id
```

Each mutating handler across the six modules adds
`current_user_id: str = Depends(get_current_user_id)` and, immediately
after its existing persistence call succeeds, calls `log_activity(...)`.
Username is resolved via a small helper in `persistence_activity.py`:

```python
def _resolve_username(user_id: str) -> str:
    from .persistence_auth import load_users
    user = next((u for u in load_users().users if u.id == user_id), None)
    return user.username if user else "unknown"
```

**Actions logged per module:**

| Module | Actions |
|---|---|
| Chores | create, update, delete, **complete** (chore or assignment completion) |
| Works | create, update, delete |
| Costs | create, update, delete |
| Inventory | create, update, delete |
| Consumables | create, update (stock change), delete |
| Knowledge Base | create, update, delete |

---

## Backend: Route

```
GET /api/homes/{home_id}/activity?module=&userId=&since=&until=&limit=50&offset=0
```

- Admin-gated via `require_auth("admin")` (matches the log's admin-only
  visibility).
- Returns `{entries: [{...ActivityEntry fields..., description: str}], total: int}`,
  newest-first, filtered by any combination of `module`, `userId`,
  `since`/`until` (ISO date bounds), paginated via `limit`/`offset`.
- `description` is computed per entry at serialization time via `describe()`
  above — not a persisted field.

---

## Frontend

New admin-gated "Activity Log" `<Card>` section in `SettingsPage.svelte`,
following the same pattern as the existing Users/MCP/SSO/Backup sections
(`{#if authStore.user?.role === "admin"}`):

- **Filters**: module `<select>`, user `<select>` (options fetched from the
  existing admin-only `GET /api/auth/users`), date range (from/to `Input`
  fields).
- **List**: paginated (a "Load more" button appending the next page, rather
  than full prev/next pagination controls — simplest given usage is
  scanning recent history, not deep archival browsing), each row showing
  formatted timestamp, username, and description.
- No new store module — local component state fetching directly, matching
  how the Backup/OIDC/MCP sections already work in this file.

---

## Testing

- **Backend unit tests**: `log_activity` writes an entry and prunes entries
  older than 90 days; `describe()` produces the expected sentence for each
  action/module combination.
- **Route tests**: filtering by `module`, `userId`, `since`/`until`;
  pagination via `limit`/`offset`; 403 for non-admin roles.
- **Per-module wiring tests** (one spot-check per module, not exhaustive
  per-action coverage): completing a chore, creating a work, creating a
  cost entry, updating an inventory item, adjusting consumable stock, and
  deleting a KB entry each produce a matching activity log entry with the
  correct `module`/`action`/`entityLabel`/`userId`.
- **Frontend**: `SettingsPage` Activity Log section — renders for admin
  only, filters trigger re-fetch with correct query params, "Load more"
  appends rather than replaces, list rendering of returned entries.

---

## Non-Goals

- Configurable retention period — fixed at 90 days in v1, matching the
  "keep last N days" answer without adding another Settings control.
- Non-admin visibility — the log is admin-only in v1.
- Cross-home activity view — scoped to the currently selected home, same
  as every other module.
- Logging read/view actions — only mutations (create/update/delete/complete)
  are logged, not GETs.
- Undo/revert from the log — this is a read-only audit trail, not a
  version-control or rollback mechanism.

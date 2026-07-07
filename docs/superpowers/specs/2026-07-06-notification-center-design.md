# Notification Center — Design Spec

**Date:** 2026-07-06
**Status:** Approved

---

## Overview

Add a per-home notification center that surfaces three kinds of alerts in one
place, instead of noticing them incidentally while browsing each module:

- **Chores due soon / overdue** — reuses the existing `pct <= threshold`
  convention (currently hardcoded at `0.25` across `HomeChoresWidget.svelte`
  and `ChoreListPage.svelte`); the threshold becomes configurable.
- **Low-stock consumables** — reuses the existing `quantity <= minQuantity`
  convention (`consumableStore.svelte.ts`'s `stockStatus`).
- **Inventory items with warranty expiring soon** — reuses the existing
  30-day "soon" convention (currently duplicated across `InventoryPage.svelte`,
  `InventoryPinPopup.svelte`, `InventoryOverlay.svelte`); the threshold
  becomes configurable.

Two surfaces, one backend computation:

- **In-app**: a bell icon in the topbar with a count badge and a dropdown
  panel listing current notifications grouped by type. Clicking a
  notification navigates to the source item.
- **HA push**: an optional daily digest notification sent via Home
  Assistant's `notify` service, once per day at a configurable local time,
  summarizing counts by category.

**Chores and low-stock are live/stateless**: they appear exactly as long as
the underlying condition is true, and disappear once resolved (chore
completed, item restocked). **Warranty is fire-once and informational**:
there's no action to take about an expiring warranty, so re-showing it every
day for the whole "soon" window would just be noise. The first time an
inventory item's warranty crosses the configured threshold, it's included in
whichever response computes it first (in-app fetch or push digest) and
simultaneously marked "notified" for that item's current
`warrantyExpiryDate`. It will not reappear unless the expiry date itself
changes (e.g. the item is edited with a new date).

No dismiss/read-state UI for chores or low-stock — they are always "what's
true right now." No changes to the `Work` model; "warranty/works
expirations" scope is limited to Inventory's existing `warrantyExpiryDate`
field, since Works has no expiration-like field today.

---

## Approach

Unlike global search (100% client-side, since it only ever runs while a
browser tab is open), the HA push digest must run as a background job with
no browser present. That forces the due-soon/low-stock/warranty computation
to exist server-side regardless — so this spec makes the **backend the
single source of truth**, rather than duplicating threshold logic in both TS
and Python (a duplication trap this codebase has already fallen into once,
with three separate inline copies of warranty-status logic in the frontend).

A new backend module computes the full notification list from the existing
per-home JSON documents (chores, consumables, inventory) plus new
notification settings. The in-app bell fetches this via a new endpoint; the
background digest job calls the same function directly, in-process.

---

## Data Model

### Settings (`models_settings.py`)

New sub-model on `SettingsDocument`, following the existing
per-category-tab, per-field-`PUT` pattern:

```python
class NotificationSettings(BaseModel):
    enabled: bool = True                    # master toggle for the in-app center
    choresDueSoonThreshold: float = 0.25    # same pct convention as today
    warrantyDaysThreshold: int = 30
    haPushEnabled: bool = False
    haNotifyService: str | None = None      # e.g. "notify.mobile_app_pixel"
    haPushTime: str = "08:00"                # local HH:MM, daily digest fire time
```

New route: `PUT /api/homes/{home_id}/settings/notifications`, mirroring the
existing per-field settings routes (e.g. `PUT .../settings/cost-categories`).

### Notification state (new persistence file)

`notifications_state.json`, one per home, following the same atomic
tmp-file-rename pattern as `persistence_settings.py`:

```python
class NotificationState(BaseModel):
    warrantyNotified: dict[str, str] = {}   # inventory item id -> warrantyExpiryDate already notified
    lastPushDigestDate: str | None = None   # ISO date, last date the daily digest actually fired
```

`lastPushDigestDate` prevents double-firing the digest if the background
check runs more than once in a day (e.g. after a restart).

No changes to `Chore`, `Assignment`, `Consumable`, `InventoryItem`, or `Work`
models — all thresholds read from existing fields (`nextDueDate`/
`periodDays`, `quantity`/`minQuantity`, `warrantyExpiryDate`).

---

## Backend: Notification Computation

New module `notifications.py`:

```python
class Notification(BaseModel):
    type: Literal["chore", "low_stock", "warranty"]
    refId: str
    title: str
    detail: str
    severity: Literal["info", "warning", "critical"]

def compute_notifications(home_id: str) -> list[Notification]:
    settings = load_settings(home_id).notifications
    state = load_notification_state(home_id)
    chores = load_chores(home_id)
    consumables = load_consumables(home_id)
    inventory = load_inventory(home_id)

    results = []
    results += _chore_notifications(chores, settings.choresDueSoonThreshold)
    results += _low_stock_notifications(consumables)
    fired, updated_state = _warranty_notifications(
        inventory, settings.warrantyDaysThreshold, state
    )
    results += fired
    if updated_state != state:
        save_notification_state(home_id, updated_state)
    return results
```

`_warranty_notifications` compares each item's `warrantyExpiryDate` against
`state.warrantyNotified[item.id]`; if the expiry has crossed the threshold
and doesn't match the stored value, it's included in `fired` and the state
dict is updated to record it as notified for that expiry date.

New route: `GET /api/homes/{home_id}/notifications` → calls
`compute_notifications`, returns the list. This is a **read with a side
effect** (marks warranty items notified) — acceptable since it's idempotent
per expiry-date, and the only consumers are the bell-icon fetch (triggered by
app load and specific mutation points, not a polling loop — see Frontend
section) and the internal digest job.

---

## Backend: Scheduler + HA Push Digest

This is the first background job in the codebase (today everything is
request-driven). Kept minimal: a single `asyncio` task started in
`main.py`'s `_lifespan`, alongside the existing MCP session-manager task
group:

```python
async def _notification_digest_loop():
    while True:
        await asyncio.sleep(60)  # check every minute
        now = local_now()
        for home_id in list_home_ids():
            settings = load_settings(home_id).notifications
            state = load_notification_state(home_id)
            if not settings.haPushEnabled or not settings.haNotifyService:
                continue
            if state.lastPushDigestDate == now.date().isoformat():
                continue
            if now.strftime("%H:%M") < settings.haPushTime:
                continue
            notifications = compute_notifications(home_id)  # also fires warranty side-effect
            if notifications:
                domain, service = settings.haNotifyService.split(".", 1)
                try:
                    await call_ha_service(domain, service,
                                           {"message": _format_digest(notifications)})
                except HTTPError:
                    log.warning("HA push failed for home %s, will retry next minute", home_id)
                    continue
            mark_digest_sent(home_id, now.date().isoformat())
```

- `call_ha_service(domain, service, data)` — new helper in `routes/ha.py`,
  POSTing to `{_HA_BASE}/services/{domain}/{service}` with the existing
  `_auth_headers` pattern. This is the first outbound *write* call to HA in
  this codebase (existing `ha.py` code — area registry lookup — is
  read-only).
- Minute-granularity polling avoids needing a cron library; per-home
  settings mean multi-home setups can each configure their own digest time.
- `_format_digest` produces counts only, e.g. *"2 chores overdue, 1 item low
  on stock, 1 warranty expiring soon"* — not a full item dump, to keep HA
  notification payloads short. Full detail lives in-app.
- **Failure handling**: if the HA call fails, log and skip without marking
  `lastPushDigestDate`, so it retries next minute rather than going dark
  until tomorrow. Warranty items are marked "notified" as part of
  `compute_notifications()` regardless of push success — their state is
  independent of push delivery, since they're also visible in-app.

---

## Frontend

- **`notificationStore.svelte.ts`** (new) — `notifications: Notification[]`,
  `init(homeId)` fetches `GET /api/homes/{home_id}/notifications` once on app
  load (same eager-load pattern as `choreStore`/`consumableStore`/
  `inventoryStore`), plus `refresh()`. `refresh()` is called from existing
  mutation call sites that already exist for chore completion, consumable
  quantity edits, and inventory saves — no new polling loop.
- **`NotificationBell.svelte`** (new) — topbar icon next to the existing
  search icon; badge shows `notifications.length` (hidden if 0). Click opens
  `NotificationPanel.svelte`.
- **`NotificationPanel.svelte`** (new) — list grouped by type (Chores / Low
  Stock / Warranty); each row clickable → navigates via
  `window.location.hash` to the source module, same pattern as
  `CommandPalette.svelte` result selection. Closes on selection or
  outside-click (same outside-click pattern as the homes picker).
- **`SettingsPage.svelte`** — new "Notifications" tab: master enable toggle,
  chores-due-soon threshold, warranty-days threshold, HA push enable toggle,
  notify-service text field, time picker.
- **`settingsStore.svelte.ts`** — extended with `NotificationSettings`
  interface and a `saveNotificationSettings()` method, mirroring existing
  category setters.

---

## Testing

- **Backend unit tests**: `compute_notifications()` per category — chore
  due-soon/overdue at threshold boundaries, consumable low/empty/ok, warranty
  fire-once (first crossing includes it and marks state; second call with
  same expiry excludes it; changing the expiry date re-fires). Digest loop
  logic tested via an injectable "now" rather than real `asyncio.sleep`.
- **HA push**: unit test `call_ha_service` request shape (follow existing
  `ha.py` test mocking pattern); test digest formatting, "skip if already
  sent today," and "retry on failure" (not marking `lastPushDigestDate`).
- **Settings**: round-trip test for `PUT .../settings/notifications`.
- **Frontend**: `notificationStore` tests (fetch, refresh after mutation);
  `NotificationBell`/`NotificationPanel` component tests (badge count,
  grouping, navigation-on-click, outside-click close); new Settings tab
  tests (field editing, save).

---

## Non-Goals

- Persisted dismiss/read state for chores or low-stock — they're always
  "what's true right now."
- Per-category HA push toggles — one master toggle covers all three
  categories in the daily digest.
- Cross-home notifications — scoped to the currently selected home, same as
  every other module.
- Expiration tracking on the Works model — out of scope; only Inventory's
  `warrantyExpiryDate` is covered.
- Real-time push (e.g. websocket) or sub-daily HA push cadence — daily
  digest only, to avoid needing per-item de-dup state beyond what warranty
  already requires.

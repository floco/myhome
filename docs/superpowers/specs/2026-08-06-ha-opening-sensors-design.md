# HA window/door sensors + roller shutters — design

## Problem

Rooms already link to a Home Assistant Area (`Room.haAreaId`), but that link is
purely informational — nothing on the floor plan reflects live HA state. The user
wants windows and doors to link to HA open/close (`binary_sensor`) entities and
change color to reflect open/closed state in near-real-time, plus optional roller
shutters on windows, linked to HA `cover` entities, with position shown visually and
open/close/stop control from the floor plan.

## Goals

- Link a window or door to an HA `binary_sensor` entity; the opening's rendered
  color reflects open (orange) / closed (default) / unavailable (gray) state.
- Windows can additionally have a roller shutter: a linked HA `cover` entity, with
  its position shown as a fill overlay on the window symbol, and open/close/stop
  buttons.
- State updates arrive near-real-time (HA push, not polling) while the floor plan is
  open, since the user anticipates linking other entity types (e.g. lights) later
  and wants the delivery mechanism to support that without redesign.
- All of this is a toggleable layer ("ha"), on by default, consistent with the
  existing chores/inventory/costs/works/consumables layer toggles, so it can be
  hidden if it gets visually cluttered.
- Entity pickers are scoped to the HA Area of the room(s) adjacent to the opening's
  wall, keeping the list short and relevant (mirrors how the room's own area picker
  works).

## Non-goals

- No websocket/live-state support for anything other than binary_sensor/cover
  entities right now — the message channel is generic enough to extend later, but
  no other entity type (lights, etc.) is being wired up in this pass.
- No historical state / trends — only current state is shown, nothing is persisted
  beyond the linked entity id.
- No confirmation dialog on shutter open/close/stop — matches the low-friction feel
  of the rest of the editor.
- No device_class filtering on the sensor picker (e.g. restricting to
  `door`/`window`/`garage_door`) — any `binary_sensor` in the matched area is
  offered, to avoid hiding valid custom sensors.
- No shared/singleton upstream HA websocket connection — each frontend connection
  gets its own backend-to-HA proxy connection, traded for simplicity over
  resource-efficiency (acceptable for a single-home self-hosted app; see Risks).

## Design

### Data model

`Opening` (backend `models.py` + frontend `geometry/src/types.ts`) gains three
optional fields:

```python
class Opening(BaseModel):
    ...
    haEntityId: str | None = None        # binary_sensor, door/window contact sensor
    hasShutter: bool = False              # windows only
    shutterEntityId: str | None = None    # cover entity
```

`houseStore.updateOpening`'s patch type extends from
`Partial<Pick<Opening, "offset" | "width" | "swing">>` to also allow `haEntityId`,
`hasShutter`, `shutterEntityId` — same shape as `updateRoom`'s `haAreaId` patch.

### Room adjacency for entity-picker scoping

Rooms are auto-detected polygons matched by centroid (`roomMatching.ts`) — `Wall`
and `Opening` don't reference a room id directly. To scope entity pickers to "this
opening's room's HA Area," a new pure function in `packages/geometry/src/`:

```ts
export function findAdjacentRooms(opening: Opening, wall: Wall, rooms: Room[]): Room[]
```

Computes the opening's midpoint on the wall, offsets it by a small epsilon (e.g.
0.05m) perpendicular to the wall in both directions (same perpendicular calculation
`OpeningShape.svelte` already does for its gap polygon), and tests each offset point
against every room's polygon via the existing `pointInPolygon`. Returns the 0-2
rooms found (0 for an opening on an unenclosed/exterior wall with no room on either
side, 1 for the common case of an exterior window, up to 2 for an interior door
between two rooms). When 2 rooms match and both have an `haAreaId`, the entity
picker unions both areas' entity lists (deduped by entity_id); no attempt to
disambiguate further.

### Backend: HA REST additions

In `routes/ha.py`, alongside the existing `/api/ha/areas`:

- **`GET /api/ha/entities?area_id=X&domain=Y`** (`domain` is `binary_sensor` or
  `cover`) — same two-tier strategy as `/api/ha/areas`: template API call using
  `area_entities(area_id)` filtered to `entity_id` starting with `f"{domain}."`,
  friendly name via `state_attr(e, 'friendly_name')`. Returns `[]` on any failure or
  missing `SUPERVISOR_TOKEN`, matching existing behavior.
- **`POST /api/ha/cover/{entity_id}/{action}`** (`action` ∈ `open`/`close`/`stop`,
  `400` for anything else) — calls the existing `call_ha_service("cover",
  f"{action}_cover", {"entity_id": entity_id})` helper. No new HA-calling logic.

### Backend: live state via WebSocket proxy

New `@router.websocket("/api/ha/ws")` in `routes/ha.py`. Per-connection, no shared
singleton:

1. Frontend connects; if `SUPERVISOR_TOKEN` is unset, the backend closes the socket
   immediately with an error code (frontend treats this like the standalone-mode
   fallback elsewhere).
2. Backend opens its own upstream connection to `ws://supervisor/core/websocket`
   using the `websockets` library (new explicit dependency —
   `uvicorn[standard]` pulls it in transitively today, but it should be declared),
   performs the HA auth handshake (`auth_required` → send `{"type": "auth",
   "access_token": token}` → expect `auth_ok`), then sends
   `{"id": 1, "type": "subscribe_events", "event_type": "state_changed"}`.
3. Frontend's first message is `{"entity_ids": [...]}`. Backend fetches current
   state for each (via HA's `GET /api/states/{entity_id}`) and sends a snapshot
   `{"entity_id": ..., "state": ..., "attributes": {...}}` per entity, then forwards
   any subsequent `state_changed` event whose `entity_id` is in the current filter
   set, in the same shape.
4. Frontend may send an updated `{"entity_ids": [...]}` later (e.g. floor switch,
   new link added); backend replaces its filter set and sends snapshots for any
   newly-added ids.
5. Either side disconnecting tears down both legs — frontend close closes the
   upstream HA socket; upstream HA socket dropping (error/timeout) closes the
   frontend socket, and the frontend reconnects (see below).

The upstream-connection step is behind an injectable factory function so tests can
substitute a fake upstream feeding canned events without a real HA instance.

### Frontend: layer toggle

`LayersDropdown.svelte`'s `layers` array gains `{ id: "ha", icon: "📡" }` (new i18n
key `common.modules.ha`, EN+FR), working through the existing
`activeLayers`/`ontoggle` mechanism. Unlike the other layers (which default off),
`App.svelte` seeds `activeLayers` as `new Set(["ha"])` so it's active by default.

### Frontend: state store

`haStateStore.svelte.ts` (new, in `packages/editor/src/lib/`): holds
`Map<entityId, { state: string; attributes: Record<string, unknown> }>` as Svelte
state. Opens the `/api/ha/ws` socket (URL derived from the existing `apiUrl()`
helper with an http→ws scheme swap, so it works under HA ingress) when both:
the floor-plan view is mounted, and `activeLayers.has("ha")`. Computes the linked
entity set (`haEntityId` + `shutterEntityId` across all openings on the *current*
floor, deduped) and sends/updates it as `entity_ids` on the socket whenever it
changes (floor switch, new link, layer toggled back on). Reconnects with a simple
capped backoff (e.g. 1s, 2s, 4s, capped at ~15s) on drop while the gating
conditions still hold. A failed connection leaves existing entries as-is rather than
clearing the map, so a transient blip doesn't flash every opening gray.

### Frontend: OpeningPanel

New `OpeningPanel.svelte`, structurally mirroring `RoomPanel.svelte` (floating
panel, drag handle via the existing `createFloatingDrag` helper, dismiss button,
same design tokens). Rendered in `App.svelte` alongside the existing
`{#if selectedRoom}` block, gated on `selectedOpening` (currently nothing renders
for a selected opening beyond resize handles).

- **Sensor field**: `<select>` bound to `opening.haEntityId`, options from
  `GET /api/ha/entities?area_id=<matched area(s)>&domain=binary_sensor` (unioned if
  two adjacent rooms), "none" option, and the RoomPanel's "(unknown id)" fallback
  pattern if the stored id isn't in the fetched list.
- **Shutter fields**, only when `opening.type === "window"`: a `hasShutter`
  checkbox; when checked, a `shutterEntityId` `<select>` (domain `cover`, same
  area-scoped fetch).
- **Shutter controls**: when `shutterEntityId` is set, Open/Close/Stop buttons
  calling `POST /api/ha/cover/{id}/{action}`, disabled while a request is in
  flight.
- If the opening has no adjacent room with an `haAreaId` set, pickers render
  disabled with a hint ("assign this room to an HA Area first") instead of an empty
  list.

Entity-list fetches are one-shot on panel open/area change (same pattern as the
existing `haAreas` fetch in `App.svelte`), separate from the websocket state
channel.

### Frontend: visual rendering

In `OpeningShape.svelte`, gated on `activeLayers.has("ha")` (passed down from
`Canvas.svelte`, same as `viewport`/`tool` today) and reading from `haStateStore`:

- **Sensor color** (windows/doors with `haEntityId` set): `state === "on"` → open →
  new CSS var `--canvas-opening-open` (orange), replacing the existing color the
  same way the `selected` ternary already swaps colors. `state === "off"` → closed →
  unchanged existing color. Missing/`"unavailable"`/`"unknown"` → new
  `--canvas-opening-unavailable` (muted gray) with a `<title>` tooltip explaining
  why. Both new CSS vars added to the theme tokens (light + dark). Unlinked openings
  or the "ha" layer being off render exactly as today — zero visual change.
- **Shutter overlay** (windows with `hasShutter` and a resolved `shutterEntityId`
  state): an additional `<rect>` along the window line (depth from the wall's
  `thickness`), filled proportional to `100 - current_position` (HA convention:
  `current_position` 0 = closed, 100 = open) using a shutter-specific fill
  color/opacity token. If the cover doesn't report `current_position` (only
  open/closed state), falls back to a binary full/empty overlay based on
  `state === "closed"`.

## Testing

- **Backend** (`test_ha.py`, pytest + `respx` for REST, FastAPI `TestClient
  .websocket_connect` for the WS route with the upstream connection mocked via the
  injectable factory): `/api/ha/entities` domain filtering and template
  success/fallback; cover-control endpoint valid/invalid actions and missing-token
  case; WS route initial snapshot delivery, live event forwarding filtered by
  entity_id, mid-connection `entity_ids` update, and immediate close when
  `SUPERVISOR_TOKEN` is absent.
- **Frontend** (Vitest): `OpeningPanel.test.ts` (pickers populate/update, buttons
  disabled while in-flight, no-area hint); `haStateStore.test.ts` (connect/gating on
  view+layer, entity_ids updates on floor switch, reconnect backoff, map preserved
  on drop); `OpeningShape.test.ts` additions (color mapping for
  on/off/unavailable/unlinked, shutter overlay fill proportional to position, no
  change when "ha" layer off); `LayersDropdown.test.ts` update for the new "ha"
  entry and its default-on seeding; a geometry test for `findAdjacentRooms`
  (exterior window → 1 room, interior door → up to 2, unenclosed wall → 0).

## Open questions / risks

- Per-connection upstream HA websockets mean N browser tabs open N connections to
  HA. Acceptable for a single-home self-hosted app with realistically 1-2 concurrent
  viewers, but worth reconsidering (shared singleton with fan-out) if that ever
  becomes a real usage pattern.
- HA's websocket auth/event-subscription message shapes are assumed stable across
  HA versions (this mirrors the existing `/api/ha/areas` two-tier
  registry-then-template fallback approach for REST, but the WS API has no
  equivalent fallback tier) — if it breaks on some HA version, the failure mode is
  "ha layer never populates," not a crash, since the store leaves state as
  unavailable/empty rather than erroring visibly.
- `current_position` isn't reported by every cover integration/device — the
  binary fallback (`state === "closed"`) may be visually coarser than expected for
  users whose shutters only report open/closed, not intermediate position.

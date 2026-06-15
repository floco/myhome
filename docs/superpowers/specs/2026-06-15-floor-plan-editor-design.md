# Floor Plan Editor — Design Spec

**Status:** Approved for planning
**Spec:** 1 of 2 (Spec 2: chore/maintenance tracker, depends on this one)

## Context

This is the first piece of a larger "myhome" project: an app for managing recurring
household chores/maintenance tasks, visualized on a floor plan with expiration
indicators, eventually extended with HomeHub-style features
([surajverma/homehub](https://github.com/surajverma/homehub),
[ThomasRooyakkers/HomeHub](https://github.com/ThomasRooyakkers/HomeHub)).

The floor plan editor is substantial enough to be its own project. It produces a
reusable foundation — room shapes mapped to Home Assistant areas, exported as SVG —
that Spec 2 (and future features) will build on.

## Goals

- Draw a minimalistic, dimensionally-accurate 2D floor plan: walls, doors, windows,
  and room dividers (virtual walls).
- Support multiple **independent** floors, switchable via a UI control.
- Automatically detect rooms as enclosed areas formed by walls/dividers.
- Assign a Home Assistant area to each room (optional, many-rooms-to-one-area allowed).
- Export each floor as SVG with room IDs and HA area data embedded, for downstream
  consumption.
- Run as a Home Assistant add-on (Docker, ingress-integrated into the HA sidebar).

## Non-goals (deferred)

- Chore/maintenance data model, scheduling, or expiration tracking (Spec 2).
- Donetick integration/migration (Spec 2).
- Rendering chores/expiration badges on the floor plan (Spec 2).
- Furniture or smart-device placement (possible future HomeHub-style feature).
- Multi-floor alignment aids (explicitly out of scope — floors are independent).
- Autosave (explicit Save only for v1).

## Architecture

**Add-on packaging:**
- Standard Home Assistant add-on: `Dockerfile`, `config.yaml` manifest, s6-overlay
  init, `ingress: true` (appears in the HA sidebar using HA's existing session — no
  separate login).
- Persistent storage in `/data` (the add-on's persistent volume).

**Stack:**
- **Backend:** Python + FastAPI. Serves the frontend bundle, exposes a JSON API for
  the floor plan model, proxies Home Assistant's Supervisor API for the area
  registry, and serves per-floor SVG exports.
- **Frontend:** TypeScript + Svelte. Renders an interactive `<svg>` editing canvas
  directly (SVG-native, not canvas-library-based).
- **Persistence:** single JSON file, `/data/house.json`.

**Relationship to Spec 2:** Spec 1 has no knowledge of chores. Its API surface for
Spec 2 is:
- `GET /api/house` — full JSON model (floors, walls, rooms with polygons + `haAreaId`)
- `GET /api/house/floors/{floorId}/svg` — rendered SVG for a floor, with
  `<path id="room-{id}" data-ha-area="{haAreaId}">` elements Spec 2 can target.

## Data Model

Single JSON document, `/data/house.json`:

```json
{
  "version": 1,
  "house": { "name": "My House", "units": "m", "gridSnap": 0.1 },
  "floors": [
    {
      "id": "floor-ground",
      "name": "Ground Floor",
      "order": 0,
      "walls": [
        {
          "id": "wall-1",
          "start": {"x": 0, "y": 0},
          "end": {"x": 5.4, "y": 0},
          "thickness": 0.15,
          "type": "wall"
        },
        {
          "id": "wall-5",
          "start": {"x": 5.4, "y": 1.0},
          "end": {"x": 5.4, "y": 4.2},
          "type": "divider"
        }
      ],
      "openings": [
        { "id": "opening-1", "wallId": "wall-1", "type": "door", "offset": 2.5, "width": 0.9, "swing": "left-in" },
        { "id": "opening-2", "wallId": "wall-3", "type": "window", "offset": 1.0, "width": 1.2 }
      ],
      "rooms": [
        {
          "id": "room-1",
          "label": "Living Room",
          "haAreaId": "living_room",
          "polygon": [{"x":0,"y":0},{"x":5.4,"y":0},{"x":5.4,"y":4.2},{"x":0,"y":4.2}],
          "areaM2": 22.68
        }
      ]
    }
  ]
}
```

Key points:
- **Units in meters**, configurable grid-snap (default 0.1 m).
- **Walls** have a `"type"`: `"wall"` (physical — has `thickness`, renders solid,
  can hold openings) or `"divider"` (virtual — no thickness, renders as a thin
  dashed line, cannot hold openings). Both participate equally in room detection.
- **Openings** (doors/windows) reference a wall by ID, with an `offset` (distance
  along the wall from its start point, clamped to the wall's length) and `width`.
  Doors additionally have a `swing` direction (`"left-in"`, `"right-in"`,
  `"left-out"`, `"right-out"` — which corner the hinge is on and which side the
  door opens to) used only for the SVG arc.
- **Rooms** store a cached `polygon` (computed from wall/divider **centerlines**,
  not inset by wall thickness — see "Room Detection" for rationale), a `label`, an
  optional `haAreaId` (nullable; multiple rooms may share the same `haAreaId`), and
  a computed `areaM2`.
- **Floors** are fully independent: own walls/openings/rooms and own coordinate
  origin. No cross-floor alignment.

## Editor UX

**Layout:**
- **Top bar:** floor switcher (buttons per floor + "+ Add Floor") and a Save action.
- **Left toolbar:** Select, Wall, Divider, Door, Window tools; Undo/Redo/Delete.
- **Canvas:** grid-snapped interactive SVG.
- **Right panel:** when a room is selected — editable label, HA area dropdown
  (populated from HA's area registry, includes "(none)"), and computed area in m².

**Interactions:**
- **Wall / Divider tools:** click to place points; snapping to grid and to nearby
  existing points; click near a previous point to close a loop; double-click/Esc to
  end a chain.
- **Door / Window tools:** click on an existing `"wall"`-type segment to place an
  opening at that point (snapped along the wall); these tools are inactive over
  `"divider"` segments.
- **Select tool:** click a room to select/highlight its polygon and edit it in the
  right panel; click a wall/divider/opening to drag endpoints or delete.
- **Floor switcher:** "+ Add Floor" creates a new, independent floor; existing
  floors are switched via buttons.

## Room Detection & SVG Generation

**Room detection** (client-side, TypeScript, recomputed on every wall/divider edit
for instant feedback):
- Build a planar graph from wall **and divider** centerlines (segments split at
  intersections). Find minimal cycles ("faces") via a standard planar-subdivision
  walk (sort edges around each vertex by angle, trace faces). Each interior face
  becomes a candidate room polygon.
- Disconnected groups of walls/dividers each produce their own faces independently
  — a floor doesn't need to be one single closed loop.
- A room with a hole (e.g. a courtyard) falls out naturally as a separate inner face.
- **Room identity across edits:** after re-detection, new polygons are matched
  against existing rooms by overlap (e.g. centroid-in-polygon test). Matched rooms
  keep their `label`/`haAreaId`/`id`; unmatched new polygons become new rooms
  (default label "Room N", no HA area); rooms whose polygon disappears are kept
  with `polygon: null` and surfaced in an "Unresolved rooms" list for the user to
  reassign or delete — assignments are never silently dropped.
- **Simplification:** room polygons follow wall/divider **centerlines**, not the
  interior face inset by wall thickness. This keeps the algorithm simpler;
  `areaM2` is therefore slightly larger than true usable floor space (by roughly
  half the surrounding walls' thickness), which is acceptable for this tool's
  "minimalistic" goals.

**SVG generation** (simple templating, not a complex algorithm — implemented in
both places without significant duplication risk):
- Walls → `<path class="wall">` (rendered with thickness on both sides of the
  centerline); dividers → thin dashed `<path class="divider">`.
- Doors/windows → door-swing arc / window symbol at the opening's position.
- Rooms → `<path id="room-{id}" data-ha-area="{haAreaId}">`.
- **Frontend:** renders this live, in the editor, for immediate visual feedback.
- **Backend:** renders the same way for the `/api/house/floors/{floorId}/svg` export
  endpoint that Spec 2 will consume.

## Home Assistant Integration

- On startup, fetch the area registry via the Supervisor API:
  `GET http://supervisor/core/api/config/area_registry`,
  `Authorization: Bearer $SUPERVISOR_TOKEN` (env var auto-injected for HA add-ons).
- Cache the area list in memory; a "Refresh areas" action re-fetches on demand
  (areas change rarely — no polling).
- Rooms store the HA area's stable ID (`haAreaId`); display names are looked up
  from the cached list. If the Supervisor API is unreachable, the dropdown falls
  back to the last-cached name list; assignments (stored by ID) are unaffected
  either way.

## Persistence

- `/data/house.json` is the single source of truth, loaded into memory on startup.
- Explicit **Save** action persists the in-memory model to disk (no autosave in v1).
- If `/data/house.json` doesn't exist on first run, initialize with an empty house
  containing one default floor ("Ground Floor").

## Error Handling & Edge Cases

- **Unclosed wall/divider chains:** no room face is produced there — normal
  mid-editing state, not an error.
- **Room polygon disappears** after an edit: room entry kept with `polygon: null`,
  surfaced in an "Unresolved rooms" list rather than silently deleted.
- **HA Supervisor API unreachable:** area dropdown falls back to last-cached names;
  a banner notes "HA areas unavailable — showing cached list." Existing
  `haAreaId` assignments are preserved (stored by ID, not name).
- **Door/window placement:** `offset` is clamped to the wall's length; the
  Door/Window tools are no-ops over `"divider"` segments (with an explanatory
  tooltip).

## Testing Strategy

- **Room-detection unit tests (Vitest, frontend):** rectangle; two rooms split by a
  physical wall; two rooms split by a divider; L-shaped room; room with a hole
  (courtyard); unclosed chains (no room produced); disconnected wall groups; room
  re-matching after edits (label/HA-area preserved on minor polygon changes, new
  room created when no match).
- **Backend unit tests (Pytest):** JSON model validation; HA area-registry proxy
  against mocked Supervisor responses (including the unreachable case); SVG export
  snapshot tests (including divider-as-dashed-line rendering).
- **Frontend interaction tests (Playwright):** draw a wall rectangle → room
  detected; add a divider → splits into two rooms; assign HA areas; save and
  reload preserves everything.
- **Local dev without real HA:** since the Supervisor API only exists inside HA OS,
  provide a stub server returning fixture area-registry data for local development.
- **Manual end-to-end:** install as a dev add-on on a test HA instance; verify
  ingress/sidebar integration and the full draw → assign → save → reload flow
  (via the webapp-testing skill).

## Open Questions for Spec 2

- Exact mechanism by which Spec 2 (a separate add-on) reads Spec 1's data — direct
  HTTP calls to `/api/house*` (ingress add-ons can call each other via the
  Supervisor's internal network) is the likely approach, to be confirmed when Spec 2
  is designed.
- Whether `areaM2` (centerline-based) needs revisiting if a future feature requires
  true interior floor area.

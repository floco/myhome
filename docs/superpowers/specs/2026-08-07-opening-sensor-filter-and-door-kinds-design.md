# Opening sensor filter + door kinds + orientation — design

## Why

Two related problems with the HA opening-sensor linking feature (PR #103):

1. **Bug**: the sensor picker in `OpeningPanel` shows every `binary_sensor` in the
   linked HA area, regardless of what it actually senses (motion, battery,
   moisture, ...) — it should only offer sensors HA itself flags as "shown as
   window" / "shown as door" (i.e. filtered by `device_class`).
2. **Missing feature**: doors only ever render as a single hinged-swing symbol,
   with no way to express sliding, double-action ("battante"), or garage doors,
   and no UI to change hinge side / swing direction even though the data model
   (`Opening.swing`) already supports it. Windows have no orientation concept
   at all.

## Data model (`packages/geometry/src/types.ts`)

```ts
export type DoorKind = "hinged" | "swinging" | "sliding" | "garage";
export type WallSide = "in" | "out";

export interface Opening {
  // ...existing fields unchanged...
  /** Only meaningful for type "door". Undefined behaves as "hinged". */
  doorKind?: DoorKind;
  /** Only meaningful for type "window". Undefined behaves as "in". */
  windowSide?: WallSide;
}
```

- `doorKind` French UI labels: `hinged` = pivotante (default), `swinging` =
  battante, `sliding` = coulissante, `garage` = garage.
- Both fields are optional with defaults, matching the existing
  `opening.swing ?? "left-in"` pattern — no data migration needed.
- `swing` (`DoorSwing`) is unchanged, but becomes editable in the UI (today
  it's only set once at creation time in `App.svelte`, hardcoded `left-in`).

## Backend (`packages/backend/src/myhome/routes/ha.py`)

`GET /api/ha/entities` gains an optional `device_classes` query param
(comma-separated device_class values). The Jinja template used to list area
entities adds `state_attr(e, 'device_class')` per entity; when
`device_classes` is present, only entities whose device_class is in that set
are returned. Omitting the param preserves today's unfiltered behavior (used
for the `cover`/shutter picker, which doesn't need this filter).

`_ALLOWED_ENTITY_DOMAINS` and the WS route are unaffected — this is an
additive filter on the existing `/api/ha/entities` endpoint only.

## `OpeningPanel.svelte`

- Sensor fetch passes `device_classes=window` for `type === "window"`,
  `device_classes=door,garage_door` for `type === "door"` (garage-door contact
  sensors are always offered for doors, not gated further by `doorKind`).
- New "Door kind" `<select>` (i18n-labeled, shown only for `type === "door"`):
  Pivotante (default) / Battante / Coulissante / Garage.
- New orientation controls:
  - `doorKind` is `hinged` (or unset): two 2-way toggles — hinge side
    (left/right) and swing direction (in/out) — together set `swing`.
  - `doorKind` is `swinging`: only the hinge-side toggle (left/right) is
    shown; the door swings both in and out from that hinge regardless of the
    in/out half of `swing`.
  - `doorKind` is `sliding` or `garage`: no orientation control.
  - `type === "window"`: a 2-way toggle for `windowSide` (in/out), always
    shown.

## `OpeningShape.svelte` rendering (canvas only)

Per `doorKind`:

- `hinged`: unchanged — existing leaf line + quarter arc, driven by `swing`.
- `swinging`: same hinge point as `hinged` (from `swing`'s left/right half),
  but draws **two** leaf+arc pairs, one swinging in and one swinging out, for
  a double-action look.
- `sliding`: a solid, thicker bar spanning the opening, offset to the "out"
  wall face (a fixed convention, matching the shutter-overlay offset
  direction already used for windows). No arc, no user-facing orientation
  control.
- `garage`: a bar spanning the full opening width with evenly-spaced
  perpendicular hatch ticks (sectional-panel look), centered in the wall
  band (no face offset). No arc.

For windows: replaces the current single line with a double-line CAD glazing
symbol (2 short parallel lines within the wall band), the pair offset toward
whichever wall face `windowSide` selects (in ⇒ toward room interior, out ⇒
toward exterior).

All variants keep using the existing `strokeColor` derivation (selection / HA
sensor-state color) unchanged — only the shape geometry changes per kind.

## Explicitly out of scope

`packages/geometry/src/svgRender.ts` (`renderFloorSvg`) has its own simpler
door/window rendering and currently has **no production consumer** — nothing
in the backend, editor, or MCP server calls it; only its own test file does.
This work leaves it drawing the old single-line/plain-arc symbols rather than
duplicating all door-kind and window-orientation rendering there. Flagged
here as a known, intentional inconsistency rather than an oversight — worth
revisiting only if/when `renderFloorSvg` gets an actual consumer (e.g. a
floor-plan export feature).

## Testing

- Backend: `device_classes` filtering in `test_ha.py` (present/absent param,
  multiple values, entities with missing/other device_class).
- Geometry: `Opening`/`DoorKind`/`WallSide` type additions need no new tests
  themselves; `svgRender.ts` behavior is unchanged (see scope note) so its
  existing tests keep passing as-is.
- Editor: `OpeningPanel.test.ts` for the new door-kind select, conditional
  orientation toggles, and `device_classes` param on entity fetches;
  `OpeningShape.test.ts` for each `doorKind`'s rendered symbol and the
  window double-line offset.

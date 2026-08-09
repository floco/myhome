# Garden Border Wall Type — Design

## Context

This is the first of a batch of floorplan editor requests (see also: viewport
reliability, opening enhancements, furniture parameters — separate specs).
The floorplan editor currently supports two `WallType` variants:

- `wall` — a real interior/exterior wall, rendered with thickness, mitered
  corners, and can host door/window openings.
- `divider` — a thin dashed line with no thickness, used to mark a room
  boundary without a physical wall. Cannot host openings.

Both types are treated identically by room detection: `detectRooms()` takes
`floor.walls` (regardless of `type`) and traces enclosed polygonal faces from
the centerlines, producing rooms with a computed area.

The user wants a third type specifically for marking the border of a garden
or plot — a boundary that should compute an area like a room does, but read
visually as "garden edge," not an interior wall or room divider.

## Design

### Data model

Extend `WallType` in `packages/geometry/src/types.ts`:

```ts
export type WallType = "wall" | "divider" | "garden";
```

No other changes to `Wall`, `detectRooms()`, `buildPlanarGraph()`, or
`roomMatching` — all of these already operate on `floor.walls` without
branching on `type`, so a closed loop of `garden`-type segments produces a
detected room/area exactly like today, through the same room-labeling flow.
Thickness stays "only meaningful for type wall," matching the existing
divider convention.

### Tooling

Add `"garden"` to `ToolType` in `toolStore.svelte.ts`. Add a new toolbar
button in `Toolbar.svelte` and in the floating toolbar in `App.svelte`,
mirroring the existing wall/divider buttons (icon, active-state highlighting,
i18n title).

Point placement requires no new logic: `App.svelte` already does
`tool as WallType` when placing a new wall segment, so a tool named
`"garden"` flows straight through to `Wall.type: "garden"`.

### Rendering

New `GardenBorderShape.svelte`, modeled on `DividerShape.svelte` (a thin
line with no thickness, screen-projected from world coordinates), but with
its own dash pattern and a new `--canvas-garden-border` CSS custom property
(distinct green tone) defined in `theme.css` for both light and dark themes,
so it doesn't read as a divider.

`Canvas.svelte`'s per-wall render loop gets a third branch:

```svelte
{#if wall.type === "wall"}
  <WallShape ... />
{:else if wall.type === "divider"}
  <DividerShape ... />
{:else}
  <GardenBorderShape ... />
{/if}
```

### Openings

No change required. `Canvas.svelte` already filters door/window placement
and `OpeningShape` rendering to `wall.type === "wall"` only, so garden-border
segments are automatically excluded from hosting openings — matching the
decision to keep gates out of scope for now.

### i18n

Add a `floorPlan.tools.garden` key ("Garden Border") to both `en.json` and
`fr.json`.

### Testing

- Geometry-level test: a closed loop of `"garden"`-type walls is detected as
  a room/area by `detectRooms()`, locking in the existing type-agnostic
  behavior for the new type.
- Extend any existing App/Canvas tests that iterate over wall types
  (tool switching, rendering dispatch) to cover `"garden"`.

## Out of scope

- Gates/openings on garden-border segments.
- Any change to how garden-border areas are labeled or displayed beyond the
  existing room/area mechanism.

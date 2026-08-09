# Double / French door — design

## Why

The opening system supports four `DoorKind`s (`hinged`, `swinging`, `sliding`,
`garage`) but has no way to represent a double/French door — two independent
leaves, one hinged at each jamb, swinging the same direction together. This
is a common real-world door type not covered by the closest existing kind
(`swinging`, which draws two arcs from a single shared hinge, not two
separate hinges).

While implementing this, also fix a pre-existing gap: the two static SVG
exporters (`packages/backend/src/myhome/svg_render.py`, behind the live
`/api/homes/{home_id}/house/floors/{floor_id}/svg` export endpoint, and
`packages/geometry/src/svgRender.ts`, currently unconsumed in production)
both ignore `doorKind` entirely — every door, regardless of kind, renders as
a single generic hinged leaf+arc. Bringing both in line with the canvas
renderer is in scope for this feature.

## Data model

`packages/geometry/src/types.ts` and `packages/backend/src/myhome/models.py`
(mirrored, as today):

```ts
export type DoorKind = "hinged" | "swinging" | "sliding" | "garage" | "double";
export type DoorSwing =
  | "left-in" | "right-in" | "left-out" | "right-out"
  | "in" | "out";
```

- `"double"` is a new `DoorKind`. `"in"`/`"out"` are new `DoorSwing` values,
  used only when `doorKind === "double"` — a double door uses both jambs
  symmetrically, so the left/right axis that the other kinds need is
  meaningless here. Existing kinds keep using the four `*-in`/`*-out`
  variants exactly as today.
- No new `Opening` fields, no persistence/migration changes — same
  JSON-blob storage as every other field. Optional fields with sensible
  defaults (`doorKind` undefined ⇒ `"hinged"`, `swing` undefined for a
  `"double"` door ⇒ treated as `"in"`).
- `houseStore.svelte.ts`'s `updateOpening` patch whitelist already includes
  `doorKind` and `swing` — no change needed there.

## Canvas rendering (`OpeningShape.svelte`)

New `doubleDoorData` derived block, parallel to the existing
`hingedOrSwingingData`/`slidingBarData`/`garageTicksData` blocks:

- Two independent hinges: leaf 1 anchored at `wp1`, leaf 2 anchored at `wp2`.
- Each leaf's length is `opening.width / 2` (so the two leaves meet in the
  middle of the opening when closed).
- Both leaves swing toward the same wall face: `perpIn` when
  `swing !== "out"`, else `perpOut` (mirrors the existing `perpIn`/`perpOut`
  convention used by `hinged`/`swinging`).
- Each leaf gets its own `chooseSweepFlag`-computed arc (reusing the
  existing `@myhome/geometry` helper, same as `hinged`/`swinging` do today)
  so both arcs are centered on their own hinge and read as two independent
  doors meeting in the middle.

Rendering reuses the existing `<line class="door-leaf">` / `<path
class="door-arc">` elements — a `"double"` door just renders two of each
instead of one, via the same `{#each ... as variant}` pattern already used
for `swinging`. No new CSS classes.

## Panel UI (`OpeningPanel.svelte`)

- Add `"double"` to the door-kind `<select>`, i18n-labeled.
- Extend the swing-direction (in/out) `<select>`'s visibility condition from
  `doorKind === "hinged"` to `doorKind === "hinged" || doorKind === "double"`.
- Hinge-side (left/right) `<select>` stays hidden for `"double"` (only shown
  for `hinged`/`swinging`, unchanged condition) — not meaningful when both
  jambs are used.
- `handleSwingDirectionChange`: branch on `doorKind`. For `"hinged"`, keep
  today's `composeSwing(side, direction)` behavior. For `"double"`, write
  `swing` directly as `"in"` or `"out"` (no side to compose).

## Python SVG export (`svg_render.py`)

`_render_door` currently ignores `doorKind` and always draws one generic
leaf+arc from `swing`. Rewrite it to branch on `doorKind` (default
`"hinged"` when unset), reproducing the same five visual treatments as the
canvas, using the existing `_choose_sweep_flag` helper:

- `hinged`: unchanged — today's single leaf+arc logic, extracted as-is.
- `swinging`: two arcs sharing one hinge (computed from `swing`'s left/right
  half), one swinging in and one swinging out.
- `sliding`: a single thick offset bar spanning the opening, no arc.
- `garage`: evenly-spaced perpendicular hatch ticks spanning the opening, no
  arc.
- `double`: two independent hinge leaf+arc pairs (`wp1`/`wp2`, each leaf
  width `width / 2`, both swinging toward the `swing`-selected face), same
  geometry as the canvas's `doubleDoorData`.

This is a real behavior fix, not just new-kind support: today every
`sliding`/`garage`/`swinging` door exported via `/svg` incorrectly renders
as a plain hinged door.

## TS twin renderer (`packages/geometry/src/svgRender.ts`)

Same doorKind-aware rewrite of `renderDoor`, for consistency with the
canvas and the Python exporter, even though nothing in production currently
calls `renderFloorSvg`. Brings all three door renderers into agreement.

## i18n

New door-kind label key (e.g. `opening.doorKind.double`) in both `en` and
`fr` message catalogs, following the existing `hinged`/`swinging`/`sliding`/
`garage` key pattern.

## Testing

- `OpeningShape.test.ts`: new `describe` block for `doorKind: "double"`
  mirroring the existing per-kind blocks — asserts 2× `door-leaf` + 2×
  `door-arc` elements, correct hinge endpoints at `wp1`/`wp2`, and swing
  `"in"`/`"out"` producing the expected face offset.
- `OpeningPanel.test.ts`: door-kind select includes `"double"`; swing-
  direction select shown for `"double"`, hidden hinge-side select; `onupdate`
  call shape for the new direct `"in"`/`"out"` swing values.
- `test_svg_render.py`: parameterized cases across all five `doorKind`
  values (the four existing kinds currently have zero coverage — only a
  single unparameterized `swing="left-in"` case exists today) plus the new
  `"double"` case; assert kind-appropriate elements appear (leaf/arc count,
  `door-sliding`/`door-garage` classes, etc.), not just presence of a
  generic leaf+arc.
- `packages/geometry/test/svgRender.test.ts`: same parameterized doorKind
  coverage added to the existing `DoorSwing`-only test block.

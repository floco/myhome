# Furniture Parameters — Design Spec

## Context

Batch group D of the 2026-08-09 floorplan editor requests (see `docs/superpowers/plans/2026-08-09-*` for the sibling groups A/B/C, already shipped). The largest and most novel item: a generic per-instance configurable-parameters system for furniture templates, plus a new Stairs template.

Today `FurnitureObject` (`packages/geometry/src/types.ts`) is a flat `{id, templateId, x, y, width, height, rotation}` and `FurnitureTemplate` (`packages/editor/src/lib/furnitureLibrary.ts`) carries a static `svgContent` SVG-fragment string rendered in a 0–100 local box, non-uniformly scaled by `FurnitureShape.svelte` to fit `width × height` meters. There is no mechanism for a furniture instance to carry options beyond width/height/rotation.

Three concrete uses drive this design:

1. **Chair count** for the Dining Table (rect) and Round Table templates.
2. **Non-uniformly-scaling plank pattern** for the Deck/Terrace template — real plank width/length (cm), laid out like a real wood terrace, scaling with the object's actual size instead of 4 fixed lines stretching.
3. **L-shaped sofa** — the existing Sofa template gains a shape (straight / L-shaped) and corner (which corner the chaise extends from) parameter.

Plus a trivial addition: a **Stairs** template (new "Structural" furniture category), with no parameters.

The system is designed to be easy to extend to future templates/parameters beyond these three, even though only these three are wired up now.

## 1. Data Model

### `packages/geometry/src/types.ts`

```ts
export interface FurnitureObject {
  id: string;
  templateId: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  params?: Record<string, string | number>; // NEW
}
```

Optional and additive — floor plans saved before this feature have no `params` and render using each template's schema defaults.

### `packages/backend/src/myhome/models.py`

```python
class FurnitureObject(BaseModel):
    id: str
    templateId: str
    x: float
    y: float
    width: float
    height: float
    rotation: float
    params: dict[str, str | float] | None = None  # NEW
```

The pydantic model has no `extra="allow"` configured, so pydantic v2's default `extra="ignore"` would silently drop an unrecognized `params` key on any save round-trip through the API. This field must be added or furniture parameters set in the UI would be lost on reload. The backend does not interpret `params` — it's opaque passthrough storage, same treatment as `width`/`height`/`rotation`.

### `packages/editor/src/lib/furnitureLibrary.ts`

```ts
export type FurnitureParamDef =
  | { id: string; type: "integer"; labelKey: string; min: number; max: number; default: number }
  | { id: string; type: "number"; labelKey: string; min: number; max: number; step?: number; unit?: string; default: number }
  | {
      id: string;
      type: "enum";
      labelKey: string;
      options: { value: string; labelKey: string }[];
      default: string;
      visibleWhen?: { paramId: string; equals: string };
    };

export interface FurnitureTemplate {
  id: string;
  label: string;
  category: FurnitureCategory;
  defaultWidth: number;
  defaultHeight: number;
  svgContent: string; // fallback / static templates keep using this
  params?: FurnitureParamDef[];             // NEW — omitted for static templates
  render?: (ctx: FurnitureRenderContext) => string; // NEW — used instead of svgContent when present
}

export interface FurnitureRenderContext {
  width: number;   // meters, from the FurnitureObject instance
  height: number;  // meters
  params: Record<string, string | number>; // schema defaults merged with object.params
}
```

`FurnitureCategory` gains `"structural"` alongside the existing seven, with a `CATEGORY_LABELS`/i18n entry, for the Stairs template.

## 2. Rendering Engine

Add a helper in `furnitureLibrary.ts`:

```ts
export function resolveFurnitureParams(template: FurnitureTemplate, object: FurnitureObject): Record<string, string | number> {
  const defaults = Object.fromEntries((template.params ?? []).map((p) => [p.id, p.default]));
  return { ...defaults, ...object.params };
}

export function resolveFurnitureSvg(template: FurnitureTemplate, object: FurnitureObject): string {
  if (!template.render) return template.svgContent;
  return template.render({ width: object.width, height: object.height, params: resolveFurnitureParams(template, object) });
}
```

`FurnitureShape.svelte` calls `resolveFurnitureSvg(template, object)` instead of reading `template.svgContent` directly. Static templates (the ~30 existing ones, plus Stairs) are unaffected — `render` is undefined, so it falls through to the static string exactly as today.

Render functions operate in the same 0–100 local box as static templates, but because they receive real `width`/`height` (meters), they can convert real-world units into that local space to counteract the outer non-uniform `scale(scaleX, scaleY)` in `FurnitureShape.svelte` — e.g. a circular chair drawn with `rx = R_meters / width * 100`, `ry = R_meters / height * 100` renders as a true circle regardless of the table's aspect ratio.

### Dining Table (rect) / Round Table — `chairCount`

- Table body: reuse the existing static path for each shape.
- Chairs: `chairCount` small chair shapes (reusing the Dining Chair silhouette at a fixed local size, corrected for aspect ratio as above) distributed around the perimeter:
  - **Rect**: split as evenly as possible across all 4 sides (e.g. `Math.ceil(n/4)` / side, skipping corners), matching typical dining layouts.
  - **Round**: spaced evenly by angle (`360 / n` degrees apart) around the circle.
- `chairCount: 0` renders the table with no chairs.

### Sofa — `shape` + `corner`

- `shape === "straight"`: today's existing sofa path, unchanged.
- `shape === "l-shaped"`: an L-shaped outline — the existing sofa silhouette plus a chaise extension (roughly half the sofa's depth again, square with the seat) attached at whichever corner `corner` selects (`nw`/`ne`/`se`/`sw`), mirrored/rotated as needed so the chaise reads correctly from all four corner choices.

### Deck / Terrace — `plankWidth` + `plankLength`

- Convert `plankWidth`/`plankLength` (cm) into local-space plank dimensions using the same `/ width * 100` / `/ height * 100` conversion.
- Lay out planks in rows spanning the object's local width, each row `plankWidth` tall; within a row, planks are `plankLength` long laid end-to-end, with each row offset by half a plank length from the row above/below (staggered "brick joint," like real decking) and clipped to the 0–100 box.
- Row/plank counts are computed from real `width`/`height`, so resizing the deck changes the number of planks drawn rather than stretching a fixed pattern.

## 3. Params UI Panel

New `packages/editor/src/lib/components/FurnitureParamsPanel.svelte`, following the existing `RoomPanel.svelte` / `OpeningPanel.svelte` floating-panel pattern:

- Draggable via the same `⠿` handle + `createFloatingDrag` helper, dismissible via a close button — same as `RoomPanel`/`OpeningPanel`.
- Shown in `App.svelte` whenever the selected furniture object's template has a non-empty `params` array. Templates without params (all ~30 static ones, plus Stairs) show no panel — identical to today's behavior.
- One field per `FurnitureParamDef`, in schema order:
  - `integer` / `number`: a number input (`min`/`max`/`step`, unit suffix shown when `unit` is set).
  - `enum`: a `<select>` of `options`.
  - A param with `visibleWhen` is hidden unless the referenced param's current value equals `visibleWhen.equals` (drives the Sofa `corner` field showing only when `shape === "l-shaped"`).
- Field labels resolve via i18n (`labelKey`), following the existing `floorPlan.furnitureLibrary.items.*` convention — new keys added under e.g. `floorPlan.furnitureLibrary.params.*`.
- `onupdate(patch: Record<string, string | number>)` calls new `houseStore.updateFurnitureParams(id, patch)`.

### `houseStore.svelte.ts`

```ts
function updateFurnitureParams(id: string, patch: Record<string, string | number>): void {
  const obj = ensureFurniture(currentFloor()).find((f) => f.id === id);
  if (!obj) return;
  saveSnapshot();
  obj.params = { ...obj.params, ...patch };
}
```

Mirrors `updateRoom`/`resizeFurniture`: pushes an undo snapshot, mutates in place (Svelte 5 reactivity picks it up), no `skipHistory` variant needed since param edits are discrete field commits, not drags.

`addFurniture()` is extended: when the template (looked up by `templateId`) has a non-empty `params` schema, the new `FurnitureObject` is created with `params` pre-populated from the schema defaults (via `resolveFurnitureParams`-equivalent at creation time), so a freshly dropped Sofa/table/deck renders correctly immediately rather than needing the panel opened first.

## 4. Concrete Templates

- **Stairs** — new template, category `"structural"` (new category, `CATEGORY_LABELS`/i18n entry added). Static `svgContent` only, no `params` — same shape as any other simple template today.
- **Dining Table (rect)** (`id: "dining-table-rect"`): `params: [{ id: "chairCount", type: "integer", labelKey: "...chairCount", min: 0, max: 8, default: 4 }]`, gains `render`.
- **Round Table** (`id: "dining-table-round"`): same `chairCount` param shape (`min: 0, max: 8, default: 4`), gains `render`.
- **Sofa** (`id: "sofa"`): `params: [{ id: "shape", type: "enum", options: [straight, l-shaped], default: "straight" }, { id: "corner", type: "enum", options: [nw, ne, se, sw], default: "se", visibleWhen: { paramId: "shape", equals: "l-shaped" } }]`, gains `render`.
- **Deck / Terrace** (`id: "deck-terrace"`): `params: [{ id: "plankWidth", type: "number", unit: "cm", min: 5, max: 30, step: 1, default: 14 }, { id: "plankLength", type: "number", unit: "cm", min: 50, max: 400, step: 10, default: 200 }]`, gains `render`.

All other existing templates are untouched.

## 5. Testing

- `furnitureLibrary.test.ts`: `resolveFurnitureParams` default-merge behavior; each of the four `render()` functions (chair count changes rendered chair-element count for both table shapes; sofa shape/corner changes the rendered path; deck plank count/layout scales with width/height and with `plankWidth`/`plankLength`).
- `FurnitureShape.test.ts`: falls back to static `svgContent` when `template.render` is absent; calls `resolveFurnitureSvg` and renders its output when present.
- New `FurnitureParamsPanel.test.ts`: renders correct field type per `FurnitureParamDef`, `visibleWhen` gating (corner field hidden/shown based on shape), `onupdate` fires with the right patch shape.
- `houseStore.furniture.test.ts`: `updateFurnitureParams` merges into `object.params` and pushes an undo snapshot; `addFurniture` seeds `params` from schema defaults for templates that declare them, and leaves `params` undefined for templates that don't.
- Backend: a model round-trip test confirming `params` survives serialize/deserialize through the pydantic `FurnitureObject` model (guards the `extra="ignore"` pitfall identified above).

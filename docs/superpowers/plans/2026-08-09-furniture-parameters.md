# Furniture Parameters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a generic per-instance configurable-parameters system to the furniture library, and use it for three concrete cases (table chair count, sofa L-shape, deck plank pattern), plus a new no-param Stairs template.

**Architecture:** `FurnitureObject` gains an optional `params` map (geometry + backend). `FurnitureTemplate` gains an optional declarative `params` schema (`FurnitureParamDef[]`) and an optional `render(ctx)` function that, when present, replaces the static `svgContent` for that template's on-canvas rendering (the static `svgContent` stays as-is and keeps serving the library picker's thumbnail). A new floating `FurnitureParamsPanel.svelte` — modeled on the existing `RoomPanel`/`OpeningPanel` — lets the user edit a selected object's params when its template declares any. `houseStore` gains `updateFurnitureParams` and seeds new instances with schema defaults.

**Tech Stack:** Svelte 5 runes + TypeScript (editor, geometry), FastAPI/Pydantic (backend), Vitest (frontend tests), pytest (backend tests).

## Global Constraints

- `FurnitureObject.params` and `FurnitureTemplate.params`/`render` are additive optional fields — no data migration, existing saved floor plans deserialize unchanged, templates without `params` render exactly as before.
- All new UI strings go through `svelte-i18n` (`$_(...)`), added to both `packages/editor/src/lib/locales/en.json` and `fr.json` — the `i18n catalog completeness` test (`packages/editor/test/i18nCompleteness.test.ts`) fails the build if the two files' key sets ever diverge, so every new key must be added to both files in the same task.
- The backend `FurnitureObject` Pydantic model (`packages/backend/src/myhome/models.py`) has no `model_config` set, so Pydantic v2's default `extra="ignore"` silently drops any JSON key not declared on the model. `params` must be added there or values set in the UI vanish on the next save/reload round-trip.
- Existing static templates (~30 of them) and the Stairs template added here are untouched by the `render`/`params` mechanism — `resolveFurnitureSvg` falls back to `template.svgContent` whenever `template.render` is absent.

---

### Task 1: Data model — `FurnitureObject.params`

**Files:**
- Modify: `packages/geometry/src/types.ts`
- Modify: `packages/backend/src/myhome/models.py`
- Test: `packages/geometry/test/types.test.ts`
- Test: `packages/backend/tests/test_persistence.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `FurnitureObject` includes `params?: Record<string, string | number>` (TS) / `params: dict[str, str | float] | None = None` (Python). All later tasks read/write this field.

- [x] **Step 1: Write the failing tests**

Add to `packages/geometry/test/types.test.ts`, importing `FurnitureObject` alongside the existing types (change line 2 to `import type { HouseDocument, Opening, FurnitureObject } from "../src/types";`), then add a new `describe` block at the end of the file:

```ts
describe("FurnitureObject params", () => {
  it("allows a furniture object with no params", () => {
    const obj: FurnitureObject = { id: "f1", templateId: "sofa", x: 0, y: 0, width: 2.2, height: 0.9, rotation: 0 };
    expect(obj.params).toBeUndefined();
  });

  it("allows a furniture object with string and number params", () => {
    const obj: FurnitureObject = {
      id: "f2", templateId: "sofa", x: 0, y: 0, width: 2.2, height: 0.9, rotation: 0,
      params: { shape: "l-shaped", corner: "se", chairCount: 4 },
    };
    expect(obj.params?.shape).toBe("l-shaped");
    expect(obj.params?.chairCount).toBe(4);
  });
});
```

Add to `packages/backend/tests/test_persistence.py`. First widen the top import (line 2) from:

```python
from myhome.models import Floor, House, HouseDocument, Opening, Wall
```

to:

```python
from myhome.models import Floor, FurnitureObject, House, HouseDocument, Opening, Wall
```

Then add this test at the end of the file:

```python
def test_round_trip_preserves_furniture_params(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = make_doc()
    doc.floors[0].furnitureObjects = [
        FurnitureObject(
            id="fo1", templateId="sofa", x=1.0, y=2.0, width=2.2, height=0.9, rotation=0,
            params={"shape": "l-shaped", "corner": "se"},
        )
    ]
    save_house(HOME_ID, doc)
    loaded = load_house(HOME_ID)
    assert loaded.floors[0].furnitureObjects[0].params == {"shape": "l-shaped", "corner": "se"}
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd packages/geometry && npx tsc --noEmit`
Expected: FAIL — `Object literal may only specify known properties, and 'params' does not exist in type 'FurnitureObject'`.

Run: `cd packages/backend && python -m pytest tests/test_persistence.py -v -k furniture_params`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'params'` (Pydantic model doesn't declare the field).

- [x] **Step 3: Add the field**

In `packages/geometry/src/types.ts`, replace the `FurnitureObject` interface:

```ts
export interface FurnitureObject {
  id: string;
  templateId: string;
  x: number;       // world coords, meters, center of object
  y: number;
  width: number;   // meters
  height: number;  // meters
  rotation: number; // degrees, clockwise
  params?: Record<string, string | number>; // per-instance template parameters, keyed by FurnitureParamDef.id
}
```

In `packages/backend/src/myhome/models.py`, find the `FurnitureObject` model and add the field:

```python
class FurnitureObject(BaseModel):
    id: str
    templateId: str
    x: float
    y: float
    width: float
    height: float
    rotation: float
    params: dict[str, str | float] | None = None
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd packages/geometry && npx tsc --noEmit && npx vitest run test/types.test.ts`
Run: `cd packages/backend && python -m pytest tests/test_persistence.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add packages/geometry/src/types.ts packages/geometry/test/types.test.ts packages/backend/src/myhome/models.py packages/backend/tests/test_persistence.py
git commit -m "feat(geometry): add optional params field to FurnitureObject"
```

---

### Task 2: `furnitureLibrary.ts` plumbing — param schema types, resolve helpers, Structural category, Stairs template

**Files:**
- Modify: `packages/editor/src/lib/furnitureLibrary.ts`
- Test: `packages/editor/test/furnitureLibrary.test.ts`

**Interfaces:**
- Consumes: `FurnitureObject.params` from Task 1.
- Produces: `FurnitureParamDef` type, `FurnitureRenderContext` type, `FurnitureTemplate.params?: FurnitureParamDef[]`, `FurnitureTemplate.render?: (ctx: FurnitureRenderContext) => string`, `defaultFurnitureParams(template): Record<string, string | number> | undefined`, `resolveFurnitureParams(template, object): Record<string, string | number>`, `resolveFurnitureSvg(template, object): string`. `FurnitureCategory` includes `"structural"`. `getTemplate("stairs")` returns a template with no `params`. These names/signatures are used unchanged by every later task.

- [x] **Step 1: Write the failing tests**

Add to `packages/editor/test/furnitureLibrary.test.ts`. First widen the import at the top (line 2) from:

```ts
import { FURNITURE_TEMPLATES, getTemplate, FURNITURE_CATEGORIES } from "../src/lib/furnitureLibrary";
```

to:

```ts
import {
  FURNITURE_TEMPLATES,
  getTemplate,
  FURNITURE_CATEGORIES,
  defaultFurnitureParams,
  resolveFurnitureParams,
  resolveFurnitureSvg,
} from "../src/lib/furnitureLibrary";
import type { FurnitureObject } from "@myhome/geometry";
```

Then add these tests at the end of the `describe("furnitureLibrary", ...)` block (before its closing `});`):

```ts
  it("includes the structural category with a Stairs template that has no params", () => {
    expect(FURNITURE_CATEGORIES).toContain("structural");
    const stairs = getTemplate("stairs");
    expect(stairs).toBeDefined();
    expect(stairs?.category).toBe("structural");
    expect(stairs?.params).toBeUndefined();
    expect(stairs?.render).toBeUndefined();
  });

  it("defaultFurnitureParams returns undefined for templates without a params schema", () => {
    const t = getTemplate("coffee-table")!;
    expect(defaultFurnitureParams(t)).toBeUndefined();
  });

  it("resolveFurnitureSvg falls back to static svgContent when template.render is absent", () => {
    const t = getTemplate("coffee-table")!;
    const obj: FurnitureObject = { id: "f1", templateId: "coffee-table", x: 0, y: 0, width: 1.2, height: 0.6, rotation: 0 };
    expect(resolveFurnitureSvg(t, obj)).toBe(t.svgContent);
  });
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/furnitureLibrary.test.ts`
Expected: FAIL — `defaultFurnitureParams`/`resolveFurnitureParams`/`resolveFurnitureSvg` are not exported, `getTemplate("stairs")` is `undefined`, `FURNITURE_CATEGORIES` doesn't contain `"structural"`.

- [x] **Step 3: Implement**

In `packages/editor/src/lib/furnitureLibrary.ts`, replace the top of the file (lines 1–31, from `export type FurnitureCategory` through the `FurnitureTemplate` interface) with:

```ts
export type FurnitureCategory =
  | "living-room"
  | "bedroom"
  | "kitchen-dining"
  | "bathroom"
  | "office"
  | "outdoor"
  | "garden"
  | "structural";

export const FURNITURE_CATEGORIES: FurnitureCategory[] = [
  "living-room", "bedroom", "kitchen-dining", "bathroom", "office", "outdoor", "garden", "structural",
];

export const CATEGORY_LABELS: Record<FurnitureCategory, string> = {
  "living-room": "Living Room",
  "bedroom": "Bedroom",
  "kitchen-dining": "Kitchen & Dining",
  "bathroom": "Bathroom",
  "office": "Office",
  "outdoor": "Outdoor",
  "garden": "Garden",
  "structural": "Structural",
};

/** A single configurable parameter a furniture template exposes to the user. */
export type FurnitureParamDef =
  | { id: string; type: "integer"; labelKey: string; min: number; max: number; default: number }
  | { id: string; type: "number"; labelKey: string; min: number; max: number; step?: number; unit?: string; default: number }
  | {
      id: string;
      type: "enum";
      labelKey: string;
      options: { value: string; labelKey: string }[];
      default: string;
      /** Hide this field in the params panel unless another param currently equals a given value. */
      visibleWhen?: { paramId: string; equals: string };
    };

/** Passed to a template's `render` function: the instance's real size and resolved params. */
export interface FurnitureRenderContext {
  width: number;  // meters, from the FurnitureObject instance
  height: number; // meters
  params: Record<string, string | number>; // schema defaults merged with the instance's own params
}

export interface FurnitureTemplate {
  id: string;
  label: string;
  category: FurnitureCategory;
  defaultWidth: number;
  defaultHeight: number;
  svgContent: string; // static fallback; always used by the library picker's thumbnail
  params?: FurnitureParamDef[]; // omitted for templates with no configurable parameters
  render?: (ctx: FurnitureRenderContext) => string; // when present, used instead of svgContent for on-canvas rendering
}
```

Then, immediately after the closing `];` of `FURNITURE_TEMPLATES` (currently followed by `export function getTemplate...`), insert a new `// ── Structural ──` section into the array itself. Find the end of the `// ── Garden ──` section — the `grass-patch` entry — and add a new entry right after it (still inside the `FURNITURE_TEMPLATES` array, before the closing `];`):

```ts
  // ── Structural ──────────────────────────────────────────
  {
    id: "stairs",
    label: "Stairs",
    category: "structural",
    defaultWidth: 1.0,
    defaultHeight: 3.0,
    svgContent: `
      <rect x="5" y="5" width="90" height="90" rx="2"/>
      <line x1="5" y1="76" x2="24" y2="76" fill="none"/>
      <line x1="24" y1="76" x2="24" y2="57" fill="none"/>
      <line x1="24" y1="57" x2="43" y2="57" fill="none"/>
      <line x1="43" y1="57" x2="43" y2="38" fill="none"/>
      <line x1="43" y1="38" x2="62" y2="38" fill="none"/>
      <line x1="62" y1="38" x2="62" y2="19" fill="none"/>
      <line x1="62" y1="19" x2="81" y2="19" fill="none"/>
    `,
  },
```

Finally, after the existing `getTemplate` function at the bottom of the file, add the three resolve helpers:

```ts
export function defaultFurnitureParams(template: FurnitureTemplate): Record<string, string | number> | undefined {
  if (!template.params || template.params.length === 0) return undefined;
  return Object.fromEntries(template.params.map((p) => [p.id, p.default]));
}

export function resolveFurnitureParams(
  template: FurnitureTemplate,
  object: { params?: Record<string, string | number> }
): Record<string, string | number> {
  return { ...defaultFurnitureParams(template), ...object.params };
}

export function resolveFurnitureSvg(
  template: FurnitureTemplate,
  object: { width: number; height: number; params?: Record<string, string | number> }
): string {
  if (!template.render) return template.svgContent;
  return template.render({ width: object.width, height: object.height, params: resolveFurnitureParams(template, object) });
}
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx tsc --noEmit --project tsconfig.json && npx vitest run test/furnitureLibrary.test.ts`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add packages/editor/src/lib/furnitureLibrary.ts packages/editor/test/furnitureLibrary.test.ts
git commit -m "feat(editor): add furniture param schema plumbing, Structural category, Stairs template"
```

---

### Task 3: Table chair-count parameter (Dining Table rect + Round Table)

**Files:**
- Modify: `packages/editor/src/lib/furnitureLibrary.ts`
- Test: `packages/editor/test/furnitureLibrary.test.ts`

**Interfaces:**
- Consumes: `FurnitureParamDef`, `FurnitureRenderContext` from Task 2.
- Produces: `computeRectTableChairPositions(chairCount): ChairPosition[]`, `computeRoundTableChairPositions(chairCount): ChairPosition[]`, `ChairPosition = { x: number; y: number; rotation: number }` — exported for direct unit testing. `dining-table-rect` and `dining-table-round` templates gain `params: [{ id: "chairCount", ... }]` and a `render` function.

- [x] **Step 1: Write the failing tests**

Add to `packages/editor/test/furnitureLibrary.test.ts`. Widen the import again to include the new exports:

```ts
import {
  FURNITURE_TEMPLATES,
  getTemplate,
  FURNITURE_CATEGORIES,
  defaultFurnitureParams,
  resolveFurnitureParams,
  resolveFurnitureSvg,
  computeRectTableChairPositions,
  computeRoundTableChairPositions,
} from "../src/lib/furnitureLibrary";
```

Add tests:

```ts
  it("computeRectTableChairPositions distributes chairs evenly across all 4 sides", () => {
    expect(computeRectTableChairPositions(0)).toEqual([]);
    expect(computeRectTableChairPositions(4)).toHaveLength(4);
    expect(computeRectTableChairPositions(8)).toHaveLength(8);
  });

  it("computeRoundTableChairPositions spaces chairs evenly by angle", () => {
    expect(computeRoundTableChairPositions(0)).toEqual([]);
    const four = computeRoundTableChairPositions(4);
    expect(four).toHaveLength(4);
    // angle 0 -> straight above table center (50,50)
    expect(four[0].x).toBeCloseTo(50, 5);
    expect(four[0].y).toBeLessThan(50);
    // angle 90 -> straight right of center
    expect(four[1].x).toBeGreaterThan(50);
    expect(four[1].y).toBeCloseTo(50, 5);
  });

  it("dining-table-rect declares a chairCount param and renders that many chair markers", () => {
    const t = getTemplate("dining-table-rect")!;
    expect(t.params?.find((p) => p.id === "chairCount")).toBeDefined();
    const obj: FurnitureObject = { id: "f1", templateId: "dining-table-rect", x: 0, y: 0, width: 1.6, height: 0.9, rotation: 0, params: { chairCount: 6 } };
    const svg = resolveFurnitureSvg(t, obj);
    expect((svg.match(/<rect/g) ?? []).length).toBe(1 /* table */ + 6 /* chairs */);
  });

  it("dining-table-round declares a chairCount param and renders that many chair markers", () => {
    const t = getTemplate("dining-table-round")!;
    expect(t.params?.find((p) => p.id === "chairCount")).toBeDefined();
    const obj: FurnitureObject = { id: "f2", templateId: "dining-table-round", x: 0, y: 0, width: 1.2, height: 1.2, rotation: 0, params: { chairCount: 3 } };
    const svg = resolveFurnitureSvg(t, obj);
    expect(svg).toContain("<circle");
    expect((svg.match(/<rect/g) ?? []).length).toBe(3);
  });

  it("a table with chairCount 0 renders the table with no chairs", () => {
    const t = getTemplate("dining-table-rect")!;
    const obj: FurnitureObject = { id: "f3", templateId: "dining-table-rect", x: 0, y: 0, width: 1.6, height: 0.9, rotation: 0, params: { chairCount: 0 } };
    const svg = resolveFurnitureSvg(t, obj);
    expect((svg.match(/<rect/g) ?? []).length).toBe(1);
  });
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/furnitureLibrary.test.ts`
Expected: FAIL — `computeRectTableChairPositions`/`computeRoundTableChairPositions` not exported, `dining-table-rect`/`dining-table-round` have no `params`, `resolveFurnitureSvg` falls back to their static `svgContent` (1 `<rect>`, no chairs).

- [x] **Step 3: Implement**

In `packages/editor/src/lib/furnitureLibrary.ts`, find the `dining-table-rect` entry (in the `// ── Kitchen & Dining ──` section) and replace it:

```ts
  {
    id: "dining-table-rect",
    label: "Dining Table",
    category: "kitchen-dining",
    defaultWidth: 1.6,
    defaultHeight: 0.9,
    svgContent: `
      <rect x="10" y="10" width="80" height="80" rx="3"/>
    `,
    params: [
      { id: "chairCount", type: "integer", labelKey: "floorPlan.furnitureLibrary.params.chairCount", min: 0, max: 8, default: 4 },
    ],
    render: renderDiningTableRect,
  },
```

Find the `dining-table-round` entry and replace it:

```ts
  {
    id: "dining-table-round",
    label: "Round Table",
    category: "kitchen-dining",
    defaultWidth: 1.2,
    defaultHeight: 1.2,
    svgContent: `
      <circle cx="50" cy="50" r="42"/>
    `,
    params: [
      { id: "chairCount", type: "integer", labelKey: "floorPlan.furnitureLibrary.params.chairCount", min: 0, max: 8, default: 4 },
    ],
    render: renderDiningTableRound,
  },
```

Then, after the `resolveFurnitureSvg` helper added in Task 2, add the chair-position helpers and render functions:

```ts
export interface ChairPosition {
  x: number;
  y: number;
  rotation: number; // degrees, so the chair's back faces away from the table
}

export function computeRectTableChairPositions(chairCount: number): ChairPosition[] {
  if (chairCount <= 0) return [];
  const positions: ChairPosition[] = [];
  const sides: Array<"top" | "right" | "bottom" | "left"> = ["top", "right", "bottom", "left"];
  const perSide = Math.ceil(chairCount / 4);
  let remaining = chairCount;
  for (const side of sides) {
    const count = Math.min(perSide, remaining);
    for (let i = 0; i < count; i++) {
      const t = (i + 1) / (count + 1);
      if (side === "top") positions.push({ x: 10 + t * 80, y: -8, rotation: 180 });
      else if (side === "bottom") positions.push({ x: 10 + t * 80, y: 108, rotation: 0 });
      else if (side === "left") positions.push({ x: -8, y: 10 + t * 80, rotation: 90 });
      else positions.push({ x: 108, y: 10 + t * 80, rotation: 270 });
    }
    remaining -= count;
    if (remaining <= 0) break;
  }
  return positions;
}

export function computeRoundTableChairPositions(chairCount: number): ChairPosition[] {
  if (chairCount <= 0) return [];
  const positions: ChairPosition[] = [];
  for (let i = 0; i < chairCount; i++) {
    const angle = (360 / chairCount) * i;
    const rad = (angle * Math.PI) / 180;
    positions.push({ x: 50 + 58 * Math.sin(rad), y: 50 - 58 * Math.cos(rad), rotation: angle });
  }
  return positions;
}

function chairMarker(pos: ChairPosition): string {
  return `<rect x="${(pos.x - 8).toFixed(2)}" y="${(pos.y - 7).toFixed(2)}" width="16" height="14" rx="2" transform="rotate(${pos.rotation.toFixed(2)} ${pos.x.toFixed(2)} ${pos.y.toFixed(2)})"/>`;
}

function renderDiningTableRect(ctx: FurnitureRenderContext): string {
  const chairCount = typeof ctx.params.chairCount === "number" ? ctx.params.chairCount : 4;
  const table = `<rect x="10" y="10" width="80" height="80" rx="3"/>`;
  const chairs = computeRectTableChairPositions(chairCount).map(chairMarker).join("\n");
  return [table, chairs].filter(Boolean).join("\n");
}

function renderDiningTableRound(ctx: FurnitureRenderContext): string {
  const chairCount = typeof ctx.params.chairCount === "number" ? ctx.params.chairCount : 4;
  const table = `<circle cx="50" cy="50" r="42"/>`;
  const chairs = computeRoundTableChairPositions(chairCount).map(chairMarker).join("\n");
  return [table, chairs].filter(Boolean).join("\n");
}
```

(`renderDiningTableRect`/`renderDiningTableRound` are referenced by name inside the `FURNITURE_TEMPLATES` array above — this works because `function` declarations are hoisted to the top of the module, so the array literal can reference them even though they're defined later in the file, exactly like `getTemplate` already does for the array.)

- [x] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx tsc --noEmit --project tsconfig.json && npx vitest run test/furnitureLibrary.test.ts`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add packages/editor/src/lib/furnitureLibrary.ts packages/editor/test/furnitureLibrary.test.ts
git commit -m "feat(editor): add chairCount parameter to dining and round tables"
```

---

### Task 4: Sofa shape + corner parameter (L-shaped sofa)

**Files:**
- Modify: `packages/editor/src/lib/furnitureLibrary.ts`
- Test: `packages/editor/test/furnitureLibrary.test.ts`

**Interfaces:**
- Consumes: `FurnitureParamDef`, `FurnitureRenderContext` from Task 2.
- Produces: `sofa` template gains `params: [{id: "shape", ...}, {id: "corner", ...}]` and a `render` function. `defaultFurnitureParams(getTemplate("sofa"))` now returns `{ shape: "straight", corner: "se" }` — used by Task 7's `addFurniture` seeding test.

- [x] **Step 1: Write the failing tests**

Add to `packages/editor/test/furnitureLibrary.test.ts`:

```ts
  it("sofa declares shape and corner params, with corner defaulting to se", () => {
    const t = getTemplate("sofa")!;
    expect(defaultFurnitureParams(t)).toEqual({ shape: "straight", corner: "se" });
  });

  it("sofa corner param is visibleWhen shape is l-shaped", () => {
    const t = getTemplate("sofa")!;
    const corner = t.params?.find((p) => p.id === "corner");
    expect(corner?.visibleWhen).toEqual({ paramId: "shape", equals: "l-shaped" });
  });

  it("renders the original straight sofa markup when shape is straight", () => {
    const t = getTemplate("sofa")!;
    const obj: FurnitureObject = { id: "f1", templateId: "sofa", x: 0, y: 0, width: 2.2, height: 0.9, rotation: 0, params: { shape: "straight" } };
    const svg = resolveFurnitureSvg(t, obj);
    expect(svg).toContain('x="8" y="18" width="84" height="68"');
  });

  it("renders an L-shape with the chaise at the requested corner", () => {
    const t = getTemplate("sofa")!;
    const nw: FurnitureObject = { id: "f2", templateId: "sofa", x: 0, y: 0, width: 2.2, height: 2.0, rotation: 0, params: { shape: "l-shaped", corner: "nw" } };
    const se: FurnitureObject = { id: "f3", templateId: "sofa", x: 0, y: 0, width: 2.2, height: 2.0, rotation: 0, params: { shape: "l-shaped", corner: "se" } };
    const svgNw = resolveFurnitureSvg(t, nw);
    const svgSe = resolveFurnitureSvg(t, se);
    expect(svgNw).toContain('x="5" y="5" width="90" height="40"'); // horizontal arm at top
    expect(svgNw).toContain('x="5" y="5" width="40" height="90"'); // vertical arm at left
    expect(svgSe).toContain('x="5" y="55" width="90" height="40"'); // horizontal arm at bottom
    expect(svgSe).toContain('x="55" y="5" width="40" height="90"'); // vertical arm at right
  });
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/furnitureLibrary.test.ts`
Expected: FAIL — `sofa` has no `params`, so `defaultFurnitureParams` returns `undefined` and `resolveFurnitureSvg` always returns the static straight-sofa markup regardless of requested shape/corner.

- [x] **Step 3: Implement**

In `packages/editor/src/lib/furnitureLibrary.ts`, find the `sofa` entry (first entry in `// ── Living Room ──`) and replace it:

```ts
  {
    id: "sofa",
    label: "Sofa",
    category: "living-room",
    defaultWidth: 2.2,
    defaultHeight: 0.9,
    svgContent: `
      <rect x="8" y="18" width="84" height="68" rx="6"/>
      <rect x="8" y="18" width="84" height="22" rx="4"/>
      <rect x="8" y="40" width="14" height="46" rx="3"/>
      <rect x="78" y="40" width="14" height="46" rx="3"/>
      <line x1="42" y1="40" x2="42" y2="86" fill="none" stroke-width="1.5"/>
      <line x1="58" y1="40" x2="58" y2="86" fill="none" stroke-width="1.5"/>
    `,
    params: [
      {
        id: "shape",
        type: "enum",
        labelKey: "floorPlan.furnitureLibrary.params.sofaShape",
        options: [
          { value: "straight", labelKey: "floorPlan.furnitureLibrary.params.sofaShapeStraight" },
          { value: "l-shaped", labelKey: "floorPlan.furnitureLibrary.params.sofaShapeLShaped" },
        ],
        default: "straight",
      },
      {
        id: "corner",
        type: "enum",
        labelKey: "floorPlan.furnitureLibrary.params.sofaCorner",
        options: [
          { value: "nw", labelKey: "floorPlan.furnitureLibrary.params.cornerNw" },
          { value: "ne", labelKey: "floorPlan.furnitureLibrary.params.cornerNe" },
          { value: "se", labelKey: "floorPlan.furnitureLibrary.params.cornerSe" },
          { value: "sw", labelKey: "floorPlan.furnitureLibrary.params.cornerSw" },
        ],
        default: "se",
        visibleWhen: { paramId: "shape", equals: "l-shaped" },
      },
    ],
    render: renderSofa,
  },
```

Then, after the table render functions added in Task 3, add:

```ts
function renderSofa(ctx: FurnitureRenderContext): string {
  const shape = ctx.params.shape === "l-shaped" ? "l-shaped" : "straight";
  if (shape === "straight") {
    return `
      <rect x="8" y="18" width="84" height="68" rx="6"/>
      <rect x="8" y="18" width="84" height="22" rx="4"/>
      <rect x="8" y="40" width="14" height="46" rx="3"/>
      <rect x="78" y="40" width="14" height="46" rx="3"/>
      <line x1="42" y1="40" x2="42" y2="86" fill="none" stroke-width="1.5"/>
      <line x1="58" y1="40" x2="58" y2="86" fill="none" stroke-width="1.5"/>
    `;
  }
  const corner = typeof ctx.params.corner === "string" ? ctx.params.corner : "se";
  const north = corner === "nw" || corner === "ne";
  const west = corner === "nw" || corner === "sw";
  const armY = north ? 5 : 55;
  const chaiseX = west ? 5 : 55;
  return `
    <rect x="5" y="${armY}" width="90" height="40" rx="6"/>
    <rect x="${chaiseX}" y="5" width="40" height="90" rx="6"/>
  `;
}
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx tsc --noEmit --project tsconfig.json && npx vitest run test/furnitureLibrary.test.ts`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add packages/editor/src/lib/furnitureLibrary.ts packages/editor/test/furnitureLibrary.test.ts
git commit -m "feat(editor): add L-shaped sofa via shape/corner parameters"
```

---

### Task 5: Deck/Terrace plank pattern parameter

**Files:**
- Modify: `packages/editor/src/lib/furnitureLibrary.ts`
- Test: `packages/editor/test/furnitureLibrary.test.ts`

**Interfaces:**
- Consumes: `FurnitureParamDef`, `FurnitureRenderContext` from Task 2.
- Produces: `computeDeckPlankLayout(widthM, heightM, plankWidthCm, plankLengthCm): { rows: number; rowHeightLocal: number; plankLengthLocal: number; planksPerRow: number }` — exported for direct unit testing. `deck-terrace` template gains `params: [{id: "plankWidth", ...}, {id: "plankLength", ...}]` and a `render` function.

- [x] **Step 1: Write the failing tests**

Add to `packages/editor/test/furnitureLibrary.test.ts`. Widen the import once more:

```ts
import {
  FURNITURE_TEMPLATES,
  getTemplate,
  FURNITURE_CATEGORIES,
  defaultFurnitureParams,
  resolveFurnitureParams,
  resolveFurnitureSvg,
  computeRectTableChairPositions,
  computeRoundTableChairPositions,
  computeDeckPlankLayout,
} from "../src/lib/furnitureLibrary";
```

Add tests:

```ts
  it("computeDeckPlankLayout adds more rows as the deck gets taller (fixed real plank width)", () => {
    const short = computeDeckPlankLayout(4, 3, 14, 200);
    const tall = computeDeckPlankLayout(4, 6, 14, 200);
    // Doubling the real height should roughly double the row count (rounding
    // to a whole number of rows means it won't land on an exact 2x).
    expect(tall.rows).toBeGreaterThan(short.rows * 1.8);
    expect(tall.rows).toBeLessThan(short.rows * 2.3);
  });

  it("computeDeckPlankLayout adds more planks per row as the deck gets wider (fixed real plank length)", () => {
    const narrow = computeDeckPlankLayout(4, 3, 14, 200);
    const wide = computeDeckPlankLayout(8, 3, 14, 200);
    expect(wide.planksPerRow).toBeGreaterThan(narrow.planksPerRow);
  });

  it("deck-terrace declares plankWidth and plankLength params and renders a plank grid", () => {
    const t = getTemplate("deck-terrace")!;
    expect(t.params?.map((p) => p.id)).toEqual(["plankWidth", "plankLength"]);
    const obj: FurnitureObject = { id: "f1", templateId: "deck-terrace", x: 0, y: 0, width: 4, height: 3, rotation: 0, params: { plankWidth: 14, plankLength: 200 } };
    const svg = resolveFurnitureSvg(t, obj);
    expect(svg).toContain("<rect"); // background + plank cells
    expect((svg.match(/<rect/g) ?? []).length).toBeGreaterThan(1);
  });
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/furnitureLibrary.test.ts`
Expected: FAIL — `computeDeckPlankLayout` not exported; `deck-terrace` has no `params`, so `resolveFurnitureSvg` falls back to the static 4-fixed-line template regardless of size.

- [x] **Step 3: Implement**

In `packages/editor/src/lib/furnitureLibrary.ts`, find the `deck-terrace` entry (in `// ── Garden ──`) and replace it:

```ts
  {
    id: "deck-terrace",
    label: "Deck / Terrace",
    category: "garden",
    defaultWidth: 4.0,
    defaultHeight: 3.0,
    svgContent: `
      <rect x="5" y="5" width="90" height="90" rx="2"/>
      <line x1="5" y1="22" x2="95" y2="22" fill="none"/>
      <line x1="5" y1="39" x2="95" y2="39" fill="none"/>
      <line x1="5" y1="56" x2="95" y2="56" fill="none"/>
      <line x1="5" y1="73" x2="95" y2="73" fill="none"/>
    `,
    params: [
      { id: "plankWidth", type: "number", labelKey: "floorPlan.furnitureLibrary.params.plankWidth", unit: "cm", min: 5, max: 30, step: 1, default: 14 },
      { id: "plankLength", type: "number", labelKey: "floorPlan.furnitureLibrary.params.plankLength", unit: "cm", min: 50, max: 400, step: 10, default: 200 },
    ],
    render: renderDeckTerrace,
  },
```

Then, after the sofa render function added in Task 4, add:

```ts
export function computeDeckPlankLayout(
  widthM: number,
  heightM: number,
  plankWidthCm: number,
  plankLengthCm: number
): { rows: number; rowHeightLocal: number; plankLengthLocal: number; planksPerRow: number } {
  const w = Math.max(widthM, 0.01);
  const h = Math.max(heightM, 0.01);
  const localPlankHeight = ((plankWidthCm / 100) / h) * 100;
  const localPlankLength = Math.max(((plankLengthCm / 100) / w) * 100, 1);
  const rows = Math.max(1, Math.round(100 / Math.max(localPlankHeight, 1)));
  const planksPerRow = Math.max(1, Math.ceil(100 / localPlankLength) + 1);
  return { rows, rowHeightLocal: 100 / rows, plankLengthLocal: localPlankLength, planksPerRow };
}

function renderDeckTerrace(ctx: FurnitureRenderContext): string {
  const plankWidthCm = typeof ctx.params.plankWidth === "number" ? ctx.params.plankWidth : 14;
  const plankLengthCm = typeof ctx.params.plankLength === "number" ? ctx.params.plankLength : 200;
  const { rows, rowHeightLocal, plankLengthLocal, planksPerRow } = computeDeckPlankLayout(ctx.width, ctx.height, plankWidthCm, plankLengthCm);

  const parts: string[] = [`<rect x="0" y="0" width="100" height="100" rx="1"/>`];
  for (let r = 0; r < rows; r++) {
    const y = r * rowHeightLocal;
    const offset = r % 2 === 0 ? 0 : -plankLengthLocal / 2;
    for (let p = 0; p < planksPerRow; p++) {
      const x = offset + p * plankLengthLocal;
      const clippedX = Math.max(x, 0);
      const clippedRight = Math.min(x + plankLengthLocal, 100);
      const w = clippedRight - clippedX;
      if (w <= 0) continue;
      parts.push(`<rect x="${clippedX.toFixed(2)}" y="${y.toFixed(2)}" width="${w.toFixed(2)}" height="${rowHeightLocal.toFixed(2)}" fill="none"/>`);
    }
  }
  return parts.join("\n");
}
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx tsc --noEmit --project tsconfig.json && npx vitest run test/furnitureLibrary.test.ts`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add packages/editor/src/lib/furnitureLibrary.ts packages/editor/test/furnitureLibrary.test.ts
git commit -m "feat(editor): add real-scale plank pattern to Deck/Terrace via plankWidth/plankLength"
```

---

### Task 6: `FurnitureShape.svelte` — render via `resolveFurnitureSvg`

**Files:**
- Modify: `packages/editor/src/lib/components/FurnitureShape.svelte`
- Test: `packages/editor/test/FurnitureShape.test.ts`

**Interfaces:**
- Consumes: `resolveFurnitureSvg` from Task 2/3/4/5.
- Produces: no prop changes — rendering-only.

- [x] **Step 1: Write the failing tests**

Add to `packages/editor/test/FurnitureShape.test.ts`, at the end of the `describe("FurnitureShape", ...)` block:

```ts
  it("falls back to static svgContent for templates without a render function", () => {
    const object = makeSofa();
    // makeSofa's sofa now has shape/corner params (Task 4), but pass none so defaults apply — still exercises the render() path, so use coffee-table here for the "no render()" case.
    const coffeeObject = { id: "f2", templateId: "coffee-table", x: 1, y: 1, width: 1.2, height: 0.6, rotation: 0 };
    const template = getTemplate("coffee-table")!;
    setup({ object: coffeeObject, template, viewport: VP, selected: false, tool: "select" });
    expect(svg.querySelector("rect")).not.toBeNull();
  });

  it("renders via template.render when present, reflecting object.params", () => {
    const object = { id: "f3", templateId: "sofa", x: 1, y: 1, width: 2.2, height: 2.0, rotation: 0, params: { shape: "l-shaped", corner: "nw" } };
    const template = getTemplate("sofa")!;
    setup({ object, template, viewport: VP, selected: false, tool: "select" });
    const rects = [...svg.querySelectorAll("rect")];
    expect(rects.some((r) => r.getAttribute("x") === "5" && r.getAttribute("y") === "5" && r.getAttribute("width") === "90")).toBe(true);
  });
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/FurnitureShape.test.ts`
Expected: FAIL — the second new test fails because `FurnitureShape.svelte` still reads `template.svgContent` directly, so a `sofa` with `params: { shape: "l-shaped", ... }` still renders the straight-sofa markup, not the L-shape rects.

- [x] **Step 3: Implement**

In `packages/editor/src/lib/components/FurnitureShape.svelte`, update the import (line 5) from:

```ts
  import type { FurnitureTemplate } from "../furnitureLibrary";
```

to:

```ts
  import type { FurnitureTemplate } from "../furnitureLibrary";
  import { resolveFurnitureSvg } from "../furnitureLibrary";
```

Add a derived value after the existing `scaleY` derived (line 28):

```ts
  const svgContent = $derived(resolveFurnitureSvg(template, object));
```

Change the template's `{@html template.svgContent}` (line 51) to:

```svelte
  {@html svgContent}
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/FurnitureShape.test.ts`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/FurnitureShape.svelte packages/editor/test/FurnitureShape.test.ts
git commit -m "feat(editor): render furniture via resolveFurnitureSvg (params-aware)"
```

---

### Task 7: `houseStore` — `updateFurnitureParams` + param-default seeding in `addFurniture`

**Files:**
- Modify: `packages/editor/src/lib/houseStore.svelte.ts`
- Test: `packages/editor/test/houseStore.furniture.test.ts`

**Interfaces:**
- Consumes: `getTemplate`, `defaultFurnitureParams` from `./furnitureLibrary` (Task 2).
- Produces: `updateFurnitureParams(id: string, patch: Record<string, string | number>): void`, returned from `createHouseStore(...)` alongside the other furniture methods. `addFurniture(templateId, x, y, width, height)` now sets `params` on the created object when the template declares any.

- [x] **Step 1: Write the failing tests**

Add to `packages/editor/test/houseStore.furniture.test.ts`, at the end of the `describe("houseStore furniture methods", ...)` block:

```ts
  it("addFurniture seeds params from the template's schema defaults", () => {
    store.addFurniture("sofa", 0, 0, 2.2, 0.9);
    expect(store.currentFurniture[0].params).toEqual({ shape: "straight", corner: "se" });
  });

  it("addFurniture leaves params undefined for templates without a schema", () => {
    store.addFurniture("coffee-table", 0, 0, 1.2, 0.6);
    expect(store.currentFurniture[0].params).toBeUndefined();
  });

  it("updateFurnitureParams merges a patch into object.params with history", () => {
    store.addFurniture("sofa", 0, 0, 2.2, 0.9);
    const id = store.currentFurniture[0].id;
    const gen0 = store.generation;
    store.updateFurnitureParams(id, { shape: "l-shaped" });
    const obj = store.currentFurniture.find((f) => f.id === id)!;
    expect(obj.params).toEqual({ shape: "l-shaped", corner: "se" });
    expect(store.generation).toBeGreaterThan(gen0);
  });

  it("updateFurnitureParams supports undo", () => {
    store.addFurniture("sofa", 0, 0, 2.2, 0.9);
    const id = store.currentFurniture[0].id;
    store.updateFurnitureParams(id, { shape: "l-shaped" });
    store.undo();
    const obj = store.currentFurniture.find((f) => f.id === id)!;
    expect(obj.params?.shape).toBe("straight");
  });

  it("updateFurnitureParams is a no-op for an unknown id", () => {
    store.addFurniture("sofa", 0, 0, 2.2, 0.9);
    store.updateFurnitureParams("nonexistent", { shape: "l-shaped" });
    expect(store.currentFurniture[0].params?.shape).toBe("straight");
  });
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/houseStore.furniture.test.ts`
Expected: FAIL — `addFurniture` never sets `params`, and `store.updateFurnitureParams` doesn't exist.

- [x] **Step 3: Implement**

In `packages/editor/src/lib/houseStore.svelte.ts`, add an import after the existing `createEmptyHouse` import (line 3):

```ts
import { getTemplate, defaultFurnitureParams } from "./furnitureLibrary";
```

Replace `addFurniture` (currently lines 215–225):

```ts
  function addFurniture(
    templateId: string,
    x: number,
    y: number,
    width: number,
    height: number
  ): void {
    saveSnapshot();
    const template = getTemplate(templateId);
    const params = template ? defaultFurnitureParams(template) : undefined;
    const obj: FurnitureObject = { id: genId(), templateId, x, y, width, height, rotation: 0, ...(params ? { params } : {}) };
    ensureFurniture(currentFloor()).push(obj);
  }
```

Add `updateFurnitureParams` right after `rotateFurniture` (which currently ends around line 268, just before the `// API load/save` comment):

```ts
  function updateFurnitureParams(id: string, patch: Record<string, string | number>): void {
    const obj = ensureFurniture(currentFloor()).find((f) => f.id === id);
    if (!obj) return;
    saveSnapshot();
    obj.params = { ...obj.params, ...patch };
  }
```

Finally, add `updateFurnitureParams` to the object returned from `createHouseStore` (in the same list as `addFurniture`, `removeFurniture`, `moveFurniture`, `resizeFurniture`, `rotateFurniture`):

```ts
    addFurniture,
    removeFurniture,
    moveFurniture,
    resizeFurniture,
    rotateFurniture,
    updateFurnitureParams,
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/houseStore.furniture.test.ts`
Expected: PASS

Run: `cd packages/editor && npx tsc --noEmit --project tsconfig.json`
Expected: PASS (no regressions from the new import/return field)

- [x] **Step 5: Commit**

```bash
git add packages/editor/src/lib/houseStore.svelte.ts packages/editor/test/houseStore.furniture.test.ts
git commit -m "feat(editor): seed furniture params on add, add updateFurnitureParams to houseStore"
```

---

### Task 8: `FurnitureParamsPanel.svelte` + i18n keys

**Files:**
- Create: `packages/editor/src/lib/components/FurnitureParamsPanel.svelte`
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`
- Test: `packages/editor/test/FurnitureParamsPanel.test.ts`

**Interfaces:**
- Consumes: `resolveFurnitureParams`, `FurnitureParamDef`, `FurnitureTemplate` from `../furnitureLibrary` (Task 2); `FurnitureObject` from `@myhome/geometry`.
- Produces: `FurnitureParamsPanel` component with props `{ object: FurnitureObject; template: FurnitureTemplate; readOnly?: boolean; onupdate: (patch: Record<string, string | number>) => void; onstartdrag?: (e: PointerEvent) => void; ondismiss?: () => void }` — consumed by Task 9's `App.svelte` wiring.

- [x] **Step 1: Write the failing tests**

Create `packages/editor/test/FurnitureParamsPanel.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import FurnitureParamsPanel from "../src/lib/components/FurnitureParamsPanel.svelte";
import { getTemplate } from "../src/lib/furnitureLibrary";
import type { FurnitureObject } from "@myhome/geometry";

function setup(overrides: Record<string, unknown> = {}) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const object: FurnitureObject = { id: "f1", templateId: "sofa", x: 0, y: 0, width: 2.2, height: 0.9, rotation: 0 };
  const props = {
    object,
    template: getTemplate("sofa")!,
    onupdate: vi.fn(),
    ...overrides,
  };
  const comp = mount(FurnitureParamsPanel, { target, props });
  flushSync();
  return { target, comp, props };
}

describe("FurnitureParamsPanel", () => {
  it("renders a select for each enum param, showing the resolved default value", () => {
    const { target, comp } = setup();
    const selects = target.querySelectorAll("select");
    expect(selects).toHaveLength(1); // shape is visible; corner is hidden (visibleWhen shape=l-shaped, default is straight)
    expect((selects[0] as HTMLSelectElement).value).toBe("straight");
    unmount(comp); target.remove();
  });

  it("shows the corner select once shape is l-shaped", () => {
    const object: FurnitureObject = { id: "f1", templateId: "sofa", x: 0, y: 0, width: 2.2, height: 0.9, rotation: 0, params: { shape: "l-shaped" } };
    const { target, comp } = setup({ object });
    const selects = target.querySelectorAll("select");
    expect(selects).toHaveLength(2);
    unmount(comp); target.remove();
  });

  it("calls onupdate with the param id and new value when a select changes", () => {
    const onupdate = vi.fn();
    const { target, comp } = setup({ onupdate });
    const select = target.querySelector("select") as HTMLSelectElement;
    select.value = "l-shaped";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ shape: "l-shaped" });
    unmount(comp); target.remove();
  });

  it("renders a number input for integer params, e.g. chairCount on a table", () => {
    const object: FurnitureObject = { id: "f2", templateId: "dining-table-rect", x: 0, y: 0, width: 1.6, height: 0.9, rotation: 0 };
    const { target, comp } = setup({ object, template: getTemplate("dining-table-rect")! });
    const input = target.querySelector('input[type="number"]') as HTMLInputElement;
    expect(input).not.toBeNull();
    expect(input.value).toBe("4");
    unmount(comp); target.remove();
  });

  it("calls onupdate with a numeric value when a number input changes", () => {
    const onupdate = vi.fn();
    const object: FurnitureObject = { id: "f2", templateId: "dining-table-rect", x: 0, y: 0, width: 1.6, height: 0.9, rotation: 0 };
    const { target, comp } = setup({ object, template: getTemplate("dining-table-rect")!, onupdate });
    const input = target.querySelector('input[type="number"]') as HTMLInputElement;
    input.value = "6";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ chairCount: 6 });
    unmount(comp); target.remove();
  });

  it("calls ondismiss when the close button is clicked", () => {
    const ondismiss = vi.fn();
    const { target, comp } = setup({ ondismiss });
    (target.querySelector('[title="Close"]') as HTMLElement).click();
    expect(ondismiss).toHaveBeenCalled();
    unmount(comp); target.remove();
  });
});
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/FurnitureParamsPanel.test.ts`
Expected: FAIL — `Failed to resolve import "../src/lib/components/FurnitureParamsPanel.svelte"`.

- [x] **Step 3: Add i18n keys**

In `packages/editor/src/lib/locales/en.json`, inside the `"furnitureLibrary"` object, add a new `"params"` key after `"items"` (so the object gains a third top-level key alongside `"searchPlaceholder"`, `"categories"`, `"items"`):

```json
      "params": {
        "chairCount": "Chairs",
        "sofaShape": "Shape",
        "sofaShapeStraight": "Straight",
        "sofaShapeLShaped": "L-shaped",
        "sofaCorner": "Chaise corner",
        "cornerNw": "Top-left",
        "cornerNe": "Top-right",
        "cornerSe": "Bottom-right",
        "cornerSw": "Bottom-left",
        "plankWidth": "Plank width",
        "plankLength": "Plank length"
      }
```

Also add the Stairs item label and Structural category label to the existing `"categories"`/`"items"` objects in the same file:

```json
        "structural": "Structural"
```

(added to `"categories"`, after `"garden": "Garden"`)

```json
        "stairs": "Stairs"
```

(added to `"items"`, after `"grass-patch": "Grass Patch"`)

In `packages/editor/src/lib/locales/fr.json`, make the matching additions. `"params"`:

```json
      "params": {
        "chairCount": "Chaises",
        "sofaShape": "Forme",
        "sofaShapeStraight": "Droit",
        "sofaShapeLShaped": "En L",
        "sofaCorner": "Coin du méridien",
        "cornerNw": "Haut-gauche",
        "cornerNe": "Haut-droit",
        "cornerSe": "Bas-droit",
        "cornerSw": "Bas-gauche",
        "plankWidth": "Largeur des lames",
        "plankLength": "Longueur des lames"
      }
```

`"categories"`:

```json
        "structural": "Structurel"
```

`"items"`:

```json
        "stairs": "Escalier"
```

- [x] **Step 4: Implement the component**

Create `packages/editor/src/lib/components/FurnitureParamsPanel.svelte`:

```svelte
<script lang="ts">
  import { _ } from "svelte-i18n";
  import type { FurnitureObject } from "@myhome/geometry";
  import type { FurnitureTemplate, FurnitureParamDef } from "../furnitureLibrary";
  import { resolveFurnitureParams } from "../furnitureLibrary";

  let {
    object,
    template,
    readOnly = false,
    onupdate,
    onstartdrag,
    ondismiss,
  }: {
    object: FurnitureObject;
    template: FurnitureTemplate;
    readOnly?: boolean;
    onupdate: (patch: Record<string, string | number>) => void;
    onstartdrag?: (e: PointerEvent) => void;
    ondismiss?: () => void;
  } = $props();

  const params = $derived(resolveFurnitureParams(template, object));

  function isVisible(def: FurnitureParamDef): boolean {
    if (!def.visibleWhen) return true;
    return params[def.visibleWhen.paramId] === def.visibleWhen.equals;
  }

  function isEnumParam(def: FurnitureParamDef): def is Extract<FurnitureParamDef, { type: "enum" }> {
    return def.type === "enum";
  }

  function paramMin(def: FurnitureParamDef): number | undefined {
    return def.type === "enum" ? undefined : def.min;
  }

  function paramMax(def: FurnitureParamDef): number | undefined {
    return def.type === "enum" ? undefined : def.max;
  }

  function paramStep(def: FurnitureParamDef): number {
    return def.type === "number" ? (def.step ?? 1) : 1;
  }

  function paramUnit(def: FurnitureParamDef): string | undefined {
    return def.type === "number" ? def.unit : undefined;
  }

  function handleNumberInput(def: FurnitureParamDef, e: Event): void {
    const value = Number((e.target as HTMLInputElement).value);
    if (Number.isNaN(value)) return;
    onupdate({ [def.id]: value });
  }

  function handleEnumChange(def: FurnitureParamDef, e: Event): void {
    onupdate({ [def.id]: (e.target as HTMLSelectElement).value });
  }
</script>

<aside class="furniture-params-panel">
  <div class="panel-header">
    {#if onstartdrag}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="drag-handle" onpointerdown={onstartdrag} title={$_('floorPlan.itemPicker.dragToReposition')}>⠿</div>
    {/if}
    <h2>{$_(`floorPlan.furnitureLibrary.items.${template.id}`)}</h2>
    {#if ondismiss}
      <button class="dismiss-btn" onclick={ondismiss} title={$_('common.close')}>✕</button>
    {/if}
  </div>

  {#each template.params ?? [] as def (def.id)}
    {#if isVisible(def)}
      <label>
        <span>{$_(def.labelKey)}{#if paramUnit(def)} ({paramUnit(def)}){/if}</span>
        {#if isEnumParam(def)}
          <select value={params[def.id]} disabled={readOnly} onchange={(e) => handleEnumChange(def, e)}>
            {#each def.options as opt (opt.value)}
              <option value={opt.value}>{$_(opt.labelKey)}</option>
            {/each}
          </select>
        {:else}
          <input
            type="number"
            min={paramMin(def)}
            max={paramMax(def)}
            step={paramStep(def)}
            value={params[def.id]}
            disabled={readOnly}
            oninput={(e) => handleNumberInput(def, e)}
          />
        {/if}
      </label>
    {/if}
  {/each}
</aside>

<style>
  .furniture-params-panel {
    width: 200px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
    padding: var(--space-3);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    overflow-y: auto;
  }

  @media (max-width: 480px) { /* --bp-mobile */
    .furniture-params-panel {
      width: 100%;
      height: 100%;
      border-radius: 0;
      border-left: none; border-right: none; border-bottom: none;
    }
  }

  .panel-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }
  h2 {
    flex: 1;
    min-width: 0;
    margin: 0;
    font-size: 13px;
    color: var(--text);
    font-weight: 600;
  }
  .drag-handle {
    cursor: grab;
    color: var(--text-muted);
    font-size: 14px;
    letter-spacing: 3px;
    opacity: 0.5;
    padding: 2px 0;
    flex-shrink: 0;
    border-radius: var(--radius-sm);
    user-select: none;
  }
  .drag-handle:hover { opacity: 1; background: var(--surface-hover); }
  .drag-handle:active { cursor: grabbing; }
  .dismiss-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-muted);
    flex-shrink: 0;
    padding: 2px 4px;
    border-radius: var(--radius-sm);
  }
  .dismiss-btn:hover { background: var(--surface-hover); color: var(--text); }
  label {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  span {
    font-size: 11px;
    color: var(--text-muted);
  }
  input,
  select {
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text);
    padding: 4px 6px;
    font-size: 12px;
    font-family: inherit;
  }
  input:focus,
  select:focus {
    outline: none;
    border-color: var(--accent);
  }
</style>
```

- [x] **Step 5: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/FurnitureParamsPanel.test.ts test/i18nCompleteness.test.ts`
Expected: PASS

Run: `cd packages/editor && npx tsc --noEmit --project tsconfig.json`
Expected: PASS — confirms the `isEnumParam` type-guard narrowing compiles correctly inside the template.

- [x] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/FurnitureParamsPanel.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/FurnitureParamsPanel.test.ts
git commit -m "feat(editor): add FurnitureParamsPanel for editing per-instance furniture parameters"
```

---

### Task 9: `App.svelte` wiring — show `FurnitureParamsPanel` for the selected furniture object

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Test: `packages/editor/test/App.furniture.test.ts`

**Interfaces:**
- Consumes: `FurnitureParamsPanel` (Task 8), `houseStore.updateFurnitureParams` (Task 7), `getTemplate` (already imported in `App.svelte`), `createFloatingDrag` (already imported).
- Produces: no new exports — this is the final integration point.

- [x] **Step 1: Write the failing test**

`packages/editor/test/App.furniture.test.ts` already has a `setup()` helper (mounts `App`, stubs `fetch` to 404 so the store starts with an empty floor) and an existing test (`"clicking (not dragging) a furniture item drops it at the canvas center..."`) that opens the furniture library, mocks `.canvas-area`'s bounding rect, and drops an item via a same-point pointerdown/pointerup click. Reuse that exact drop technique, then click the placed `.furniture-object` to select it (mirrors `FurnitureShape.test.ts`'s `g!.dispatchEvent(new MouseEvent("click", { bubbles: true }))`). Add these two tests to the `describe("App furniture integration", ...)` block, after the existing drop test:

```ts
  it("shows the FurnitureParamsPanel with a select once a parameterized furniture object is selected", async () => {
    app = await setup();
    const btn = Array.from(target.querySelectorAll(".floating-toolbar button")).find(
      (b) => (b as HTMLButtonElement).title === "Toggle furniture library",
    ) as HTMLButtonElement;
    btn.click();
    flushSync();

    const canvasArea = target.querySelector(".canvas-area") as HTMLElement;
    vi.spyOn(canvasArea, "getBoundingClientRect").mockReturnValue({
      left: 0, top: 0, right: 800, bottom: 600, width: 800, height: 600, x: 0, y: 0, toJSON() {},
    });

    const sofaItem = target.querySelector('.furniture-item[data-template-id="sofa"]') as HTMLElement;
    const clickX = 750, clickY = 550;
    sofaItem.dispatchEvent(new PointerEvent("pointerdown", { clientX: clickX, clientY: clickY, bubbles: true }));
    flushSync();
    canvasArea.dispatchEvent(new PointerEvent("pointerup", { clientX: clickX, clientY: clickY, bubbles: true }));
    flushSync();

    const placed = target.querySelector(".furniture-object") as SVGGElement;
    placed.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".furniture-params-panel")).not.toBeNull();
    expect(target.querySelector(".furniture-params-panel select")).not.toBeNull();
  });

  it("shows no FurnitureParamsPanel for a non-parameterized furniture object", async () => {
    app = await setup();
    const btn = Array.from(target.querySelectorAll(".floating-toolbar button")).find(
      (b) => (b as HTMLButtonElement).title === "Toggle furniture library",
    ) as HTMLButtonElement;
    btn.click();
    flushSync();

    const canvasArea = target.querySelector(".canvas-area") as HTMLElement;
    vi.spyOn(canvasArea, "getBoundingClientRect").mockReturnValue({
      left: 0, top: 0, right: 800, bottom: 600, width: 800, height: 600, x: 0, y: 0, toJSON() {},
    });

    const coffeeTableItem = target.querySelector('.furniture-item[data-template-id="coffee-table"]') as HTMLElement;
    const clickX = 750, clickY = 550;
    coffeeTableItem.dispatchEvent(new PointerEvent("pointerdown", { clientX: clickX, clientY: clickY, bubbles: true }));
    flushSync();
    canvasArea.dispatchEvent(new PointerEvent("pointerup", { clientX: clickX, clientY: clickY, bubbles: true }));
    flushSync();

    const placed = target.querySelector(".furniture-object") as SVGGElement;
    placed.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".furniture-params-panel")).toBeNull();
  });
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/App.furniture.test.ts`
Expected: FAIL — `App.svelte` has no `.furniture-params-panel` anywhere yet.

- [x] **Step 3: Implement**

In `packages/editor/src/App.svelte`, add the import after the existing `import FurnitureLibraryPanel from "./lib/components/FurnitureLibraryPanel.svelte";` (line 76):

```ts
  import FurnitureParamsPanel from "./lib/components/FurnitureParamsPanel.svelte";
```

Add a new floating-drag instance alongside the existing ones (after line 312's `const opDrag = createFloatingDrag(".opening-panel-float");`):

```ts
  const fpanelDrag = createFloatingDrag(".furniture-params-panel-float");
```

Add derived values for the selected furniture object/template, near the existing `selectedOpening`/`selectedRoom` derived values (after the `selectedOpeningAreaIds` derived block, around line 376):

```ts
  const selectedFurnitureObject = $derived(
    selectedFurnitureId
      ? (floorStore.currentFurniture.find((f) => f.id === selectedFurnitureId) ?? null)
      : null
  );
  const selectedFurnitureTemplate = $derived(
    selectedFurnitureObject ? (getTemplate(selectedFurnitureObject.templateId) ?? null) : null
  );
```

(`selectedFurnitureId` is declared later in the file as `let selectedFurnitureId = $state<string | null>(null);` — Svelte's `$derived` reads are fine referencing a `$state` declared later in script-module order since both run at component init before first render, matching how `selectedRoom`/`selectedOpening` already reference `toolStore.state` similarly.)

In the template, add the panel block right after the existing `{#if selectedRoom} ... {/if}` block (after line 1012):

```svelte
            {#if selectedFurnitureObject && selectedFurnitureTemplate && selectedFurnitureTemplate.params?.length}
              <div class="furniture-params-panel-float" style={fpanelDrag.pos ? `left:${fpanelDrag.pos.x}px;top:${fpanelDrag.pos.y}px;right:auto;transform:none` : ''}>
                <FurnitureParamsPanel
                  object={selectedFurnitureObject}
                  template={selectedFurnitureTemplate}
                  readOnly={viewMode}
                  onupdate={(patch) => floorStore.updateFurnitureParams(selectedFurnitureObject.id, patch)}
                  onstartdrag={fpanelDrag.startDrag}
                  ondismiss={() => { selectedFurnitureId = null; }}
                />
              </div>
            {/if}
```

Add the CSS block right after the existing `.opening-panel-float` block and its media query (after line 1657):

```css

  .furniture-params-panel-float {
    position: absolute; right: 120px; top: 50%; transform: translateY(-50%);
    z-index: 21;
  }

  @media (max-width: 480px) { /* --bp-mobile */
    .furniture-params-panel-float {
      position: fixed;
      left: 0; right: 0; bottom: 48px; top: auto;
      transform: none !important;
      width: 100%;
      max-height: 45vh;
      z-index: 26;
    }
  }
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/App.furniture.test.ts`
Expected: PASS

Run: `cd packages/editor && npx tsc --noEmit --project tsconfig.json`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.furniture.test.ts
git commit -m "feat(editor): show FurnitureParamsPanel for the selected parameterized furniture object"
```

---

## Final verification

- [x] Run: `cd packages/backend && python -m pytest -v` — full backend suite passes.
- [x] Run: `cd packages/geometry && npx tsc --noEmit && npx vitest run` — full geometry suite passes.
- [x] Run: `cd packages/editor && npx tsc --noEmit --project tsconfig.json && npx vitest run` — full editor suite passes (all existing tests + all tests added in this plan).
- [x] Run: `cd packages/editor && npx svelte-check --tsconfig ./tsconfig.json` — confirms `FurnitureParamsPanel.svelte`'s type-guard narrowing and all other template type-checks are clean.
- [x] Manually verify in a running dev instance: drop a Stairs object from the furniture library onto the canvas; drop a Dining Table and a Round Table, select each, change the chair-count field in the new params panel, confirm the chair count on the canvas updates live; drop a Sofa, select it, switch shape to L-shaped, cycle through all 4 corners, confirm the chaise moves to each corner; drop a Deck/Terrace, resize it larger, confirm more plank rows/columns appear rather than the old fixed 4 lines stretching; change plankWidth/plankLength in the panel and confirm the pattern updates; reload the page after saving and confirm all params persisted.

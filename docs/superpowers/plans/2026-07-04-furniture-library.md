# Furniture Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a drag-and-drop library of furniture/outdoor objects that can be placed on the floor plan canvas, resized freely, and rotated.

**Architecture:** `FurnitureObject` records (id, templateId, x, y, width, height, rotation) are stored inside the existing `Floor.furnitureObjects[]` array and saved with the `HouseDocument`. A bundled `furnitureLibrary.ts` holds all SVG template shapes. Three new Svelte components handle rendering (`FurnitureShape`), interactive handles (`FurnitureHandles`), and the drag-source panel (`FurnitureLibraryPanel`). Everything is wired together in `Canvas.svelte` and `App.svelte`.

**Tech Stack:** Svelte 5 (runes), TypeScript, SVG, vitest + jsdom, existing `houseStore` snapshot/undo pattern.

---

## File Map

**New files:**
- `packages/editor/src/lib/furnitureLibrary.ts` — all templates + SVG shapes
- `packages/editor/src/lib/components/FurnitureShape.svelte` — renders one object in SVG
- `packages/editor/src/lib/components/FurnitureHandles.svelte` — move/resize/rotate handles
- `packages/editor/src/lib/components/FurnitureLibraryPanel.svelte` — drag-source sidebar
- `packages/editor/test/furnitureLibrary.test.ts`
- `packages/editor/test/houseStore.furniture.test.ts`
- `packages/editor/test/FurnitureShape.test.ts`
- `packages/editor/test/FurnitureLibraryPanel.test.ts`
- `packages/editor/test/FurnitureHandles.test.ts`
- `packages/editor/test/App.furniture.test.ts`

**Modified files:**
- `packages/geometry/src/types.ts` — add `FurnitureObject`, extend `Floor`
- `packages/editor/src/lib/sampleFloor.ts` — add `furnitureObjects: []` to sample floor
- `packages/editor/src/lib/houseStore.svelte.ts` — 5 new methods + backward compat load
- `packages/editor/src/lib/theme.css` — 2 new canvas tokens
- `packages/editor/src/lib/components/Canvas.svelte` — add furniture props + rendering
- `packages/editor/src/App.svelte` — toolbar button, panel, drop handler, delete, keyboard

---

## Task 1: Geometry Types

**Files:**
- Modify: `packages/geometry/src/types.ts`
- Modify: `packages/editor/src/lib/sampleFloor.ts`
- Test: `packages/geometry/test/types.test.ts` (already exists — check it still passes)

- [ ] **Step 1: Add `FurnitureObject` to `packages/geometry/src/types.ts`**

  After the `Room` interface, add:

  ```ts
  export interface FurnitureObject {
    id: string;
    templateId: string;
    x: number;       // world coords, meters, center of object
    y: number;
    width: number;   // meters
    height: number;  // meters
    rotation: number; // degrees, clockwise
  }
  ```

  Change `Floor` to add the optional field (optional so old saved docs are backward-compatible):

  ```ts
  export interface Floor {
    id: string;
    name: string;
    order: number;
    walls: Wall[];
    openings: Opening[];
    rooms: Room[];
    furnitureObjects?: FurnitureObject[];  // add this line
  }
  ```

- [ ] **Step 2: Update `sampleFloor.ts` to include the new field**

  In `packages/editor/src/lib/sampleFloor.ts`, add `furnitureObjects: []` to `SAMPLE_FLOOR`:

  ```ts
  export const SAMPLE_FLOOR: Floor = {
    id: "floor-1",
    name: "Ground Floor",
    order: 0,
    walls: [
      { id: "wall-1", type: "wall", start: { x: 0, y: 0 }, end: { x: 4, y: 0 }, thickness: 0.1 },
      { id: "wall-2", type: "wall", start: { x: 4, y: 0 }, end: { x: 4, y: 3 }, thickness: 0.1 },
      { id: "wall-3", type: "wall", start: { x: 4, y: 3 }, end: { x: 0, y: 3 }, thickness: 0.1 },
      { id: "wall-4", type: "wall", start: { x: 0, y: 3 }, end: { x: 0, y: 0 }, thickness: 0.1 },
      { id: "divider-1", type: "divider", start: { x: 2, y: 0 }, end: { x: 2, y: 3 } },
    ],
    openings: [],
    rooms: [],
    furnitureObjects: [],
  };
  ```

- [ ] **Step 3: Run existing geometry tests to confirm nothing broke**

  ```bash
  cd packages/geometry && npm run test
  ```
  Expected: all pass.

- [ ] **Step 4: Run existing editor tests to confirm nothing broke**

  ```bash
  cd packages/editor && npm run test
  ```
  Expected: all pass (TypeScript will now know about `furnitureObjects`).

- [ ] **Step 5: Commit**

  ```bash
  git add packages/geometry/src/types.ts packages/editor/src/lib/sampleFloor.ts
  git commit -m "feat: add FurnitureObject type and Floor.furnitureObjects field"
  ```

---

## Task 2: Furniture Library

**Files:**
- Create: `packages/editor/src/lib/furnitureLibrary.ts`
- Create: `packages/editor/test/furnitureLibrary.test.ts`

Each template's `svgContent` is raw SVG (no outer `<svg>` tag) drawn in a 100×100 coordinate space, centered at (50, 50). The enclosing `<g>` in `FurnitureShape` applies `fill` and `stroke` via CSS variables, so elements inherit those. Lines and open paths that should show only as stroke must specify `fill="none"` explicitly.

- [ ] **Step 1: Write failing tests**

  Create `packages/editor/test/furnitureLibrary.test.ts`:

  ```ts
  import { describe, it, expect } from "vitest";
  import { FURNITURE_TEMPLATES, getTemplate, FURNITURE_CATEGORIES } from "../src/lib/furnitureLibrary";

  describe("furnitureLibrary", () => {
    it("exports a non-empty template array", () => {
      expect(FURNITURE_TEMPLATES.length).toBeGreaterThan(0);
    });

    it("every template has all required fields", () => {
      for (const t of FURNITURE_TEMPLATES) {
        expect(t.id, `${t.id} missing id`).toBeTruthy();
        expect(t.label, `${t.id} missing label`).toBeTruthy();
        expect(FURNITURE_CATEGORIES, `${t.id} bad category`).toContain(t.category);
        expect(t.defaultWidth, `${t.id} bad width`).toBeGreaterThan(0);
        expect(t.defaultHeight, `${t.id} bad height`).toBeGreaterThan(0);
        expect(t.svgContent, `${t.id} missing svgContent`).toBeTruthy();
      }
    });

    it("template ids are unique", () => {
      const ids = FURNITURE_TEMPLATES.map((t) => t.id);
      expect(new Set(ids).size).toBe(ids.length);
    });

    it("getTemplate returns the correct template", () => {
      const t = getTemplate("sofa");
      expect(t).toBeDefined();
      expect(t?.label).toBe("Sofa");
    });

    it("getTemplate returns undefined for unknown id", () => {
      expect(getTemplate("nonexistent")).toBeUndefined();
    });

    it("covers all required categories", () => {
      const cats = new Set(FURNITURE_TEMPLATES.map((t) => t.category));
      expect(cats.has("living-room")).toBe(true);
      expect(cats.has("bedroom")).toBe(true);
      expect(cats.has("kitchen-dining")).toBe(true);
      expect(cats.has("bathroom")).toBe(true);
      expect(cats.has("office")).toBe(true);
      expect(cats.has("outdoor")).toBe(true);
      expect(cats.has("garden")).toBe(true);
    });
  });
  ```

- [ ] **Step 2: Run test to verify it fails**

  ```bash
  cd packages/editor && npm run test -- --reporter=verbose furnitureLibrary
  ```
  Expected: FAIL — module not found.

- [ ] **Step 3: Create `packages/editor/src/lib/furnitureLibrary.ts`**

  ```ts
  export type FurnitureCategory =
    | "living-room"
    | "bedroom"
    | "kitchen-dining"
    | "bathroom"
    | "office"
    | "outdoor"
    | "garden";

  export const FURNITURE_CATEGORIES: FurnitureCategory[] = [
    "living-room", "bedroom", "kitchen-dining", "bathroom", "office", "outdoor", "garden",
  ];

  export const CATEGORY_LABELS: Record<FurnitureCategory, string> = {
    "living-room": "Living Room",
    "bedroom": "Bedroom",
    "kitchen-dining": "Kitchen & Dining",
    "bathroom": "Bathroom",
    "office": "Office",
    "outdoor": "Outdoor",
    "garden": "Garden",
  };

  export interface FurnitureTemplate {
    id: string;
    label: string;
    category: FurnitureCategory;
    defaultWidth: number;
    defaultHeight: number;
    svgContent: string;
  }

  export const FURNITURE_TEMPLATES: FurnitureTemplate[] = [
    // ── Living Room ──────────────────────────────────────────
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
    },
    {
      id: "armchair",
      label: "Armchair",
      category: "living-room",
      defaultWidth: 1.0,
      defaultHeight: 0.9,
      svgContent: `
        <rect x="10" y="18" width="80" height="70" rx="6"/>
        <rect x="10" y="18" width="80" height="24" rx="4"/>
        <rect x="10" y="42" width="14" height="46" rx="3"/>
        <rect x="76" y="42" width="14" height="46" rx="3"/>
      `,
    },
    {
      id: "coffee-table",
      label: "Coffee Table",
      category: "living-room",
      defaultWidth: 1.2,
      defaultHeight: 0.6,
      svgContent: `
        <rect x="8" y="8" width="84" height="84" rx="4"/>
        <rect x="16" y="16" width="68" height="68" rx="2" fill="none"/>
      `,
    },
    {
      id: "tv-unit",
      label: "TV Unit",
      category: "living-room",
      defaultWidth: 1.8,
      defaultHeight: 0.45,
      svgContent: `
        <rect x="5" y="20" width="90" height="60" rx="3"/>
        <line x1="5" y1="38" x2="95" y2="38" fill="none"/>
        <rect x="28" y="24" width="44" height="11" rx="1" fill="none"/>
      `,
    },
    {
      id: "bookshelf",
      label: "Bookshelf",
      category: "living-room",
      defaultWidth: 1.2,
      defaultHeight: 0.3,
      svgContent: `
        <rect x="5" y="5" width="90" height="90" rx="2"/>
        <line x1="5" y1="28" x2="95" y2="28" fill="none"/>
        <line x1="5" y1="51" x2="95" y2="51" fill="none"/>
        <line x1="5" y1="74" x2="95" y2="74" fill="none"/>
        <line x1="50" y1="5" x2="50" y2="95" fill="none"/>
      `,
    },
    // ── Bedroom ──────────────────────────────────────────────
    {
      id: "bed-single",
      label: "Single Bed",
      category: "bedroom",
      defaultWidth: 1.0,
      defaultHeight: 2.0,
      svgContent: `
        <rect x="5" y="5" width="90" height="90" rx="4"/>
        <rect x="12" y="8" width="76" height="28" rx="14"/>
        <line x1="5" y1="38" x2="95" y2="38" fill="none"/>
      `,
    },
    {
      id: "bed-double",
      label: "Double Bed",
      category: "bedroom",
      defaultWidth: 1.6,
      defaultHeight: 2.0,
      svgContent: `
        <rect x="5" y="5" width="90" height="90" rx="4"/>
        <rect x="10" y="8" width="36" height="26" rx="12"/>
        <rect x="54" y="8" width="36" height="26" rx="12"/>
        <line x1="5" y1="36" x2="95" y2="36" fill="none"/>
        <line x1="50" y1="36" x2="50" y2="95" fill="none"/>
      `,
    },
    {
      id: "wardrobe",
      label: "Wardrobe",
      category: "bedroom",
      defaultWidth: 2.0,
      defaultHeight: 0.6,
      svgContent: `
        <rect x="5" y="5" width="90" height="90" rx="2"/>
        <line x1="50" y1="5" x2="50" y2="95" fill="none"/>
        <path d="M 50 22 Q 32 35 22 55" fill="none"/>
        <path d="M 50 22 Q 68 35 78 55" fill="none"/>
      `,
    },
    {
      id: "nightstand",
      label: "Nightstand",
      category: "bedroom",
      defaultWidth: 0.5,
      defaultHeight: 0.5,
      svgContent: `
        <rect x="8" y="8" width="84" height="84" rx="4"/>
        <line x1="8" y1="46" x2="92" y2="46" fill="none"/>
        <circle cx="50" cy="27" r="5" fill="none"/>
        <circle cx="50" cy="70" r="5" fill="none"/>
      `,
    },
    {
      id: "desk-bedroom",
      label: "Desk",
      category: "bedroom",
      defaultWidth: 1.2,
      defaultHeight: 0.6,
      svgContent: `
        <rect x="5" y="12" width="90" height="76" rx="3"/>
        <rect x="5" y="78" width="90" height="10" rx="2"/>
      `,
    },
    // ── Kitchen & Dining ─────────────────────────────────────
    {
      id: "dining-table-rect",
      label: "Dining Table",
      category: "kitchen-dining",
      defaultWidth: 1.6,
      defaultHeight: 0.9,
      svgContent: `
        <rect x="10" y="10" width="80" height="80" rx="3"/>
      `,
    },
    {
      id: "dining-table-round",
      label: "Round Table",
      category: "kitchen-dining",
      defaultWidth: 1.2,
      defaultHeight: 1.2,
      svgContent: `
        <circle cx="50" cy="50" r="42"/>
      `,
    },
    {
      id: "dining-chair",
      label: "Dining Chair",
      category: "kitchen-dining",
      defaultWidth: 0.45,
      defaultHeight: 0.45,
      svgContent: `
        <rect x="15" y="32" width="70" height="58" rx="4"/>
        <rect x="15" y="10" width="70" height="24" rx="4"/>
      `,
    },
    {
      id: "kitchen-island",
      label: "Kitchen Island",
      category: "kitchen-dining",
      defaultWidth: 2.0,
      defaultHeight: 1.0,
      svgContent: `
        <rect x="5" y="5" width="90" height="90" rx="3"/>
        <line x1="5" y1="32" x2="95" y2="32" fill="none"/>
        <circle cx="25" cy="18" r="7" fill="none"/>
        <circle cx="50" cy="18" r="7" fill="none"/>
        <circle cx="75" cy="18" r="7" fill="none"/>
      `,
    },
    {
      id: "fridge",
      label: "Fridge",
      category: "kitchen-dining",
      defaultWidth: 0.7,
      defaultHeight: 0.7,
      svgContent: `
        <rect x="8" y="5" width="84" height="90" rx="5"/>
        <line x1="8" y1="40" x2="92" y2="40" fill="none"/>
        <line x1="22" y1="22" x2="22" y2="37" fill="none" stroke-width="2"/>
        <line x1="22" y1="55" x2="22" y2="90" fill="none" stroke-width="2"/>
      `,
    },
    {
      id: "oven",
      label: "Oven",
      category: "kitchen-dining",
      defaultWidth: 0.6,
      defaultHeight: 0.6,
      svgContent: `
        <rect x="8" y="8" width="84" height="84" rx="4"/>
        <rect x="18" y="16" width="64" height="42" rx="2" fill="none"/>
        <circle cx="30" cy="72" r="8" fill="none"/>
        <circle cx="50" cy="72" r="8" fill="none"/>
        <circle cx="70" cy="72" r="8" fill="none"/>
      `,
    },
    {
      id: "sink-kitchen",
      label: "Kitchen Sink",
      category: "kitchen-dining",
      defaultWidth: 1.0,
      defaultHeight: 0.6,
      svgContent: `
        <rect x="5" y="5" width="90" height="90" rx="3"/>
        <rect x="10" y="12" width="38" height="76" rx="3" fill="none"/>
        <rect x="52" y="12" width="38" height="76" rx="3" fill="none"/>
        <circle cx="29" cy="50" r="5" fill="none"/>
        <circle cx="71" cy="50" r="5" fill="none"/>
      `,
    },
    // ── Bathroom ─────────────────────────────────────────────
    {
      id: "toilet",
      label: "Toilet",
      category: "bathroom",
      defaultWidth: 0.38,
      defaultHeight: 0.7,
      svgContent: `
        <rect x="20" y="5" width="60" height="33" rx="3"/>
        <ellipse cx="50" cy="70" rx="34" ry="28"/>
        <ellipse cx="50" cy="68" rx="26" ry="21" fill="none"/>
      `,
    },
    {
      id: "bathtub",
      label: "Bathtub",
      category: "bathroom",
      defaultWidth: 0.75,
      defaultHeight: 1.7,
      svgContent: `
        <rect x="8" y="5" width="84" height="90" rx="16"/>
        <rect x="15" y="12" width="70" height="76" rx="10" fill="none"/>
        <circle cx="50" cy="22" r="8" fill="none"/>
      `,
    },
    {
      id: "shower",
      label: "Shower",
      category: "bathroom",
      defaultWidth: 0.9,
      defaultHeight: 0.9,
      svgContent: `
        <rect x="5" y="5" width="90" height="90" rx="3"/>
        <line x1="5" y1="5" x2="95" y2="95" fill="none" stroke-dasharray="8 4"/>
        <line x1="95" y1="5" x2="5" y2="95" fill="none" stroke-dasharray="8 4"/>
        <circle cx="50" cy="50" r="12" fill="none"/>
      `,
    },
    {
      id: "sink-basin",
      label: "Sink",
      category: "bathroom",
      defaultWidth: 0.45,
      defaultHeight: 0.55,
      svgContent: `
        <ellipse cx="50" cy="50" rx="42" ry="44"/>
        <ellipse cx="50" cy="50" rx="30" ry="32" fill="none"/>
        <circle cx="50" cy="50" r="5" fill="none"/>
      `,
    },
    // ── Office ───────────────────────────────────────────────
    {
      id: "desk-office",
      label: "Office Desk",
      category: "office",
      defaultWidth: 1.4,
      defaultHeight: 0.7,
      svgContent: `
        <rect x="5" y="18" width="90" height="64" rx="3"/>
        <rect x="5" y="78" width="90" height="14" rx="2"/>
      `,
    },
    {
      id: "office-chair",
      label: "Office Chair",
      category: "office",
      defaultWidth: 0.6,
      defaultHeight: 0.6,
      svgContent: `
        <circle cx="50" cy="50" r="36"/>
        <circle cx="50" cy="50" r="22" fill="none"/>
        <line x1="50" y1="14" x2="50" y2="50" fill="none"/>
      `,
    },
    {
      id: "filing-cabinet",
      label: "Filing Cabinet",
      category: "office",
      defaultWidth: 0.4,
      defaultHeight: 0.6,
      svgContent: `
        <rect x="8" y="5" width="84" height="90" rx="3"/>
        <line x1="8" y1="36" x2="92" y2="36" fill="none"/>
        <line x1="8" y1="67" x2="92" y2="67" fill="none"/>
        <line x1="22" y1="20" x2="22" y2="34" fill="none" stroke-width="2"/>
        <line x1="22" y1="51" x2="22" y2="65" fill="none" stroke-width="2"/>
        <line x1="22" y1="82" x2="22" y2="90" fill="none" stroke-width="2"/>
      `,
    },
    // ── Outdoor ──────────────────────────────────────────────
    {
      id: "garden-table",
      label: "Garden Table",
      category: "outdoor",
      defaultWidth: 1.0,
      defaultHeight: 1.0,
      svgContent: `
        <circle cx="50" cy="50" r="42"/>
        <circle cx="50" cy="50" r="5" fill="none"/>
      `,
    },
    {
      id: "garden-chair",
      label: "Garden Chair",
      category: "outdoor",
      defaultWidth: 0.6,
      defaultHeight: 0.6,
      svgContent: `
        <rect x="14" y="32" width="72" height="58" rx="5"/>
        <rect x="14" y="8" width="72" height="26" rx="5"/>
      `,
    },
    {
      id: "sunlounger",
      label: "Sunlounger",
      category: "outdoor",
      defaultWidth: 0.7,
      defaultHeight: 2.0,
      svgContent: `
        <rect x="10" y="5" width="80" height="75" rx="8"/>
        <rect x="10" y="5" width="80" height="24" rx="8"/>
        <rect x="10" y="82" width="80" height="13" rx="3"/>
      `,
    },
    {
      id: "bbq",
      label: "BBQ",
      category: "outdoor",
      defaultWidth: 0.6,
      defaultHeight: 0.5,
      svgContent: `
        <ellipse cx="50" cy="50" rx="42" ry="38"/>
        <ellipse cx="50" cy="50" rx="30" ry="27" fill="none"/>
        <line x1="8" y1="50" x2="92" y2="50" fill="none"/>
        <line x1="50" y1="12" x2="50" y2="88" fill="none"/>
      `,
    },
    {
      id: "pool-rect",
      label: "Pool (rect)",
      category: "outdoor",
      defaultWidth: 4.0,
      defaultHeight: 8.0,
      svgContent: `
        <rect x="5" y="5" width="90" height="90" rx="5"/>
        <rect x="13" y="13" width="74" height="74" rx="3" fill="none"/>
        <line x1="13" y1="50" x2="87" y2="50" fill="none" stroke-dasharray="6 3"/>
      `,
    },
    {
      id: "pool-oval",
      label: "Pool (oval)",
      category: "outdoor",
      defaultWidth: 4.0,
      defaultHeight: 6.0,
      svgContent: `
        <ellipse cx="50" cy="50" rx="44" ry="44"/>
        <ellipse cx="50" cy="50" rx="34" ry="34" fill="none"/>
      `,
    },
    {
      id: "hot-tub",
      label: "Hot Tub",
      category: "outdoor",
      defaultWidth: 2.0,
      defaultHeight: 2.0,
      svgContent: `
        <rect x="8" y="8" width="84" height="84" rx="12"/>
        <rect x="16" y="16" width="68" height="68" rx="8" fill="none"/>
        <circle cx="50" cy="50" r="8" fill="none"/>
      `,
    },
    {
      id: "garden-bench",
      label: "Garden Bench",
      category: "outdoor",
      defaultWidth: 0.5,
      defaultHeight: 1.5,
      svgContent: `
        <rect x="8" y="22" width="84" height="56" rx="4"/>
        <line x1="8" y1="44" x2="92" y2="44" fill="none"/>
        <rect x="8" y="5" width="84" height="19" rx="3"/>
      `,
    },
    {
      id: "shed",
      label: "Shed",
      category: "outdoor",
      defaultWidth: 3.0,
      defaultHeight: 2.5,
      svgContent: `
        <rect x="5" y="5" width="90" height="90" rx="2"/>
        <line x1="5" y1="5" x2="50" y2="28" fill="none"/>
        <line x1="95" y1="5" x2="50" y2="28" fill="none"/>
        <rect x="38" y="58" width="24" height="37" rx="1" fill="none"/>
      `,
    },
    // ── Garden ───────────────────────────────────────────────
    {
      id: "tree",
      label: "Tree",
      category: "garden",
      defaultWidth: 1.5,
      defaultHeight: 1.5,
      svgContent: `
        <circle cx="50" cy="50" r="44"/>
        <circle cx="50" cy="50" r="28" fill="none"/>
        <circle cx="50" cy="50" r="6"/>
      `,
    },
    {
      id: "hedge",
      label: "Hedge",
      category: "garden",
      defaultWidth: 0.5,
      defaultHeight: 2.0,
      svgContent: `
        <rect x="5" y="5" width="90" height="90" rx="8"/>
        <ellipse cx="25" cy="28" rx="18" ry="18" fill="none"/>
        <ellipse cx="50" cy="28" rx="18" ry="18" fill="none"/>
        <ellipse cx="75" cy="28" rx="18" ry="18" fill="none"/>
        <ellipse cx="25" cy="72" rx="18" ry="18" fill="none"/>
        <ellipse cx="50" cy="72" rx="18" ry="18" fill="none"/>
        <ellipse cx="75" cy="72" rx="18" ry="18" fill="none"/>
      `,
    },
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
        <line x1="5" y1="90" x2="95" y2="90" fill="none"/>
      `,
    },
    {
      id: "car",
      label: "Car",
      category: "garden",
      defaultWidth: 2.0,
      defaultHeight: 4.5,
      svgContent: `
        <rect x="8" y="5" width="84" height="90" rx="12"/>
        <rect x="15" y="18" width="70" height="28" rx="5" fill="none"/>
        <rect x="15" y="62" width="70" height="22" rx="3" fill="none"/>
        <rect x="8" y="8" width="18" height="12" rx="3" fill="none"/>
        <rect x="74" y="8" width="18" height="12" rx="3" fill="none"/>
        <rect x="8" y="78" width="18" height="15" rx="3" fill="none"/>
        <rect x="74" y="78" width="18" height="15" rx="3" fill="none"/>
      `,
    },
    {
      id: "plant",
      label: "Plant",
      category: "garden",
      defaultWidth: 0.4,
      defaultHeight: 0.4,
      svgContent: `
        <circle cx="50" cy="50" r="36"/>
        <circle cx="50" cy="50" r="20" fill="none"/>
        <path d="M 50 22 Q 34 36 34 52" fill="none"/>
        <path d="M 50 22 Q 66 36 66 52" fill="none"/>
      `,
    },
    {
      id: "grass-patch",
      label: "Grass Patch",
      category: "garden",
      defaultWidth: 2.0,
      defaultHeight: 2.0,
      svgContent: `
        <rect x="5" y="5" width="90" height="90" rx="3"/>
        <line x1="22" y1="5" x2="22" y2="95" fill="none" stroke-dasharray="3 7" stroke-width="1"/>
        <line x1="39" y1="5" x2="39" y2="95" fill="none" stroke-dasharray="3 7" stroke-width="1"/>
        <line x1="56" y1="5" x2="56" y2="95" fill="none" stroke-dasharray="3 7" stroke-width="1"/>
        <line x1="73" y1="5" x2="73" y2="95" fill="none" stroke-dasharray="3 7" stroke-width="1"/>
      `,
    },
  ];

  export function getTemplate(id: string): FurnitureTemplate | undefined {
    return FURNITURE_TEMPLATES.find((t) => t.id === id);
  }
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  cd packages/editor && npm run test -- --reporter=verbose furnitureLibrary
  ```
  Expected: all pass.

- [ ] **Step 5: Commit**

  ```bash
  git add packages/editor/src/lib/furnitureLibrary.ts packages/editor/test/furnitureLibrary.test.ts
  git commit -m "feat: add furniture template library with 35 built-in shapes"
  ```

---

## Task 3: houseStore Furniture Methods

**Files:**
- Modify: `packages/editor/src/lib/houseStore.svelte.ts`
- Create: `packages/editor/test/houseStore.furniture.test.ts`

- [ ] **Step 1: Write failing tests**

  Create `packages/editor/test/houseStore.furniture.test.ts`:

  ```ts
  import { describe, it, expect, vi, afterEach } from "vitest";
  import { createHouseStore } from "../src/lib/houseStore.svelte";
  import type { FurnitureObject } from "@myhome/geometry";

  afterEach(() => vi.unstubAllGlobals());

  function makeFetch404() {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => undefined }));
  }

  function makeStore() {
    makeFetch404();
    return createHouseStore(() => null);
  }

  const BASE: Omit<FurnitureObject, "id"> = {
    templateId: "sofa",
    x: 1,
    y: 1,
    width: 2.2,
    height: 0.9,
    rotation: 0,
  };

  describe("houseStore — furniture", () => {
    it("addFurniture adds an object with a generated id", () => {
      const store = makeStore();
      store.addFurniture(BASE);
      expect(store.floor.furnitureObjects?.length).toBe(1);
      expect(store.floor.furnitureObjects?.[0].id).toBeTruthy();
      expect(store.floor.furnitureObjects?.[0].templateId).toBe("sofa");
    });

    it("removeFurniture removes the object by id", () => {
      const store = makeStore();
      store.addFurniture(BASE);
      const id = store.floor.furnitureObjects![0].id;
      store.removeFurniture(id);
      expect(store.floor.furnitureObjects?.length).toBe(0);
    });

    it("moveFurniture updates x and y", () => {
      const store = makeStore();
      store.addFurniture(BASE);
      const id = store.floor.furnitureObjects![0].id;
      store.moveFurniture(id, 5, 6);
      expect(store.floor.furnitureObjects![0].x).toBe(5);
      expect(store.floor.furnitureObjects![0].y).toBe(6);
    });

    it("resizeFurniture updates width and height", () => {
      const store = makeStore();
      store.addFurniture(BASE);
      const id = store.floor.furnitureObjects![0].id;
      store.resizeFurniture(id, 3.0, 1.2);
      expect(store.floor.furnitureObjects![0].width).toBe(3.0);
      expect(store.floor.furnitureObjects![0].height).toBe(1.2);
    });

    it("rotateFurniture updates rotation", () => {
      const store = makeStore();
      store.addFurniture(BASE);
      const id = store.floor.furnitureObjects![0].id;
      store.rotateFurniture(id, 45);
      expect(store.floor.furnitureObjects![0].rotation).toBe(45);
    });

    it("addFurniture → undo removes the object", () => {
      const store = makeStore();
      store.addFurniture(BASE);
      expect(store.floor.furnitureObjects?.length).toBe(1);
      store.undo();
      expect(store.floor.furnitureObjects?.length).toBe(0);
    });

    it("removeFurniture → undo restores the object", () => {
      const store = makeStore();
      store.addFurniture(BASE);
      const id = store.floor.furnitureObjects![0].id;
      store.removeFurniture(id);
      store.undo(); // undo remove
      store.undo(); // undo add
      expect(store.floor.furnitureObjects?.length).toBe(0);
    });

    it("moveFurniture with skipHistory does not create an undo entry", () => {
      const store = makeStore();
      store.addFurniture(BASE);
      const id = store.floor.furnitureObjects![0].id;
      const undoBefore = store.hasUndo;
      store.moveFurniture(id, 9, 9, { skipHistory: true });
      expect(store.hasUndo).toBe(undoBefore);
    });
  });
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  cd packages/editor && npm run test -- --reporter=verbose houseStore.furniture
  ```
  Expected: FAIL — methods not found.

- [ ] **Step 3: Add furniture methods to `houseStore.svelte.ts`**

  In `createHouseStore`, after the `openingOverlaps` function and before the `init` function, add:

  ```ts
  function currentFurniture(): FurnitureObject[] {
    const floor = currentFloor();
    if (!floor.furnitureObjects) floor.furnitureObjects = [];
    return floor.furnitureObjects;
  }

  function addFurniture(obj: Omit<FurnitureObject, "id">): void {
    saveSnapshot();
    currentFurniture().push({
      ...obj,
      id: crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36),
    });
  }

  function removeFurniture(id: string): void {
    saveSnapshot();
    const floor = currentFloor();
    floor.furnitureObjects = (floor.furnitureObjects ?? []).filter((o) => o.id !== id);
  }

  function moveFurniture(id: string, x: number, y: number, opts?: { skipHistory?: boolean }): void {
    const obj = currentFurniture().find((o) => o.id === id);
    if (!obj) return;
    if (!opts?.skipHistory) saveSnapshot();
    else generation++;
    obj.x = x;
    obj.y = y;
  }

  function resizeFurniture(id: string, width: number, height: number, opts?: { skipHistory?: boolean }): void {
    const obj = currentFurniture().find((o) => o.id === id);
    if (!obj) return;
    if (!opts?.skipHistory) saveSnapshot();
    else generation++;
    obj.width = Math.max(0.1, width);
    obj.height = Math.max(0.1, height);
  }

  function rotateFurniture(id: string, rotation: number, opts?: { skipHistory?: boolean }): void {
    const obj = currentFurniture().find((o) => o.id === id);
    if (!obj) return;
    if (!opts?.skipHistory) saveSnapshot();
    else generation++;
    obj.rotation = rotation;
  }
  ```

  Also add the import at the top of `houseStore.svelte.ts`:
  ```ts
  import type { Floor, Wall, Opening, Room, Point, House, HouseDocument, FurnitureObject } from "@myhome/geometry";
  ```

  And expose the new methods in the returned object at the bottom of `createHouseStore`:
  ```ts
  return {
    // ... existing properties ...
    addFurniture,
    removeFurniture,
    moveFurniture,
    resizeFurniture,
    rotateFurniture,
  };
  ```

  Also patch the `init` function to default `furnitureObjects` when loading old documents. In the `init` function, after `applyState({ floors: doc.floors, currentFloorId: newCurrentId })`, add:

  ```ts
  for (const f of floors) {
    if (!f.furnitureObjects) f.furnitureObjects = [];
  }
  ```

  Do the same in the `status === 404` branch:
  ```ts
  for (const f of floors) {
    const detected = detectRooms(f.walls);
    const { rooms } = matchRooms(detected, f.rooms);
    f.rooms = rooms.filter((r) => r.polygon !== null);
    if (!f.furnitureObjects) f.furnitureObjects = [];
  }
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  cd packages/editor && npm run test -- --reporter=verbose houseStore.furniture
  ```
  Expected: all pass.

- [ ] **Step 5: Run all editor tests to confirm no regressions**

  ```bash
  cd packages/editor && npm run test
  ```
  Expected: all pass.

- [ ] **Step 6: Commit**

  ```bash
  git add packages/editor/src/lib/houseStore.svelte.ts packages/editor/test/houseStore.furniture.test.ts
  git commit -m "feat: add furniture methods to houseStore (add/remove/move/resize/rotate)"
  ```

---

## Task 4: Theme Tokens

**Files:**
- Modify: `packages/editor/src/lib/theme.css`

- [ ] **Step 1: Add furniture tokens to light theme in `theme.css`**

  After the `--canvas-selected-fill` line (inside `:root {}`):

  ```css
  --canvas-furniture-fill: #ede9e0;
  --canvas-furniture-stroke: #8a7f6e;
  ```

- [ ] **Step 2: Add furniture tokens to dark theme in `theme.css`**

  Inside `[data-theme="dark"] {}`, after the last `--canvas-*` token:

  ```css
  --canvas-furniture-fill: #2a2822;
  --canvas-furniture-stroke: #6a5f4e;
  ```

- [ ] **Step 3: Run tests to confirm nothing broke**

  ```bash
  cd packages/editor && npm run test
  ```
  Expected: all pass.

- [ ] **Step 4: Commit**

  ```bash
  git add packages/editor/src/lib/theme.css
  git commit -m "feat: add canvas-furniture-fill/stroke CSS tokens"
  ```

---

## Task 5: FurnitureShape Component

**Files:**
- Create: `packages/editor/src/lib/components/FurnitureShape.svelte`
- Create: `packages/editor/test/FurnitureShape.test.ts`

The component renders one furniture object inside the Canvas SVG. It computes a single SVG transform from world coords to screen coords, applies rotation, and scales the 100×100 template viewBox to the object's actual size.

Transform math:
- `scaleX = object.width * viewport.zoom / 100`
- `scaleY = object.height * viewport.zoom / 100`
- `cs = worldToScreen({x: object.x, y: object.y}, viewport)` → `{x: cs.x, y: cs.y}`
- Full transform: `translate(${cs.x}, ${cs.y}) rotate(${object.rotation}) scale(${scaleX}, ${scaleY}) translate(-50, -50)`

- [ ] **Step 1: Write failing tests**

  Create `packages/editor/test/FurnitureShape.test.ts`:

  ```ts
  import { describe, it, expect, afterEach } from "vitest";
  import { mount, unmount, flushSync } from "svelte";
  import FurnitureShape from "../src/lib/components/FurnitureShape.svelte";
  import { getTemplate } from "../src/lib/furnitureLibrary";
  import type { FurnitureObject } from "@myhome/geometry";
  import { DEFAULT_VIEWPORT } from "../src/lib/viewportStore.svelte";

  const template = getTemplate("sofa")!;
  const obj: FurnitureObject = {
    id: "f1",
    templateId: "sofa",
    x: 1,
    y: 1,
    width: 2.2,
    height: 0.9,
    rotation: 0,
  };

  describe("FurnitureShape", () => {
    let target: HTMLElement;
    let app: ReturnType<typeof mount> | undefined;

    afterEach(() => {
      if (app) { unmount(app); app = undefined; }
      target?.remove();
    });

    it("renders a <g> with class 'furniture-shape'", () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      target.appendChild(svg);
      app = mount(FurnitureShape, {
        target: svg,
        props: { object: obj, template, viewport: { ...DEFAULT_VIEWPORT }, selected: false, tool: "select" },
      });
      flushSync();
      expect(svg.querySelector("g.furniture-shape")).not.toBeNull();
    });

    it("renders with a transform attribute containing translate and rotate", () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      target.appendChild(svg);
      app = mount(FurnitureShape, {
        target: svg,
        props: { object: obj, template, viewport: { ...DEFAULT_VIEWPORT }, selected: false, tool: "select" },
      });
      flushSync();
      const g = svg.querySelector("g.furniture-shape")!;
      expect(g.getAttribute("transform")).toContain("translate");
      expect(g.getAttribute("transform")).toContain("rotate");
      expect(g.getAttribute("transform")).toContain("scale");
    });

    it("fires onselect with the object id when clicked in select mode", () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      target.appendChild(svg);
      let selected: string | null = null;
      app = mount(FurnitureShape, {
        target: svg,
        props: {
          object: obj,
          template,
          viewport: { ...DEFAULT_VIEWPORT },
          selected: false,
          tool: "select",
          onselect: (id: string) => { selected = id; },
        },
      });
      flushSync();
      const g = svg.querySelector("g.furniture-shape")!;
      g.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      flushSync();
      expect(selected).toBe("f1");
    });

    it("does not fire onselect when tool is not select", () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      target.appendChild(svg);
      let selected: string | null = null;
      app = mount(FurnitureShape, {
        target: svg,
        props: {
          object: obj,
          template,
          viewport: { ...DEFAULT_VIEWPORT },
          selected: false,
          tool: "wall",
          onselect: (id: string) => { selected = id; },
        },
      });
      flushSync();
      svg.querySelector("g.furniture-shape")!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      flushSync();
      expect(selected).toBeNull();
    });

    it("adds 'selected' class when selected prop is true", () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      target.appendChild(svg);
      app = mount(FurnitureShape, {
        target: svg,
        props: { object: obj, template, viewport: { ...DEFAULT_VIEWPORT }, selected: true, tool: "select" },
      });
      flushSync();
      expect(svg.querySelector("g.furniture-shape.selected")).not.toBeNull();
    });
  });
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  cd packages/editor && npm run test -- --reporter=verbose FurnitureShape
  ```
  Expected: FAIL — component not found.

- [ ] **Step 3: Create `FurnitureShape.svelte`**

  ```svelte
  <script lang="ts">
    import type { FurnitureObject } from "@myhome/geometry";
    import type { FurnitureTemplate } from "../furnitureLibrary";
    import type { ViewportState } from "../viewportStore.svelte";
    import type { ToolType } from "../toolStore.svelte";
    import { worldToScreen } from "../viewportStore.svelte";

    let {
      object,
      template,
      viewport,
      selected = false,
      tool = "select",
      onselect,
      onbodymousedown,
    }: {
      object: FurnitureObject;
      template: FurnitureTemplate;
      viewport: ViewportState;
      selected?: boolean;
      tool?: ToolType;
      onselect?: (id: string) => void;
      onbodymousedown?: (id: string, event: MouseEvent) => void;
    } = $props();

    const cs = $derived(worldToScreen({ x: object.x, y: object.y }, viewport));
    const scaleX = $derived((object.width * viewport.zoom) / 100);
    const scaleY = $derived((object.height * viewport.zoom) / 100);
    const transform = $derived(
      `translate(${cs.x}, ${cs.y}) rotate(${object.rotation}) scale(${scaleX}, ${scaleY}) translate(-50, -50)`
    );

    function handleClick(event: MouseEvent): void {
      if (tool !== "select") return;
      event.stopPropagation();
      onselect?.(object.id);
    }

    function handleMouseDown(event: MouseEvent): void {
      if (tool !== "select") return;
      onbodymousedown?.(object.id, event);
    }
  </script>

  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <g
    class="furniture-shape"
    class:selected
    {transform}
    onclick={handleClick}
    onmousedown={handleMouseDown}
    style="cursor: {tool === 'select' ? 'pointer' : 'default'}"
    fill="var(--canvas-furniture-fill)"
    stroke="var(--canvas-furniture-stroke)"
    stroke-width="2"
  >
    {@html template.svgContent}
  </g>

  <style>
    .furniture-shape.selected {
      stroke: var(--canvas-wall-selected);
      stroke-width: 2.5;
    }
  </style>
  ```

- [ ] **Step 4: Run tests**

  ```bash
  cd packages/editor && npm run test -- --reporter=verbose FurnitureShape
  ```
  Expected: all pass.

- [ ] **Step 5: Commit**

  ```bash
  git add packages/editor/src/lib/components/FurnitureShape.svelte packages/editor/test/FurnitureShape.test.ts
  git commit -m "feat: add FurnitureShape SVG component"
  ```

---

## Task 6: FurnitureHandles Component

**Files:**
- Create: `packages/editor/src/lib/components/FurnitureHandles.svelte`
- Create: `packages/editor/test/FurnitureHandles.test.ts`

This component renders 4 corner resize handles, 1 rotation handle, and a transparent move-drag rect over the selected furniture object. All positions are computed in screen space from the object's world coords + rotation.

**Corner screen positions:** For object center at screen `(cx, cy)`, half-width `hw = width*zoom/2`, half-height `hh = height*zoom/2`, rotation `θ`:
```
cos = Math.cos(θ * π/180), sin = Math.sin(θ * π/180)
corner(localX, localY) = { x: cx + cos*localX - sin*localY, y: cy + sin*localX + cos*localY }
TL = corner(-hw, -hh), TR = corner(hw, -hh), BR = corner(hw, hh), BL = corner(-hw, hh)
rotHandle = corner(0, -hh - 20)
topMid = corner(0, -hh)
```

- [ ] **Step 1: Write failing tests**

  Create `packages/editor/test/FurnitureHandles.test.ts`:

  ```ts
  import { describe, it, expect, afterEach } from "vitest";
  import { mount, unmount, flushSync } from "svelte";
  import FurnitureHandles from "../src/lib/components/FurnitureHandles.svelte";
  import type { FurnitureObject } from "@myhome/geometry";
  import { DEFAULT_VIEWPORT } from "../src/lib/viewportStore.svelte";

  const obj: FurnitureObject = {
    id: "f1", templateId: "sofa",
    x: 2, y: 2, width: 2.0, height: 1.0, rotation: 0,
  };

  describe("FurnitureHandles", () => {
    let target: HTMLElement;
    let app: ReturnType<typeof mount> | undefined;

    afterEach(() => {
      if (app) { unmount(app); app = undefined; }
      target?.remove();
    });

    it("renders 4 corner handles and 1 rotation handle", () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      target.appendChild(svg);
      app = mount(FurnitureHandles, {
        target: svg,
        props: { object: obj, viewport: { ...DEFAULT_VIEWPORT } },
      });
      flushSync();
      expect(svg.querySelectorAll("rect.corner-handle").length).toBe(4);
      expect(svg.querySelectorAll("circle.rotate-handle").length).toBe(1);
    });

    it("fires onresizestart with correct corner on corner mousedown", () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      target.appendChild(svg);
      let resizeArgs: { id: string; corner: string } | null = null;
      app = mount(FurnitureHandles, {
        target: svg,
        props: {
          object: obj,
          viewport: { ...DEFAULT_VIEWPORT },
          onresizestart: (id: string, corner: string, event: MouseEvent) => {
            resizeArgs = { id, corner };
          },
        },
      });
      flushSync();
      const corners = svg.querySelectorAll("rect.corner-handle");
      corners[0].dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
      flushSync();
      expect(resizeArgs).not.toBeNull();
      expect(resizeArgs!.id).toBe("f1");
    });

    it("fires onrotatestart on rotation handle mousedown", () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      target.appendChild(svg);
      let rotateId: string | null = null;
      app = mount(FurnitureHandles, {
        target: svg,
        props: {
          object: obj,
          viewport: { ...DEFAULT_VIEWPORT },
          onrotatestart: (id: string, _event: MouseEvent) => { rotateId = id; },
        },
      });
      flushSync();
      svg.querySelector("circle.rotate-handle")!.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
      flushSync();
      expect(rotateId).toBe("f1");
    });
  });
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  cd packages/editor && npm run test -- --reporter=verbose FurnitureHandles
  ```
  Expected: FAIL — component not found.

- [ ] **Step 3: Create `FurnitureHandles.svelte`**

  ```svelte
  <script lang="ts">
    import type { FurnitureObject } from "@myhome/geometry";
    import type { ViewportState } from "../viewportStore.svelte";
    import { worldToScreen } from "../viewportStore.svelte";

    type Corner = "tl" | "tr" | "br" | "bl";

    let {
      object,
      viewport,
      onresizestart,
      onrotatestart,
    }: {
      object: FurnitureObject;
      viewport: ViewportState;
      onresizestart?: (id: string, corner: Corner, event: MouseEvent) => void;
      onrotatestart?: (id: string, event: MouseEvent) => void;
    } = $props();

    const cs = $derived(worldToScreen({ x: object.x, y: object.y }, viewport));
    const hw = $derived((object.width * viewport.zoom) / 2);
    const hh = $derived((object.height * viewport.zoom) / 2);
    const rad = $derived((object.rotation * Math.PI) / 180);
    const cosR = $derived(Math.cos(rad));
    const sinR = $derived(Math.sin(rad));

    function rot(localX: number, localY: number): { x: number; y: number } {
      return {
        x: cs.x + cosR * localX - sinR * localY,
        y: cs.y + sinR * localX + cosR * localY,
      };
    }

    const corners = $derived({
      tl: rot(-hw, -hh),
      tr: rot(hw, -hh),
      br: rot(hw, hh),
      bl: rot(-hw, hh),
    });

    const rotHandle = $derived(rot(0, -hh - 20));
    const topMid = $derived(rot(0, -hh));

    const HANDLE_SIZE = 8;
  </script>

  <!-- Rotation stem line -->
  <line
    x1={topMid.x} y1={topMid.y}
    x2={rotHandle.x} y2={rotHandle.y}
    stroke="var(--canvas-wall-selected)"
    stroke-width="1"
    pointer-events="none"
  />

  <!-- Rotation handle -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <circle
    class="rotate-handle"
    cx={rotHandle.x} cy={rotHandle.y}
    r="5"
    fill="white"
    stroke="var(--canvas-wall-selected)"
    stroke-width="1.5"
    style="cursor: crosshair"
    onmousedown={(e) => { e.stopPropagation(); onrotatestart?.(object.id, e); }}
  />

  <!-- Corner handles -->
  {#each (["tl", "tr", "br", "bl"] as Corner[]) as corner}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <rect
      class="corner-handle"
      x={corners[corner].x - HANDLE_SIZE / 2}
      y={corners[corner].y - HANDLE_SIZE / 2}
      width={HANDLE_SIZE}
      height={HANDLE_SIZE}
      fill="white"
      stroke="var(--canvas-wall-selected)"
      stroke-width="1.5"
      style="cursor: {corner === 'tl' || corner === 'br' ? 'nwse-resize' : 'nesw-resize'}"
      onmousedown={(e) => { e.stopPropagation(); onresizestart?.(object.id, corner, e); }}
    />
  {/each}
  ```

- [ ] **Step 4: Run tests**

  ```bash
  cd packages/editor && npm run test -- --reporter=verbose FurnitureHandles
  ```
  Expected: all pass.

- [ ] **Step 5: Commit**

  ```bash
  git add packages/editor/src/lib/components/FurnitureHandles.svelte packages/editor/test/FurnitureHandles.test.ts
  git commit -m "feat: add FurnitureHandles component with corner and rotation handles"
  ```

---

## Task 7: FurnitureLibraryPanel Component

**Files:**
- Create: `packages/editor/src/lib/components/FurnitureLibraryPanel.svelte`
- Create: `packages/editor/test/FurnitureLibraryPanel.test.ts`

A fixed-width scrollable sidebar that shows furniture categories with SVG thumbnails. Each item is draggable: `dragstart` puts `furnitureTemplateId` in `dataTransfer`.

- [ ] **Step 1: Write failing tests**

  Create `packages/editor/test/FurnitureLibraryPanel.test.ts`:

  ```ts
  import { describe, it, expect, afterEach } from "vitest";
  import { mount, unmount, flushSync } from "svelte";
  import FurnitureLibraryPanel from "../src/lib/components/FurnitureLibraryPanel.svelte";

  describe("FurnitureLibraryPanel", () => {
    let target: HTMLElement;
    let app: ReturnType<typeof mount> | undefined;

    afterEach(() => {
      if (app) { unmount(app); app = undefined; }
      target?.remove();
    });

    it("renders at least one category section", () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      app = mount(FurnitureLibraryPanel, { target, props: {} });
      flushSync();
      expect(target.querySelectorAll(".category-section").length).toBeGreaterThan(0);
    });

    it("renders furniture items with draggable attribute", () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      app = mount(FurnitureLibraryPanel, { target, props: {} });
      flushSync();
      const items = target.querySelectorAll(".furniture-item[draggable='true']");
      expect(items.length).toBeGreaterThan(0);
    });

    it("fires ondragstart with the template id", () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      let draggedId: string | null = null;
      app = mount(FurnitureLibraryPanel, {
        target,
        props: {
          ondragstart: (templateId: string) => { draggedId = templateId; },
        },
      });
      flushSync();
      const item = target.querySelector(".furniture-item[draggable='true']") as HTMLElement;
      const dt = { setData: (k: string, v: string) => {}, setDragImage: () => {} } as unknown as DataTransfer;
      item.dispatchEvent(new DragEvent("dragstart", { bubbles: true, dataTransfer: dt }));
      flushSync();
      expect(draggedId).not.toBeNull();
    });

    it("renders an SVG thumbnail for each item", () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      app = mount(FurnitureLibraryPanel, { target, props: {} });
      flushSync();
      const svgs = target.querySelectorAll(".furniture-item svg");
      expect(svgs.length).toBeGreaterThan(0);
    });

    it("filters items when search query is entered", () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      app = mount(FurnitureLibraryPanel, { target, props: {} });
      flushSync();
      const allItems = target.querySelectorAll(".furniture-item").length;
      const input = target.querySelector("input.search") as HTMLInputElement;
      input.value = "sofa";
      input.dispatchEvent(new Event("input"));
      flushSync();
      const filteredItems = target.querySelectorAll(".furniture-item").length;
      expect(filteredItems).toBeLessThan(allItems);
      expect(filteredItems).toBeGreaterThan(0);
    });
  });
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  cd packages/editor && npm run test -- --reporter=verbose FurnitureLibraryPanel
  ```
  Expected: FAIL.

- [ ] **Step 3: Create `FurnitureLibraryPanel.svelte`**

  ```svelte
  <script lang="ts">
    import {
      FURNITURE_TEMPLATES,
      FURNITURE_CATEGORIES,
      CATEGORY_LABELS,
      type FurnitureTemplate,
      type FurnitureCategory,
    } from "../furnitureLibrary";

    let {
      ondragstart,
      ondragend,
    }: {
      ondragstart?: (templateId: string, event: DragEvent) => void;
      ondragend?: () => void;
    } = $props();

    let query = $state("");

    function filteredByCategory(cat: FurnitureCategory): FurnitureTemplate[] {
      const q = query.trim().toLowerCase();
      return FURNITURE_TEMPLATES.filter(
        (t) => t.category === cat && (!q || t.label.toLowerCase().includes(q))
      );
    }

    function handleDragStart(template: FurnitureTemplate, event: DragEvent): void {
      if (!event.dataTransfer) return;
      event.dataTransfer.effectAllowed = "copy";
      event.dataTransfer.setData("furnitureTemplateId", template.id);
      ondragstart?.(template.id, event);
    }
  </script>

  <div class="furniture-panel">
    <div class="panel-header">
      <span class="panel-title">Furniture</span>
    </div>
    <input
      class="search"
      type="text"
      placeholder="Search…"
      bind:value={query}
    />
    <div class="panel-body">
      {#each FURNITURE_CATEGORIES as cat}
        {@const items = filteredByCategory(cat)}
        {#if items.length > 0}
          <div class="category-section">
            <div class="category-label">{CATEGORY_LABELS[cat]}</div>
            <div class="item-grid">
              {#each items as template (template.id)}
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div
                  class="furniture-item"
                  draggable="true"
                  title={template.label}
                  ondragstart={(e) => handleDragStart(template, e)}
                  ondragend={() => ondragend?.()}
                >
                  <svg
                    viewBox="0 0 100 100"
                    width="44"
                    height="44"
                    fill="var(--canvas-furniture-fill)"
                    stroke="var(--canvas-furniture-stroke)"
                    stroke-width="3"
                  >
                    {@html template.svgContent}
                  </svg>
                  <span class="item-label">{template.label}</span>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      {/each}
    </div>
  </div>

  <style>
    .furniture-panel {
      width: 180px;
      height: 100%;
      display: flex;
      flex-direction: column;
      background: var(--surface);
      border-left: 1px solid var(--border);
      flex-shrink: 0;
      overflow: hidden;
    }
    .panel-header {
      display: flex;
      align-items: center;
      padding: 8px 10px 4px;
      flex-shrink: 0;
    }
    .panel-title {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
    }
    .search {
      margin: 0 8px 6px;
      padding: 4px 8px;
      font-size: 12px;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      background: var(--surface-alt);
      color: var(--text);
      outline: none;
      flex-shrink: 0;
    }
    .search:focus { border-color: var(--accent); }
    .panel-body {
      flex: 1;
      overflow-y: auto;
      padding: 0 6px 8px;
    }
    .category-section { margin-bottom: 10px; }
    .category-label {
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      padding: 4px 2px 4px;
    }
    .item-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 4px;
    }
    .furniture-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;
      padding: 4px 2px;
      border-radius: var(--radius-sm);
      cursor: grab;
      user-select: none;
    }
    .furniture-item:hover { background: var(--surface-hover); }
    .furniture-item:active { cursor: grabbing; }
    .item-label {
      font-size: 9px;
      color: var(--text-muted);
      text-align: center;
      line-height: 1.2;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      width: 100%;
    }
  </style>
  ```

- [ ] **Step 4: Run tests**

  ```bash
  cd packages/editor && npm run test -- --reporter=verbose FurnitureLibraryPanel
  ```
  Expected: all pass.

- [ ] **Step 5: Commit**

  ```bash
  git add packages/editor/src/lib/components/FurnitureLibraryPanel.svelte packages/editor/test/FurnitureLibraryPanel.test.ts
  git commit -m "feat: add FurnitureLibraryPanel drag-source sidebar"
  ```

---

## Task 8: Canvas Integration

**Files:**
- Modify: `packages/editor/src/lib/components/Canvas.svelte`
- Modify: `packages/editor/test/Canvas.test.ts` (add 1 test at bottom)

Add furniture rendering and event forwarding to Canvas.svelte. Furniture renders below walls (between rooms and walls in the SVG order). The component does NOT manage drag state — it just fires events up to App.svelte.

- [ ] **Step 1: Write failing test (append to `Canvas.test.ts`)**

  At the bottom of `packages/editor/test/Canvas.test.ts`, inside the `describe("Canvas", ...)` block, add:

  ```ts
  it("renders furniture shapes for objects in the floor", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    const floor = createSampleFloor();
    floor.furnitureObjects = [
      { id: "f1", templateId: "sofa", x: 2, y: 1.5, width: 2.2, height: 0.9, rotation: 0 },
    ];

    app = mount(Canvas, {
      target,
      props: {
        floor,
        viewport: { ...DEFAULT_VIEWPORT },
        width: 800,
        height: 600,
        furnitureObjects: floor.furnitureObjects,
      },
    });
    flushSync();

    expect(target.querySelector("g.furniture-shape")).not.toBeNull();
  });
  ```

- [ ] **Step 2: Run test to verify it fails**

  ```bash
  cd packages/editor && npm run test -- --reporter=verbose Canvas
  ```
  Expected: the new test fails (Canvas doesn't accept `furnitureObjects` yet).

- [ ] **Step 3: Update `Canvas.svelte`**

  Add imports at the top of the `<script>` block:

  ```ts
  import type { FurnitureObject } from "@myhome/geometry";
  import { getTemplate } from "../furnitureLibrary";
  import FurnitureShape from "./FurnitureShape.svelte";
  import FurnitureHandles from "./FurnitureHandles.svelte";
  ```

  Add new props to the props destructure (after existing props):

  ```ts
  furnitureObjects = [] as FurnitureObject[],
  selectedFurnitureId = null as string | null,
  onselectfurniture,
  onmovefurniturestart,
  onresizefurniturestart,
  onrotatefurniturestart,
  ```

  Add to the type annotation block:

  ```ts
  furnitureObjects?: FurnitureObject[];
  selectedFurnitureId?: string | null;
  onselectfurniture?: (id: string | null) => void;
  onmovefurniturestart?: (id: string, worldPoint: Point) => void;
  onresizefurniturestart?: (id: string, corner: "tl"|"tr"|"bl"|"br", worldPoint: Point) => void;
  onrotatefurniturestart?: (id: string, worldPoint: Point) => void;
  ```

  Add a derived for the selected furniture object:

  ```ts
  const selectedFurnitureObj = $derived(
    selectedFurnitureId ? (furnitureObjects.find((o) => o.id === selectedFurnitureId) ?? null) : null
  );
  ```

  In `handleClick`, when `tool === "select"` and clicking on canvas background (the existing `onselect?.(null)` block), also clear furniture selection:

  ```ts
  if (tool === "select") {
    onselect?.(null);
    onselectopening?.(null);
    onselectroom?.(null);
    onselectfurniture?.(null);  // add this line
    return;
  }
  ```

  In the SVG template, between the rooms `{#each}` and the walls `{#each}`, add:

  ```svelte
  {#each furnitureObjects as obj (obj.id)}
    {@const tmpl = getTemplate(obj.templateId)}
    {#if tmpl}
      <FurnitureShape
        object={obj}
        template={tmpl}
        {viewport}
        {tool}
        selected={obj.id === selectedFurnitureId}
        onselect={(id) => { onselectfurniture?.(id); }}
        onbodymousedown={(id, event) => {
          event.stopPropagation();
          onmovefurniturestart?.(id, toWorld(event));
        }}
      />
    {/if}
  {/each}
  {#if selectedFurnitureObj}
    <FurnitureHandles
      object={selectedFurnitureObj}
      {viewport}
      onresizestart={(id, corner, event) => {
        event.stopPropagation();
        onresizefurniturestart?.(id, corner, toWorld(event));
      }}
      onrotatestart={(id, event) => {
        event.stopPropagation();
        onrotatefurniturestart?.(id, toWorld(event));
      }}
    />
  {/if}
  ```

- [ ] **Step 4: Run all Canvas tests**

  ```bash
  cd packages/editor && npm run test -- --reporter=verbose Canvas
  ```
  Expected: all pass including the new test.

- [ ] **Step 5: Commit**

  ```bash
  git add packages/editor/src/lib/components/Canvas.svelte packages/editor/test/Canvas.test.ts
  git commit -m "feat: integrate furniture rendering and handles into Canvas"
  ```

---

## Task 9: App.svelte Integration

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Create: `packages/editor/test/App.furniture.test.ts`

Wire up the furniture library panel, toolbar toggle button, drag-drop-to-place, move/resize/rotate interactions, keyboard delete, and undo/redo.

**Drag state types (used only inside App.svelte):**

```ts
type FurnitureDragMode =
  | { type: "move"; id: string; startX: number; startY: number; mouseStartX: number; mouseStartY: number }
  | { type: "resize"; id: string; corner: "tl"|"tr"|"bl"|"br"; fixedX: number; fixedY: number; rotation: number }
  | { type: "rotate"; id: string; centerX: number; centerY: number };
```

**Resize math** (when dragging corner `corner` to `mouseWorldX, mouseWorldY`):

```ts
// Opposite corner's world position (fixed anchor):
// fixedX, fixedY = world coords of the corner opposite to `corner` at drag start

const rad = rotation * Math.PI / 180;
const cos = Math.cos(rad);
const sin = Math.sin(rad);

// Vector from fixed corner to mouse (world space)
const dx = mouseWorldX - fixedX;
const dy = mouseWorldY - fixedY;

// Project onto object's local axes
const localX = cos * dx + sin * dy;
const localY = -sin * dx + cos * dy;

// For corner "br" (bottom-right), local axes point toward br
// For other corners, adjust sign:
const signX = (corner === "tr" || corner === "br") ? 1 : -1;
const signY = (corner === "bl" || corner === "br") ? 1 : -1;
const newHW = Math.max(0.05, signX * localX / 2);  // half-width in world coords
const newHH = Math.max(0.05, signY * localY / 2);  // half-height in world coords

// Wait — this isn't right. Let me be more precise.
```

**Correct resize math:**

When user drags corner `corner`, the opposite corner `opp` stays fixed at `(fixedX, fixedY)` in world coords.

The dragged corner is now at `(mouseWorldX, mouseWorldY)`.

New object center = midpoint of opposite and dragged corner:
```
newCX = (fixedX + mouseWorldX) / 2
newCY = (fixedY + mouseWorldY) / 2
```

New extents in local frame: project (mouse - fixed) onto object axes:
```
deltaX = mouseWorldX - fixedX
deltaY = mouseWorldY - fixedY
localExtentX = (cos * deltaX + sin * deltaY) / 2   // half-width in local frame
localExtentY = (-sin * deltaX + cos * deltaY) / 2  // half-height in local frame
newWidth  = Math.max(0.1, Math.abs(localExtentX) * 2)
newHeight = Math.max(0.1, Math.abs(localExtentY) * 2)
```

**Rotate math:**

```ts
const dx = mouseWorldX - centerX;
const dy = mouseWorldY - centerY;
const angle = Math.atan2(dx, -dy) * 180 / Math.PI; // 0 = up, 90 = right
```

**Computing the fixed corner's world position at drag start:**

Given object `{x, y, width, height, rotation}`, to get corner `opp = opposite(corner)`:
```ts
function worldCorner(obj: FurnitureObject, c: "tl"|"tr"|"br"|"bl"): {x: number, y: number} {
  const hw = obj.width / 2, hh = obj.height / 2;
  const lx = (c === "tr" || c === "br") ? hw : -hw;
  const ly = (c === "bl" || c === "br") ? hh : -hh;
  const rad = obj.rotation * Math.PI / 180;
  const cos = Math.cos(rad), sin = Math.sin(rad);
  return { x: obj.x + cos * lx - sin * ly, y: obj.y + sin * lx + cos * ly };
}

function oppositeCorner(c: "tl"|"tr"|"br"|"bl"): "tl"|"tr"|"br"|"bl" {
  return c === "tl" ? "br" : c === "tr" ? "bl" : c === "br" ? "tl" : "tr";
}
```

- [ ] **Step 1: Write failing tests**

  Create `packages/editor/test/App.furniture.test.ts`:

  ```ts
  import { describe, it, expect, afterEach, beforeEach, vi } from "vitest";
  import { mount, unmount, flushSync, tick } from "svelte";
  import App from "../src/App.svelte";

  function stubFetch404() {
    vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
      if (url === "/api/auth/me") return Promise.resolve({ ok: true, status: 200, json: async () => ({ id: "u1", username: "admin", role: "admin" }) });
      return Promise.resolve({ ok: false, status: 404, json: async () => undefined });
    }));
  }

  async function mountAndLoad(target: HTMLElement): Promise<ReturnType<typeof mount>> {
    window.location.hash = "#/plan";
    const app = mount(App, { target });
    await tick(); await tick(); await tick();
    flushSync();
    return app;
  }

  describe("App — furniture", () => {
    let target: HTMLElement;
    let app: ReturnType<typeof mount> | undefined;

    beforeEach(() => { stubFetch404(); });
    afterEach(() => {
      if (app) { unmount(app); app = undefined; }
      target?.remove();
      vi.unstubAllGlobals();
    });

    it("renders the Furniture toolbar button", async () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      app = await mountAndLoad(target);

      const btn = Array.from(target.querySelectorAll(".floating-toolbar .ft-btn"))
        .find((b) => b.textContent?.includes("Furniture")) as HTMLButtonElement | undefined;
      expect(btn).toBeDefined();
    });

    it("clicking Furniture button toggles the library panel", async () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      app = await mountAndLoad(target);

      expect(target.querySelector(".furniture-panel")).toBeNull();

      const btn = Array.from(target.querySelectorAll(".floating-toolbar .ft-btn"))
        .find((b) => b.textContent?.includes("Furniture")) as HTMLButtonElement;
      btn.click();
      flushSync();

      expect(target.querySelector(".furniture-panel")).not.toBeNull();
    });

    it("dropping a furnitureTemplateId onto the canvas creates a furniture shape", async () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      app = await mountAndLoad(target);

      const canvasArea = target.querySelector(".canvas-area") as HTMLElement;
      expect(canvasArea).not.toBeNull();

      const dt = {
        getData: (k: string) => k === "furnitureTemplateId" ? "sofa" : "",
        setData: () => {},
      } as unknown as DataTransfer;

      canvasArea.dispatchEvent(new DragEvent("drop", {
        bubbles: true,
        clientX: 400,
        clientY: 300,
        dataTransfer: dt,
      }));
      flushSync();

      expect(target.querySelector("g.furniture-shape")).not.toBeNull();
    });

    it("clicking a furniture shape selects it and shows handles", async () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      app = await mountAndLoad(target);

      // Drop a sofa first
      const canvasArea = target.querySelector(".canvas-area") as HTMLElement;
      const dt = { getData: (k: string) => k === "furnitureTemplateId" ? "sofa" : "", setData: () => {} } as unknown as DataTransfer;
      canvasArea.dispatchEvent(new DragEvent("drop", { bubbles: true, clientX: 400, clientY: 300, dataTransfer: dt }));
      flushSync();

      // Click it to select
      const shape = target.querySelector("g.furniture-shape")!;
      shape.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      flushSync();

      expect(target.querySelector("rect.corner-handle")).not.toBeNull();
    });

    it("Delete key removes selected furniture", async () => {
      target = document.createElement("div");
      document.body.appendChild(target);
      app = await mountAndLoad(target);

      const canvasArea = target.querySelector(".canvas-area") as HTMLElement;
      const dt = { getData: (k: string) => k === "furnitureTemplateId" ? "sofa" : "", setData: () => {} } as unknown as DataTransfer;
      canvasArea.dispatchEvent(new DragEvent("drop", { bubbles: true, clientX: 400, clientY: 300, dataTransfer: dt }));
      flushSync();

      target.querySelector("g.furniture-shape")!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      flushSync();
      expect(target.querySelector("g.furniture-shape")).not.toBeNull();

      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Delete" }));
      flushSync();
      expect(target.querySelector("g.furniture-shape")).toBeNull();
    });
  });
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  cd packages/editor && npm run test -- --reporter=verbose App.furniture
  ```
  Expected: FAIL.

- [ ] **Step 3: Update `App.svelte` — imports and state**

  Add imports (alongside existing imports):

  ```ts
  import FurnitureLibraryPanel from "./lib/components/FurnitureLibraryPanel.svelte";
  import type { FurnitureObject } from "@myhome/geometry";
  import { getTemplate } from "./lib/furnitureLibrary";
  ```

  Add state variables (alongside existing `$state` declarations):

  ```ts
  let furnitureLibraryOpen = $state(false);
  let selectedFurnitureId = $state<string | null>(null);

  type FurnitureDragMode =
    | { type: "move"; id: string; startX: number; startY: number; mouseStartX: number; mouseStartY: number }
    | { type: "resize"; id: string; corner: "tl"|"tr"|"bl"|"br"; fixedX: number; fixedY: number; rotation: number }
    | { type: "rotate"; id: string; centerX: number; centerY: number };

  let furnitureDrag = $state<FurnitureDragMode | null>(null);
  ```

- [ ] **Step 4: Add helper functions to `App.svelte`**

  Add these functions after `handleOpeningHandleDrag`:

  ```ts
  function worldCorner(obj: FurnitureObject, c: "tl"|"tr"|"br"|"bl"): { x: number; y: number } {
    const hw = obj.width / 2, hh = obj.height / 2;
    const lx = (c === "tr" || c === "br") ? hw : -hw;
    const ly = (c === "bl" || c === "br") ? hh : -hh;
    const rad = obj.rotation * Math.PI / 180;
    const cos = Math.cos(rad), sin = Math.sin(rad);
    return { x: obj.x + cos * lx - sin * ly, y: obj.y + sin * lx + cos * ly };
  }

  function oppositeCorner(c: "tl"|"tr"|"br"|"bl"): "tl"|"tr"|"br"|"bl" {
    return c === "tl" ? "br" : c === "tr" ? "bl" : c === "br" ? "tl" : "tr";
  }

  function handleSelectFurniture(id: string | null): void {
    selectedFurnitureId = id;
    if (id !== null) {
      toolStore.select(null);
      toolStore.selectRoom(null);
      toolStore.selectOpening(null);
    }
  }

  function handleMoveFurnitureStart(id: string, worldPoint: Point): void {
    const obj = floorStore.floor.furnitureObjects?.find((o) => o.id === id);
    if (!obj) return;
    floorStore.saveSnapshot();
    furnitureDrag = { type: "move", id, startX: obj.x, startY: obj.y, mouseStartX: worldPoint.x, mouseStartY: worldPoint.y };
  }

  function handleResizeFurnitureStart(id: string, corner: "tl"|"tr"|"br"|"bl", _worldPoint: Point): void {
    const obj = floorStore.floor.furnitureObjects?.find((o) => o.id === id);
    if (!obj) return;
    floorStore.saveSnapshot();
    const opp = oppositeCorner(corner);
    const fixed = worldCorner(obj, opp);
    furnitureDrag = { type: "resize", id, corner, fixedX: fixed.x, fixedY: fixed.y, rotation: obj.rotation };
  }

  function handleRotateFurnitureStart(id: string, _worldPoint: Point): void {
    const obj = floorStore.floor.furnitureObjects?.find((o) => o.id === id);
    if (!obj) return;
    floorStore.saveSnapshot();
    furnitureDrag = { type: "rotate", id, centerX: obj.x, centerY: obj.y };
  }

  function handleFurnitureDragMove(worldPoint: Point): void {
    if (!furnitureDrag) return;
    if (furnitureDrag.type === "move") {
      const d = furnitureDrag;
      floorStore.moveFurniture(d.id, d.startX + worldPoint.x - d.mouseStartX, d.startY + worldPoint.y - d.mouseStartY, { skipHistory: true });
    } else if (furnitureDrag.type === "resize") {
      const d = furnitureDrag;
      const rad = d.rotation * Math.PI / 180;
      const cos = Math.cos(rad), sin = Math.sin(rad);
      const dx = worldPoint.x - d.fixedX;
      const dy = worldPoint.y - d.fixedY;
      const localX = cos * dx + sin * dy;
      const localY = -sin * dx + cos * dy;
      const newWidth = Math.max(0.1, Math.abs(localX));
      const newHeight = Math.max(0.1, Math.abs(localY));
      const newCX = (d.fixedX + worldPoint.x) / 2;
      const newCY = (d.fixedY + worldPoint.y) / 2;
      floorStore.resizeFurniture(d.id, newWidth, newHeight, { skipHistory: true });
      floorStore.moveFurniture(d.id, newCX, newCY, { skipHistory: true });
    } else if (furnitureDrag.type === "rotate") {
      const d = furnitureDrag;
      const dx = worldPoint.x - d.centerX;
      const dy = worldPoint.y - d.centerY;
      const angle = Math.atan2(dx, -dy) * 180 / Math.PI;
      floorStore.rotateFurniture(d.id, angle, { skipHistory: true });
    }
  }
  ```

- [ ] **Step 5: Update `handlePointerMove` to route furniture drags**

  The existing `handlePointerMove` function:

  ```ts
  function handlePointerMove(world: Point): void {
    toolStore.setCursor(world);
    if (toolStore.state.draggingPoint) handleDragMove(world);
    if (toolStore.state.draggingOpeningHandle) handleOpeningHandleDrag(world);
    if (furnitureDrag) handleFurnitureDragMove(world);  // add this line
  }
  ```

- [ ] **Step 6: Update `handleDragEnd` to clear furniture drag**

  ```ts
  function handleDragEnd(): void {
    toolStore.endDrag();
    furnitureDrag = null;  // add this line
  }
  ```

- [ ] **Step 7: Update `handleDelete` to include furniture**

  ```ts
  function handleDelete(): void {
    const { selectedId, selectedOpeningId } = toolStore.state;
    if (selectedFurnitureId) {
      floorStore.removeFurniture(selectedFurnitureId);
      selectedFurnitureId = null;
      return;
    }
    if (selectedId) { floorStore.removeWall(selectedId); toolStore.select(null); }
    else if (selectedOpeningId) { floorStore.removeOpening(selectedOpeningId); toolStore.selectOpening(null); }
  }
  ```

- [ ] **Step 8: Update `handleKeydown` to allow Delete for furniture**

  The existing keyboard handler already calls `handleDelete` when `Delete`/`Backspace` is pressed. Update the guard condition to also consider `selectedFurnitureId`:

  ```ts
  if ((event.key === "Delete" || event.key === "Backspace") &&
      (toolStore.state.selectedId || toolStore.state.selectedOpeningId || selectedFurnitureId)) handleDelete();
  ```

- [ ] **Step 9: Update `handleDrop` in `App.svelte` to handle furniture drops**

  In the existing `handleDrop` function, add a new branch before the existing `layerId` checks:

  ```ts
  function handleDrop(e: DragEvent): void {
    e.preventDefault();

    // Check for furniture drop first
    const furnitureTemplateId = e.dataTransfer?.getData("furnitureTemplateId");
    if (furnitureTemplateId) {
      const template = getTemplate(furnitureTemplateId);
      if (!template) return;
      const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
      const worldX = (e.clientX - rect.left - viewportStore.viewport.panX) / viewportStore.viewport.zoom;
      const worldY = (e.clientY - rect.top - viewportStore.viewport.panY) / viewportStore.viewport.zoom;
      floorStore.addFurniture({
        templateId: furnitureTemplateId,
        x: worldX,
        y: worldY,
        width: template.defaultWidth,
        height: template.defaultHeight,
        rotation: 0,
      });
      return;
    }

    // ... existing layerId handling unchanged ...
  ```

- [ ] **Step 10: Update `handleUndo` and `handleRedo` to clear furniture selection**

  ```ts
  function handleUndo(): void {
    floorStore.undo();
    toolStore.select(null); toolStore.selectRoom(null); toolStore.selectOpening(null);
    selectedFurnitureId = null;  // add this line
  }

  function handleRedo(): void {
    floorStore.redo();
    toolStore.select(null); toolStore.selectRoom(null); toolStore.selectOpening(null);
    selectedFurnitureId = null;  // add this line
  }
  ```

- [ ] **Step 11: Add the Furniture toolbar button (in the floating toolbar template)**

  In the `{#if floorStore.loaded && !allFloorsMode}` block, add the Furniture button alongside the Picker button (after the Layers dropdown, before the separator):

  ```svelte
  <button
    class="ft-btn"
    class:active={furnitureLibraryOpen}
    title="Toggle furniture library"
    onclick={() => { furnitureLibraryOpen = !furnitureLibraryOpen; }}
  >🪑 <span class="ft-label">Furniture</span></button>
  ```

- [ ] **Step 12: Add FurnitureLibraryPanel to the right panels template**

  In the `.right-panels` div (where `ItemPickerPanel` appears), add:

  ```svelte
  {#if furnitureLibraryOpen}
    <FurnitureLibraryPanel />
  {/if}
  ```

- [ ] **Step 13: Pass furniture props to Canvas**

  Update the `<Canvas ... />` call in the `{:else}` branch to include:

  ```svelte
  furnitureObjects={floorStore.floor.furnitureObjects ?? []}
  {selectedFurnitureId}
  onselectfurniture={handleSelectFurniture}
  onmovefurniturestart={handleMoveFurnitureStart}
  onresizefurniturestart={handleResizeFurnitureStart}
  onrotatefurniturestart={handleRotateFurnitureStart}
  ```

- [ ] **Step 14: Run App.furniture tests**

  ```bash
  cd packages/editor && npm run test -- --reporter=verbose App.furniture
  ```
  Expected: all pass.

- [ ] **Step 15: Run all editor tests**

  ```bash
  cd packages/editor && npm run test
  ```
  Expected: all pass. Note: the App.test.ts toolbar title list check will need updating because the new "Furniture" button is added. Update this line in `App.test.ts`:

  ```ts
  expect(titles).toEqual([
    "Toggle item picker", "Toggle furniture library", "Save", "Reset view",
    "Undo (Ctrl+Z)", "Redo (Ctrl+Y)", "Select", "Wall", "Divider", "Door", "Window", "Delete selected (Del)"
  ]);
  ```

- [ ] **Step 16: Commit**

  ```bash
  git add packages/editor/src/App.svelte packages/editor/test/App.furniture.test.ts packages/editor/test/App.test.ts
  git commit -m "feat: wire furniture library panel, drop, select, move, resize, rotate, delete in App"
  ```

---

## Self-Review Checklist

Run this mentally after implementing all tasks before declaring done:

- [ ] All 35 templates have unique ids, non-zero dimensions, non-empty svgContent
- [ ] Dropping a furniture item from the panel onto the canvas places it at the correct world position
- [ ] Clicking a placed object selects it (shows 4 corner handles + 1 rotation handle)
- [ ] Dragging the object body moves it; releasing leaves it in the new position; undo restores
- [ ] Dragging a corner resizes from the opposite fixed corner; aspect ratio changes freely
- [ ] Dragging the rotation handle rotates around the object center
- [ ] Pressing Delete/Backspace removes the selected furniture object
- [ ] Undo/redo cycle works for add, remove, move, resize, rotate
- [ ] Old floor plan documents (without `furnitureObjects`) load without error
- [ ] Selecting furniture clears wall/opening/room selection and vice versa
- [ ] The furniture panel shows a search field that filters by label

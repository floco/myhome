import { describe, it, expect } from "vitest";
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
import type { FurnitureParamDef } from "../src/lib/furnitureLibrary";
import type { FurnitureObject } from "@myhome/geometry";

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

  it("resolveFurnitureParams returns an empty object for a template with no schema and no instance params", () => {
    const t = getTemplate("coffee-table")!;
    const obj: FurnitureObject = { id: "f1", templateId: "coffee-table", x: 0, y: 0, width: 1.2, height: 0.6, rotation: 0 };
    expect(resolveFurnitureParams(t, obj)).toEqual({});
  });

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

  it("sofa declares shape and corner params, with corner defaulting to se", () => {
    const t = getTemplate("sofa")!;
    expect(defaultFurnitureParams(t)).toEqual({ shape: "straight", corner: "se" });
  });

  it("sofa corner param is visibleWhen shape is l-shaped", () => {
    const t = getTemplate("sofa")!;
    const corner = t.params?.find((p) => p.id === "corner") as Extract<FurnitureParamDef, { type: "enum" }> | undefined;
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
});

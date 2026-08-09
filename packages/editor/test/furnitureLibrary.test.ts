import { describe, it, expect } from "vitest";
import {
  FURNITURE_TEMPLATES,
  getTemplate,
  FURNITURE_CATEGORIES,
  defaultFurnitureParams,
  resolveFurnitureParams,
  resolveFurnitureSvg,
} from "../src/lib/furnitureLibrary";
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
});

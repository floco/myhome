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

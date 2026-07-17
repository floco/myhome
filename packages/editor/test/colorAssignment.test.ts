import { describe, it, expect } from "vitest";
import { assignCategoryColors } from "../src/lib/colorAssignment";

describe("assignCategoryColors", () => {
  it("gives every category within the base palette a distinct color", () => {
    const categories = ["Tools", "Furniture", "Electronics", "Books", "Kitchen"];
    const colors = assignCategoryColors(categories);
    const values = [...colors.values()];
    expect(new Set(values).size).toBe(categories.length);
  });

  it("gives every category a distinct color even beyond the 8-slot base palette", () => {
    const categories = Array.from({ length: 15 }, (_, i) => `Category ${i}`);
    const colors = assignCategoryColors(categories);
    const values = [...colors.values()];
    expect(new Set(values).size).toBe(15);
  });

  it("is deterministic for the same category set regardless of input order", () => {
    const a = assignCategoryColors(["Tools", "Furniture", "Electronics"]);
    const b = assignCategoryColors(["Electronics", "Tools", "Furniture"]);
    expect(a).toEqual(b);
  });

  it("returns an empty map for no categories", () => {
    expect(assignCategoryColors([]).size).toBe(0);
  });

  it("deduplicates repeated category names", () => {
    const colors = assignCategoryColors(["Tools", "Tools", "Furniture"]);
    expect(colors.size).toBe(2);
  });

  it("uses the base palette tokens for the first 8 categories", () => {
    const categories = ["A", "B", "C", "D", "E", "F", "G", "H"];
    const colors = assignCategoryColors(categories);
    for (const color of colors.values()) {
      expect(color).toMatch(/^var\(--chart-series-[1-8]\)$/);
    }
  });
});

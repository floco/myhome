import { describe, it, expect } from "vitest";
import { computeTreemap, cellContentTier } from "../src/lib/treemapLayout";

describe("computeTreemap", () => {
  it("tiles the full rectangle with no gaps or overlaps", () => {
    const rects = computeTreemap([50, 30, 20], 300, 200);
    const totalArea = rects.reduce((a, r) => a + r.w * r.h, 0);
    expect(totalArea).toBeCloseTo(300 * 200, 0);
  });

  it("gives each rect area proportional to its input value", () => {
    const rects = computeTreemap([60, 40], 300, 200);
    const area0 = rects[0].w * rects[0].h;
    const area1 = rects[1].w * rects[1].h;
    expect(area0 / area1).toBeCloseTo(60 / 40, 1);
  });

  it("returns one rect per input value", () => {
    const rects = computeTreemap([10, 20, 30], 100, 100);
    expect(rects).toHaveLength(3);
  });

  it("returns an empty array for empty input", () => {
    expect(computeTreemap([], 100, 100)).toEqual([]);
  });

  it("fills the whole rect for a single value", () => {
    const rects = computeTreemap([42], 300, 200);
    expect(rects).toEqual([{ x: 0, y: 0, w: 300, h: 200 }]);
  });
});

describe("cellContentTier", () => {
  it("shows a full label for a roomy cell", () => {
    expect(cellContentTier(100, 50)).toBe("label");
  });

  it("shows only an icon for a small-but-square cell", () => {
    expect(cellContentTier(30, 30)).toBe("icon");
  });

  it("shows nothing for a thin sliver", () => {
    expect(cellContentTier(300, 8)).toBe("none");
  });

  it("shows nothing for a tiny cell", () => {
    expect(cellContentTier(10, 10)).toBe("none");
  });
});

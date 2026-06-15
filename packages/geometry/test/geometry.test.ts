import { describe, it, expect } from "vitest";
import { segmentsIntersection, pointOnSegmentInterior } from "../src/geometry";

describe("segmentsIntersection", () => {
  it("finds the crossing point of two segments that cross in their interiors", () => {
    const p = segmentsIntersection(
      { x: 0, y: 0 },
      { x: 4, y: 4 },
      { x: 0, y: 4 },
      { x: 4, y: 0 }
    );
    expect(p).not.toBeNull();
    expect(p!.x).toBeCloseTo(2, 5);
    expect(p!.y).toBeCloseTo(2, 5);
  });

  it("returns null for parallel segments", () => {
    const p = segmentsIntersection(
      { x: 0, y: 0 },
      { x: 4, y: 0 },
      { x: 0, y: 1 },
      { x: 4, y: 1 }
    );
    expect(p).toBeNull();
  });

  it("returns null when segments only touch at an endpoint", () => {
    const p = segmentsIntersection(
      { x: 0, y: 0 },
      { x: 4, y: 0 },
      { x: 4, y: 0 },
      { x: 4, y: 4 }
    );
    expect(p).toBeNull();
  });

  it("returns null when segments don't cross within their bounds", () => {
    const p = segmentsIntersection(
      { x: 0, y: 0 },
      { x: 1, y: 1 },
      { x: 5, y: 5 },
      { x: 5, y: -5 }
    );
    expect(p).toBeNull();
  });
});

describe("pointOnSegmentInterior", () => {
  it("returns true for a point strictly between the endpoints", () => {
    expect(pointOnSegmentInterior({ x: 2, y: 0 }, { x: 0, y: 0 }, { x: 4, y: 0 })).toBe(true);
  });

  it("returns false for a point at an endpoint", () => {
    expect(pointOnSegmentInterior({ x: 0, y: 0 }, { x: 0, y: 0 }, { x: 4, y: 0 })).toBe(false);
    expect(pointOnSegmentInterior({ x: 4, y: 0 }, { x: 0, y: 0 }, { x: 4, y: 0 })).toBe(false);
  });

  it("returns false for a point not collinear with the segment", () => {
    expect(pointOnSegmentInterior({ x: 2, y: 1 }, { x: 0, y: 0 }, { x: 4, y: 0 })).toBe(false);
  });

  it("returns false for a point collinear but outside the segment's range", () => {
    expect(pointOnSegmentInterior({ x: 6, y: 0 }, { x: 0, y: 0 }, { x: 4, y: 0 })).toBe(false);
  });
});

import { describe, it, expect } from "vitest";
import { segmentsIntersection, pointOnSegmentInterior } from "../src/geometry";
import {
  polygonSignedArea,
  polygonArea,
  polygonCentroid,
  pointInPolygon,
} from "../src/geometry";

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

describe("polygonSignedArea / polygonArea", () => {
  it("returns a positive signed area for a counter-clockwise square", () => {
    const square = [
      { x: 0, y: 0 },
      { x: 1, y: 0 },
      { x: 1, y: 1 },
      { x: 0, y: 1 },
    ];
    expect(polygonSignedArea(square)).toBeCloseTo(1, 5);
    expect(polygonArea(square)).toBeCloseTo(1, 5);
  });

  it("returns a negative signed area for the same square traversed clockwise", () => {
    const square = [
      { x: 0, y: 0 },
      { x: 0, y: 1 },
      { x: 1, y: 1 },
      { x: 1, y: 0 },
    ];
    expect(polygonSignedArea(square)).toBeCloseTo(-1, 5);
    expect(polygonArea(square)).toBeCloseTo(1, 5);
  });
});

describe("polygonCentroid", () => {
  it("computes the centroid of a rectangle", () => {
    const rect = [
      { x: 0, y: 0 },
      { x: 4, y: 0 },
      { x: 4, y: 2 },
      { x: 0, y: 2 },
    ];
    const c = polygonCentroid(rect);
    expect(c.x).toBeCloseTo(2, 5);
    expect(c.y).toBeCloseTo(1, 5);
  });

  it("computes the centroid of an L-shape (not the bounding-box center)", () => {
    // L-shape: 4x4 square minus a 2x2 notch from the top-right corner
    const lShape = [
      { x: 0, y: 0 },
      { x: 4, y: 0 },
      { x: 4, y: 2 },
      { x: 2, y: 2 },
      { x: 2, y: 4 },
      { x: 0, y: 4 },
    ];
    const c = polygonCentroid(lShape);
    // The bounding-box center would be (2,2), but the L-shape's mass is
    // skewed toward the bottom-left.
    expect(c.x).toBeLessThan(2);
    expect(c.y).toBeLessThan(2);
    expect(pointInPolygon(c, lShape)).toBe(true);
  });
});

describe("pointInPolygon", () => {
  const square = [
    { x: 0, y: 0 },
    { x: 4, y: 0 },
    { x: 4, y: 4 },
    { x: 0, y: 4 },
  ];

  it("returns true for a point inside the polygon", () => {
    expect(pointInPolygon({ x: 2, y: 2 }, square)).toBe(true);
  });

  it("returns false for a point outside the polygon", () => {
    expect(pointInPolygon({ x: 5, y: 5 }, square)).toBe(false);
  });
});

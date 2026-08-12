import { describe, it, expect } from "vitest";
import { segmentsIntersection, pointOnSegmentInterior, computeMiterCorners } from "../src/geometry";
import {
  polygonSignedArea,
  polygonArea,
  polygonCentroid,
  pointInPolygon,
  computeLabelPosition,
} from "../src/geometry";
import type { Room, Point } from "../src/types";

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

describe("computeMiterCorners", () => {
  const P = { x: 0, y: 0 };

  it("90° corner: wall going right meeting wall going up (decreasing y)", () => {
    const result = computeMiterCorners(P, { x: 1, y: 0 }, 0.1, { x: 0, y: -1 }, 0.1);
    expect(result).not.toBeNull();
    expect(result!.plus.x).toBeCloseTo(0.1);
    expect(result!.plus.y).toBeCloseTo(0.1);
    expect(result!.minus.x).toBeCloseTo(-0.1);
    expect(result!.minus.y).toBeCloseTo(-0.1);
  });

  it("90° corner: different thicknesses", () => {
    const result = computeMiterCorners(P, { x: 1, y: 0 }, 0.1, { x: 0, y: -1 }, 0.15);
    expect(result).not.toBeNull();
    expect(result!.plus.x).toBeCloseTo(0.15);
    expect(result!.plus.y).toBeCloseTo(0.1);
    expect(result!.minus.x).toBeCloseTo(-0.15);
    expect(result!.minus.y).toBeCloseTo(-0.1);
  });

  it("parallel walls return null", () => {
    const result = computeMiterCorners(P, { x: 1, y: 0 }, 0.1, { x: 1, y: 0 }, 0.1);
    expect(result).toBeNull();
  });

  it("anti-parallel walls (180°) return null", () => {
    const result = computeMiterCorners(P, { x: 1, y: 0 }, 0.1, { x: -1, y: 0 }, 0.1);
    expect(result).toBeNull();
  });

  it("45° corner returns a miter further from P than 90°", () => {
    const s = Math.SQRT2 / 2;
    const result = computeMiterCorners(P, { x: 1, y: 0 }, 0.1, { x: s, y: -s }, 0.1);
    expect(result).not.toBeNull();
    expect(Math.hypot(result!.plus.x - P.x, result!.plus.y - P.y)).toBeGreaterThan(0.1);
  });

  it("nearly straight wall deflection (170°) returns null due to spike limit", () => {
    // Two walls forming a ~170° angle (almost straight through) would produce a
    // miter spike far from P — fall back to flat cap.
    const angle = (170 * Math.PI) / 180;
    const result = computeMiterCorners(
      P, { x: 1, y: 0 }, 0.1,
      { x: Math.cos(angle), y: Math.sin(angle) }, 0.1,
    );
    expect(result).toBeNull();
  });
});

function makeRoom(id: string, polygon: Point[] | null): Room {
  return { id, label: id, haAreaId: null, polygon, areaM2: 0 };
}

describe("computeLabelPosition", () => {
  const outerSquare: Point[] = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }];

  it("returns the plain centroid when no other room is contained inside it", () => {
    const room = makeRoom("outer", outerSquare);
    const other = makeRoom("far", [{ x: 20, y: 20 }, { x: 22, y: 20 }, { x: 22, y: 22 }, { x: 20, y: 22 }]);
    const pos = computeLabelPosition(room, [room, other]);
    expect(pos.x).toBeCloseTo(5, 5);
    expect(pos.y).toBeCloseTo(5, 5);
  });

  it("ignores a room that only barely overlaps (below the 50% containment threshold)", () => {
    const room = makeRoom("outer", outerSquare);
    // 12x12 room overlapping the outer square only in its bottom-left 2x2 corner (~2.8% of its own area)
    const sliver = makeRoom("sliver", [{ x: 8, y: 8 }, { x: 20, y: 8 }, { x: 20, y: 20 }, { x: 8, y: 20 }]);
    const pos = computeLabelPosition(room, [room, sliver]);
    expect(pos.x).toBeCloseTo(5, 5);
    expect(pos.y).toBeCloseTo(5, 5);
  });

  it("moves the label off a fully-contained child room's area", () => {
    const room = makeRoom("zone", outerSquare);
    // Fully inside the outer square, and it covers the outer square's own centroid (5,5).
    const child = makeRoom("child", [{ x: 3, y: 3 }, { x: 7, y: 3 }, { x: 7, y: 7 }, { x: 3, y: 7 }]);
    const pos = computeLabelPosition(room, [room, child]);
    expect(pointInPolygon(pos, child.polygon!)).toBe(false);
    expect(pointInPolygon(pos, room.polygon!)).toBe(true);
    // The plain centroid (5,5) would have landed inside the child -- confirm we moved off it.
    expect(pos.x === 5 && pos.y === 5).toBe(false);
  });

  it("returns {x:0,y:0} when the room has no polygon", () => {
    const room = makeRoom("unresolved", null);
    expect(computeLabelPosition(room, [room])).toEqual({ x: 0, y: 0 });
  });
});

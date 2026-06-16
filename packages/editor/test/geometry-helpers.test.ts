import { describe, it, expect } from "vitest";
import { GRID_SIZE, snapToGrid, distance, findSnapPoint } from "../src/lib/geometry-helpers";

describe("GRID_SIZE", () => {
  it("is 0.1 meters", () => {
    expect(GRID_SIZE).toBe(0.1);
  });
});

describe("snapToGrid", () => {
  it("snaps to the nearest 0.1m grid intersection", () => {
    expect(snapToGrid({ x: 1.27, y: 4.55 })).toEqual({ x: 1.3, y: 4.5 });
  });

  it("leaves points already on the grid unchanged", () => {
    expect(snapToGrid({ x: 2, y: 3 })).toEqual({ x: 2, y: 3 });
  });

  it("rounds toward the nearer grid line", () => {
    expect(snapToGrid({ x: 0.37, y: 0.94 })).toEqual({ x: 0.4, y: 0.9 });
  });

  it("cleans up floating-point drift near an exact grid point", () => {
    expect(snapToGrid({ x: 1.0000004, y: 2.9999996 })).toEqual({ x: 1, y: 3 });
  });
});

describe("distance", () => {
  it("computes Euclidean distance between two points", () => {
    expect(distance({ x: 0, y: 0 }, { x: 3, y: 4 })).toBe(5);
  });
});

describe("findSnapPoint", () => {
  const candidates = [
    { x: 0, y: 0 },
    { x: 4, y: 0 },
    { x: 2, y: 3 },
  ];

  it("returns the closest candidate within radius", () => {
    expect(findSnapPoint({ x: 0.05, y: 0.05 }, candidates, 0.5)).toEqual({ x: 0, y: 0 });
  });

  it("returns null when no candidate is within radius", () => {
    expect(findSnapPoint({ x: 10, y: 10 }, candidates, 0.5)).toBeNull();
  });

  it("returns the nearest of multiple candidates within radius", () => {
    const close = [
      { x: 1, y: 0 },
      { x: 1.1, y: 0 },
    ];
    expect(findSnapPoint({ x: 1, y: 0.05 }, close, 1)).toEqual({ x: 1, y: 0 });
  });
});

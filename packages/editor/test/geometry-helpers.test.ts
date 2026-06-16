import { describe, it, expect } from "vitest";
import { GRID_SIZE, snapToGrid, distance, findSnapPoint, hitTestWall } from "../src/lib/geometry-helpers";
import type { Wall } from "@myhome/geometry";

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

function makeWall(id: string, x0: number, y0: number, x1: number, y1: number): Wall {
  return { id, start: { x: x0, y: y0 }, end: { x: x1, y: y1 }, thickness: 0.15, type: "wall" };
}

describe("hitTestWall", () => {
  const walls: Wall[] = [makeWall("w1", 0, 0, 4, 0)]; // horizontal wall (0,0)→(4,0)

  it("returns null when cursor is far from all walls", () => {
    expect(hitTestWall({ x: 2, y: 5 }, walls, 0.5)).toBeNull();
  });

  it("returns the wall and offset when cursor is near the middle of a wall", () => {
    const result = hitTestWall({ x: 2, y: 0.1 }, walls, 0.5);
    expect(result).not.toBeNull();
    expect(result!.wall.id).toBe("w1");
    expect(result!.offset).toBeCloseTo(2, 5);
  });

  it("clamps projected offset to wall length when cursor is past the end", () => {
    const result = hitTestWall({ x: 5, y: 0 }, walls, 0.5);
    if (result) expect(result.offset).toBeCloseTo(4, 5);
  });

  it("ignores dividers", () => {
    const divider: Wall = { id: "d1", start: { x: 0, y: 0 }, end: { x: 4, y: 0 }, type: "divider" };
    expect(hitTestWall({ x: 2, y: 0 }, [divider], 0.5)).toBeNull();
  });

  it("returns the closest wall when multiple walls are nearby", () => {
    const wallA = makeWall("wA", 0, 0, 4, 0);      // y=0 (closer)
    const wallB = makeWall("wB", 0, 0.3, 4, 0.3);  // y=0.3 (farther)
    const result = hitTestWall({ x: 2, y: 0.1 }, [wallA, wallB], 0.5);
    expect(result!.wall.id).toBe("wA");
  });

  it("grid-snaps the offset (GRID_SIZE=0.1)", () => {
    // cursor at x=1.23 → raw offset=1.23 → snap to 1.2
    const result = hitTestWall({ x: 1.23, y: 0 }, walls, 0.5);
    expect(result!.offset).toBeCloseTo(1.2, 5);
  });
});

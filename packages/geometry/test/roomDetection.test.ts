import { describe, it, expect } from "vitest";
import { detectRooms } from "../src/roomDetection";
import type { Wall, Point } from "../src/types";
import { polygonArea } from "../src/geometry";

function wall(id: string, start: Point, end: Point, type: "wall" | "divider" = "wall"): Wall {
  return { id, start, end, thickness: type === "wall" ? 0.15 : undefined, type };
}

describe("detectRooms", () => {
  it("detects a single room from a simple rectangle", () => {
    const walls: Wall[] = [
      wall("w1", { x: 0, y: 0 }, { x: 5, y: 0 }),
      wall("w2", { x: 5, y: 0 }, { x: 5, y: 4 }),
      wall("w3", { x: 5, y: 4 }, { x: 0, y: 4 }),
      wall("w4", { x: 0, y: 4 }, { x: 0, y: 0 }),
    ];

    const rooms = detectRooms(walls);

    expect(rooms).toHaveLength(1);
    expect(rooms[0].areaM2).toBeCloseTo(20, 5);
    expect(polygonArea(rooms[0].polygon)).toBeCloseTo(20, 5);
  });

  it("splits two rooms divided by a physical wall", () => {
    // 4x2 outer rectangle split down the middle by a vertical wall at x=2
    const walls: Wall[] = [
      wall("bottom-left", { x: 0, y: 0 }, { x: 2, y: 0 }),
      wall("bottom-right", { x: 2, y: 0 }, { x: 4, y: 0 }),
      wall("right", { x: 4, y: 0 }, { x: 4, y: 2 }),
      wall("top-right", { x: 4, y: 2 }, { x: 2, y: 2 }),
      wall("top-left", { x: 2, y: 2 }, { x: 0, y: 2 }),
      wall("left", { x: 0, y: 2 }, { x: 0, y: 0 }),
      wall("divider-wall", { x: 2, y: 0 }, { x: 2, y: 2 }),
    ];

    const rooms = detectRooms(walls);

    expect(rooms).toHaveLength(2);
    const areas = rooms.map((r) => r.areaM2).sort();
    expect(areas).toEqual([4, 4]);
  });

  it("splits two rooms divided by a virtual divider (same geometry as a wall)", () => {
    const walls: Wall[] = [
      wall("bottom-left", { x: 0, y: 0 }, { x: 2, y: 0 }),
      wall("bottom-right", { x: 2, y: 0 }, { x: 4, y: 0 }),
      wall("right", { x: 4, y: 0 }, { x: 4, y: 2 }),
      wall("top-right", { x: 4, y: 2 }, { x: 2, y: 2 }),
      wall("top-left", { x: 2, y: 2 }, { x: 0, y: 2 }),
      wall("left", { x: 0, y: 2 }, { x: 0, y: 0 }),
      wall("divider", { x: 2, y: 0 }, { x: 2, y: 2 }, "divider"),
    ];

    const rooms = detectRooms(walls);

    expect(rooms).toHaveLength(2);
    const areas = rooms.map((r) => r.areaM2).sort();
    expect(areas).toEqual([4, 4]);
  });

  it("detects an L-shaped room", () => {
    // L-shape: 4x4 square with a 2x2 notch cut from the top-right corner
    const walls: Wall[] = [
      wall("w1", { x: 0, y: 0 }, { x: 4, y: 0 }),
      wall("w2", { x: 4, y: 0 }, { x: 4, y: 2 }),
      wall("w3", { x: 4, y: 2 }, { x: 2, y: 2 }),
      wall("w4", { x: 2, y: 2 }, { x: 2, y: 4 }),
      wall("w5", { x: 2, y: 4 }, { x: 0, y: 4 }),
      wall("w6", { x: 0, y: 4 }, { x: 0, y: 0 }),
    ];

    const rooms = detectRooms(walls);

    expect(rooms).toHaveLength(1);
    // Full 4x4 (16) minus the 2x2 notch (4) = 12
    expect(rooms[0].areaM2).toBeCloseTo(12, 5);
    expect(rooms[0].polygon).toHaveLength(6);
  });

  it("detects a room with a hole (courtyard) as a separate inner face", () => {
    const outer: Wall[] = [
      wall("o1", { x: 0, y: 0 }, { x: 10, y: 0 }),
      wall("o2", { x: 10, y: 0 }, { x: 10, y: 10 }),
      wall("o3", { x: 10, y: 10 }, { x: 0, y: 10 }),
      wall("o4", { x: 0, y: 10 }, { x: 0, y: 0 }),
    ];
    // Inner courtyard, fully disconnected from the outer loop
    const inner: Wall[] = [
      wall("i1", { x: 4, y: 4 }, { x: 6, y: 4 }),
      wall("i2", { x: 6, y: 4 }, { x: 6, y: 6 }),
      wall("i3", { x: 6, y: 6 }, { x: 4, y: 6 }),
      wall("i4", { x: 4, y: 6 }, { x: 4, y: 4 }),
    ];

    const rooms = detectRooms([...outer, ...inner]);

    expect(rooms).toHaveLength(2);
    const areas = rooms.map((r) => r.areaM2).sort((a, b) => a - b);
    // Courtyard interior (2x2=4) and the outer interior (10x10=100, not
    // subtracting the hole - see spec's centerline simplification)
    expect(areas).toEqual([4, 100]);
  });

  it("produces no room for an unclosed chain of walls", () => {
    const walls: Wall[] = [
      wall("w1", { x: 0, y: 0 }, { x: 5, y: 0 }),
      wall("w2", { x: 5, y: 0 }, { x: 5, y: 4 }),
      wall("w3", { x: 5, y: 4 }, { x: 0, y: 4 }),
      // missing the 4th side - chain does not close
    ];

    const rooms = detectRooms(walls);

    expect(rooms).toHaveLength(0);
  });

  it("detects rooms independently in disconnected wall groups", () => {
    const groupA: Wall[] = [
      wall("a1", { x: 0, y: 0 }, { x: 2, y: 0 }),
      wall("a2", { x: 2, y: 0 }, { x: 2, y: 2 }),
      wall("a3", { x: 2, y: 2 }, { x: 0, y: 2 }),
      wall("a4", { x: 0, y: 2 }, { x: 0, y: 0 }),
    ];
    const groupB: Wall[] = [
      wall("b1", { x: 10, y: 10 }, { x: 13, y: 10 }),
      wall("b2", { x: 13, y: 10 }, { x: 13, y: 13 }),
      wall("b3", { x: 13, y: 13 }, { x: 10, y: 13 }),
      wall("b4", { x: 10, y: 13 }, { x: 10, y: 10 }),
    ];

    const rooms = detectRooms([...groupA, ...groupB]);

    expect(rooms).toHaveLength(2);
    const areas = rooms.map((r) => r.areaM2).sort((a, b) => a - b);
    expect(areas).toEqual([4, 9]);
  });

  it("splits a wall at a T-intersection from a perpendicular divider", () => {
    // Same as the "split by divider" case, but the divider's endpoint lands
    // exactly on the midpoint of the top and bottom walls (T-intersections),
    // rather than on pre-split sub-segments.
    const walls: Wall[] = [
      wall("bottom", { x: 0, y: 0 }, { x: 4, y: 0 }),
      wall("right", { x: 4, y: 0 }, { x: 4, y: 2 }),
      wall("top", { x: 4, y: 2 }, { x: 0, y: 2 }),
      wall("left", { x: 0, y: 2 }, { x: 0, y: 0 }),
      wall("divider", { x: 2, y: 0 }, { x: 2, y: 2 }, "divider"),
    ];

    const rooms = detectRooms(walls);

    expect(rooms).toHaveLength(2);
    const areas = rooms.map((r) => r.areaM2).sort();
    expect(areas).toEqual([4, 4]);
  });

  it("splits a wall at a proper crossing (X intersection)", () => {
    // Two dividers crossing in the middle of a 4x4 room, splitting it into 4 quadrants
    const walls: Wall[] = [
      wall("w1", { x: 0, y: 0 }, { x: 4, y: 0 }),
      wall("w2", { x: 4, y: 0 }, { x: 4, y: 4 }),
      wall("w3", { x: 4, y: 4 }, { x: 0, y: 4 }),
      wall("w4", { x: 0, y: 4 }, { x: 0, y: 0 }),
      wall("d1", { x: 2, y: 0 }, { x: 2, y: 4 }, "divider"),
      wall("d2", { x: 0, y: 2 }, { x: 4, y: 2 }, "divider"),
    ];

    const rooms = detectRooms(walls);

    expect(rooms).toHaveLength(4);
    const areas = rooms.map((r) => r.areaM2).sort();
    expect(areas).toEqual([4, 4, 4, 4]);
  });
});

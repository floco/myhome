import { describe, it, expect } from "vitest";
import { computeSnap, placePoint, allEndpoints } from "../src/lib/drawingTool";
import type { Wall } from "@myhome/geometry";

describe("computeSnap", () => {
  it("snaps to the grid when nothing nearby", () => {
    const result = computeSnap({ x: 1.04, y: 2.03 }, [], [], 0.12);
    expect(result.point).toEqual({ x: 1, y: 2 });
    expect(result.snappedToExisting).toBe(false);
    expect(result.closesLoop).toBe(false);
  });

  it("snaps to an existing endpoint within radius", () => {
    const result = computeSnap({ x: 1.02, y: 2.01 }, [{ x: 1, y: 2 }], [], 0.12);
    expect(result.point).toEqual({ x: 1, y: 2 });
    expect(result.snappedToExisting).toBe(true);
  });

  it("detects closing the loop back to the chain's start point", () => {
    const chain = [
      { x: 0, y: 0 },
      { x: 2, y: 0 },
      { x: 2, y: 2 },
    ];
    const result = computeSnap({ x: 0.01, y: 0.01 }, [], chain, 0.12);
    expect(result.point).toEqual({ x: 0, y: 0 });
    expect(result.closesLoop).toBe(true);
  });
});

describe("placePoint", () => {
  const ids = (function* () {
    let i = 0;
    while (true) yield `wall-${++i}`;
  })();
  const nextId = () => ids.next().value as string;

  it("returns no segment for the first point in a chain", () => {
    const result = placePoint([], { x: 0, y: 0 }, "wall", nextId);
    expect(result.segment).toBeNull();
    expect(result.chainEnds).toBe(false);
  });

  it("creates a wall segment to the new point with default thickness", () => {
    const result = placePoint([{ x: 0, y: 0 }], { x: 2, y: 0 }, "wall", nextId);
    expect(result.segment).toEqual({
      id: "wall-1",
      type: "wall",
      start: { x: 0, y: 0 },
      end: { x: 2, y: 0 },
      thickness: 0.1,
    });
    expect(result.chainEnds).toBe(false);
  });

  it("creates a divider segment without thickness", () => {
    const result = placePoint([{ x: 0, y: 0 }], { x: 2, y: 0 }, "divider", nextId);
    expect(result.segment).toEqual({
      id: "wall-2",
      type: "divider",
      start: { x: 0, y: 0 },
      end: { x: 2, y: 0 },
    });
  });

  it("ignores a zero-length click on the same point", () => {
    const result = placePoint([{ x: 0, y: 0 }], { x: 0, y: 0 }, "wall", nextId);
    expect(result.segment).toBeNull();
    expect(result.chainEnds).toBe(false);
  });

  it("reports chainEnds when the new point closes the loop back to the start", () => {
    const chain = [
      { x: 0, y: 0 },
      { x: 2, y: 0 },
      { x: 2, y: 2 },
    ];
    const result = placePoint(chain, { x: 0, y: 0 }, "wall", nextId);
    expect(result.segment?.end).toEqual({ x: 0, y: 0 });
    expect(result.chainEnds).toBe(true);
  });
});

describe("allEndpoints", () => {
  it("flattens start/end points of all walls", () => {
    const walls: Wall[] = [
      { id: "a", type: "wall", start: { x: 0, y: 0 }, end: { x: 1, y: 0 }, thickness: 0.1 },
      { id: "b", type: "divider", start: { x: 1, y: 0 }, end: { x: 1, y: 1 } },
    ];
    expect(allEndpoints(walls)).toEqual([
      { x: 0, y: 0 },
      { x: 1, y: 0 },
      { x: 1, y: 0 },
      { x: 1, y: 1 },
    ]);
  });
});

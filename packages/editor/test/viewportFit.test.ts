import { describe, it, expect } from "vitest";
import { fitViewportToFloor } from "../src/lib/viewportFit";
import { worldToScreen } from "../src/lib/viewportStore.svelte";
import type { Floor } from "@myhome/geometry";

function makeFloor(walls: Floor["walls"]): Floor {
  return { id: "f1", name: "Floor", order: 0, walls, openings: [], rooms: [] };
}

describe("fitViewportToFloor", () => {
  it("centers a single wall's midpoint in the viewport", () => {
    const floor = makeFloor([
      { id: "w1", start: { x: 0, y: 0 }, end: { x: 4, y: 0 }, type: "wall" },
    ]);
    const viewport = fitViewportToFloor(floor, 400, 300);

    const mid = worldToScreen({ x: 2, y: 0 }, viewport);
    expect(mid.x).toBeCloseTo(200, 0);
    expect(mid.y).toBeCloseTo(150, 0);
  });

  it("fits the bounding box within the available width/height", () => {
    const floor = makeFloor([
      { id: "w1", start: { x: 0, y: 0 }, end: { x: 10, y: 0 }, type: "wall" },
      { id: "w2", start: { x: 10, y: 0 }, end: { x: 10, y: 4 }, type: "wall" },
    ]);
    const viewport = fitViewportToFloor(floor, 400, 300, 20);

    const corners = [
      worldToScreen({ x: 0, y: 0 }, viewport),
      worldToScreen({ x: 10, y: 4 }, viewport),
    ];
    for (const p of corners) {
      expect(p.x).toBeGreaterThanOrEqual(20 - 1);
      expect(p.x).toBeLessThanOrEqual(400 - 20 + 1);
      expect(p.y).toBeGreaterThanOrEqual(20 - 1);
      expect(p.y).toBeLessThanOrEqual(300 - 20 + 1);
    }
  });

  it("returns a centered default viewport for a floor with no walls", () => {
    const floor = makeFloor([]);
    const viewport = fitViewportToFloor(floor, 400, 300);
    expect(viewport.panX).toBe(200);
    expect(viewport.panY).toBe(150);
  });
});

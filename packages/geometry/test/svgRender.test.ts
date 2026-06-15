import { describe, it, expect } from "vitest";
import { renderFloorSvg } from "../src/svgRender";
import type { Floor, Wall, Opening } from "../src/types";

function baseFloor(overrides: Partial<Floor> = {}): Floor {
  return {
    id: "floor-1",
    name: "Ground Floor",
    order: 0,
    walls: [],
    openings: [],
    rooms: [],
    ...overrides,
  };
}

describe("renderFloorSvg - walls and dividers", () => {
  it("renders a wall with no openings as a single rectangle path", () => {
    const wall: Wall = {
      id: "w1",
      start: { x: 0, y: 0 },
      end: { x: 4, y: 0 },
      thickness: 0.2,
      type: "wall",
    };
    const svg = renderFloorSvg(baseFloor({ walls: [wall] }));

    // One wall path, a rectangle (M + 3*L + Z = 4 points)
    const wallPaths = [...svg.matchAll(/<path class="wall" d="([^"]+)"/g)];
    expect(wallPaths).toHaveLength(1);
    const d = wallPaths[0][1];
    expect(d.startsWith("M 0 0.1")).toBe(true);
    expect(d).toContain("L 4 0.1");
    expect(d).toContain("L 4 -0.1");
    expect(d).toContain("L 0 -0.1");
    expect(d.endsWith("Z")).toBe(true);
  });

  it("splits a wall into two path segments around a window opening", () => {
    const wall: Wall = {
      id: "w1",
      start: { x: 0, y: 0 },
      end: { x: 4, y: 0 },
      thickness: 0.2,
      type: "wall",
    };
    const opening: Opening = {
      id: "op1",
      wallId: "w1",
      type: "window",
      offset: 1,
      width: 1,
    };
    const svg = renderFloorSvg(baseFloor({ walls: [wall], openings: [opening] }));

    const wallPaths = [...svg.matchAll(/<path class="wall" d="([^"]+)"/g)];
    expect(wallPaths).toHaveLength(2);

    const windowLines = [...svg.matchAll(/<line class="window"[^>]*\/>/g)];
    expect(windowLines).toHaveLength(1);
    expect(windowLines[0][0]).toContain('x1="1"');
    expect(windowLines[0][0]).toContain('x2="2"');
  });

  it("clamps an opening that would overflow the wall length", () => {
    const wall: Wall = {
      id: "w1",
      start: { x: 0, y: 0 },
      end: { x: 4, y: 0 },
      thickness: 0.2,
      type: "wall",
    };
    const opening: Opening = {
      id: "op1",
      wallId: "w1",
      type: "window",
      offset: 3.5,
      width: 1, // would extend to 4.5, beyond the wall's length of 4
    };
    const svg = renderFloorSvg(baseFloor({ walls: [wall], openings: [opening] }));

    const windowLines = [...svg.matchAll(/<line class="window"[^>]*\/>/g)];
    expect(windowLines[0][0]).toContain('x1="3.5"');
    expect(windowLines[0][0]).toContain('x2="4"');

    // Only one wall segment remains (before the opening); nothing after it
    const wallPaths = [...svg.matchAll(/<path class="wall" d="([^"]+)"/g)];
    expect(wallPaths).toHaveLength(1);
  });

  it("renders a divider as a dashed centerline with no thickness", () => {
    const divider: Wall = {
      id: "d1",
      start: { x: 0, y: 0 },
      end: { x: 4, y: 0 },
      type: "divider",
    };
    const svg = renderFloorSvg(baseFloor({ walls: [divider] }));

    expect(svg).toContain('<path class="divider"');
    expect(svg).toContain("stroke-dasharray");
    expect(svg).toContain("M 0 0 L 4 0");
    // dividers must not produce wall rectangles
    expect(svg).not.toContain('<path class="wall"');
  });
});

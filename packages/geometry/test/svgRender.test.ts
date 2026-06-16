import { describe, it, expect } from "vitest";
import { renderFloorSvg, chooseSweepFlag } from "../src/svgRender";
import type { Floor, Wall, Opening, Room, DoorSwing, Point } from "../src/types";

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

  it("clips opening symbol to the same interval as the wall gap when offset is negative", () => {
    // offset=-0.5, width=1 on a 4m wall: the gap covers [0, 0.5] (clamped).
    // Before the fix, the symbol was drawn from 0 to 1 (full width), extending into solid wall.
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
      offset: -0.5,
      width: 1,
    };
    const svg = renderFloorSvg(baseFloor({ walls: [wall], openings: [opening] }));

    // Symbol should span [0, 0.5], matching the wall gap — not [0, 1]
    const windowLines = [...svg.matchAll(/<line class="window"[^>]*\/>/g)];
    expect(windowLines).toHaveLength(1);
    expect(windowLines[0][0]).toContain('x1="0"');
    expect(windowLines[0][0]).toContain('x2="0.5"');
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

describe("renderFloorSvg - rooms", () => {
  it("renders a room polygon with its id and HA area data attribute", () => {
    const room: Room = {
      id: "room-1",
      label: "Living Room",
      haAreaId: "living_room",
      polygon: [
        { x: 0, y: 0 },
        { x: 4, y: 0 },
        { x: 4, y: 3 },
        { x: 0, y: 3 },
      ],
      areaM2: 12,
    };
    const svg = renderFloorSvg(baseFloor({ rooms: [room] }));

    expect(svg).toContain('<path id="room-room-1" data-ha-area="living_room" class="room"');
  });

  it("renders an empty data-ha-area attribute for rooms with no assigned area", () => {
    const room: Room = {
      id: "room-2",
      label: "Unassigned",
      haAreaId: null,
      polygon: [
        { x: 0, y: 0 },
        { x: 2, y: 0 },
        { x: 2, y: 2 },
        { x: 0, y: 2 },
      ],
      areaM2: 4,
    };
    const svg = renderFloorSvg(baseFloor({ rooms: [room] }));

    expect(svg).toContain('<path id="room-room-2" data-ha-area="" class="room"');
  });

  it("skips rooms with a null polygon (unresolved rooms)", () => {
    const room: Room = {
      id: "room-3",
      label: "Gone",
      haAreaId: null,
      polygon: null,
      areaM2: 0,
    };
    const svg = renderFloorSvg(baseFloor({ rooms: [room] }));

    expect(svg).not.toContain("room-room-3");
  });
});

describe("door swing rendering", () => {
  const wall: Wall = {
    id: "w1",
    start: { x: 0, y: 0 },
    end: { x: 4, y: 0 },
    thickness: 0.2,
    type: "wall",
  };

  function doorSvg(swing: DoorSwing): string {
    const opening: Opening = {
      id: "op1",
      wallId: "w1",
      type: "door",
      offset: 1,
      width: 0.9,
      swing,
    };
    return renderFloorSvg(baseFloor({ walls: [wall], openings: [opening] }));
  }

  const swings: DoorSwing[] = ["left-in", "right-in", "left-out", "right-out"];

  it.each(swings)("renders a leaf line and an arc for swing=%s", (swing) => {
    const svg = doorSvg(swing);
    expect(svg).toContain('<line class="door-leaf"');
    expect(svg).toContain('<path class="door-swing" d="M');
  });

  it.each(swings)("the door-leaf for swing=%s has length equal to the opening width", (swing) => {
    const svg = doorSvg(swing);
    const match = svg.match(/<line class="door-leaf" x1="([^"]+)" y1="([^"]+)" x2="([^"]+)" y2="([^"]+)"/);
    expect(match).not.toBeNull();
    const [, x1, y1, x2, y2] = match!.map(Number);
    const length = Math.hypot(x2 - x1, y2 - y1);
    expect(length).toBeCloseTo(0.9, 5);
  });

  it.each(swings)("the door-leaf for swing=%s starts at the correct hinge corner", (swing) => {
    const svg = doorSvg(swing);
    const match = svg.match(/<line class="door-leaf" x1="([^"]+)" y1="([^"]+)"/);
    const [, x1, y1] = match!;
    const hingeX = swing.startsWith("left") ? 1 : 1.9;
    expect(Number(x1)).toBeCloseTo(hingeX, 5);
    expect(Number(y1)).toBeCloseTo(0, 5);
  });

  it.each(swings)("the door-swing arc for swing=%s is centered on the hinge point", (swing) => {
    const svg = doorSvg(swing);
    const arcMatch = svg.match(
      /<path class="door-swing" d="M ([\d.-]+) ([\d.-]+) A ([\d.-]+) ([\d.-]+) 0 0 (\d) ([\d.-]+) ([\d.-]+)"/
    );
    expect(arcMatch).not.toBeNull();
    const [, mx, my, rx, , sweep, ex, ey] = arcMatch!;

    const start: Point = { x: Number(mx), y: Number(my) };
    const end: Point = { x: Number(ex), y: Number(ey) };
    const radius = Number(rx);

    const hingeX = swing.startsWith("left") ? 1 : 1.9;
    const hinge: Point = { x: hingeX, y: 0 };

    // Recompute both candidate centers for this (start, end, radius) and
    // confirm the chosen sweep-flag corresponds to the one nearest `hinge`.
    const chosen = chooseSweepFlag(start, end, radius, hinge);
    expect(Number(sweep)).toBe(chosen);

    // And confirm `hinge` really is one of the two candidate centers
    // (i.e. our test's expected hinge matches the geometry under test).
    const x1p = (start.x - end.x) / 2;
    const y1p = (start.y - end.y) / 2;
    const midX = (start.x + end.x) / 2;
    const midY = (start.y + end.y) / 2;
    const sumSq = x1p * x1p + y1p * y1p;
    const factor = Math.sqrt(Math.max((radius * radius - sumSq) / sumSq, 0));
    const center0 = { x: midX - factor * y1p, y: midY + factor * x1p };
    const center1 = { x: midX + factor * y1p, y: midY - factor * x1p };
    const d0 = Math.hypot(center0.x - hinge.x, center0.y - hinge.y);
    const d1 = Math.hypot(center1.x - hinge.x, center1.y - hinge.y);
    expect(Math.min(d0, d1)).toBeCloseTo(0, 5);
  });

  it("produces a different arc end point for each swing direction", () => {
    const ends = swings.map((swing) => {
      const svg = doorSvg(swing);
      const arcMatch = svg.match(/A [\d.-]+ [\d.-]+ 0 0 \d ([\d.-]+) ([\d.-]+)"/);
      return `${arcMatch![1]},${arcMatch![2]}`;
    });
    expect(new Set(ends).size).toBe(4);
  });
});

import { describe, it, expect } from "vitest";
import { matchRooms } from "../src/roomMatching";
import type { DetectedRoom } from "../src/roomDetection";
import type { Room, Point } from "../src/types";

function rect(x0: number, y0: number, x1: number, y1: number): Point[] {
  return [
    { x: x0, y: y0 },
    { x: x1, y: y0 },
    { x: x1, y: y1 },
    { x: x0, y: y1 },
  ];
}

describe("matchRooms", () => {
  it("preserves label/haAreaId/id when a room's polygon changes slightly", () => {
    const existing: Room[] = [
      {
        id: "room-living",
        label: "Living Room",
        haAreaId: "living_room",
        polygon: rect(0, 0, 5, 4),
        areaM2: 20,
      },
    ];

    // Slightly enlarged (e.g. user nudged a wall outward)
    const detected: DetectedRoom[] = [{ polygon: rect(0, 0, 5.2, 4), areaM2: 20.8 }];

    const result = matchRooms(detected, existing);

    expect(result.rooms).toHaveLength(1);
    expect(result.rooms[0].id).toBe("room-living");
    expect(result.rooms[0].label).toBe("Living Room");
    expect(result.rooms[0].haAreaId).toBe("living_room");
    expect(result.rooms[0].areaM2).toBeCloseTo(20.8, 5);
    expect(result.unresolved).toHaveLength(0);
  });

  it("creates a new default-labeled room when a polygon has no match", () => {
    const existing: Room[] = [];
    const detected: DetectedRoom[] = [{ polygon: rect(0, 0, 3, 3), areaM2: 9 }];

    const result = matchRooms(detected, existing);

    expect(result.rooms).toHaveLength(1);
    expect(result.rooms[0].label).toBe("Room 1");
    expect(result.rooms[0].haAreaId).toBeNull();
    expect(result.rooms[0].id).toBeTruthy();
    expect(result.unresolved).toHaveLength(0);
  });

  it("when a room is split in two, one half keeps identity and the other becomes a new room", () => {
    const existing: Room[] = [
      {
        id: "room-open-plan",
        label: "Kitchen/Living",
        haAreaId: "downstairs",
        polygon: rect(0, 0, 4, 2),
        areaM2: 8,
      },
    ];

    // A divider at x=2 splits the room into two 2x2 halves
    const detected: DetectedRoom[] = [
      { polygon: rect(0, 0, 2, 2), areaM2: 4 },
      { polygon: rect(2, 0, 4, 2), areaM2: 4 },
    ];

    const result = matchRooms(detected, existing);

    expect(result.rooms).toHaveLength(2);
    const matched = result.rooms.find((r) => r.id === "room-open-plan");
    const created = result.rooms.find((r) => r.id !== "room-open-plan");

    expect(matched).toBeDefined();
    expect(matched!.label).toBe("Kitchen/Living");
    expect(matched!.haAreaId).toBe("downstairs");

    expect(created).toBeDefined();
    expect(created!.label).toBe("Room 1");
    expect(created!.haAreaId).toBeNull();

    expect(result.unresolved).toHaveLength(0);
  });

  it("marks a room as unresolved (polygon: null) when it disappears", () => {
    const existing: Room[] = [
      {
        id: "room-old",
        label: "Old Room",
        haAreaId: "office",
        polygon: rect(0, 0, 3, 3),
        areaM2: 9,
      },
    ];

    // No detected rooms at all (e.g. user deleted the walls)
    const detected: DetectedRoom[] = [];

    const result = matchRooms(detected, existing);

    expect(result.rooms).toHaveLength(1);
    expect(result.rooms[0].id).toBe("room-old");
    expect(result.rooms[0].polygon).toBeNull();
    expect(result.rooms[0].label).toBe("Old Room");
    expect(result.rooms[0].haAreaId).toBe("office");

    expect(result.unresolved).toHaveLength(1);
    expect(result.unresolved[0].id).toBe("room-old");
  });

  it("picks the smallest containing polygon when centroids are nested (courtyard case)", () => {
    // Outer room: 10x10, inner courtyard: 2x2 at centre — inner centroid is inside BOTH polygons.
    // matchRooms should pick the smaller (inner) existing room for the inner detected polygon,
    // not whichever appears first in the existing array.
    const outer: Room = {
      id: "room-outer",
      label: "Outer",
      haAreaId: null,
      polygon: rect(0, 0, 10, 10),
      areaM2: 100,
    };
    const inner: Room = {
      id: "room-inner",
      label: "Courtyard",
      haAreaId: null,
      polygon: rect(4, 4, 6, 6),
      areaM2: 4,
    };

    // Detected: inner polygon shifts slightly, outer polygon shifts slightly.
    // Inner centroid (4.55, 4.55) is inside BOTH existing polygons — tie-break by smallest area.
    const detectedInner: DetectedRoom = { polygon: rect(4.1, 4.1, 6.1, 6.1), areaM2: 4 };
    const detectedOuter: DetectedRoom = { polygon: rect(0.1, 0, 10.1, 10), areaM2: 100 };

    // existing[0] is outer — without the fix, find() would return outer for the inner detected polygon
    const result = matchRooms([detectedInner, detectedOuter], [outer, inner]);

    const matchedInner = result.rooms.find((r) => r.id === "room-inner");
    const matchedOuter = result.rooms.find((r) => r.id === "room-outer");
    expect(matchedInner).toBeDefined();
    expect(matchedInner!.polygon).toEqual(detectedInner.polygon);
    expect(matchedOuter).toBeDefined();
    expect(matchedOuter!.polygon).toEqual(detectedOuter.polygon);
    expect(result.unresolved).toHaveLength(0);
  });

  it("matches multiple rooms independently by centroid containment", () => {
    const existing: Room[] = [
      { id: "room-a", label: "A", haAreaId: "a", polygon: rect(0, 0, 2, 2), areaM2: 4 },
      { id: "room-b", label: "B", haAreaId: "b", polygon: rect(10, 10, 12, 12), areaM2: 4 },
    ];

    // Both rooms shift slightly, order reversed in the detected list
    const detected: DetectedRoom[] = [
      { polygon: rect(10.1, 10, 12.1, 12), areaM2: 4 },
      { polygon: rect(0.1, 0, 2.1, 2), areaM2: 4 },
    ];

    const result = matchRooms(detected, existing);

    expect(result.rooms).toHaveLength(2);
    const a = result.rooms.find((r) => r.id === "room-a");
    const b = result.rooms.find((r) => r.id === "room-b");
    expect(a!.label).toBe("A");
    expect(b!.label).toBe("B");
    expect(result.unresolved).toHaveLength(0);
  });
});

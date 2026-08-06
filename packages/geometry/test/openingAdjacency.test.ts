import { describe, it, expect } from "vitest";
import { findAdjacentRooms } from "../src/openingAdjacency";
import type { Opening, Room, Wall } from "../src/types";

describe("findAdjacentRooms", () => {
  const exteriorWall: Wall = { id: "w1", type: "wall", start: { x: 0, y: 0 }, end: { x: 4, y: 0 }, thickness: 0.1 };
  const interiorWall: Wall = { id: "w2", type: "wall", start: { x: 2, y: 0 }, end: { x: 2, y: 4 }, thickness: 0.1 };
  const windowOpening: Opening = { id: "o1", wallId: "w1", type: "window", offset: 1, width: 1 };
  const doorOpening: Opening = { id: "o2", wallId: "w2", type: "door", offset: 1, width: 0.9 };

  const roomBelow: Room = {
    id: "r1", label: "Living Room", haAreaId: "living_room", areaM2: 12,
    polygon: [{ x: 0, y: 0 }, { x: 4, y: 0 }, { x: 4, y: 3 }, { x: 0, y: 3 }],
  };
  const roomLeft: Room = {
    id: "r2", label: "Kitchen", haAreaId: "kitchen", areaM2: 8,
    polygon: [{ x: 0, y: 0 }, { x: 2, y: 0 }, { x: 2, y: 4 }, { x: 0, y: 4 }],
  };
  const roomRight: Room = {
    id: "r3", label: "Hallway", haAreaId: "hallway", areaM2: 8,
    polygon: [{ x: 2, y: 0 }, { x: 4, y: 0 }, { x: 4, y: 4 }, { x: 2, y: 4 }],
  };

  it("finds exactly one room for a window on an exterior wall", () => {
    const found = findAdjacentRooms(windowOpening, exteriorWall, [roomBelow]);
    expect(found.map((r) => r.id)).toEqual(["r1"]);
  });

  it("finds both rooms for a door on an interior wall shared by two rooms", () => {
    const found = findAdjacentRooms(doorOpening, interiorWall, [roomLeft, roomRight]);
    expect(found.map((r) => r.id).sort()).toEqual(["r2", "r3"]);
  });

  it("finds no rooms when neither side is enclosed", () => {
    const found = findAdjacentRooms(windowOpening, exteriorWall, []);
    expect(found).toEqual([]);
  });

  it("skips rooms with a null (unresolved) polygon", () => {
    const unresolved: Room = { ...roomBelow, polygon: null };
    const found = findAdjacentRooms(windowOpening, exteriorWall, [unresolved]);
    expect(found).toEqual([]);
  });
});

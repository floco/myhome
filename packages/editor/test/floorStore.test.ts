import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { createFloorStore, STORAGE_KEY } from "../src/lib/floorStore.svelte";
import type { Opening } from "@myhome/geometry";

describe("floorStore", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("seeds the sample floor with two detected rooms when localStorage is empty", () => {
    const store = createFloorStore();
    expect(store.floor.walls).toHaveLength(5);
    expect(store.floor.rooms).toHaveLength(2);
    for (const room of store.floor.rooms) {
      expect(room.areaM2).toBe(6);
    }
  });

  it("persists the floor to localStorage 300ms after a change", () => {
    vi.useFakeTimers();
    const store = createFloorStore();
    store.removeWall("divider-1");

    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    vi.advanceTimersByTime(300);

    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
    expect(saved.walls).toHaveLength(4);
  });

  it("recomputes rooms when a divider is removed", () => {
    const store = createFloorStore();
    store.removeWall("divider-1");
    expect(store.floor.rooms).toHaveLength(1);
    expect(store.floor.rooms[0].areaM2).toBe(12);
  });

  it("drops rooms whose polygon disappears (unresolved) after an edit", () => {
    const store = createFloorStore();
    expect(store.floor.rooms).toHaveLength(2);

    store.removeWall("wall-2");

    expect(store.floor.rooms).toHaveLength(1);
    expect(store.floor.rooms[0].areaM2).toBe(6);
  });

  it("moveSharedPoint updates every wall endpoint at the shared corner", () => {
    const store = createFloorStore();
    store.floor.walls = [];
    store.addWall({ id: "a", type: "wall", start: { x: 0, y: 0 }, end: { x: 1, y: 1 }, thickness: 0.1 });
    store.addWall({ id: "b", type: "wall", start: { x: 1, y: 1 }, end: { x: 2, y: 0 }, thickness: 0.1 });

    store.moveSharedPoint({ x: 1, y: 1 }, { x: 1, y: 2 });

    expect(store.floor.walls[0].end).toEqual({ x: 1, y: 2 });
    expect(store.floor.walls[1].start).toEqual({ x: 1, y: 2 });
  });
});

describe("floorStore — openings", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  function makeOpening(wallId: string): Opening {
    return { id: "op-1", wallId, type: "window", offset: 1, width: 1.2 };
  }

  it("addOpening adds to floor.openings", () => {
    const store = createFloorStore();
    const wallId = store.floor.walls[0]?.id ?? "w1";
    store.addOpening(makeOpening(wallId));
    expect(store.floor.openings.some((o) => o.id === "op-1")).toBe(true);
  });

  it("removeOpening removes by id", () => {
    const store = createFloorStore();
    const wallId = store.floor.walls[0]?.id ?? "w1";
    store.addOpening(makeOpening(wallId));
    store.removeOpening("op-1");
    expect(store.floor.openings.some((o) => o.id === "op-1")).toBe(false);
  });

  it("removeWall also removes orphaned openings on that wall", () => {
    const store = createFloorStore();
    const wallId = store.floor.walls.find((w) => w.type === "wall")?.id;
    expect(wallId).toBeDefined();
    if (!wallId) return;
    store.addOpening(makeOpening(wallId));
    store.removeWall(wallId);
    expect(store.floor.openings.some((o) => o.wallId === wallId)).toBe(false);
  });
});

describe("floorStore — room update", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("updateRoom sets label", () => {
    const store = createFloorStore();
    const room = store.floor.rooms[0];
    expect(room).toBeDefined();
    if (!room) return;
    store.updateRoom(room.id, { label: "Kitchen" });
    expect(store.floor.rooms.find((r) => r.id === room.id)?.label).toBe("Kitchen");
  });

  it("updateRoom sets haAreaId", () => {
    const store = createFloorStore();
    const room = store.floor.rooms[0];
    expect(room).toBeDefined();
    if (!room) return;
    store.updateRoom(room.id, { haAreaId: "kitchen_area" });
    expect(store.floor.rooms.find((r) => r.id === room.id)?.haAreaId).toBe("kitchen_area");
  });

  it("updateRoom ignores unknown id", () => {
    const store = createFloorStore();
    const before = store.floor.rooms.map((r) => r.label);
    store.updateRoom("no-such-id", { label: "X" });
    expect(store.floor.rooms.map((r) => r.label)).toEqual(before);
  });
});

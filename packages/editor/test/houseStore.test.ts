import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { createHouseStore, HOUSE_STORAGE_KEY } from "../src/lib/houseStore.svelte";

describe("houseStore — initial state", () => {
  beforeEach(() => { localStorage.clear(); });

  it("starts with one floor and detects two rooms from the sample floor", () => {
    const store = createHouseStore();
    expect(store.floors.length).toBe(1);
    expect(store.floor.rooms.length).toBe(2);
  });

  it("currentFloorId matches the single floor's id", () => {
    const store = createHouseStore();
    expect(store.currentFloorId).toBe(store.floors[0].id);
  });
});

describe("houseStore — floor management", () => {
  beforeEach(() => { localStorage.clear(); });

  it("addFloor adds a new empty floor and switches to it", () => {
    const store = createHouseStore();
    const before = store.floors.length;
    store.addFloor("First Floor");
    expect(store.floors.length).toBe(before + 1);
    const newFloor = store.floors[store.floors.length - 1];
    expect(newFloor.name).toBe("First Floor");
    expect(store.currentFloorId).toBe(newFloor.id);
    expect(store.floor.walls.length).toBe(0);
  });

  it("switchFloor changes the active floor", () => {
    const store = createHouseStore();
    store.addFloor("Upstairs");
    const upstairs = store.floors[store.floors.length - 1].id;
    const groundId = store.floors[0].id;
    store.switchFloor(groundId);
    expect(store.currentFloorId).toBe(groundId);
    store.switchFloor(upstairs);
    expect(store.currentFloorId).toBe(upstairs);
  });

  it("renameFloor changes the floor name", () => {
    const store = createHouseStore();
    const id = store.floors[0].id;
    store.renameFloor(id, "Basement");
    expect(store.floors.find((f) => f.id === id)?.name).toBe("Basement");
  });

  it("removeFloor removes the floor and switches to the first remaining floor", () => {
    const store = createHouseStore();
    store.addFloor("Upstairs");
    const upstairs = store.floors[store.floors.length - 1].id;
    const groundId = store.floors[0].id;
    store.switchFloor(upstairs);
    store.removeFloor(upstairs);
    expect(store.floors.some((f) => f.id === upstairs)).toBe(false);
    expect(store.currentFloorId).toBe(groundId);
  });

  it("removeFloor is a no-op when only one floor remains", () => {
    const store = createHouseStore();
    const id = store.floors[0].id;
    store.removeFloor(id);
    expect(store.floors.length).toBe(1);
    expect(store.currentFloorId).toBe(id);
  });

  it("addFloor assigns incrementing order values", () => {
    const store = createHouseStore();
    store.addFloor("F2");
    store.addFloor("F3");
    const orders = store.floors.map((f) => f.order);
    expect(orders[0]).toBe(0);
    expect(orders[1]).toBe(1);
    expect(orders[2]).toBe(2);
  });
});

describe("houseStore — floor mutations (forwarded to current floor)", () => {
  beforeEach(() => { localStorage.clear(); });

  it("addWall on the current floor does not affect other floors", () => {
    const store = createHouseStore();
    const groundWallsBefore = store.floors[0].walls.length;
    store.addFloor("F2");
    store.addWall({ id: "w-x", start: { x: 10, y: 0 }, end: { x: 20, y: 0 }, type: "wall", thickness: 0.1 });
    store.switchFloor(store.floors[0].id);
    expect(store.floor.walls.length).toBe(groundWallsBefore);
    const f2 = store.floors.find((f) => f.name === "F2")!;
    expect(f2.walls.some((w) => w.id === "w-x")).toBe(true);
  });
});

describe("houseStore — undo/redo across floors", () => {
  beforeEach(() => { localStorage.clear(); });

  it("undo reverts addFloor", () => {
    const store = createHouseStore();
    const before = store.floors.length;
    store.addFloor("F2");
    expect(store.floors.length).toBe(before + 1);
    store.undo();
    expect(store.floors.length).toBe(before);
  });

  it("redo re-applies addFloor", () => {
    const store = createHouseStore();
    const before = store.floors.length;
    store.addFloor("F2");
    store.undo();
    store.redo();
    expect(store.floors.length).toBe(before + 1);
  });

  it("hasUndo is false initially and true after addFloor", () => {
    const store = createHouseStore();
    expect(store.hasUndo).toBe(false);
    store.addFloor("F2");
    expect(store.hasUndo).toBe(true);
  });
});

describe("houseStore — persistence", () => {
  beforeEach(() => { localStorage.clear(); });
  afterEach(() => { vi.useRealTimers(); });

  it("persists to the house storage key after 300ms", () => {
    vi.useFakeTimers();
    const store = createHouseStore();
    store.addFloor("Attic");
    vi.advanceTimersByTime(300);
    const saved = JSON.parse(localStorage.getItem(HOUSE_STORAGE_KEY)!);
    expect(Array.isArray(saved.floors)).toBe(true);
    expect(saved.floors.some((f: { name: string }) => f.name === "Attic")).toBe(true);
  });

  it("migrates old myhome.editor.floor data on first load", () => {
    const OLD_KEY = "myhome.editor.floor";
    const oldFloor = {
      id: "old-floor",
      name: "Old Floor",
      order: 0,
      walls: [{ id: "w1", type: "wall", start: { x: 0, y: 0 }, end: { x: 5, y: 0 }, thickness: 0.1 }],
      openings: [],
      rooms: [],
    };
    localStorage.setItem(OLD_KEY, JSON.stringify(oldFloor));
    const store = createHouseStore();
    expect(store.floors.length).toBe(1);
    expect(store.floor.walls.some((w) => w.id === "w1")).toBe(true);
  });
});

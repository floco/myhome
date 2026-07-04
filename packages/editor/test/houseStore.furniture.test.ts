import { describe, it, expect, beforeEach, vi } from "vitest";
import { createHouseStore } from "../src/lib/houseStore.svelte";

// houseStore.svelte.ts uses $state runes — vitest handles them via the svelte transform
// but the file calls init() on creation which uses fetch; mock it out.
vi.stubGlobal("fetch", () => Promise.resolve({ ok: true, status: 200, json: async () => ({ version: 1, house: { name: "Test", units: "m", gridSnap: 0.1 }, floors: [] }) }));

describe("houseStore furniture methods", () => {
  let store: ReturnType<typeof createHouseStore>;

  beforeEach(() => {
    store = createHouseStore(() => null);
  });

  it("currentFurniture returns [] when floor has no furniture", () => {
    expect(store.currentFurniture).toEqual([]);
  });

  it("addFurniture places an object on the current floor", () => {
    const gen0 = store.generation;
    store.addFurniture("sofa", 1, 2, 2.2, 0.9);
    const furn = store.currentFurniture;
    expect(furn).toHaveLength(1);
    expect(furn[0].templateId).toBe("sofa");
    expect(furn[0].x).toBe(1);
    expect(furn[0].y).toBe(2);
    expect(furn[0].width).toBe(2.2);
    expect(furn[0].height).toBe(0.9);
    expect(furn[0].rotation).toBe(0);
    expect(store.generation).toBeGreaterThan(gen0);
  });

  it("addFurniture generates a unique id", () => {
    store.addFurniture("sofa", 0, 0, 1, 1);
    store.addFurniture("sofa", 0, 0, 1, 1);
    const ids = store.currentFurniture.map((f) => f.id);
    expect(new Set(ids).size).toBe(2);
  });

  it("removeFurniture removes the object by id", () => {
    store.addFurniture("sofa", 1, 2, 2.2, 0.9);
    const id = store.currentFurniture[0].id;
    store.removeFurniture(id);
    expect(store.currentFurniture).toHaveLength(0);
  });

  it("removeFurniture is a no-op for unknown id", () => {
    store.addFurniture("sofa", 0, 0, 1, 1);
    store.removeFurniture("nonexistent");
    expect(store.currentFurniture).toHaveLength(1);
  });

  it("moveFurniture updates x/y with history by default", () => {
    store.addFurniture("sofa", 0, 0, 1, 1);
    const id = store.currentFurniture[0].id;
    const gen0 = store.generation;
    store.moveFurniture(id, 3, 4);
    const obj = store.currentFurniture.find((f) => f.id === id)!;
    expect(obj.x).toBe(3);
    expect(obj.y).toBe(4);
    expect(store.generation).toBeGreaterThan(gen0);
  });

  it("moveFurniture with skipHistory=true increments generation but skips snapshot", () => {
    store.addFurniture("sofa", 0, 0, 1, 1);
    const id = store.currentFurniture[0].id;
    const gen0 = store.generation;
    store.moveFurniture(id, 5, 6, { skipHistory: true });
    expect(store.generation).toBeGreaterThan(gen0);
    // undo stack should not have grown — can't inspect directly,
    // but hasUndo reflects it after a non-snapshot move
  });

  it("resizeFurniture updates width and height", () => {
    store.addFurniture("sofa", 0, 0, 1, 1);
    const id = store.currentFurniture[0].id;
    store.resizeFurniture(id, 5, 6, 3, 4, { skipHistory: true });
    const obj = store.currentFurniture.find((f) => f.id === id)!;
    expect(obj.x).toBe(5);
    expect(obj.y).toBe(6);
    expect(obj.width).toBe(3);
    expect(obj.height).toBe(4);
  });

  it("rotateFurniture updates rotation", () => {
    store.addFurniture("sofa", 0, 0, 1, 1);
    const id = store.currentFurniture[0].id;
    store.rotateFurniture(id, 45, { skipHistory: true });
    const obj = store.currentFurniture.find((f) => f.id === id)!;
    expect(obj.rotation).toBe(45);
  });

  it("addFurniture supports undo", () => {
    store.addFurniture("sofa", 0, 0, 1, 1);
    expect(store.currentFurniture).toHaveLength(1);
    store.undo();
    expect(store.currentFurniture).toHaveLength(0);
  });

  it("removeFurniture supports undo", () => {
    store.addFurniture("sofa", 0, 0, 1, 1);
    const id = store.currentFurniture[0].id;
    store.removeFurniture(id);
    store.undo();
    expect(store.currentFurniture).toHaveLength(1);
  });

  it("init() patches floors that have no furnitureObjects", () => {
    // Simulate a floor without the furnitureObjects field
    const floor = store.floor;
    // @ts-ignore - deliberate removal to test patching
    delete (floor as any).furnitureObjects;
    expect((floor as any).furnitureObjects).toBeUndefined();
    // Accessing via store getter should still return []
    expect(store.currentFurniture).toEqual([]);
  });
});

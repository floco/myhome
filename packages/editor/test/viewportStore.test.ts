import { describe, it, expect } from "vitest";
import { createViewportStore, DEFAULT_VIEWPORT } from "../src/lib/viewportStore.svelte";

describe("viewportStore", () => {
  it("starts at the default pan/zoom", () => {
    const store = createViewportStore();
    expect(store.viewport).toEqual(DEFAULT_VIEWPORT);
  });

  it("converts world to screen and back losslessly", () => {
    const store = createViewportStore();
    const world = { x: 2.5, y: -1.5 };
    const screen = store.worldToScreen(world);
    const roundTrip = store.screenToWorld(screen);
    expect(roundTrip.x).toBeCloseTo(world.x, 9);
    expect(roundTrip.y).toBeCloseTo(world.y, 9);
  });

  it("pan shifts panX/panY", () => {
    const store = createViewportStore();
    store.pan(10, -5);
    expect(store.viewport.panX).toBe(DEFAULT_VIEWPORT.panX + 10);
    expect(store.viewport.panY).toBe(DEFAULT_VIEWPORT.panY - 5);
  });

  it("zoomAt keeps the world point under the cursor fixed on screen", () => {
    const store = createViewportStore();
    const cursor = { x: 300, y: 200 };
    const worldBefore = store.screenToWorld(cursor);

    store.zoomAt(cursor, 2);

    const screenAfter = store.worldToScreen(worldBefore);
    expect(screenAfter.x).toBeCloseTo(cursor.x, 9);
    expect(screenAfter.y).toBeCloseTo(cursor.y, 9);
    expect(store.viewport.zoom).toBe(DEFAULT_VIEWPORT.zoom * 2);
  });

  it("reset restores the default viewport", () => {
    const store = createViewportStore();
    store.pan(100, 100);
    store.zoomAt({ x: 0, y: 0 }, 3);
    store.reset();
    expect(store.viewport).toEqual(DEFAULT_VIEWPORT);
  });
});

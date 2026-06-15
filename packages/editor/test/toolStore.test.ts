import { describe, it, expect } from "vitest";
import { createToolStore } from "../src/lib/toolStore.svelte";

describe("toolStore", () => {
  it("starts on the select tool with nothing selected or drawn", () => {
    const store = createToolStore();
    expect(store.state.tool).toBe("select");
    expect(store.state.selectedId).toBeNull();
    expect(store.state.drawPoints).toEqual([]);
  });

  it("setTool switches tools and clears selection/drawing state", () => {
    const store = createToolStore();
    store.select("wall-1");
    store.addDrawPoint({ x: 0, y: 0 });

    store.setTool("wall");

    expect(store.state.tool).toBe("wall");
    expect(store.state.selectedId).toBeNull();
    expect(store.state.drawPoints).toEqual([]);
  });

  it("addDrawPoint appends to the in-progress chain", () => {
    const store = createToolStore();
    store.addDrawPoint({ x: 0, y: 0 });
    store.addDrawPoint({ x: 1, y: 0 });
    expect(store.state.drawPoints).toEqual([
      { x: 0, y: 0 },
      { x: 1, y: 0 },
    ]);
  });

  it("resetDraw clears the in-progress chain without changing tool", () => {
    const store = createToolStore();
    store.setTool("wall");
    store.addDrawPoint({ x: 0, y: 0 });
    store.resetDraw();
    expect(store.state.drawPoints).toEqual([]);
    expect(store.state.tool).toBe("wall");
  });

  it("select sets and clears the selected id", () => {
    const store = createToolStore();
    store.select("wall-2");
    expect(store.state.selectedId).toBe("wall-2");
    store.select(null);
    expect(store.state.selectedId).toBeNull();
  });
});

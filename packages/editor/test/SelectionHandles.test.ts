import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SelectionHandles from "../src/lib/components/SelectionHandles.svelte";
import type { Wall } from "@myhome/geometry";
import { DEFAULT_VIEWPORT } from "../src/lib/viewportStore.svelte";

function makeWall(overrides: Partial<Wall> = {}): Wall {
  return { id: "w1", start: { x: 0, y: 0 }, end: { x: 3, y: 0 }, type: "wall", thickness: 0.1, ...overrides };
}

function setup(overrides: Record<string, unknown> = {}) {
  const target = document.createElement("svg");
  document.body.appendChild(target);
  const props = { wall: makeWall(), viewport: DEFAULT_VIEWPORT, ondragstart: vi.fn(), draggingPoint: null, ...overrides };
  const comp = mount(SelectionHandles, { target, props });
  flushSync();
  return { target, comp };
}

describe("SelectionHandles — resize length label", () => {
  it("shows no length label when not dragging", () => {
    const { target, comp } = setup({ draggingPoint: null });
    expect(target.querySelector(".length-label")).toBeNull();
    unmount(comp); target.remove();
  });

  it("shows the wall's live length when a drag is in progress", () => {
    const { target, comp } = setup({ draggingPoint: { x: 0, y: 0 } });
    expect(target.querySelector(".length-label")?.textContent?.trim()).toBe("3.00 m");
    unmount(comp); target.remove();
  });
});

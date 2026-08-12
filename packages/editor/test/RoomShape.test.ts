import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import RoomShape from "../src/lib/components/RoomShape.svelte";
import type { Room } from "@myhome/geometry";
import { createViewportStore } from "../src/lib/viewportStore.svelte";

let target: HTMLElement;

beforeEach(() => {
  target = document.createElement("div");
  document.body.appendChild(target);
});
afterEach(() => {
  target.remove();
});

function identityViewport() {
  const store = createViewportStore();
  store.viewport.zoom = 1;
  store.viewport.panX = 0;
  store.viewport.panY = 0;
  return store.viewport;
}

describe("RoomShape — label placement", () => {
  it("places the label at the plain centroid when no other room is contained", () => {
    const room: Room = {
      id: "r1", label: "Living Room", haAreaId: null, areaM2: 100,
      polygon: [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }],
    };
    const comp = mount(RoomShape, { target, props: { room, allRooms: [room], viewport: identityViewport() } });
    flushSync();
    const text = target.querySelector("text.room-label") as SVGTextElement;
    expect(Number(text.getAttribute("x"))).toBeCloseTo(5, 5);
    expect(Number(text.getAttribute("y"))).toBeCloseTo(5, 5);
    unmount(comp);
  });

  it("moves the label off a fully-contained child room", () => {
    const zone: Room = {
      id: "zone", label: "Zone", haAreaId: null, areaM2: 100,
      polygon: [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }],
    };
    const child: Room = {
      id: "child", label: "Child", haAreaId: null, areaM2: 16,
      polygon: [{ x: 3, y: 3 }, { x: 7, y: 3 }, { x: 7, y: 7 }, { x: 3, y: 7 }],
    };
    const comp = mount(RoomShape, { target, props: { room: zone, allRooms: [zone, child], viewport: identityViewport() } });
    flushSync();
    const text = target.querySelector("text.room-label") as SVGTextElement;
    const x = Number(text.getAttribute("x"));
    const y = Number(text.getAttribute("y"));
    // Plain centroid (5,5) sits inside the child room; confirm the label moved off it.
    expect(x === 5 && y === 5).toBe(false);
    unmount(comp);
  });
});

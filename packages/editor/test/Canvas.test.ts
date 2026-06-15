import { describe, it, expect, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import Canvas from "../src/lib/components/Canvas.svelte";
import { createSampleFloor } from "../src/lib/sampleFloor";
import { detectRooms, matchRooms } from "@myhome/geometry";
import { DEFAULT_VIEWPORT } from "../src/lib/viewportStore.svelte";

describe("Canvas", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  afterEach(() => {
    if (app) {
      unmount(app);
      app = undefined;
    }
    target?.remove();
  });

  it("renders walls, dividers, and room polygons with area labels", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    const floor = createSampleFloor();
    const detected = detectRooms(floor.walls);
    floor.rooms = matchRooms(detected, floor.rooms).rooms.filter((r) => r.polygon !== null);

    app = mount(Canvas, {
      target,
      props: { floor, viewport: { ...DEFAULT_VIEWPORT }, width: 800, height: 600 },
    });
    flushSync();

    const svg = target.querySelector("svg.canvas");
    expect(svg).not.toBeNull();
    expect(svg!.querySelectorAll("polygon.wall")).toHaveLength(4);
    expect(svg!.querySelectorAll("line.divider")).toHaveLength(1);
    expect(svg!.querySelectorAll("polygon.room")).toHaveLength(2);
    expect(svg!.querySelectorAll("line.grid-line").length).toBeGreaterThan(0);

    const labels = Array.from(svg!.querySelectorAll("text.room-label")).map((el) =>
      el.textContent?.trim(),
    );
    expect(labels).toEqual(["6 m²", "6 m²"]);
  });

  it("selects a wall on click and clears selection on background click", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    const floor = createSampleFloor();
    let selectedId: string | null = null;

    app = mount(Canvas, {
      target,
      props: {
        floor,
        viewport: { ...DEFAULT_VIEWPORT },
        width: 800,
        height: 600,
        selectedId: null,
        onselect: (id: string | null) => {
          selectedId = id;
        },
      },
    });
    flushSync();

    const wall = target.querySelector("polygon.wall")!;
    wall.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    expect(selectedId).toBe("wall-1");

    const svg = target.querySelector("svg.canvas")!;
    svg.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    expect(selectedId).toBeNull();
  });
});

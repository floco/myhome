import { describe, it, expect, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import Canvas from "../src/lib/components/Canvas.svelte";
import { createSampleFloor } from "../src/lib/sampleFloor";
import { detectRooms, matchRooms } from "@myhome/geometry";
import type { Point } from "@myhome/geometry";
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

  it("computes a snap result and renders a draw preview while a wall chain is in progress", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    const floor = createSampleFloor();
    let placed: Point | null = null;

    app = mount(Canvas, {
      target,
      props: {
        floor,
        viewport: { ...DEFAULT_VIEWPORT },
        width: 800,
        height: 600,
        tool: "wall",
        drawPoints: [{ x: 0, y: 0 }],
        cursorWorld: { x: 2.02, y: 0.01 },
        onplacepoint: (p: Point) => {
          placed = p;
        },
      },
    });
    flushSync();

    const preview = target.querySelector("g.draw-preview")!;
    expect(preview.querySelector("line.rubber-band")).not.toBeNull();
    expect(preview.querySelector("text.length-label")?.textContent?.trim()).toBe("2.00 m");

    const svg = target.querySelector("svg.canvas")!;
    svg.dispatchEvent(new MouseEvent("click", { bubbles: true, clientX: 600, clientY: 301 }));
    flushSync();

    expect(placed).toEqual({ x: 2, y: 0 });
  });

  it("placing the first point of a chain reports the snapped cursor position", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    const floor = createSampleFloor();
    let placed: Point | null = null;

    app = mount(Canvas, {
      target,
      props: {
        floor,
        viewport: { ...DEFAULT_VIEWPORT },
        width: 800,
        height: 600,
        tool: "wall",
        drawPoints: [],
        cursorWorld: { x: -1, y: -1 },
        onplacepoint: (p: Point) => {
          placed = p;
        },
      },
    });
    flushSync();

    const svg = target.querySelector("svg.canvas")!;
    svg.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(placed).toEqual({ x: -1, y: -1 });
  });

  it("notifies on endpoint drag start, pointer move, and drag end", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    const floor = createSampleFloor();
    const events: string[] = [];
    let dragStartPoint: Point | null = null;
    let lastPointerWorld: Point | null = null;

    app = mount(Canvas, {
      target,
      props: {
        floor,
        viewport: { ...DEFAULT_VIEWPORT },
        width: 800,
        height: 600,
        selectedId: "wall-1",
        onpointermove: (p: Point) => {
          lastPointerWorld = p;
          events.push("move");
        },
        ondragstart: (p: Point) => {
          dragStartPoint = p;
          events.push("dragstart");
        },
        ondragend: () => events.push("dragend"),
      },
    });
    flushSync();

    const handle = target.querySelectorAll("circle.handle")[0]!;
    handle.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    flushSync();
    expect(dragStartPoint).toEqual({ x: 0, y: 0 });

    const svg = target.querySelector("svg.canvas")!;
    svg.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: 410, clientY: 300 }));
    flushSync();
    expect(lastPointerWorld).toEqual({ x: 0.1, y: 0 });

    svg.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
    flushSync();
    expect(events).toEqual(["dragstart", "move", "dragend"]);
  });
});

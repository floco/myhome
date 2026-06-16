import { describe, it, expect, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import Canvas from "../src/lib/components/Canvas.svelte";
import { createSampleFloor } from "../src/lib/sampleFloor";
import { detectRooms, matchRooms } from "@myhome/geometry";
import type { Point, Wall, Opening, Floor } from "@myhome/geometry";
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

    // RoomShape now shows room.label when set; newly-detected rooms get auto-labels "Room N"
    const labels = Array.from(svg!.querySelectorAll("text.room-label")).map((el) =>
      el.textContent?.trim(),
    );
    expect(labels).toHaveLength(2);
    expect(labels.every((l) => l?.startsWith("Room "))).toBe(true);
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

  it("middle-mouse drag reports pan deltas instead of pointer moves", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    const floor = createSampleFloor();
    let panDelta: { dx: number; dy: number } | null = null;
    let moveCount = 0;

    app = mount(Canvas, {
      target,
      props: {
        floor,
        viewport: { ...DEFAULT_VIEWPORT },
        width: 800,
        height: 600,
        onpan: (dx: number, dy: number) => {
          panDelta = { dx, dy };
        },
        onpointermove: () => moveCount++,
      },
    });
    flushSync();

    const svg = target.querySelector("svg.canvas")!;
    svg.dispatchEvent(
      new MouseEvent("mousedown", { bubbles: true, button: 1, clientX: 100, clientY: 100 }),
    );
    svg.dispatchEvent(
      new MouseEvent("mousemove", { bubbles: true, button: 1, clientX: 120, clientY: 90 }),
    );
    flushSync();

    expect(panDelta).toEqual({ dx: 20, dy: -10 });
    expect(moveCount).toBe(0);
  });

  it("wheel events report a zoom factor centered on the cursor", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    const floor = createSampleFloor();
    let zoomCall: { screen: Point; factor: number } | null = null;

    // Give the SVG a non-zero bounding rect so the rect.left/top subtraction
    // is exercised, confirming that the screen point is canvas-relative.
    const origGetBCR = SVGSVGElement.prototype.getBoundingClientRect;
    SVGSVGElement.prototype.getBoundingClientRect = () =>
      ({ left: 50, top: 30, right: 850, bottom: 630, width: 800, height: 600 }) as DOMRect;

    app = mount(Canvas, {
      target,
      props: {
        floor,
        viewport: { ...DEFAULT_VIEWPORT },
        width: 800,
        height: 600,
        onzoom: (screen: Point, factor: number) => {
          zoomCall = { screen, factor };
        },
      },
    });
    flushSync();

    const svg = target.querySelector("svg.canvas")!;
    svg.dispatchEvent(new WheelEvent("wheel", { bubbles: true, deltaY: -100, clientX: 200, clientY: 150 }));
    flushSync();

    expect(zoomCall!.screen).toEqual({ x: 200 - 50, y: 150 - 30 }); // { x: 150, y: 120 }
    expect(zoomCall!.factor).toBeGreaterThan(1);

    SVGSVGElement.prototype.getBoundingClientRect = origGetBCR;
  });

  it("double-click ends the chain without placing an extra segment", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    const floor = createSampleFloor();
    let dblclickCalled = false;
    const placedPoints: Point[] = [];

    app = mount(Canvas, {
      target,
      props: {
        floor,
        viewport: { ...DEFAULT_VIEWPORT },
        width: 800,
        height: 600,
        tool: "wall",
        drawPoints: [{ x: 0, y: 0 }],
        cursorWorld: { x: 2, y: 0 },
        onplacepoint: (p: Point) => {
          placedPoints.push(p);
        },
        ondblclick: () => {
          dblclickCalled = true;
        },
      },
    });
    flushSync();

    // Before dblclick, there should be a rubber-band line
    const preview = target.querySelector("g.draw-preview")!;
    expect(preview.querySelector("line.rubber-band")).not.toBeNull();

    const svg = target.querySelector("svg.canvas")!;
    // Dispatch the real browser sequence: click, click, dblclick
    svg.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    svg.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    svg.dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
    flushSync();

    // The first click should place a point (at the snapped cursor position)
    expect(placedPoints).toEqual([{ x: 2, y: 0 }]);
    // The second click should be suppressed (no extra point placed)
    // dblclick should be called
    expect(dblclickCalled).toBe(true);
  });

  describe("Canvas — openings", () => {
    it("renders a window opening SVG element", async () => {
      target = document.createElement("div");
      document.body.appendChild(target);

      const wall: Wall = {
        id: "w1",
        start: { x: 0, y: 0 },
        end: { x: 4, y: 0 },
        thickness: 0.2,
        type: "wall",
      };
      const opening: Opening = {
        id: "op1",
        wallId: "w1",
        type: "window",
        offset: 1,
        width: 1.2,
      };
      const floor: Floor = {
        id: "f1",
        name: "G",
        order: 0,
        walls: [wall],
        openings: [opening],
        rooms: [],
      };
      const viewport = { zoom: 50, panX: 0, panY: 0 };

      app = mount(Canvas, {
        target,
        props: { floor, viewport, width: 600, height: 400 },
      });
      await tick();

      // Window symbol should be rendered as a line with class "window-sym"
      const lines = document.querySelectorAll("line.window-sym");
      expect(lines.length).toBeGreaterThan(0);
    });

    it("renders a door opening with leaf and arc", async () => {
      target = document.createElement("div");
      document.body.appendChild(target);

      const wall: Wall = { id: "w1", start: { x: 0, y: 0 }, end: { x: 4, y: 0 }, thickness: 0.2, type: "wall" };
      const opening: Opening = { id: "op2", wallId: "w1", type: "door", offset: 1, width: 0.9, swing: "left-in" };
      const floor: Floor = { id: "f1", name: "G", order: 0, walls: [wall], openings: [opening], rooms: [] };
      const viewport = { zoom: 50, panX: 0, panY: 0 };

      app = mount(Canvas, { props: { floor, viewport, width: 600, height: 400 }, target });
      await tick();

      expect(document.querySelectorAll("line.door-leaf").length).toBeGreaterThan(0);
      expect(document.querySelectorAll("path.door-arc").length).toBeGreaterThan(0);
    });
  });
});

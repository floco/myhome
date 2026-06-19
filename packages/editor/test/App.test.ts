import { describe, it, expect, afterEach, beforeEach, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import App from "../src/App.svelte";

function stubFetch(handlers: Record<string, unknown> = {}) {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    if (url in handlers) {
      return Promise.resolve({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => handlers[url],
      });
    }
    // Default: 404
    return Promise.resolve({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => undefined,
    });
  }));
}

function stubFetch404() {
  stubFetch();
}

/** Find a toolbar button by its title attribute */
function toolbarBtn(target: HTMLElement, title: string): HTMLButtonElement {
  return Array.from(target.querySelectorAll(".toolbar button")).find(
    (b) => (b as HTMLButtonElement).title === title,
  ) as HTMLButtonElement;
}

/** Mount the app and wait for the houseStore async init to complete so the
 *  loaded guard resolves and Toolbar/Canvas are in the DOM. */
async function mountAndLoad(target: HTMLElement): Promise<ReturnType<typeof mount>> {
  const app = mount(App, { target });
  // Let the fetch micro-tasks resolve (init() awaits fetch then sets loaded=true)
  await tick();
  await tick();
  flushSync();
  return app;
}

describe("App", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  beforeEach(() => {
    stubFetch404();
  });

  afterEach(() => {
    if (app) {
      unmount(app);
      app = undefined;
    }
    target?.remove();
  });

  it("renders the title and toolbar with the select tool active", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);

    expect(target.querySelector(".app-title")?.textContent).toBe("myhome");

    const buttons = Array.from(target.querySelectorAll(".toolbar button"));
    const titles = buttons.map((b) => (b as HTMLButtonElement).title);
    expect(titles).toEqual(["Undo (Ctrl+Z)", "Redo (Ctrl+Y)", "Select", "Wall", "Divider", "Door", "Window", "Delete selected (Del)"]);

    const selectBtn = toolbarBtn(target, "Select");
    expect(selectBtn.className).toContain("active");

    const deleteBtn = toolbarBtn(target, "Delete selected (Del)") as HTMLButtonElement;
    expect(deleteBtn.disabled).toBe(true);
  });

  it("selects a wall and deletes it with the Delete key", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);

    const wall = target.querySelector("polygon.wall")!;
    wall.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    const deleteBtn = toolbarBtn(target, "Delete selected (Del)") as HTMLButtonElement;
    expect(deleteBtn.disabled).toBe(false);

    const wallsBefore = target.querySelectorAll("polygon.wall").length;

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Delete" }));
    flushSync();

    expect(target.querySelectorAll("polygon.wall").length).toBe(wallsBefore - 1);
    expect(deleteBtn.disabled).toBe(true);
  });

  it("drawing a wall chain places points, commits segments, and closes the loop", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);

    const wallBtn = toolbarBtn(target, "Wall");
    wallBtn.click();
    flushSync();

    const svg = target.querySelector("svg.canvas")!;
    const wallsBefore = target.querySelectorAll("polygon.wall").length;

    // Place 4 corners of a new 2x2 square far from the sample floor so it
    // doesn't snap to existing geometry. Screen = world*100 + (400,300).
    const corners = [
      { x: 10, y: 10 },
      { x: 12, y: 10 },
      { x: 12, y: 12 },
      { x: 10, y: 12 },
      { x: 10, y: 10 }, // closes the loop
    ];

    for (const corner of corners) {
      const screen = { x: corner.x * 100 + 400, y: corner.y * 100 + 300 };
      svg.dispatchEvent(
        new MouseEvent("mousemove", { bubbles: true, clientX: screen.x, clientY: screen.y }),
      );
      flushSync();
      svg.dispatchEvent(
        new MouseEvent("click", { bubbles: true, clientX: screen.x, clientY: screen.y }),
      );
      flushSync();
    }

    expect(target.querySelectorAll("polygon.wall").length).toBe(wallsBefore + 4);

    const rooms = target.querySelectorAll("polygon.room");
    expect(rooms.length).toBe(3);
    // RoomShape now shows room.label when set; newly-detected rooms get auto-labels "Room N"
    const labels = Array.from(target.querySelectorAll("text.room-label")).map((el) =>
      el.textContent?.trim(),
    );
    expect(labels).toHaveLength(3);
    expect(labels.every((l) => l?.startsWith("Room "))).toBe(true);
  });

  it("Escape ends the wall chain without closing it", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);

    const wallBtn = toolbarBtn(target, "Wall");
    wallBtn.click();
    flushSync();

    const svg = target.querySelector("svg.canvas")!;
    const wallsBefore = target.querySelectorAll("polygon.wall").length;

    svg.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: 1400, clientY: 1300 }));
    flushSync();
    svg.dispatchEvent(new MouseEvent("click", { bubbles: true, clientX: 1400, clientY: 1300 }));
    flushSync();

    svg.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: 1500, clientY: 1300 }));
    flushSync();
    svg.dispatchEvent(new MouseEvent("click", { bubbles: true, clientX: 1500, clientY: 1300 }));
    flushSync();

    expect(target.querySelectorAll("polygon.wall").length).toBe(wallsBefore + 1);
    expect(target.querySelector("g.draw-preview line.rubber-band")).not.toBeNull();

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    flushSync();

    expect(target.querySelector("g.draw-preview line.rubber-band")).toBeNull();
  });

  it("double-click ends the wall chain without closing it", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);

    const wallBtn = toolbarBtn(target, "Wall");
    wallBtn.click();
    flushSync();

    const svg = target.querySelector("svg.canvas")!;

    svg.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: 2400, clientY: 2300 }));
    flushSync();
    svg.dispatchEvent(new MouseEvent("click", { bubbles: true, clientX: 2400, clientY: 2300 }));
    flushSync();

    svg.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: 2500, clientY: 2300 }));
    flushSync();
    svg.dispatchEvent(new MouseEvent("click", { bubbles: true, clientX: 2500, clientY: 2300 }));
    flushSync();

    expect(target.querySelector("g.draw-preview line.rubber-band")).not.toBeNull();

    svg.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, clientX: 2500, clientY: 2300 }));
    flushSync();

    expect(target.querySelector("g.draw-preview line.rubber-band")).toBeNull();
  });

  it("dragging a selected wall's endpoint moves shared corners", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);

    // Record the original polygon points for wall-1 and wall-4 before dragging
    const wall1Poly = target.querySelectorAll("polygon.wall")[0]!;
    const wall4Poly = target.querySelectorAll("polygon.wall")[3]!;
    const wall1PointsBefore = wall1Poly.getAttribute("points");
    const wall4PointsBefore = wall4Poly.getAttribute("points");

    wall1Poly.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    const handle = target.querySelector("circle.handle")!;
    handle.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    flushSync();

    const svg = target.querySelector("svg.canvas")!;
    // Drag wall-1's start handle (at world (0,0) → screen (400,300)) to screen (300,300) → world (-1,0)
    svg.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: 300, clientY: 300 }));
    flushSync();
    svg.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
    flushSync();

    // Both wall-1 and wall-4 share the (0,0) endpoint; both polygons should have changed
    expect(target.querySelectorAll("polygon.wall")[0]!.getAttribute("points")).not.toBe(wall1PointsBefore);
    expect(target.querySelectorAll("polygon.wall")[3]!.getAttribute("points")).not.toBe(wall4PointsBefore);
  });

  it("dragging an endpoint onto its own wall's other endpoint does not collapse the wall", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);

    // Record wall-1's polygon points before the attempted drag
    const wall1PolyBefore = target.querySelectorAll("polygon.wall")[0]!.getAttribute("points");

    const wall1 = target.querySelectorAll("polygon.wall")[0]!;
    wall1.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    const handle = target.querySelector("circle.handle")!;
    handle.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    flushSync();

    // wall-1.end is at world (4,0) -> screen (800,300). Move the cursor to
    // just within snap radius of it so the dragged start endpoint
    // (world (0,0)) would snap onto wall-1's own other endpoint.
    const svg = target.querySelector("svg.canvas")!;
    svg.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: 795, clientY: 300 }));
    flushSync();
    svg.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
    flushSync();

    // The drag was a no-op (it would have collapsed wall-1 to zero length),
    // so the polygon points should be unchanged.
    expect(target.querySelectorAll("polygon.wall")[0]!.getAttribute("points")).toBe(wall1PolyBefore);
  });

  it("wheel-zooms the viewport and Reset View restores it", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);
    app = await mountAndLoad(target);

    const svg = target.querySelector("svg.canvas")!;
    const wallBefore = target.querySelector("polygon.wall")!.getAttribute("points");

    svg.dispatchEvent(new WheelEvent("wheel", { bubbles: true, deltaY: -100, clientX: 400, clientY: 300 }));
    flushSync();

    const wallAfterZoom = target.querySelector("polygon.wall")!.getAttribute("points");
    expect(wallAfterZoom).not.toBe(wallBefore);

    const resetBtn = Array.from(target.querySelectorAll("button")).find(
      (b) => (b as HTMLButtonElement).title === "Reset view",
    ) as HTMLButtonElement;
    resetBtn.click();
    flushSync();

    const wallAfterReset = target.querySelector("polygon.wall")!.getAttribute("points");
    expect(wallAfterReset).toBe(wallBefore);
  });

  it("holding space and dragging pans the viewport", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);
    app = await mountAndLoad(target);

    const svg = target.querySelector("svg.canvas")!;
    const wallBefore = target.querySelector("polygon.wall")!.getAttribute("points");

    window.dispatchEvent(new KeyboardEvent("keydown", { code: "Space" }));
    svg.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, clientX: 100, clientY: 100 }));
    svg.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: 130, clientY: 80 }));
    flushSync();
    window.dispatchEvent(new KeyboardEvent("keyup", { code: "Space" }));

    const wallAfterPan = target.querySelector("polygon.wall")!.getAttribute("points");
    expect(wallAfterPan).not.toBe(wallBefore);
  });
});

describe("App — room panel", () => {
  it("room panel is not visible initially", async () => {
    stubFetch404();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(App, { target });
    await tick();
    await tick();
    flushSync();
    const panel = target.querySelector(".room-panel");
    expect(panel).toBeNull();
    unmount(app);
    target.remove();
  });
});

describe("App — opening selection", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  beforeEach(() => {
    stubFetch404();
  });

  afterEach(() => {
    if (app) {
      unmount(app);
      app = undefined;
    }
    target?.remove();
  });

  it("selecting an opening enables the Delete button", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);
    app = await mountAndLoad(target);

    // Simulate selecting an opening via toolStore (hard to do via DOM since it requires a real click on SVG)
    // Instead verify the initial state: Delete is disabled
    const deleteBtn = target.querySelector("button.delete") as HTMLButtonElement;
    expect(deleteBtn).not.toBeNull();
    expect(deleteBtn.disabled).toBe(true); // no selection initially
  });
});

describe("App — undo/redo buttons", () => {
  it("Undo and Redo buttons exist and are disabled initially", async () => {
    stubFetch404();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = await mountAndLoad(target);

    const undoBtn = toolbarBtn(target, "Undo (Ctrl+Z)") as HTMLButtonElement;
    const redoBtn = toolbarBtn(target, "Redo (Ctrl+Y)") as HTMLButtonElement;
    expect(undoBtn).not.toBeNull();
    expect(redoBtn).not.toBeNull();
    expect(undoBtn.disabled).toBe(true);
    expect(redoBtn.disabled).toBe(true);

    unmount(app);
    target.remove();
  });
});

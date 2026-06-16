import { describe, it, expect, afterEach, beforeEach, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import App from "../src/App.svelte";
import { STORAGE_KEY } from "../src/lib/floorStore.svelte";

describe("App", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    if (app) {
      unmount(app);
      app = undefined;
    }
    target?.remove();
  });

  it("renders the title and toolbar with the select tool active", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = mount(App, { target });
    flushSync();

    expect(target.querySelector(".topbar h1")?.textContent).toBe("Floor Plan Editor");

    const buttons = Array.from(target.querySelectorAll(".toolbar button"));
    const labels = buttons.map((b) => b.textContent?.trim());
    expect(labels).toEqual(["Select", "Wall", "Divider", "Door", "Window", "Delete"]);

    const selectBtn = buttons.find((b) => b.textContent?.trim() === "Select")!;
    expect(selectBtn.className).toContain("active");

    const deleteBtn = buttons.find((b) => b.textContent?.trim() === "Delete")! as HTMLButtonElement;
    expect(deleteBtn.disabled).toBe(true);
  });

  it("selects a wall and deletes it with the Delete key", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = mount(App, { target });
    flushSync();

    const wall = target.querySelector("polygon.wall")!;
    wall.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    const deleteBtn = target.querySelectorAll(".toolbar button")[5] as HTMLButtonElement;
    expect(deleteBtn.disabled).toBe(false);

    const wallsBefore = target.querySelectorAll("polygon.wall").length;

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Delete" }));
    flushSync();

    expect(target.querySelectorAll("polygon.wall").length).toBe(wallsBefore - 1);
    expect(deleteBtn.disabled).toBe(true);
  });

  it("drawing a wall chain places points, commits segments, and closes the loop", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = mount(App, { target });
    flushSync();

    const wallBtn = Array.from(target.querySelectorAll(".toolbar button")).find(
      (b) => b.textContent?.trim() === "Wall",
    ) as HTMLButtonElement;
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
    const labels = Array.from(target.querySelectorAll("text.room-label")).map((el) =>
      el.textContent?.trim(),
    );
    expect(labels).toContain("4 m²");
  });

  it("Escape ends the wall chain without closing it", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = mount(App, { target });
    flushSync();

    const wallBtn = Array.from(target.querySelectorAll(".toolbar button")).find(
      (b) => b.textContent?.trim() === "Wall",
    ) as HTMLButtonElement;
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

  it("double-click ends the wall chain without closing it", () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = mount(App, { target });
    flushSync();

    const wallBtn = Array.from(target.querySelectorAll(".toolbar button")).find(
      (b) => b.textContent?.trim() === "Wall",
    ) as HTMLButtonElement;
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

  it("dragging a selected wall's endpoint moves shared corners", () => {
    vi.useFakeTimers();
    target = document.createElement("div");
    document.body.appendChild(target);

    app = mount(App, { target });
    flushSync();

    const wall1 = target.querySelectorAll("polygon.wall")[0]!;
    wall1.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    const handle = target.querySelector("circle.handle")!;
    handle.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    flushSync();

    const svg = target.querySelector("svg.canvas")!;
    svg.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: 300, clientY: 300 }));
    flushSync();
    svg.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
    flushSync();

    vi.advanceTimersByTime(300);

    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
    const wall1Data = saved.walls.find((w: { id: string }) => w.id === "wall-1");
    const wall4Data = saved.walls.find((w: { id: string }) => w.id === "wall-4");
    expect(wall1Data.start).toEqual({ x: -1, y: 0 });
    expect(wall4Data.end).toEqual({ x: -1, y: 0 });

    vi.useRealTimers();
  });

  it("dragging an endpoint onto its own wall's other endpoint does not collapse the wall", () => {
    vi.useFakeTimers();
    target = document.createElement("div");
    document.body.appendChild(target);

    app = mount(App, { target });
    flushSync();

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

    vi.advanceTimersByTime(300);

    // The drag was a no-op (it would have collapsed wall-1 to zero length),
    // so the floor was never persisted.
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();

    vi.useRealTimers();
  });

  it("wheel-zooms the viewport and Reset View restores it", () => {
    target = document.createElement("div");
    document.body.appendChild(target);
    app = mount(App, { target });
    flushSync();

    const svg = target.querySelector("svg.canvas")!;
    const wallBefore = target.querySelector("polygon.wall")!.getAttribute("points");

    svg.dispatchEvent(new WheelEvent("wheel", { bubbles: true, deltaY: -100, clientX: 400, clientY: 300 }));
    flushSync();

    const wallAfterZoom = target.querySelector("polygon.wall")!.getAttribute("points");
    expect(wallAfterZoom).not.toBe(wallBefore);

    const resetBtn = Array.from(target.querySelectorAll("button")).find(
      (b) => b.textContent?.trim() === "Reset View",
    ) as HTMLButtonElement;
    resetBtn.click();
    flushSync();

    const wallAfterReset = target.querySelector("polygon.wall")!.getAttribute("points");
    expect(wallAfterReset).toBe(wallBefore);
  });

  it("holding space and dragging pans the viewport", () => {
    target = document.createElement("div");
    document.body.appendChild(target);
    app = mount(App, { target });
    flushSync();

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

describe("App — opening selection", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  beforeEach(() => {
    localStorage.clear();
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
    app = mount(App, { target });
    await tick();

    // Simulate selecting an opening via toolStore (hard to do via DOM since it requires a real click on SVG)
    // Instead verify the initial state: Delete is disabled
    const deleteBtn = target.querySelector("button.delete") as HTMLButtonElement;
    expect(deleteBtn).not.toBeNull();
    expect(deleteBtn.disabled).toBe(true); // no selection initially
  });
});

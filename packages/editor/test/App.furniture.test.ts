import { describe, it, expect, afterEach, beforeEach, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import App from "../src/App.svelte";

function stubFetch404() {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    if (url === "/api/auth/me") {
      return Promise.resolve({ ok: true, status: 200, statusText: "OK", json: async () => ({ id: "u1", username: "admin", role: "admin" }) });
    }
    return Promise.resolve({ ok: false, status: 404, statusText: "Not Found", json: async () => undefined });
  }));
}

async function mountAndLoad(target: HTMLElement, route = "#/plan"): Promise<ReturnType<typeof mount>> {
  window.location.hash = route;
  const app = mount(App, { target });
  await tick(); await tick(); await tick();
  flushSync();
  return app;
}

describe("App furniture integration", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  beforeEach(() => { stubFetch404(); });

  afterEach(() => {
    if (app) { unmount(app); app = undefined; }
    target?.remove();
    vi.restoreAllMocks();
  });

  function setup(): Promise<ReturnType<typeof mount>> {
    target = document.createElement("div");
    document.body.appendChild(target);
    return mountAndLoad(target);
  }

  it("shows the Furniture toolbar button on the floor plan view", async () => {
    app = await setup();
    const btn = Array.from(target.querySelectorAll(".floating-toolbar button")).find(
      (b) => (b as HTMLButtonElement).title === "Toggle furniture library",
    ) as HTMLButtonElement | undefined;
    expect(btn).toBeDefined();
  });

  it("opens and closes the FurnitureLibraryPanel when Furniture button is clicked", async () => {
    app = await setup();
    const btn = Array.from(target.querySelectorAll(".floating-toolbar button")).find(
      (b) => (b as HTMLButtonElement).title === "Toggle furniture library",
    ) as HTMLButtonElement;

    expect(target.querySelector(".furniture-panel")).toBeNull();
    btn.click();
    flushSync();
    expect(target.querySelector(".furniture-panel")).not.toBeNull();
    btn.click();
    flushSync();
    expect(target.querySelector(".furniture-panel")).toBeNull();
  });

  it("furniture panel has draggable items when open", async () => {
    app = await setup();
    const btn = Array.from(target.querySelectorAll(".floating-toolbar button")).find(
      (b) => (b as HTMLButtonElement).title === "Toggle furniture library",
    ) as HTMLButtonElement;
    btn.click();
    flushSync();
    const items = target.querySelectorAll(".furniture-item");
    expect(items.length).toBeGreaterThan(0);
  });

  it("clicking (not dragging) a furniture item drops it at the canvas center, not under the picker panel", async () => {
    app = await setup();
    const btn = Array.from(target.querySelectorAll(".floating-toolbar button")).find(
      (b) => (b as HTMLButtonElement).title === "Toggle furniture library",
    ) as HTMLButtonElement;
    btn.click();
    flushSync();

    const canvasArea = target.querySelector(".canvas-area") as HTMLElement;
    vi.spyOn(canvasArea, "getBoundingClientRect").mockReturnValue({
      left: 0, top: 0, right: 800, bottom: 600, width: 800, height: 600, x: 0, y: 0, toJSON() {},
    });

    const sofaItem = target.querySelector('.furniture-item[data-template-id="sofa"]') as HTMLElement;
    expect(sofaItem).not.toBeNull();

    // A plain click: pointerdown and pointerup at the same spot, far from
    // canvas center (near where the picker panel sits), no movement between.
    const clickX = 750, clickY = 550;
    sofaItem.dispatchEvent(new PointerEvent("pointerdown", { clientX: clickX, clientY: clickY, bubbles: true }));
    flushSync();
    canvasArea.dispatchEvent(new PointerEvent("pointerup", { clientX: clickX, clientY: clickY, bubbles: true }));
    flushSync();

    const placed = target.querySelector(".furniture-object") as SVGGElement | null;
    expect(placed).not.toBeNull();
    const match = placed!.getAttribute("transform")!.match(/translate\(([-\d.]+),([-\d.]+)\)/);
    const [sx, sy] = [Number(match![1]), Number(match![2])];

    // Center of the mocked 800x600 canvas is (400, 300) -- nowhere near the
    // (750, 550) click point.
    expect(Math.abs(sx - 400)).toBeLessThan(5);
    expect(Math.abs(sy - 300)).toBeLessThan(5);
  });

  it("shows the FurnitureParamsPanel with a select once a parameterized furniture object is selected", async () => {
    app = await setup();
    const btn = Array.from(target.querySelectorAll(".floating-toolbar button")).find(
      (b) => (b as HTMLButtonElement).title === "Toggle furniture library",
    ) as HTMLButtonElement;
    btn.click();
    flushSync();

    const canvasArea = target.querySelector(".canvas-area") as HTMLElement;
    vi.spyOn(canvasArea, "getBoundingClientRect").mockReturnValue({
      left: 0, top: 0, right: 800, bottom: 600, width: 800, height: 600, x: 0, y: 0, toJSON() {},
    });

    const sofaItem = target.querySelector('.furniture-item[data-template-id="sofa"]') as HTMLElement;
    const clickX = 750, clickY = 550;
    sofaItem.dispatchEvent(new PointerEvent("pointerdown", { clientX: clickX, clientY: clickY, bubbles: true }));
    flushSync();
    canvasArea.dispatchEvent(new PointerEvent("pointerup", { clientX: clickX, clientY: clickY, bubbles: true }));
    flushSync();

    const placed = target.querySelector(".furniture-object") as SVGGElement;
    placed.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".furniture-params-panel")).not.toBeNull();
    expect(target.querySelector(".furniture-params-panel select")).not.toBeNull();
  });

  it("shows no FurnitureParamsPanel for a non-parameterized furniture object", async () => {
    app = await setup();
    const btn = Array.from(target.querySelectorAll(".floating-toolbar button")).find(
      (b) => (b as HTMLButtonElement).title === "Toggle furniture library",
    ) as HTMLButtonElement;
    btn.click();
    flushSync();

    const canvasArea = target.querySelector(".canvas-area") as HTMLElement;
    vi.spyOn(canvasArea, "getBoundingClientRect").mockReturnValue({
      left: 0, top: 0, right: 800, bottom: 600, width: 800, height: 600, x: 0, y: 0, toJSON() {},
    });

    const coffeeTableItem = target.querySelector('.furniture-item[data-template-id="coffee-table"]') as HTMLElement;
    const clickX = 750, clickY = 550;
    coffeeTableItem.dispatchEvent(new PointerEvent("pointerdown", { clientX: clickX, clientY: clickY, bubbles: true }));
    flushSync();
    canvasArea.dispatchEvent(new PointerEvent("pointerup", { clientX: clickX, clientY: clickY, bubbles: true }));
    flushSync();

    const placed = target.querySelector(".furniture-object") as SVGGElement;
    placed.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".furniture-params-panel")).toBeNull();
  });

  it("enables the toolbar Delete button once a furniture object is selected", async () => {
    app = await setup();
    const btn = Array.from(target.querySelectorAll(".floating-toolbar button")).find(
      (b) => (b as HTMLButtonElement).title === "Toggle furniture library",
    ) as HTMLButtonElement;
    btn.click();
    flushSync();

    const canvasArea = target.querySelector(".canvas-area") as HTMLElement;
    vi.spyOn(canvasArea, "getBoundingClientRect").mockReturnValue({
      left: 0, top: 0, right: 800, bottom: 600, width: 800, height: 600, x: 0, y: 0, toJSON() {},
    });

    const sofaItem = target.querySelector('.furniture-item[data-template-id="sofa"]') as HTMLElement;
    const clickX = 750, clickY = 550;
    sofaItem.dispatchEvent(new PointerEvent("pointerdown", { clientX: clickX, clientY: clickY, bubbles: true }));
    flushSync();
    canvasArea.dispatchEvent(new PointerEvent("pointerup", { clientX: clickX, clientY: clickY, bubbles: true }));
    flushSync();

    const deleteBtn = Array.from(target.querySelectorAll(".floating-toolbar button")).find(
      (b) => (b as HTMLButtonElement).title === "Delete selected (Del)",
    ) as HTMLButtonElement;
    expect(deleteBtn.disabled).toBe(true);

    const placed = target.querySelector(".furniture-object") as SVGGElement;
    placed.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    // Placing/selecting furniture must enable the toolbar delete button --
    // it previously stayed disabled because `hasSelection` only checked
    // wall/opening selection, not furniture. On touch devices there's no
    // Delete/Backspace key to fall back on, so this button is the only way
    // to delete furniture on mobile.
    expect(deleteBtn.disabled).toBe(false);

    const furnitureBefore = target.querySelectorAll(".furniture-object").length;
    deleteBtn.click();
    flushSync();

    expect(target.querySelectorAll(".furniture-object").length).toBe(furnitureBefore - 1);
    expect(deleteBtn.disabled).toBe(true);
  });
});

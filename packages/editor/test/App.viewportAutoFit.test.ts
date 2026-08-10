import { describe, it, expect, afterEach, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import App from "../src/App.svelte";

const HOME = { id: "home-1", name: "Main House", type: "existing", enabledModules: [], createdAt: "2026-01-01T00:00:00.000Z" };

// A single divider segment far from world-origin (50,50)-(54,50). DividerShape
// renders a plain <line> at worldToScreen(start/end) with no thickness/miter
// offset, so its rendered x1/y1/x2/y2 let us assert the exact fitted viewport
// without duplicating fitViewportToFloor's math.
// "gf-1", not "floor-1": createEmptyFloor() (the transient placeholder
// floor rendered before any real data loads) hardcodes id "floor-1". If our
// fixture reused that id, currentFloorId would look unchanged once the real
// floor replaces the placeholder, and the auto-fit effect wouldn't re-fire.
const HOUSE_DOC = {
  version: 1,
  house: { name: "Main House", units: "m", gridSnap: 0.1 },
  floors: [
    {
      id: "gf-1",
      name: "Ground Floor",
      order: 0,
      walls: [
        { id: "w1", type: "divider", start: { x: 50, y: 50 }, end: { x: 54, y: 50 } },
      ],
      openings: [],
      rooms: [],
      furnitureObjects: [],
    },
  ],
  currentFloorId: "gf-1",
};

function stubFetch() {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    const handlers: Record<string, unknown> = {
      "/api/auth/me": { id: "u1", username: "admin", role: "admin" },
      "/api/homes": [HOME],
      [`/api/homes/${HOME.id}/house`]: HOUSE_DOC,
    };
    if (url in handlers) {
      return Promise.resolve({ ok: true, status: 200, json: async () => handlers[url] });
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => undefined });
  }));
}

// jsdom reports 0 for clientWidth/clientHeight on every element (no real
// layout engine), which is what keeps the auto-fit effect inert in every
// *other* test in this suite (its width/height guard blocks it). Here we
// override it globally for this file so the effect has real dimensions to
// fit against — 1000x700 was chosen so the expected fit below works out to
// round numbers (see the math comment at the first assertion).
let originalClientWidth: PropertyDescriptor | undefined;
let originalClientHeight: PropertyDescriptor | undefined;

function stubContainerSize(): void {
  originalClientWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "clientWidth");
  originalClientHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "clientHeight");
  Object.defineProperty(HTMLElement.prototype, "clientWidth", { configurable: true, value: 1000 });
  Object.defineProperty(HTMLElement.prototype, "clientHeight", { configurable: true, value: 700 });
}

function restoreContainerSize(): void {
  if (originalClientWidth) Object.defineProperty(HTMLElement.prototype, "clientWidth", originalClientWidth);
  if (originalClientHeight) Object.defineProperty(HTMLElement.prototype, "clientHeight", originalClientHeight);
}

async function mountApp(target: HTMLElement): Promise<ReturnType<typeof mount>> {
  window.location.hash = "#/plan";
  const app = mount(App, { target });
  // authStore resolves, then homesStore.loadHomes() fetches and sets
  // activeHomeId, then the $effect watching activeHomeId fires .reload() on
  // every module store — and *this* test also stubs a real /house response,
  // so floorStore.reload() does a second real fetch beyond what
  // CommandPalette.integration.test.ts's 6-tick budget accounted for.
  // Verified empirically: 7 ticks is the minimum that reaches a stable DOM
  // here; 10 leaves margin.
  for (let i = 0; i < 10; i++) await tick();
  flushSync();
  return app;
}

describe("App — viewport auto-fit", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  afterEach(() => {
    if (app) {
      unmount(app);
      app = undefined;
    }
    target?.remove();
    restoreContainerSize();
    vi.unstubAllGlobals();
  });

  it("fits the viewport to the loaded floor's geometry instead of the hardcoded default", async () => {
    stubContainerSize();
    stubFetch();
    target = document.createElement("div");
    document.body.appendChild(target);
    app = await mountApp(target);

    // fitViewportToFloor(floor, 1000, 700): bounds (50,50)-(54,50), spanX=4,
    // spanY clamped to 0.1, padding=40 default.
    // availW=920, availH=620 -> zoom = min(920/4, 620/0.1) = min(230, 6200) = 230
    // cx=52, cy=50 -> panX = 500 - 52*230 = -11460; panY = 350 - 50*230 = -11150
    // screen(50,50) = (50*230-11460, 50*230-11150) = (40, 350)
    // screen(54,50) = (54*230-11460, 50*230-11150) = (960, 350)
    const line = target.querySelector("line.divider")!;
    expect(line.getAttribute("x1")).toBe("40");
    expect(line.getAttribute("y1")).toBe("350");
    expect(line.getAttribute("x2")).toBe("960");
    expect(line.getAttribute("y2")).toBe("350");
  });

  it("re-fits when switching to a different floor and back", async () => {
    stubContainerSize();
    stubFetch();
    target = document.createElement("div");
    document.body.appendChild(target);
    app = await mountApp(target);

    expect(target.querySelector("line.divider")).not.toBeNull();

    // Add a floor (switches to it automatically; it starts empty, so no
    // divider renders) via the compact FloorSwitcher, matching the pattern
    // in App.test.ts's "house-wide assignments" test.
    (target.querySelector(".compact-btn") as HTMLButtonElement).click();
    flushSync();
    (document.querySelector(".compact-floor-item.add") as HTMLButtonElement).click();
    flushSync();

    expect(target.querySelector("line.divider")).toBeNull();

    // Switch back to Ground Floor.
    (target.querySelector(".compact-btn") as HTMLButtonElement).click();
    flushSync();
    const groundFloorItem = Array.from(document.querySelectorAll(".compact-floor-item")).find(
      (b) => b.textContent?.trim() === "Ground Floor",
    ) as HTMLButtonElement;
    groundFloorItem.click();
    flushSync();

    // Re-fit produces the same numbers as the initial load, proving the
    // effect fires again on every switch, not just once.
    const line = target.querySelector("line.divider")!;
    expect(line.getAttribute("x1")).toBe("40");
    expect(line.getAttribute("y1")).toBe("350");
    expect(line.getAttribute("x2")).toBe("960");
    expect(line.getAttribute("y2")).toBe("350");
  });
});

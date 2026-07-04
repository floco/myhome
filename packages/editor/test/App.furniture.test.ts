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
    const items = target.querySelectorAll("[draggable='true']");
    expect(items.length).toBeGreaterThan(0);
  });
});

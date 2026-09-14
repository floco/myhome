import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import App from "../src/App.svelte";

const HOME = { id: "home-1", name: "Main House", type: "existing", enabledModules: [], createdAt: "2026-01-01T00:00:00.000Z" };

const HOUSE_DOC = {
  version: 1,
  house: { name: "Main House", units: "m", gridSnap: 0.1 },
  floors: [
    {
      id: "gf-1",
      name: "Ground Floor",
      order: 0,
      walls: [],
      openings: [],
      rooms: [],
      furnitureObjects: [],
    },
  ],
  currentFloorId: "gf-1",
};

const CONSUMABLES_DOC = {
  version: 1,
  consumables: [
    { id: "con1", name: "Heating Oil", emoji: "🛢️", unit: "L", quantity: 200, minQuantity: 50, categoryId: null, description: "", placement: null },
  ],
  transactions: [],
};

function stubFetch() {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    const handlers: Record<string, unknown> = {
      "/api/auth/me": { id: "u1", username: "admin", role: "admin" },
      "/api/homes": [HOME],
      [`/api/homes/${HOME.id}/house`]: HOUSE_DOC,
      [`/api/homes/${HOME.id}/consumables`]: CONSUMABLES_DOC,
    };
    if (url in handlers) {
      return Promise.resolve({ ok: true, status: 200, json: async () => handlers[url] });
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => undefined });
  }));
}

async function mountApp(target: HTMLElement, route: string): Promise<ReturnType<typeof mount>> {
  window.location.hash = route;
  const app = mount(App, { target });
  for (let i = 0; i < 10; i++) await tick();
  flushSync();
  return app;
}

describe("App — place on map switches to edit mode", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  afterEach(() => {
    if (app) { unmount(app); app = undefined; }
    target?.remove();
    vi.unstubAllGlobals();
  });

  it("navigates to the floor plan in edit mode when Place on map is clicked", async () => {
    stubFetch();
    target = document.createElement("div");
    document.body.appendChild(target);
    app = await mountApp(target, "#/consumables");

    const pinButton = target.querySelector('button[title="Place on map"]') as HTMLButtonElement;
    expect(pinButton).not.toBeNull();
    pinButton.click();
    await new Promise((r) => setTimeout(r, 0));
    await tick();
    flushSync();

    expect(window.location.hash).toBe("#/plan");
    // The floating toolbar's mode toggle now offers "switch to view mode",
    // meaning the floor plan landed in edit mode rather than the read-only
    // default -- previously it stayed in view mode and the drop silently
    // no-op'd.
    const modeToggle = target.querySelector(
      'button[title="Switch to view mode (read-only)"], button[title="Switch to edit mode"]',
    ) as HTMLButtonElement;
    expect(modeToggle.title).toBe("Switch to view mode (read-only)");
  });
});

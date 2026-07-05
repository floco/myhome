import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import App from "../src/App.svelte";

const HOME = { id: "home-1", name: "Main House", type: "existing", enabledModules: [], createdAt: "2026-01-01T00:00:00.000Z" };

const CHORES_DOC = {
  version: 1,
  chores: [{ id: "c1", donetickId: null, name: "Sweep kitchen", emoji: "🧹", periodDays: 7, frequencyType: "interval", frequency: 7, frequencyMetadata: {}, scheduleFromDue: false, nextDueDate: "2026-08-01T12:00:00.000Z", description: "", attachments: [] }],
  assignments: [],
  completions: [],
};

const SETTINGS_DOC = {
  version: 1,
  costCategories: [], inventoryCategories: [], workCategories: [], suppliers: [], consumableCategories: [], consumableUnits: [],
};

function stubFetch() {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    const handlers: Record<string, unknown> = {
      "/api/auth/me": { id: "u1", username: "admin", role: "admin" },
      "/api/homes": [HOME],
      [`/api/homes/${HOME.id}/chores`]: CHORES_DOC,
      [`/api/homes/${HOME.id}/settings`]: SETTINGS_DOC,
      [`/api/homes/${HOME.id}/inventory`]: { version: 1, items: [] },
      [`/api/homes/${HOME.id}/consumables`]: { version: 1, consumables: [], transactions: [] },
      [`/api/homes/${HOME.id}/works`]: { version: 1, works: [] },
      [`/api/homes/${HOME.id}/costs`]: { version: 1, entries: [] },
      [`/api/homes/${HOME.id}/kb`]: { version: 1, entries: [] },
    };
    if (url in handlers) {
      return Promise.resolve({ ok: true, status: 200, json: async () => handlers[url] });
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => undefined });
  }));
}

async function mountApp(target: HTMLElement): Promise<ReturnType<typeof mount>> {
  window.location.hash = "#/";
  const app = mount(App, { target });
  // This chain is longer than existing App tests exercise: authStore resolves,
  // then homesStore.loadHomes() fetches and sets activeHomeId, then the
  // $effect watching activeHomeId fires .reload() on every module store, each
  // doing its own fetch. No prior test in this suite stubs "/api/homes" with
  // real data, so treat this tick count as a starting guess.
  for (let i = 0; i < 6; i++) await tick();
  flushSync();
  return app;
}

describe("Global search integration", () => {
  let target: HTMLElement;
  let app: ReturnType<typeof mount> | undefined;

  beforeEach(() => { stubFetch(); });
  afterEach(() => { if (app) { unmount(app); app = undefined; } target?.remove(); vi.unstubAllGlobals(); });

  it("opens the palette with Ctrl+K, selects a chore, and navigates to Chores with its edit modal open", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);
    app = await mountApp(target);

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true }));
    flushSync();
    expect(target.querySelector(".cmdk")).not.toBeNull();

    const input = target.querySelector(".cmdk-input") as HTMLInputElement;
    input.value = "sweep";
    input.dispatchEvent(new Event("input"));
    flushSync();

    const result = target.querySelector(".cmdk-result") as HTMLElement;
    expect(result.textContent).toContain("Sweep kitchen");
    result.click();
    flushSync();
    // jsdom dispatches "hashchange" as a queued task, not synchronously —
    // give it a turn before asserting the route changed.
    await new Promise((r) => setTimeout(r, 0));
    await tick();
    flushSync();

    expect(target.querySelector(".cmdk")).toBeNull();
    expect(window.location.hash).toBe("#/chores");
    expect(target.querySelector(".ui-modal-title")?.textContent).toBe("🧹 Sweep kitchen");
  });

  it("opens the palette from the topbar search button", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);
    app = await mountApp(target);

    const btn = target.querySelector(".topbar .search-btn") as HTMLButtonElement;
    btn.click();
    flushSync();

    expect(target.querySelector(".cmdk")).not.toBeNull();
  });
});

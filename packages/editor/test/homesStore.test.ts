import { describe, it, expect, afterEach, vi } from "vitest";
import { homesStore } from "../src/lib/homesStore.svelte";

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => {
  vi.unstubAllGlobals();
  // Reset singleton state between tests
  homesStore._reset();
});

describe("homesStore — loadHomes", () => {
  it("starts with empty homes and null activeHomeId", () => {
    expect(homesStore.homes).toEqual([]);
    expect(homesStore.activeHomeId).toBeNull();
    expect(homesStore.loaded).toBe(false);
  });

  it("loads homes and sets activeHomeId to first home", async () => {
    const homes = [
      { id: "h1", name: "Rue des Lilas", type: "existing", enabledModules: ["home", "plan"], createdAt: "2026-01-01T00:00:00Z" },
      { id: "h2", name: "Dream Build", type: "project", enabledModules: ["home", "plan", "works"], createdAt: "2026-01-02T00:00:00Z" },
    ];
    vi.stubGlobal("fetch", makeFetch(200, homes));
    await homesStore.loadHomes();
    expect(homesStore.homes.length).toBe(2);
    expect(homesStore.activeHomeId).toBe("h1");
    expect(homesStore.loaded).toBe(true);
  });

  it("sets loaded=true and empty homes on empty list", async () => {
    vi.stubGlobal("fetch", makeFetch(200, []));
    await homesStore.loadHomes();
    expect(homesStore.homes).toEqual([]);
    expect(homesStore.activeHomeId).toBeNull();
    expect(homesStore.loaded).toBe(true);
  });
});

describe("homesStore — setActiveHomeId", () => {
  it("switches active home", async () => {
    const homes = [
      { id: "h1", name: "A", type: "existing", enabledModules: [], createdAt: "" },
      { id: "h2", name: "B", type: "existing", enabledModules: [], createdAt: "" },
    ];
    vi.stubGlobal("fetch", makeFetch(200, homes));
    await homesStore.loadHomes();
    homesStore.setActiveHomeId("h2");
    expect(homesStore.activeHomeId).toBe("h2");
  });
});

describe("homesStore — createHome", () => {
  it("posts to /api/homes and adds home to list", async () => {
    const newHome = { id: "h-new", name: "Villa", type: "existing", enabledModules: ["home"], createdAt: "" };
    vi.stubGlobal("fetch", makeFetch(201, newHome));
    await homesStore.createHome("Villa", "existing");
    expect(homesStore.homes.length).toBe(1);
    expect(homesStore.activeHomeId).toBe("h-new");
  });
});

describe("homesStore — patchHome", () => {
  it("patches and updates local homes list", async () => {
    const home = { id: "h1", name: "Old", type: "existing" as const, enabledModules: ["home"], createdAt: "" };
    vi.stubGlobal("fetch", makeFetch(200, { ...home, name: "New" }));
    homesStore.homes.push(home);
    await homesStore.patchHome("h1", { name: "New" });
    expect(homesStore.homes[0].name).toBe("New");
  });
});

describe("homesStore — deleteHome", () => {
  it("deletes home and switches to first remaining", async () => {
    vi.stubGlobal("fetch", makeFetch(204));
    const h1 = { id: "h1", name: "A", type: "existing" as const, enabledModules: [], createdAt: "" };
    const h2 = { id: "h2", name: "B", type: "existing" as const, enabledModules: [], createdAt: "" };
    homesStore.homes.push(h1, h2);
    homesStore.setActiveHomeId("h1");
    await homesStore.deleteHome("h1");
    expect(homesStore.homes.length).toBe(1);
    expect(homesStore.activeHomeId).toBe("h2");
  });
});

describe("homesStore — activeHome", () => {
  it("returns the active home object", async () => {
    const home = { id: "h1", name: "Test", type: "existing" as const, enabledModules: ["home"], createdAt: "" };
    vi.stubGlobal("fetch", makeFetch(200, [home]));
    await homesStore.loadHomes();
    expect(homesStore.activeHome?.name).toBe("Test");
  });
});

describe("homesStore — createHome demo type", () => {
  it("accepts type 'demo' and switches to the new home", async () => {
    const newHome = { id: "h-demo", name: "Demo House", type: "demo", enabledModules: ["home", "plan", "chores"], createdAt: "" };
    vi.stubGlobal("fetch", makeFetch(201, newHome));
    await homesStore.createHome("Demo House", "demo");
    expect(homesStore.homes[0].type).toBe("demo");
    expect(homesStore.activeHomeId).toBe("h-demo");
  });
});

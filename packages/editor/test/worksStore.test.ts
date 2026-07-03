import { describe, it, expect, afterEach, vi } from "vitest";
import { createWorksStore } from "../src/lib/worksStore.svelte";
import type { Work } from "../src/lib/worksStore.svelte";

const HOME = "home-123";
const getHomeId = () => HOME;

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

afterEach(() => vi.unstubAllGlobals());

function makeWork(overrides: Partial<Work> = {}): Work {
  return {
    id: "w1", title: "Boiler repair", description: "", status: "done",
    categoryId: null, date: "2025-11-10", totalCost: 1200, supplierId: null,
    notes: "", attachments: [], placement: null,
    ...overrides,
  };
}

const emptyDoc = { version: 1, works: [] };

describe("worksStore — init", () => {
  it("loads works from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, works: [makeWork()] }));
    const store = createWorksStore(getHomeId);
    await tick();
    expect(store.works.length).toBe(1);
    expect(store.works[0].id).toBe("w1");
    expect(store.loaded).toBe(true);
  });

  it("marks loaded on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("net fail")));
    const store = createWorksStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("net fail");
  });

  it("does not fetch when no homeId provided", async () => {
    const fetchFn = vi.fn();
    vi.stubGlobal("fetch", fetchFn);
    const store = createWorksStore();
    await tick();
    expect(fetchFn).not.toHaveBeenCalled();
    expect(store.loaded).toBe(true);
  });
});

describe("worksStore — createWork", () => {
  it("posts to /api/homes/{homeId}/works and refreshes", async () => {
    const created = makeWork({ id: "w2", title: "New work" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, works: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createWorksStore(getHomeId);
    await tick();
    await store.createWork({ title: "New work", description: "", status: "planned", categoryId: null, date: "2026-01-01", totalCost: null, supplierId: null, notes: "" });
    await tick();
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/works`);
    expect(fetchFn.mock.calls[1][1].method).toBe("POST");
    expect(store.works.length).toBe(1);
  });
});

describe("worksStore — setPlacement", () => {
  it("calls PUT /api/homes/{homeId}/works/{id}/placement when placement provided", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createWorksStore(getHomeId);
    await tick();
    await store.setPlacement("w1", { floorId: "f1", position: { x: 10, y: 20 } });
    const [url, opts] = fetchFn.mock.calls[1];
    expect(url).toBe(`/api/homes/${HOME}/works/w1/placement`);
    expect(opts.method).toBe("PUT");
  });

  it("calls DELETE /api/homes/{homeId}/works/{id}/placement when placement is null", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createWorksStore(getHomeId);
    await tick();
    await store.setPlacement("w1", null);
    const [url, opts] = fetchFn.mock.calls[1];
    expect(url).toBe(`/api/homes/${HOME}/works/w1/placement`);
    expect(opts.method).toBe("DELETE");
  });
});

describe("worksStore — deleteWork", () => {
  it("calls DELETE /api/homes/{homeId}/works/{id}", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createWorksStore(getHomeId);
    await tick();
    await store.deleteWork("w1");
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/works/w1`);
    expect(fetchFn.mock.calls[1][1].method).toBe("DELETE");
  });
});

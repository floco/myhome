import { describe, it, expect, afterEach, vi } from "vitest";
import { createKBStore } from "../src/lib/kbStore.svelte";
import type { KBEntry } from "../src/lib/kbStore.svelte";

const HOME = "home-123";
const getHomeId = () => HOME;

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

function makeEntry(overrides: Partial<KBEntry> = {}): KBEntry {
  return {
    id: "e1",
    title: "How to paint",
    content: "# Painting\n\nUse good brushes.",
    createdAt: "2026-06-28T10:00:00Z",
    updatedAt: "2026-06-28T10:00:00Z",
    attachments: [],
    parentId: null,
    icon: "📄",
    order: 0,
    ...overrides,
  };
}

// Routes requests by URL/method rather than call order, so tests don't break
// every time an internal method (e.g. init()) changes how many requests it
// fires -- init() also fetches /kb/trash now, on top of /kb, and every
// mutating method calls init() to refresh, so a fixed-position mock chain
// would be extremely brittle here.
type Route = {
  match: (url: string, method: string) => boolean;
  respond: (url: string, init?: RequestInit) => { ok: boolean; status: number; json: () => Promise<unknown> };
};

function stubRoutedFetch(routes: Route[]): ReturnType<typeof vi.fn> {
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    const route = routes.find((r) => r.match(url, method));
    if (!route) throw new Error(`Unhandled request in test: ${method} ${url}`);
    return route.respond(url, init);
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

function ok(status: number, body: unknown) {
  return { ok: true, status, json: async () => body };
}

function fail(status: number) {
  return { ok: false, status, json: async () => null };
}

function get(urlSuffix: string): Route["match"] {
  return (url, method) => method === "GET" && url.endsWith(urlSuffix);
}

function methodAt(method: string, urlSuffix: string): Route["match"] {
  return (url, m) => m === method && url.endsWith(urlSuffix);
}

describe("kbStore — init", () => {
  it("loads entries and trash count from API", async () => {
    const fetchFn = stubRoutedFetch([
      { match: get("/kb"), respond: () => ok(200, { version: 1, entries: [makeEntry()] }) },
      { match: get("/kb/trash"), respond: () => ok(200, { entries: [] }) },
    ]);
    const store = createKBStore(getHomeId);
    await tick();
    expect(store.entries.length).toBe(1);
    expect(store.entries[0].id).toBe("e1");
    expect(store.entries[0].icon).toBe("📄");
    expect(store.loaded).toBe(true);
    expect(fetchFn).toHaveBeenCalledWith(`/api/homes/${HOME}/kb/trash`);
  });

  it("marks loaded and sets loadError on network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("net fail")));
    const store = createKBStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("net fail");
  });

  it("marks loaded and sets loadError on HTTP error", async () => {
    stubRoutedFetch([{ match: get("/kb"), respond: () => fail(500) }]);
    const store = createKBStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("HTTP 500");
  });

  it("does not fetch when no homeId provided", async () => {
    const fetchFn = vi.fn();
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore();
    await tick();
    expect(fetchFn).not.toHaveBeenCalled();
    expect(store.loaded).toBe(true);
  });
});

describe("kbStore — createEntry", () => {
  it("POSTs to /api/homes/{homeId}/kb, returns new entry, and refreshes", async () => {
    const created = makeEntry({ id: "e2", title: "New page", content: "" });
    const fetchFn = stubRoutedFetch([
      { match: get("/kb"), respond: () => ok(200, { version: 1, entries: [created] }) },
      { match: get("/kb/trash"), respond: () => ok(200, { entries: [] }) },
      { match: methodAt("POST", "/kb"), respond: () => ok(201, created) },
    ]);
    const store = createKBStore(getHomeId);
    await tick();
    const entry = await store.createEntry({ title: "New page", content: "" });
    await tick();
    expect(entry.id).toBe("e2");
    expect(store.entries.length).toBe(1);
    const postCall = fetchFn.mock.calls.find((c) => (c[1] as RequestInit | undefined)?.method === "POST")!;
    expect(postCall[0]).toBe(`/api/homes/${HOME}/kb`);
    expect(JSON.parse((postCall[1] as RequestInit).body as string)).toEqual({ title: "New page", content: "" });
  });

  it("includes parentId and icon in the POST body only when provided", async () => {
    const created = makeEntry({ id: "e2", parentId: "p1", icon: "🔧" });
    const fetchFn = stubRoutedFetch([
      { match: get("/kb"), respond: () => ok(200, { version: 1, entries: [created] }) },
      { match: get("/kb/trash"), respond: () => ok(200, { entries: [] }) },
      { match: methodAt("POST", "/kb"), respond: () => ok(201, created) },
    ]);
    const store = createKBStore(getHomeId);
    await tick();
    await store.createEntry({ title: "New page", content: "", parentId: "p1", icon: "🔧" });
    const postCall = fetchFn.mock.calls.find((c) => (c[1] as RequestInit | undefined)?.method === "POST")!;
    expect(JSON.parse((postCall[1] as RequestInit).body as string)).toEqual({
      title: "New page", content: "", parentId: "p1", icon: "🔧",
    });
  });

  it("throws on HTTP error", async () => {
    stubRoutedFetch([
      { match: get("/kb"), respond: () => ok(200, { version: 1, entries: [] }) },
      { match: get("/kb/trash"), respond: () => ok(200, { entries: [] }) },
      { match: methodAt("POST", "/kb"), respond: () => fail(422) },
    ]);
    const store = createKBStore(getHomeId);
    await tick();
    await expect(store.createEntry({ title: "x", content: "" })).rejects.toThrow("HTTP 422");
  });
});

describe("kbStore — updateEntry", () => {
  it("PUTs to /api/homes/{homeId}/kb/{id} and refreshes", async () => {
    const updated = makeEntry({ title: "Updated title" });
    const fetchFn = stubRoutedFetch([
      { match: get("/kb"), respond: () => ok(200, { version: 1, entries: [updated] }) },
      { match: get("/kb/trash"), respond: () => ok(200, { entries: [] }) },
      { match: methodAt("PUT", "/kb/e1"), respond: () => ok(204, null) },
    ]);
    const store = createKBStore(getHomeId);
    await tick();
    await store.updateEntry("e1", { title: "Updated title" });
    await tick();
    expect(store.entries[0].title).toBe("Updated title");
    const putCall = fetchFn.mock.calls.find((c) => (c[1] as RequestInit | undefined)?.method === "PUT")!;
    expect(putCall[0]).toBe(`/api/homes/${HOME}/kb/e1`);
  });

  it("includes parentId and icon in the PUT body when provided", async () => {
    const fetchFn = stubRoutedFetch([
      { match: get("/kb"), respond: () => ok(200, { version: 1, entries: [makeEntry({ parentId: "p1" })] }) },
      { match: get("/kb/trash"), respond: () => ok(200, { entries: [] }) },
      { match: methodAt("PUT", "/kb/e1"), respond: () => ok(204, null) },
    ]);
    const store = createKBStore(getHomeId);
    await tick();
    await store.updateEntry("e1", { parentId: "p1", icon: "🔧" });
    const putCall = fetchFn.mock.calls.find((c) => (c[1] as RequestInit | undefined)?.method === "PUT")!;
    expect(JSON.parse((putCall[1] as RequestInit).body as string)).toEqual({ parentId: "p1", icon: "🔧" });
  });

  it("throws on HTTP error", async () => {
    stubRoutedFetch([
      { match: get("/kb"), respond: () => ok(200, { version: 1, entries: [makeEntry()] }) },
      { match: get("/kb/trash"), respond: () => ok(200, { entries: [] }) },
      { match: methodAt("PUT", "/kb/e1"), respond: () => fail(404) },
    ]);
    const store = createKBStore(getHomeId);
    await tick();
    await expect(store.updateEntry("e1", { title: "x" })).rejects.toThrow("HTTP 404");
  });
});

describe("kbStore — reorderSiblings", () => {
  it("PUTs to /api/homes/{homeId}/kb/reorder and refreshes", async () => {
    const a = makeEntry({ id: "a", order: 1 });
    const b = makeEntry({ id: "b", order: 0 });
    const fetchFn = stubRoutedFetch([
      { match: get("/kb"), respond: () => ok(200, { version: 1, entries: [b, a] }) },
      { match: get("/kb/trash"), respond: () => ok(200, { entries: [] }) },
      { match: methodAt("PUT", "/kb/reorder"), respond: () => ok(204, null) },
    ]);
    const store = createKBStore(getHomeId);
    await tick();
    await store.reorderSiblings(null, ["b", "a"]);
    await tick();
    const putCall = fetchFn.mock.calls.find((c) => (c[1] as RequestInit | undefined)?.method === "PUT")!;
    expect(putCall[0]).toBe(`/api/homes/${HOME}/kb/reorder`);
    expect(JSON.parse((putCall[1] as RequestInit).body as string)).toEqual({ parentId: null, orderedIds: ["b", "a"] });
    expect(store.entries[0].id).toBe("b");
  });
});

describe("kbStore — deleteEntry", () => {
  it("DELETEs /api/homes/{homeId}/kb/{id}, returns deletedCount, and refreshes entries and trash", async () => {
    const fetchFn = stubRoutedFetch([
      { match: get("/kb"), respond: () => ok(200, { version: 1, entries: [] }) },
      { match: get("/kb/trash"), respond: () => ok(200, { entries: [makeEntry({ deletedAt: "2026-07-01T00:00:00Z" })] }) },
      { match: methodAt("DELETE", "/kb/e1"), respond: () => ok(200, { deletedCount: 3 }) },
    ]);
    const store = createKBStore(getHomeId);
    await tick();
    const count = await store.deleteEntry("e1");
    await tick();
    expect(count).toBe(3);
    expect(store.entries.length).toBe(0);
    expect(store.trash.length).toBe(1);
    const delCall = fetchFn.mock.calls.find((c) => (c[1] as RequestInit | undefined)?.method === "DELETE")!;
    expect(delCall[0]).toBe(`/api/homes/${HOME}/kb/e1`);
  });

  it("throws on HTTP error", async () => {
    stubRoutedFetch([
      { match: get("/kb"), respond: () => ok(200, { version: 1, entries: [makeEntry()] }) },
      { match: get("/kb/trash"), respond: () => ok(200, { entries: [] }) },
      { match: methodAt("DELETE", "/kb/e1"), respond: () => fail(404) },
    ]);
    const store = createKBStore(getHomeId);
    await tick();
    await expect(store.deleteEntry("e1")).rejects.toThrow("HTTP 404");
  });
});

describe("kbStore — trash", () => {
  it("loadTrash GETs /kb/trash and populates trash", async () => {
    const trashed = makeEntry({ id: "t1", deletedAt: "2026-07-01T00:00:00Z" });
    const fetchFn = stubRoutedFetch([
      { match: get("/kb"), respond: () => ok(200, { version: 1, entries: [] }) },
      { match: get("/kb/trash"), respond: () => ok(200, { entries: [trashed] }) },
    ]);
    const store = createKBStore(getHomeId);
    await tick();
    await store.loadTrash();
    expect(store.trash.length).toBe(1);
    expect(store.trash[0].id).toBe("t1");
    expect(fetchFn).toHaveBeenCalledWith(`/api/homes/${HOME}/kb/trash`);
  });

  it("restoreEntry POSTs to /kb/trash/{id}/restore, then refreshes entries and trash", async () => {
    const fetchFn = stubRoutedFetch([
      { match: get("/kb"), respond: () => ok(200, { version: 1, entries: [makeEntry()] }) },
      { match: get("/kb/trash"), respond: () => ok(200, { entries: [] }) },
      { match: methodAt("POST", "/kb/trash/e1/restore"), respond: () => ok(200, { restoredCount: 1 }) },
    ]);
    const store = createKBStore(getHomeId);
    await tick();
    await store.restoreEntry("e1");
    await tick();
    const restoreCall = fetchFn.mock.calls.find((c) => (c[1] as RequestInit | undefined)?.method === "POST")!;
    expect(restoreCall[0]).toBe(`/api/homes/${HOME}/kb/trash/e1/restore`);
    expect(store.entries.length).toBe(1);
    expect(store.trash.length).toBe(0);
  });

  it("permanentlyDeleteEntry DELETEs /kb/trash/{id}, then refreshes trash", async () => {
    const fetchFn = stubRoutedFetch([
      { match: get("/kb"), respond: () => ok(200, { version: 1, entries: [] }) },
      { match: get("/kb/trash"), respond: () => ok(200, { entries: [] }) },
      { match: methodAt("DELETE", "/kb/trash/t1"), respond: () => ok(204, null) },
    ]);
    const store = createKBStore(getHomeId);
    await tick();
    await store.permanentlyDeleteEntry("t1");
    const delCall = fetchFn.mock.calls.find((c) => (c[1] as RequestInit | undefined)?.method === "DELETE")!;
    expect(delCall[0]).toBe(`/api/homes/${HOME}/kb/trash/t1`);
  });

  it("emptyTrash POSTs to /kb/trash/empty, then refreshes trash", async () => {
    const fetchFn = stubRoutedFetch([
      { match: get("/kb"), respond: () => ok(200, { version: 1, entries: [] }) },
      { match: get("/kb/trash"), respond: () => ok(200, { entries: [] }) },
      { match: methodAt("POST", "/kb/trash/empty"), respond: () => ok(200, { deletedCount: 2 }) },
    ]);
    const store = createKBStore(getHomeId);
    await tick();
    await store.emptyTrash();
    const emptyCall = fetchFn.mock.calls.find((c) => (c[1] as RequestInit | undefined)?.method === "POST")!;
    expect(emptyCall[0]).toBe(`/api/homes/${HOME}/kb/trash/empty`);
  });
});

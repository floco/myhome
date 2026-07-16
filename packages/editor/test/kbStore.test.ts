import { describe, it, expect, afterEach, vi } from "vitest";
import { createKBStore } from "../src/lib/kbStore.svelte";
import type { KBEntry } from "../src/lib/kbStore.svelte";

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

const emptyDoc = { version: 1, entries: [] };

describe("kbStore — init", () => {
  it("loads entries from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, entries: [makeEntry()] }));
    const store = createKBStore(getHomeId);
    await tick();
    expect(store.entries.length).toBe(1);
    expect(store.entries[0].id).toBe("e1");
    expect(store.entries[0].icon).toBe("📄");
    expect(store.loaded).toBe(true);
  });

  it("marks loaded and sets loadError on network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("net fail")));
    const store = createKBStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("net fail");
  });

  it("marks loaded and sets loadError on HTTP error", async () => {
    vi.stubGlobal("fetch", makeFetch(500));
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
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    const entry = await store.createEntry({ title: "New page", content: "" });
    await tick();
    expect(entry.id).toBe("e2");
    expect(store.entries.length).toBe(1);
    const [, postCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(postCall[0]).toBe(`/api/homes/${HOME}/kb`);
    expect(postCall[1].method).toBe("POST");
    expect(JSON.parse(postCall[1].body as string)).toEqual({ title: "New page", content: "" });
  });

  it("includes parentId and icon in the POST body only when provided", async () => {
    const created = makeEntry({ id: "e2", parentId: "p1", icon: "🔧" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.createEntry({ title: "New page", content: "", parentId: "p1", icon: "🔧" });
    const [, postCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(JSON.parse(postCall[1].body as string)).toEqual({
      title: "New page", content: "", parentId: "p1", icon: "🔧",
    });
  });

  it("throws on HTTP error", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: false, status: 422, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await expect(store.createEntry({ title: "x", content: "" })).rejects.toThrow("HTTP 422");
  });
});

describe("kbStore — updateEntry", () => {
  it("PUTs to /api/homes/{homeId}/kb/{id} and refreshes", async () => {
    const entry = makeEntry();
    const updated = makeEntry({ title: "Updated title" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [updated] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.updateEntry("e1", { title: "Updated title" });
    await tick();
    expect(store.entries[0].title).toBe("Updated title");
    const [, putCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(putCall[0]).toBe(`/api/homes/${HOME}/kb/e1`);
    expect(putCall[1].method).toBe("PUT");
  });

  it("includes parentId and icon in the PUT body when provided", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [{ ...entry, parentId: "p1" }] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.updateEntry("e1", { parentId: "p1", icon: "🔧" });
    const [, putCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(JSON.parse(putCall[1].body as string)).toEqual({ parentId: "p1", icon: "🔧" });
  });

  it("throws on HTTP error", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await expect(store.updateEntry("e1", { title: "x" })).rejects.toThrow("HTTP 404");
  });
});

describe("kbStore — reorderSiblings", () => {
  it("PUTs to /api/homes/{homeId}/kb/reorder and refreshes", async () => {
    const a = makeEntry({ id: "a", order: 0 });
    const b = makeEntry({ id: "b", order: 1 });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [a, b] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [{ ...b, order: 0 }, { ...a, order: 1 }] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.reorderSiblings(null, ["b", "a"]);
    await tick();
    const [, putCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(putCall[0]).toBe(`/api/homes/${HOME}/kb/reorder`);
    expect(JSON.parse(putCall[1].body as string)).toEqual({ parentId: null, orderedIds: ["b", "a"] });
    expect(store.entries[0].id).toBe("b");
  });
});

describe("kbStore — deleteEntry", () => {
  it("DELETEs /api/homes/{homeId}/kb/{id}, returns deletedCount, and refreshes", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ deletedCount: 3 }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    expect(store.entries.length).toBe(1);
    const count = await store.deleteEntry("e1");
    await tick();
    expect(count).toBe(3);
    expect(store.entries.length).toBe(0);
    const [, delCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(delCall[0]).toBe(`/api/homes/${HOME}/kb/e1`);
    expect(delCall[1].method).toBe("DELETE");
  });

  it("throws on HTTP error", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await expect(store.deleteEntry("e1")).rejects.toThrow("HTTP 404");
  });
});

describe("kbStore — trash", () => {
  it("loadTrash GETs /kb/trash and populates trash", async () => {
    const trashed = makeEntry({ id: "t1", deletedAt: "2026-07-01T00:00:00Z" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ entries: [trashed] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.loadTrash();
    expect(store.trash.length).toBe(1);
    expect(store.trash[0].id).toBe("t1");
    const [, trashCall] = fetchFn.mock.calls as [unknown, [string]][];
    expect(trashCall[0]).toBe(`/api/homes/${HOME}/kb/trash`);
  });

  it("restoreEntry POSTs to /kb/trash/{id}/restore, then refreshes entries and trash", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ restoredCount: 1 }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [makeEntry()] }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ entries: [] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.restoreEntry("e1");
    const [, restoreCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(restoreCall[0]).toBe(`/api/homes/${HOME}/kb/trash/e1/restore`);
    expect(restoreCall[1].method).toBe("POST");
    expect(store.entries.length).toBe(1);
  });

  it("permanentlyDeleteEntry DELETEs /kb/trash/{id}, then refreshes trash", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ entries: [] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.permanentlyDeleteEntry("t1");
    const [, delCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(delCall[0]).toBe(`/api/homes/${HOME}/kb/trash/t1`);
    expect(delCall[1].method).toBe("DELETE");
  });

  it("emptyTrash POSTs to /kb/trash/empty, then refreshes trash", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ deletedCount: 2 }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ entries: [] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.emptyTrash();
    const [, emptyCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(emptyCall[0]).toBe(`/api/homes/${HOME}/kb/trash/empty`);
    expect(emptyCall[1].method).toBe("POST");
  });
});

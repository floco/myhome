import { describe, it, expect, afterEach, vi } from "vitest";
import { createKBStore } from "../src/lib/kbStore.svelte";
import type { KBEntry } from "../src/lib/kbStore.svelte";

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
    ...overrides,
  };
}

const emptyDoc = { version: 1, entries: [] };

describe("kbStore — init", () => {
  it("loads entries from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, entries: [makeEntry()] }));
    const store = createKBStore();
    await tick();
    expect(store.entries.length).toBe(1);
    expect(store.entries[0].id).toBe("e1");
    expect(store.loaded).toBe(true);
  });

  it("marks loaded and sets loadError on network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("net fail")));
    const store = createKBStore();
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("net fail");
  });

  it("marks loaded and sets loadError on HTTP error", async () => {
    vi.stubGlobal("fetch", makeFetch(500));
    const store = createKBStore();
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("HTTP 500");
  });
});

describe("kbStore — createEntry", () => {
  it("POSTs to /api/kb, returns new entry, and refreshes", async () => {
    const created = makeEntry({ id: "e2", title: "New entry", content: "" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore();
    await tick();
    const entry = await store.createEntry({ title: "New entry", content: "" });
    await tick();
    expect(entry.id).toBe("e2");
    expect(entry.title).toBe("New entry");
    expect(store.entries.length).toBe(1);
    const [, postCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(postCall[0]).toBe("/api/kb");
    expect(postCall[1].method).toBe("POST");
    expect(JSON.parse(postCall[1].body as string)).toEqual({ title: "New entry", content: "" });
  });

  it("throws on HTTP error", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: false, status: 422, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore();
    await tick();
    await expect(store.createEntry({ title: "x", content: "" })).rejects.toThrow("HTTP 422");
  });
});

describe("kbStore — updateEntry", () => {
  it("PUTs to /api/kb/{id} and refreshes", async () => {
    const entry = makeEntry();
    const updated = makeEntry({ title: "Updated title" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [updated] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore();
    await tick();
    await store.updateEntry("e1", { title: "Updated title" });
    await tick();
    expect(store.entries[0].title).toBe("Updated title");
    const [, putCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(putCall[0]).toBe("/api/kb/e1");
    expect(putCall[1].method).toBe("PUT");
  });

  it("throws on HTTP error", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore();
    await tick();
    await expect(store.updateEntry("e1", { title: "x" })).rejects.toThrow("HTTP 404");
  });
});

describe("kbStore — deleteEntry", () => {
  it("DELETEs /api/kb/{id} and refreshes", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore();
    await tick();
    expect(store.entries.length).toBe(1);
    await store.deleteEntry("e1");
    await tick();
    expect(store.entries.length).toBe(0);
    const [, delCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(delCall[0]).toBe("/api/kb/e1");
    expect(delCall[1].method).toBe("DELETE");
  });

  it("throws on HTTP error", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore();
    await tick();
    await expect(store.deleteEntry("e1")).rejects.toThrow("HTTP 404");
  });
});

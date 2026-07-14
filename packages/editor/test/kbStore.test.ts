import { describe, it, expect, afterEach, vi } from "vitest";
import { createKBStore } from "../src/lib/kbStore.svelte";
import type { KBEntry, KBFolder } from "../src/lib/kbStore.svelte";

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
    ...overrides,
  };
}

function makeFolder(overrides: Partial<KBFolder> = {}): KBFolder {
  return { id: "f1", name: "Appliances", parentId: null, ...overrides };
}

const emptyDoc = { version: 1, entries: [] };

describe("kbStore — init", () => {
  it("loads entries from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, entries: [makeEntry()] }));
    const store = createKBStore(getHomeId);
    await tick();
    expect(store.entries.length).toBe(1);
    expect(store.entries[0].id).toBe("e1");
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
    const created = makeEntry({ id: "e2", title: "New entry", content: "" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    const entry = await store.createEntry({ title: "New entry", content: "" });
    await tick();
    expect(entry.id).toBe("e2");
    expect(entry.title).toBe("New entry");
    expect(store.entries.length).toBe(1);
    const [, postCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(postCall[0]).toBe(`/api/homes/${HOME}/kb`);
    expect(postCall[1].method).toBe("POST");
    expect(JSON.parse(postCall[1].body as string)).toEqual({ title: "New entry", content: "" });
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

describe("kbStore — deleteEntry", () => {
  it("DELETEs /api/homes/{homeId}/kb/{id} and refreshes", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    expect(store.entries.length).toBe(1);
    await store.deleteEntry("e1");
    await tick();
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

describe("kbStore — folders init", () => {
  it("loads folders from API alongside entries", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, entries: [], folders: [makeFolder()] }));
    const store = createKBStore(getHomeId);
    await tick();
    expect(store.folders.length).toBe(1);
    expect(store.folders[0].name).toBe("Appliances");
  });
});

describe("kbStore — createFolder", () => {
  it("POSTs to /api/homes/{homeId}/kb/folders, returns new folder, and refreshes", async () => {
    const created = makeFolder({ id: "f2", name: "New folder" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [] }) })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    const folder = await store.createFolder({ name: "New folder" });
    await tick();
    expect(folder.id).toBe("f2");
    expect(store.folders.length).toBe(1);
    const [, postCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(postCall[0]).toBe(`/api/homes/${HOME}/kb/folders`);
    expect(JSON.parse(postCall[1].body as string)).toEqual({ name: "New folder", parentId: null });
  });

  it("throws on HTTP error", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [] }) })
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await expect(store.createFolder({ name: "x" })).rejects.toThrow("HTTP 404");
  });
});

describe("kbStore — updateFolder", () => {
  it("PUTs to /api/homes/{homeId}/kb/folders/{id} and refreshes", async () => {
    const folder = makeFolder();
    const renamed = makeFolder({ name: "Renamed" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [folder] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [renamed] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.updateFolder("f1", { name: "Renamed" });
    await tick();
    expect(store.folders[0].name).toBe("Renamed");
    const [, putCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(putCall[0]).toBe(`/api/homes/${HOME}/kb/folders/f1`);
    expect(JSON.parse(putCall[1].body as string)).toEqual({ name: "Renamed" });
  });

  it("sends an explicit null parentId when moving to root", async () => {
    const folder = makeFolder({ parentId: "parent1" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [folder] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [{ ...folder, parentId: null }] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.updateFolder("f1", { parentId: null });
    await tick();
    const [, putCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(JSON.parse(putCall[1].body as string)).toEqual({ parentId: null });
  });

  it("throws on HTTP error", async () => {
    const folder = makeFolder();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [folder] }) })
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await expect(store.updateFolder("f1", { name: "x" })).rejects.toThrow("HTTP 404");
  });
});

describe("kbStore — deleteFolder", () => {
  it("DELETEs /api/homes/{homeId}/kb/folders/{id} and refreshes", async () => {
    const folder = makeFolder();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [folder] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [], folders: [] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.deleteFolder("f1");
    await tick();
    expect(store.folders.length).toBe(0);
    const [, delCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(delCall[0]).toBe(`/api/homes/${HOME}/kb/folders/f1`);
    expect(delCall[1].method).toBe("DELETE");
  });
});

describe("kbStore — createEntry with folderId", () => {
  it("includes folderId in the POST body only when provided", async () => {
    const created = makeEntry({ id: "e2", folderId: "f1" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.createEntry({ title: "New entry", content: "", folderId: "f1" });
    const [, postCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(JSON.parse(postCall[1].body as string)).toEqual({ title: "New entry", content: "", folderId: "f1" });
  });
});

describe("kbStore — updateEntry with folderId", () => {
  it("includes folderId in the PUT body when provided", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [{ ...entry, folderId: "f1" }] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore(getHomeId);
    await tick();
    await store.updateEntry("e1", { folderId: "f1" });
    await tick();
    const [, putCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(JSON.parse(putCall[1].body as string)).toEqual({ folderId: "f1" });
  });
});

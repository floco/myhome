import { describe, it, expect, afterEach, vi } from "vitest";
import { createContactsStore } from "../src/lib/contactsStore.svelte";
import type { Contact } from "../src/lib/contactsStore.svelte";

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

function makeContact(overrides: Partial<Contact> = {}): Contact {
  return {
    id: "c1", name: "Metro Plumbing", companyName: null, typeId: "ctype-supplier",
    phone: null, email: null, address: null, website: null, notes: "",
    ...overrides,
  };
}

const emptyDoc = { version: 1, contacts: [] };

describe("contactsStore — init", () => {
  it("loads contacts from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, contacts: [makeContact()] }));
    const store = createContactsStore(getHomeId);
    await tick();
    expect(store.contacts.length).toBe(1);
    expect(store.contacts[0].id).toBe("c1");
    expect(store.loaded).toBe(true);
  });

  it("marks loaded on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("net fail")));
    const store = createContactsStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("net fail");
  });

  it("does not fetch when no homeId provided", async () => {
    const fetchFn = vi.fn();
    vi.stubGlobal("fetch", fetchFn);
    const store = createContactsStore();
    await tick();
    expect(fetchFn).not.toHaveBeenCalled();
    expect(store.loaded).toBe(true);
  });
});

describe("contactsStore — createContact", () => {
  it("posts to /api/homes/{homeId}/contacts and refreshes", async () => {
    const created = makeContact({ id: "c2", name: "New Contact" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, contacts: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createContactsStore(getHomeId);
    await tick();
    await store.createContact({ name: "New Contact", companyName: null, typeId: "ctype-supplier", phone: null, email: null, address: null, website: null, notes: "" });
    await tick();
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/contacts`);
    expect(fetchFn.mock.calls[1][1].method).toBe("POST");
    expect(store.contacts.length).toBe(1);
  });
});

describe("contactsStore — deleteContact", () => {
  it("calls DELETE /api/homes/{homeId}/contacts/{id}", async () => {
    const fetchFn = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createContactsStore(getHomeId);
    await tick();
    await store.deleteContact("c1");
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/contacts/c1`);
    expect(fetchFn.mock.calls[1][1].method).toBe("DELETE");
  });
});

describe("contactsStore — getUsage", () => {
  it("fetches usage references for a contact", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ references: [{ module: "works", id: "w1", label: "Fix sink" }] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createContactsStore(getHomeId);
    await tick();
    const refs = await store.getUsage("c1");
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/contacts/c1/usage`);
    expect(refs).toEqual([{ module: "works", id: "w1", label: "Fix sink" }]);
  });
});

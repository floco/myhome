import { describe, it, expect, afterEach, vi } from "vitest";
import { createPropertiesStore } from "../src/lib/propertiesStore.svelte";
import type { Property } from "../src/lib/propertiesStore.svelte";

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

function makeProperty(overrides: Partial<Property> = {}): Property {
  return {
    id: "p1", name: "Casa da Rua das Flores", emoji: "🏠", type: "house", status: "watching",
    locationId: null, address: "", price: null, landSize: null, builtSize: null,
    bedrooms: null, bathrooms: null, listingUrl: null, contact: "",
    pros: [], cons: [], notes: "", attachments: [],
    ...overrides,
  };
}

const emptyDoc = { version: 1, properties: [] };

describe("propertiesStore — init", () => {
  it("loads properties from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, properties: [makeProperty()] }));
    const store = createPropertiesStore(getHomeId);
    await tick();
    expect(store.properties.length).toBe(1);
    expect(store.properties[0].id).toBe("p1");
    expect(store.loaded).toBe(true);
  });

  it("marks loaded on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("net fail")));
    const store = createPropertiesStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("net fail");
  });

  it("does not fetch when no homeId provided", async () => {
    const fetchFn = vi.fn();
    vi.stubGlobal("fetch", fetchFn);
    const store = createPropertiesStore();
    await tick();
    expect(fetchFn).not.toHaveBeenCalled();
    expect(store.loaded).toBe(true);
  });
});

describe("propertiesStore — createProperty", () => {
  it("posts to /api/homes/{homeId}/properties and refreshes", async () => {
    const created = makeProperty({ id: "p2", name: "Terreno Norte", type: "land" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, properties: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createPropertiesStore(getHomeId);
    await tick();
    await store.createProperty({
      name: "Terreno Norte", emoji: "🏠", type: "land", status: "watching",
      locationId: null, address: "", price: null, landSize: null, builtSize: null,
      bedrooms: null, bathrooms: null, listingUrl: null, contact: "", pros: [], cons: [], notes: "",
    });
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/properties`);
    expect(fetchFn.mock.calls[1][1].method).toBe("POST");
    expect(store.properties.length).toBe(1);
  });
});

describe("propertiesStore — updateProperty", () => {
  it("calls PUT /api/homes/{homeId}/properties/{id}", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createPropertiesStore(getHomeId);
    await tick();
    await store.updateProperty("p1", { status: "visited" });
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/properties/p1`);
    expect(fetchFn.mock.calls[1][1].method).toBe("PUT");
  });
});

describe("propertiesStore — deleteProperty", () => {
  it("calls DELETE /api/homes/{homeId}/properties/{id}", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createPropertiesStore(getHomeId);
    await tick();
    await store.deleteProperty("p1");
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/properties/p1`);
    expect(fetchFn.mock.calls[1][1].method).toBe("DELETE");
  });
});

describe("propertiesStore — uploadAttachment", () => {
  it("POSTs FormData to /api/homes/{homeId}/properties/{id}/attachments", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({ filename: "listing.pdf" }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createPropertiesStore(getHomeId);
    await tick();
    const file = new File(["%PDF"], "listing.pdf", { type: "application/pdf" });
    const filename = await store.uploadAttachment("p1", file);
    expect(fetchFn.mock.calls[1][0]).toBe(`/api/homes/${HOME}/properties/p1/attachments`);
    expect(filename).toBe("listing.pdf");
  });
});

import { describe, it, expect, afterEach, vi } from "vitest";
import { createInventoryStore } from "../src/lib/inventoryStore.svelte";
import type { InventoryItem } from "../src/lib/inventoryStore.svelte";

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

function makeItem(overrides: Partial<InventoryItem> = {}): InventoryItem {
  return {
    id: "i1",
    name: "TV",
    emoji: "📺",
    category: "Electronics",
    brand: null,
    model: null,
    serialNumber: null,
    purchaseDate: null,
    purchasePrice: 1200,
    warrantyExpiryDate: null,
    notes: "",
    attachments: [],
    placement: null,
    ...overrides,
  };
}

const emptyDoc = { version: 1, items: [] };

describe("inventoryStore — init", () => {
  it("loads items from API", async () => {
    const doc = { version: 1, items: [makeItem()] };
    vi.stubGlobal("fetch", makeFetch(200, doc));
    const store = createInventoryStore();
    await tick();
    expect(store.items.length).toBe(1);
    expect(store.items[0].id).toBe("i1");
    expect(store.loaded).toBe(true);
  });

  it("marks loaded on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("net fail")));
    const store = createInventoryStore();
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("net fail");
  });
});

describe("inventoryStore — warrantyStatus", () => {
  it("returns ok when no warrantyExpiryDate", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createInventoryStore();
    await tick();
    expect(store.warrantyStatus(makeItem({ warrantyExpiryDate: null }))).toBe("ok");
  });

  it("returns ok when expiry more than 30 days away", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createInventoryStore();
    await tick();
    const future = new Date(Date.now() + 31 * 86400 * 1000).toISOString().slice(0, 10);
    expect(store.warrantyStatus(makeItem({ warrantyExpiryDate: future }))).toBe("ok");
  });

  it("returns soon when expiry 30 days or less away but not past", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createInventoryStore();
    await tick();
    const soon = new Date(Date.now() + 15 * 86400 * 1000).toISOString().slice(0, 10);
    expect(store.warrantyStatus(makeItem({ warrantyExpiryDate: soon }))).toBe("soon");
  });

  it("returns soon at exactly 30 days", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createInventoryStore();
    await tick();
    const exactly30 = new Date(Date.now() + 30 * 86400 * 1000).toISOString().slice(0, 10);
    expect(store.warrantyStatus(makeItem({ warrantyExpiryDate: exactly30 }))).toBe("soon");
  });

  it("returns expired when expiry is in the past", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createInventoryStore();
    await tick();
    const past = new Date(Date.now() - 86400 * 1000).toISOString().slice(0, 10);
    expect(store.warrantyStatus(makeItem({ warrantyExpiryDate: past }))).toBe("expired");
  });
});

describe("inventoryStore — placedItems / unplacedItems", () => {
  it("splits by placement presence", async () => {
    const placed = makeItem({ id: "p1", placement: { floorId: "f1", roomId: null, position: { x: 1, y: 2 } } });
    const unplaced = makeItem({ id: "u1", placement: null });
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, items: [placed, unplaced] }));
    const store = createInventoryStore();
    await tick();
    expect(store.placedItems().length).toBe(1);
    expect(store.placedItems()[0].id).toBe("p1");
    expect(store.unplacedItems().length).toBe(1);
    expect(store.unplacedItems()[0].id).toBe("u1");
  });

  it("returns empty arrays when all items are unplaced", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, items: [makeItem()] }));
    const store = createInventoryStore();
    await tick();
    expect(store.placedItems()).toEqual([]);
    expect(store.unplacedItems().length).toBe(1);
  });
});

describe("inventoryStore — uploadAttachment", () => {
  it("posts to /attachments and returns filename", async () => {
    const updatedDoc = { version: 1, items: [makeItem({ attachments: ["invoice.pdf"] })] };
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
        .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({ filename: "invoice.pdf" }) })
        .mockResolvedValueOnce({ ok: true, status: 200, json: async () => updatedDoc }),
    );
    const store = createInventoryStore();
    await tick();
    const file = new File(["%PDF-1.4"], "invoice.pdf", { type: "application/pdf" });
    const filename = await store.uploadAttachment("i1", file);
    await tick();
    expect(filename).toBe("invoice.pdf");
    expect(store.items[0].attachments).toContain("invoice.pdf");
  });

  it("throws on HTTP error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
        .mockResolvedValueOnce({ ok: false, status: 400, json: async () => ({}) }),
    );
    const store = createInventoryStore();
    await tick();
    await expect(
      store.uploadAttachment("i1", new File(["img"], "img.png")),
    ).rejects.toThrow("HTTP 400");
  });
});

describe("inventoryStore — deleteAttachment", () => {
  it("calls DELETE and removes filename from store", async () => {
    const initDoc = { version: 1, items: [makeItem({ attachments: ["invoice.pdf"] })] };
    const clearedDoc = { version: 1, items: [makeItem({ attachments: [] })] };
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce({ ok: true, status: 200, json: async () => initDoc })
        .mockResolvedValueOnce({ ok: true, status: 204, json: async () => ({}) })
        .mockResolvedValueOnce({ ok: true, status: 200, json: async () => clearedDoc }),
    );
    const store = createInventoryStore();
    await tick();
    expect(store.items[0].attachments).toContain("invoice.pdf");
    await store.deleteAttachment("i1", "invoice.pdf");
    await tick();
    expect(store.items[0].attachments).not.toContain("invoice.pdf");
  });

  it("throws on HTTP error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
        .mockResolvedValueOnce({ ok: false, status: 404, json: async () => ({}) }),
    );
    const store = createInventoryStore();
    await tick();
    await expect(store.deleteAttachment("i1", "invoice.pdf")).rejects.toThrow("HTTP 404");
  });
});

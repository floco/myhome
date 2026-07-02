import { describe, it, expect, afterEach, vi } from "vitest";
import { createConsumableStore, stockStatus, barFill } from "../src/lib/consumableStore.svelte";

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

const emptyDoc = { version: 1, consumables: [], transactions: [] };

const sampleDoc = {
  version: 1,
  consumables: [
    {
      id: "c1",
      name: "AA Batteries",
      emoji: "🔋",
      unit: "count",
      quantity: 6.0,
      minQuantity: 4.0,
      categoryId: null,
      description: "",
      placement: null,
    },
    {
      id: "c2",
      name: "Dish Soap",
      emoji: "🧴",
      unit: "mL",
      quantity: 0.0,
      minQuantity: 100.0,
      categoryId: null,
      description: "",
      placement: null,
    },
  ],
  transactions: [
    {
      id: "t1",
      consumableId: "c1",
      delta: 6.0,
      quantityAfter: 6.0,
      note: "",
      timestamp: "2026-07-02T10:00:00Z",
    },
  ],
};

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

describe("consumableStore — init", () => {
  it("loads consumables and transactions from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createConsumableStore();
    await tick();
    expect(store.consumables.length).toBe(2);
    expect(store.transactions.length).toBe(1);
    expect(store.loaded).toBe(true);
  });

  it("marks loaded on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network")));
    const store = createConsumableStore();
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("Network");
  });
});

describe("stockStatus", () => {
  it("returns empty when quantity is 0", () => {
    const c = {
      id: "x",
      name: "",
      emoji: "",
      unit: "count",
      quantity: 0,
      minQuantity: 5,
      categoryId: null,
      description: "",
      placement: null,
    };
    expect(stockStatus(c)).toBe("empty");
  });

  it("returns low when quantity <= minQuantity", () => {
    const c = {
      id: "x",
      name: "",
      emoji: "",
      unit: "count",
      quantity: 3,
      minQuantity: 5,
      categoryId: null,
      description: "",
      placement: null,
    };
    expect(stockStatus(c)).toBe("low");
  });

  it("returns ok when quantity > minQuantity", () => {
    const c = {
      id: "x",
      name: "",
      emoji: "",
      unit: "count",
      quantity: 10,
      minQuantity: 5,
      categoryId: null,
      description: "",
      placement: null,
    };
    expect(stockStatus(c)).toBe("ok");
  });
});

describe("barFill", () => {
  it("returns 1/3 fill at minQuantity (threshold mark)", () => {
    const c = {
      id: "x",
      name: "",
      emoji: "",
      unit: "count",
      quantity: 5,
      minQuantity: 5,
      categoryId: null,
      description: "",
      placement: null,
    };
    expect(barFill(c)).toBeCloseTo(1 / 3, 5);
  });

  it("returns 1 at 3× minQuantity", () => {
    const c = {
      id: "x",
      name: "",
      emoji: "",
      unit: "count",
      quantity: 15,
      minQuantity: 5,
      categoryId: null,
      description: "",
      placement: null,
    };
    expect(barFill(c)).toBe(1);
  });

  it("returns 0 when empty", () => {
    const c = {
      id: "x",
      name: "",
      emoji: "",
      unit: "count",
      quantity: 0,
      minQuantity: 5,
      categoryId: null,
      description: "",
      placement: null,
    };
    expect(barFill(c)).toBe(0);
  });

  it("handles zero minQuantity without NaN", () => {
    const c = {
      id: "x",
      name: "",
      emoji: "",
      unit: "count",
      quantity: 5,
      minQuantity: 0,
      categoryId: null,
      description: "",
      placement: null,
    };
    const fill = barFill(c);
    expect(isNaN(fill)).toBe(false);
    expect(fill).toBe(1);
  });
});

describe("consumableStore — updateStock", () => {
  it("calls POST /api/consumables/:id/stock and re-fetches", async () => {
    const fetchMock = makeFetch(200, sampleDoc);
    vi.stubGlobal("fetch", fetchMock);
    const store = createConsumableStore();
    await tick();
    fetchMock.mockResolvedValueOnce({ ok: true, status: 204, json: async () => ({}) });
    fetchMock.mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc });
    await store.updateStock("c1", 10.0, "restock");
    const stockCall = fetchMock.mock.calls.find((c: unknown[]) => c[0] === "/api/consumables/c1/stock");
    expect(stockCall).toBeTruthy();
    const body = JSON.parse((stockCall![1] as RequestInit).body as string);
    expect(body.quantity).toBe(10.0);
    expect(body.note).toBe("restock");
  });
});

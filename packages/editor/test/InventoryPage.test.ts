import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import InventoryPage from "../src/lib/components/InventoryPage.svelte";
import type { InventoryItem } from "../src/lib/inventoryStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeItem(overrides: Partial<InventoryItem> = {}): InventoryItem {
  return {
    id: "i1", name: "Drill", emoji: "🔧", category: "Tools", brand: null, model: null,
    serialNumber: null, purchaseDate: null, purchasePrice: 80, warrantyExpiryDate: null,
    notes: "", attachments: [], placement: null,
    ...overrides,
  };
}

function makeStore(items: InventoryItem[]) {
  return {
    items, loaded: true, loadError: null,
    createItem: vi.fn(), updateItem: vi.fn(), deleteItem: vi.fn(),
    uploadAttachment: vi.fn(), deleteAttachment: vi.fn(),
  };
}

describe("InventoryPage — category summary", () => {
  it("renders one donut segment per category and the right stat numbers", () => {
    const store = makeStore([
      makeItem({ id: "i1", category: "Tools", purchasePrice: 80 }),
      makeItem({ id: "i2", category: "Tools", purchasePrice: 20 }),
      makeItem({ id: "i3", category: "Electronics", purchasePrice: 100 }),
    ]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(InventoryPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    expect(target.querySelectorAll(".chart-card-wrap svg path")).toHaveLength(2);
    const values = Array.from(target.querySelectorAll(".stat-value")).map((el) => el.textContent);
    expect(values).toEqual(["3", "200 €"]);

    unmount(comp);
  });

  it("shows the empty-charts placeholder when there are no items", () => {
    const store = makeStore([]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(InventoryPage, { target, props: { store, floorStore: { floors: [] } } });
    flushSync();

    expect(target.querySelector(".empty-charts")).not.toBeNull();
    expect(target.querySelector(".chart-card-wrap")).toBeNull();

    unmount(comp);
  });
});

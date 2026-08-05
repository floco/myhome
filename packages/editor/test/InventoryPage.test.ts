import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import InventoryPage from "../src/lib/components/InventoryPage.svelte";
import type { InventoryItem } from "../src/lib/inventoryStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeItem(overrides: Partial<InventoryItem> = {}): InventoryItem {
  return {
    id: "i1", name: "Drill", emoji: "🔧", categoryId: "cat-tools", ownerId: null, storeId: null,
    brand: null, model: null,
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

const BASE_PROPS = {
  inventoryCategories: [] as { id: string; name: string }[],
  owners: [] as { id: string; name: string }[],
  stores: [] as { id: string; name: string }[],
  oncreatecategory: vi.fn(),
  oncreateowner: vi.fn(),
  oncreatestore: vi.fn(),
};

describe("InventoryPage — category summary", () => {
  it("renders one donut segment per category and the right stat numbers", () => {
    const store = makeStore([
      makeItem({ id: "i1", categoryId: "cat-tools", purchasePrice: 80 }),
      makeItem({ id: "i2", categoryId: "cat-tools", purchasePrice: 20 }),
      makeItem({ id: "i3", categoryId: "cat-electronics", purchasePrice: 100 }),
    ]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(InventoryPage, {
      target,
      props: {
        store, floorStore: { floors: [] }, ...BASE_PROPS,
        inventoryCategories: [
          { id: "cat-tools", name: "Tools" },
          { id: "cat-electronics", name: "Electronics" },
        ],
      },
    });
    flushSync();

    expect(target.querySelectorAll(".chart-card-wrap svg path")).toHaveLength(2);
    const values = Array.from(target.querySelectorAll(".ui-stat-value")).map((el) => el.textContent);
    expect(values).toEqual(["3", "200 €", "0"]);

    unmount(comp);
  });

  it("gives every category a distinct color, even with more than 8 categories", () => {
    const items = Array.from({ length: 12 }, (_, i) =>
      makeItem({ id: `i${i}`, categoryId: `cat-${i}`, purchasePrice: 10 }),
    );
    const store = makeStore(items);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(InventoryPage, {
      target,
      props: {
        store, floorStore: { floors: [] }, ...BASE_PROPS,
        inventoryCategories: Array.from({ length: 12 }, (_, i) => ({ id: `cat-${i}`, name: `Category ${i}` })),
      },
    });
    flushSync();

    const fills = Array.from(target.querySelectorAll(".chart-card-wrap svg path")).map((p) =>
      p.getAttribute("fill"),
    );
    expect(fills).toHaveLength(12);
    expect(new Set(fills).size).toBe(12);

    unmount(comp);
  });

  it("shows the empty-charts placeholder when there are no items", () => {
    const store = makeStore([]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(InventoryPage, { target, props: { store, floorStore: { floors: [] }, ...BASE_PROPS } });
    flushSync();

    expect(target.querySelector(".empty-charts")).not.toBeNull();
    expect(target.querySelector(".chart-card-wrap")).toBeNull();

    unmount(comp);
  });
});

describe("InventoryPage — owner/store filters and columns", () => {
  it("filters by owner and shows the resolved owner name in the table", () => {
    const store = makeStore([
      makeItem({ id: "i1", name: "Drill", ownerId: "o1" }),
      makeItem({ id: "i2", name: "Saw", ownerId: "o2" }),
    ]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(InventoryPage, {
      target,
      props: {
        store, floorStore: { floors: [] }, ...BASE_PROPS,
        owners: [{ id: "o1", name: "Alice" }, { id: "o2", name: "Bob" }],
      },
    });
    flushSync();
    expect(target.textContent).toContain("Alice");
    expect(target.textContent).toContain("Bob");
    const ownerSelects = Array.from(target.querySelectorAll("select")).filter((s) =>
      Array.from(s.querySelectorAll("option")).some((o) => o.textContent === "Alice"),
    );
    expect(ownerSelects.length).toBe(1);
    unmount(app);
  });
});

describe("InventoryPage — responsive columns", () => {
  it("hides category/owner/store/room at tablet and purchased/cost/warranty at mobile", () => {
    const store = makeStore([makeItem()]);
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(InventoryPage, { target, props: { store, floorStore: { floors: [] }, ...BASE_PROPS } });
    flushSync();

    const headers = target.querySelectorAll("thead th");
    // emoji, name, category, owner, store, room, purchased, cost, warranty
    for (const i of [2, 3, 4, 5]) {
      expect(headers[i].classList.contains("col-hide-tablet")).toBe(true);
    }
    for (const i of [6, 7, 8]) {
      expect(headers[i].classList.contains("col-hide-mobile")).toBe(true);
    }
    expect(headers[1].classList.contains("col-hide-tablet")).toBe(false); // name always visible
    expect(headers[1].classList.contains("col-hide-mobile")).toBe(false);

    unmount(comp);
  });
});

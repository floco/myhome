import { describe, it, expect } from "vitest";
import { buildSearchIndex, filterResults, MODULE_ORDER } from "../src/lib/searchIndex";

function makeStores(overrides: Partial<Parameters<typeof buildSearchIndex>[0]> = {}) {
  return {
    choreStore: { chores: [] },
    inventoryStore: { items: [] },
    consumableStore: { consumables: [] },
    worksStore: { works: [] },
    costsStore: { entries: [] },
    kbStore: { entries: [] },
    settingsStore: { costCategories: [], workCategories: [], suppliers: [] },
    ...overrides,
  };
}

describe("buildSearchIndex", () => {
  it("maps a chore into a SearchResult using its own emoji and next due date", () => {
    const stores = makeStores({
      choreStore: {
        chores: [
          { id: "c1", name: "Sweep kitchen", emoji: "🧹", description: "Daily sweep", nextDueDate: "2026-08-01T12:00:00.000Z" } as any,
        ],
      },
    });
    const index = buildSearchIndex(stores);
    expect(index).toEqual([
      {
        module: "chores",
        id: "c1",
        icon: "🧹",
        title: "Sweep kitchen",
        subtitle: "Aug 1, 2026",
        searchText: "sweep kitchen daily sweep",
        titleText: "sweep kitchen",
      },
    ]);
  });

  it("maps an inventory item using its category as subtitle", () => {
    const stores = makeStores({
      inventoryStore: {
        items: [
          { id: "i1", name: "Samsung TV", emoji: "📺", category: "Electronics", brand: "Samsung", model: "QE65", serialNumber: "XYZ", notes: "Living room" } as any,
        ],
      },
    });
    const index = buildSearchIndex(stores);
    expect(index[0]).toEqual({
      module: "inventory",
      id: "i1",
      icon: "📺",
      title: "Samsung TV",
      subtitle: "Electronics",
      searchText: "samsung tv samsung qe65 xyz living room",
      titleText: "samsung tv",
    });
  });

  it("falls back to a default subtitle when an inventory item has no category", () => {
    const stores = makeStores({
      inventoryStore: { items: [{ id: "i1", name: "Ladder", emoji: "🪜", category: "", brand: null, model: null, serialNumber: null, notes: "" } as any] },
    });
    const index = buildSearchIndex(stores);
    expect(index[0].subtitle).toBe("Inventory");
  });

  it("maps a consumable using quantity and unit as subtitle", () => {
    const stores = makeStores({
      consumableStore: { consumables: [{ id: "co1", name: "Dish Soap", emoji: "🧴", unit: "mL", quantity: 250, description: "Under the sink" } as any] },
    });
    const index = buildSearchIndex(stores);
    expect(index[0]).toEqual({
      module: "consumables",
      id: "co1",
      icon: "🧴",
      title: "Dish Soap",
      subtitle: "250 mL",
      searchText: "dish soap under the sink",
      titleText: "dish soap",
    });
  });

  it("maps a work using a humanized status and date as subtitle, with its category emoji", () => {
    const stores = makeStores({
      worksStore: { works: [{ id: "w1", title: "Fix roof leak", description: "Patch near chimney", notes: "", status: "in_progress", categoryId: "wcat-roofing", date: "2026-06-10T12:00:00.000Z" } as any] },
      settingsStore: { costCategories: [], suppliers: [], workCategories: [{ id: "wcat-roofing", name: "Roofing", emoji: "🏠" }] },
    });
    const index = buildSearchIndex(stores);
    expect(index[0]).toEqual({
      module: "works",
      id: "w1",
      icon: "🏠",
      title: "Fix roof leak",
      subtitle: "In progress · Jun 10, 2026",
      searchText: "fix roof leak patch near chimney",
      titleText: "fix roof leak",
    });
  });

  it("falls back to a default icon when a work has no matching category", () => {
    const stores = makeStores({
      worksStore: { works: [{ id: "w1", title: "Fix roof leak", description: "", notes: "", status: "planned", categoryId: null, date: "2026-06-10T12:00:00.000Z" } as any] },
    });
    const index = buildSearchIndex(stores);
    expect(index[0].icon).toBe("🔧");
  });

  it("maps a cost entry resolving category and supplier names, with the category emoji", () => {
    const stores = makeStores({
      costsStore: { entries: [{ id: "ce1", categoryId: "cat-electricity", supplierId: "sup1", notes: "Winter bill", totalAmount: 120.5 } as any] },
      settingsStore: {
        costCategories: [{ id: "cat-electricity", name: "Electricity", emoji: "💡", unit: "kWh", color: "#4466cc" }],
        workCategories: [],
        suppliers: [{ id: "sup1", name: "PowerCo" }],
      },
    });
    const index = buildSearchIndex(stores);
    expect(index[0]).toEqual({
      module: "costs",
      id: "ce1",
      icon: "💡",
      title: "Electricity",
      subtitle: "120.5 €",
      searchText: "electricity powerco winter bill",
      titleText: "electricity",
    });
  });

  it("maps a KB entry using the fixed Knowledge Base icon and subtitle", () => {
    const stores = makeStores({
      kbStore: { entries: [{ id: "kb1", title: "Boiler manual", content: "Reset procedure is..." } as any] },
    });
    const index = buildSearchIndex(stores);
    expect(index[0]).toEqual({
      module: "kb",
      id: "kb1",
      icon: "📄",
      title: "Boiler manual",
      subtitle: "Knowledge Base",
      searchText: "boiler manual reset procedure is...",
      titleText: "boiler manual",
    });
  });
});

describe("filterResults", () => {
  const index = [
    { module: "chores" as const, id: "c1", icon: "🧹", title: "Sweep kitchen", subtitle: "", searchText: "sweep kitchen daily sweep", titleText: "sweep kitchen" },
    { module: "chores" as const, id: "c2", icon: "🪟", title: "Clean windows", subtitle: "", searchText: "clean windows sweep up glass dust", titleText: "clean windows" },
    { module: "inventory" as const, id: "i1", icon: "📺", title: "Samsung TV", subtitle: "", searchText: "samsung tv", titleText: "samsung tv" },
  ];

  it("returns nothing for queries shorter than 2 characters", () => {
    expect(filterResults(index, "s")).toEqual([]);
    expect(filterResults(index, "")).toEqual([]);
  });

  it("matches case-insensitively against searchText", () => {
    const results = filterResults(index, "SAMSUNG");
    expect(results.map((r) => r.id)).toEqual(["i1"]);
  });

  it("ranks title matches above body-only matches within the same module", () => {
    // "sweep" matches c1's title and c2's body text only
    const results = filterResults(index, "sweep");
    expect(results.map((r) => r.id)).toEqual(["c1", "c2"]);
  });

  it("groups results by module in the fixed MODULE_ORDER", () => {
    const results2 = filterResults(index, "sa");
    expect(results2.map((r) => r.module)).toEqual(["inventory"]);
    expect(MODULE_ORDER).toEqual(["chores", "inventory", "consumables", "works", "costs", "kb"]);
  });

  it("caps results at the given limit", () => {
    const big = Array.from({ length: 25 }, (_, i) => ({
      module: "chores" as const, id: `c${i}`, icon: "🧹", title: `Sweep ${i}`, subtitle: "", searchText: `sweep ${i}`, titleText: `sweep ${i}`,
    }));
    expect(filterResults(big, "sweep", 20).length).toBe(20);
  });
});

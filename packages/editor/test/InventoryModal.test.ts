import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import InventoryModal from "../src/lib/components/InventoryModal.svelte";
import type { InventoryItem } from "../src/lib/inventoryStore.svelte";

afterEach(() => { document.body.innerHTML = ""; });

function makeItem(overrides: Partial<InventoryItem> = {}): InventoryItem {
  return {
    id: "i1", name: "Samsung TV", emoji: "📺", category: "Electronics",
    brand: null, model: null, serialNumber: null, purchaseDate: null,
    purchasePrice: null, warrantyExpiryDate: null, notes: "", attachments: [],
    placement: null, ...overrides,
  };
}

function makeStore(item: InventoryItem | null = null) {
  return {
    items: item ? [item] : [],
    loaded: true,
    loadError: null,
    createItem: vi.fn().mockResolvedValue(undefined),
    updateItem: vi.fn().mockResolvedValue(undefined),
    deleteItem: vi.fn().mockResolvedValue(undefined),
    uploadAttachment: vi.fn().mockResolvedValue("photo.jpg"),
    deleteAttachment: vi.fn().mockResolvedValue(undefined),
    setPlacement: vi.fn().mockResolvedValue(undefined),
    warrantyStatus: vi.fn().mockReturnValue("ok"),
    placedItems: vi.fn().mockReturnValue([]),
    unplacedItems: vi.fn().mockReturnValue([]),
  };
}

describe("InventoryModal — Media tab", () => {
  it("shows Media tab (not Attachments)", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const item = makeItem();
    const store = makeStore(item);
    const app = mount(InventoryModal, {
      target,
      props: { item, store, inventoryCategories: [], onclose: vi.fn() },
    });
    flushSync();
    const tabs = Array.from(target.querySelectorAll(".tab")).map(t => t.textContent?.trim());
    expect(tabs.some(t => t?.includes("Media"))).toBe(true);
    expect(tabs.every(t => !t?.includes("Attachments"))).toBe(true);
    unmount(app);
  });

  it("Media tab is disabled when creating (item=null)", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(InventoryModal, {
      target,
      props: { item: null, store, inventoryCategories: [], onclose: vi.fn() },
    });
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement;
    expect(mediaTab.disabled).toBe(true);
    unmount(app);
  });

  it("clicking Media tab renders drop-zone", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const item = makeItem({ attachments: ["photo.jpg"] });
    const store = makeStore(item);
    const app = mount(InventoryModal, {
      target,
      props: { item, store, inventoryCategories: [], onclose: vi.fn() },
    });
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement;
    mediaTab.click();
    flushSync();
    expect(target.querySelector(".drop-zone") || target.querySelector(".media-grid")).not.toBeNull();
    unmount(app);
  });

  it("Media tab badge shows attachment count", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const item = makeItem({ attachments: ["photo.jpg", "doc.pdf"] });
    const store = makeStore(item);
    const app = mount(InventoryModal, {
      target,
      props: { item, store, inventoryCategories: [], onclose: vi.fn() },
    });
    flushSync();
    const mediaTab = Array.from(target.querySelectorAll(".tab"))
      .find(t => t.textContent?.includes("Media")) as HTMLButtonElement;
    expect(mediaTab.textContent).toContain("2");
    unmount(app);
  });
});

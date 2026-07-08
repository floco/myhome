import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsCategories from "../src/lib/components/settings/SettingsCategories.svelte";

function makeStore() {
  return {
    costCategories: [{ id: "c1", name: "Electricity", emoji: "⚡", unit: "kWh", color: "#4466cc" }],
    inventoryCategories: [{ id: "i1", name: "Tools" }],
    workCategories: [{ id: "w1", name: "Plumbing", emoji: "🔧" }],
    suppliers: [{ id: "s1", name: "Acme Co" }],
    consumableUnits: ["tablets"],
    consumableCategories: [{ id: "cc1", name: "Cleaning", emoji: "🧼" }],
    updateCostCategories: vi.fn(),
    updateInventoryCategories: vi.fn(),
    updateWorkCategories: vi.fn(),
    updateSuppliers: vi.fn(),
    updateConsumableUnits: vi.fn(),
    updateConsumableCategories: vi.fn(),
  };
}

describe("SettingsCategories", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("shows the Cost categories tab by default", () => {
    const app = mount(SettingsCategories, { target, props: { store: makeStore() } });
    flushSync();
    expect(target.textContent).toContain("Cost categories");
    expect(target.textContent).toContain("Electricity");
    expect(target.textContent).not.toContain("Tools");
    unmount(app);
  });

  it("switches to the Inventory categories tab", () => {
    const app = mount(SettingsCategories, { target, props: { store: makeStore() } });
    flushSync();
    const tab = [...target.querySelectorAll(".tab")].find((b) => b.textContent === "Inventory categories")!;
    (tab as HTMLButtonElement).click();
    flushSync();
    expect(target.textContent).toContain("Tools");
    expect(target.textContent).not.toContain("Electricity");
    unmount(app);
  });

  it("adding a cost category calls store.updateCostCategories", async () => {
    const store = makeStore();
    const app = mount(SettingsCategories, { target, props: { store } });
    flushSync();
    const addBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("＋ Add"))!;
    addBtn.click();
    flushSync();
    const nameInput = target.querySelector('input[placeholder="Name *"]') as HTMLInputElement;
    nameInput.value = "Water";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const okBtn = target.querySelector(".icon-action.ok") as HTMLButtonElement;
    okBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(store.updateCostCategories).toHaveBeenCalledWith(
      expect.arrayContaining([expect.objectContaining({ name: "Water" })]),
    );
    unmount(app);
  });

  it("switches to the Consumables tab and shows units and categories", () => {
    const app = mount(SettingsCategories, { target, props: { store: makeStore() } });
    flushSync();
    const tab = [...target.querySelectorAll(".tab")].find((b) => b.textContent === "Consumables")!;
    (tab as HTMLButtonElement).click();
    flushSync();
    expect(target.textContent).toContain("tablets");
    expect(target.textContent).toContain("Cleaning");
    unmount(app);
  });
});

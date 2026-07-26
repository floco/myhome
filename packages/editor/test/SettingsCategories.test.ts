import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsCategories from "../src/lib/components/settings/SettingsCategories.svelte";

function makeStore() {
  return {
    costCategories: [{ id: "c1", name: "Electricity", emoji: "⚡", unit: "kWh", color: "#4466cc" }],
    inventoryCategories: [{ id: "i1", name: "Tools" }],
    workCategories: [{ id: "w1", name: "Plumbing", emoji: "🔧" }],
    contactTypes: [{ id: "t1", name: "Supplier" }],
    consumableUnits: ["tablets"],
    consumableCategories: [{ id: "cc1", name: "Cleaning", emoji: "🧼" }],
    insuranceCategories: [{ id: "icat-home", name: "Home", emoji: "🏠" }],
    updateCostCategories: vi.fn(),
    updateInventoryCategories: vi.fn(),
    updateWorkCategories: vi.fn(),
    updateContactTypes: vi.fn(),
    updateConsumableUnits: vi.fn(),
    updateConsumableCategories: vi.fn(),
    updateInsuranceCategories: vi.fn(),
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

  it("switches to the Contact Types tab and shows contact types", () => {
    const app = mount(SettingsCategories, { target, props: { store: makeStore() } });
    flushSync();
    const tab = [...target.querySelectorAll(".tab")].find((b) => b.textContent === "Contact Types")!;
    (tab as HTMLButtonElement).click();
    flushSync();
    expect(target.textContent).toContain("Supplier");
    unmount(app);
  });

  it("adding a contact type calls store.updateContactTypes", async () => {
    const store = makeStore();
    const app = mount(SettingsCategories, { target, props: { store } });
    flushSync();
    const tab = [...target.querySelectorAll(".tab")].find((b) => b.textContent === "Contact Types")!;
    (tab as HTMLButtonElement).click();
    flushSync();
    const addBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("＋ Add"))!;
    addBtn.click();
    flushSync();
    const nameInput = target.querySelector('input[placeholder="Name *"]') as HTMLInputElement;
    nameInput.value = "Agent";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const okBtn = target.querySelector(".icon-action.ok") as HTMLButtonElement;
    okBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(store.updateContactTypes).toHaveBeenCalledWith(
      expect.arrayContaining([expect.objectContaining({ name: "Agent" })]),
    );
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

  it("switches to the Insurance categories tab and shows insurance categories", () => {
    const app = mount(SettingsCategories, { target, props: { store: makeStore() } });
    flushSync();
    const tab = [...target.querySelectorAll(".tab")].find((b) => b.textContent === "Insurance categories")!;
    (tab as HTMLButtonElement).click();
    flushSync();
    expect(target.textContent).toContain("Home");
    unmount(app);
  });

  it("adding an insurance category calls store.updateInsuranceCategories", async () => {
    const store = makeStore();
    const app = mount(SettingsCategories, { target, props: { store } });
    flushSync();
    const tab = [...target.querySelectorAll(".tab")].find((b) => b.textContent === "Insurance categories")!;
    (tab as HTMLButtonElement).click();
    flushSync();
    const addBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("＋ Add"))!;
    addBtn.click();
    flushSync();
    const nameInput = target.querySelector('input[placeholder="Name *"]') as HTMLInputElement;
    nameInput.value = "Pet";
    nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const okBtn = target.querySelector(".icon-action.ok") as HTMLButtonElement;
    okBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(store.updateInsuranceCategories).toHaveBeenCalledWith(
      expect.arrayContaining([expect.objectContaining({ name: "Pet" })]),
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

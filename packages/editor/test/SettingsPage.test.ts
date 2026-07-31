import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsPage from "../src/lib/components/SettingsPage.svelte";
import { homesStore } from "../src/lib/homesStore.svelte";

function makeStore() {
  return {
    costCategories: [],
    inventoryCategories: [],
    workCategories: [],
    contactTypes: [],
    consumableUnits: [],
    consumableCategories: [],
    notificationSettings: {
      enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
      haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
    },
    loaded: true,
    updateCostCategories: vi.fn(),
    updateInventoryCategories: vi.fn(),
    updateWorkCategories: vi.fn(),
    updateSuppliers: vi.fn(),
    updateConsumableUnits: vi.fn(),
    updateConsumableCategories: vi.fn(),
    updateNotificationSettings: vi.fn(),
  };
}

function makeAuthStore(role: "admin" | "normal" | "ro" = "admin") {
  return {
    user: { id: "u1", username: "admin", role },
    checking: false,
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
  };
}

describe("SettingsPage — nav shell", () => {
  let target: HTMLDivElement;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
    homesStore._reset();
  });

  it("shows the General panel by default", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore(), importFromDonetick: vi.fn(async () => 0) } });
    flushSync();
    expect(target.textContent).toContain("Home");
    expect(target.textContent).toContain("Modules");
    unmount(app);
  });

  it("shows all 9 groups for an admin, including Localization, Integrations, Activity Log, and About", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin"), importFromDonetick: vi.fn(async () => 0) } });
    flushSync();
    const labels = [...target.querySelectorAll(".nav-item")].map((b) => b.textContent);
    expect(labels.some((l) => l?.includes("General"))).toBe(true);
    expect(labels.some((l) => l?.includes("Localization"))).toBe(true);
    expect(labels.some((l) => l?.includes("Categories"))).toBe(true);
    expect(labels.some((l) => l?.includes("Notifications"))).toBe(true);
    expect(labels.some((l) => l?.includes("Security & Access"))).toBe(true);
    expect(labels.some((l) => l?.includes("Integrations"))).toBe(true);
    expect(labels.some((l) => l?.includes("Backup & Restore"))).toBe(true);
    expect(labels.some((l) => l?.includes("Activity Log"))).toBe(true);
    expect(labels.some((l) => l?.includes("About"))).toBe(true);
    unmount(app);
  });

  it("places Localization immediately after General in the nav order", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin"), importFromDonetick: vi.fn(async () => 0) } });
    flushSync();
    const labels = [...target.querySelectorAll(".nav-item")].map((b) => b.textContent?.trim());
    const generalIdx = labels.findIndex((l) => l?.includes("General"));
    expect(labels[generalIdx + 1]).toContain("Localization");
    unmount(app);
  });

  it("switching to Localization via the nav shows the language and date format fields", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore(), importFromDonetick: vi.fn(async () => 0) } });
    flushSync();
    const localizationBtn = [...target.querySelectorAll<HTMLButtonElement>(".nav-item")].find((b) => b.textContent?.includes("Localization"))!;
    localizationBtn.click();
    flushSync();
    expect(target.textContent).toContain("Select your preferred language");
    expect(target.textContent).toContain("Choose how dates should be displayed throughout the application");
    unmount(app);
  });

  it("shows About for a non-admin too", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("normal"), importFromDonetick: vi.fn(async () => 0) } });
    flushSync();
    const labels = [...target.querySelectorAll(".nav-item")].map((b) => b.textContent);
    expect(labels.some((l) => l?.includes("About"))).toBe(true);
    unmount(app);
  });

  it("hides Integrations for a non-admin, but keeps Security & Access and Activity Log", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("normal"), importFromDonetick: vi.fn(async () => 0) } });
    flushSync();
    const labels = [...target.querySelectorAll(".nav-item")].map((b) => b.textContent);
    expect(labels.some((l) => l?.includes("Integrations"))).toBe(false);
    expect(labels.some((l) => l?.includes("Activity Log"))).toBe(true);
    expect(labels.some((l) => l?.includes("Security & Access"))).toBe(true);
    unmount(app);
  });

  it("switching to Categories via the nav shows the category sub-tabs", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore(), importFromDonetick: vi.fn(async () => 0) } });
    flushSync();
    const categoriesBtn = [...target.querySelectorAll<HTMLButtonElement>(".nav-item")].find((b) => b.textContent?.includes("Categories"))!;
    categoriesBtn.click();
    flushSync();
    expect(target.textContent).toContain("Cost categories");
    expect(target.textContent).not.toContain("Home");
    unmount(app);
  });

  it("the mobile dropdown lists the same groups as the sidebar", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin"), importFromDonetick: vi.fn(async () => 0) } });
    flushSync();
    const sidebarCount = target.querySelectorAll(".nav-item").length;
    const dropdownCount = target.querySelectorAll(".nav-select option").length;
    expect(dropdownCount).toBe(sidebarCount);
    unmount(app);
  });

  it("threads reloadAllStores through to the General panel's module reset flow", async () => {
    homesStore.homes.push({ id: "h1", name: "Test Home", type: "existing", enabledModules: ["home", "plan", "chores"], createdAt: "" });
    homesStore.setActiveHomeId("h1");
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, status: 204, json: async () => ({}) });
    const reloadAllStores = vi.fn();
    const app = mount(SettingsPage, {
      target,
      props: { store: makeStore(), authStore: makeAuthStore(), importFromDonetick: vi.fn(async () => 0), reloadAllStores },
    });
    flushSync();
    const choresRow = [...target.querySelectorAll(".module-row")].find((r) => r.textContent?.includes("Chores"))!;
    const resetBtn = [...choresRow.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Reset")!;
    resetBtn.click();
    flushSync();
    const confirmBtn = [...target.querySelectorAll(".ui-modal button")].find((b) => b.textContent?.trim() === "Reset")!;
    confirmBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(reloadAllStores).toHaveBeenCalledOnce();
    unmount(app);
  });
});

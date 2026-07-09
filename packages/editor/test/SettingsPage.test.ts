import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsPage from "../src/lib/components/SettingsPage.svelte";

function makeStore() {
  return {
    costCategories: [],
    inventoryCategories: [],
    workCategories: [],
    suppliers: [],
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
  });

  it("shows the General panel by default", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();
    expect(target.textContent).toContain("Home");
    expect(target.textContent).toContain("Modules");
    unmount(app);
  });

  it("shows all 7 groups for an admin, including Integrations and Activity Log", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    flushSync();
    const labels = [...target.querySelectorAll(".nav-item")].map((b) => b.textContent);
    expect(labels.some((l) => l?.includes("General"))).toBe(true);
    expect(labels.some((l) => l?.includes("Categories"))).toBe(true);
    expect(labels.some((l) => l?.includes("Notifications"))).toBe(true);
    expect(labels.some((l) => l?.includes("Security & Access"))).toBe(true);
    expect(labels.some((l) => l?.includes("Integrations"))).toBe(true);
    expect(labels.some((l) => l?.includes("Backup & Restore"))).toBe(true);
    expect(labels.some((l) => l?.includes("Activity Log"))).toBe(true);
    unmount(app);
  });

  it("hides Integrations for a non-admin, but keeps Security & Access and Activity Log", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("normal") } });
    flushSync();
    const labels = [...target.querySelectorAll(".nav-item")].map((b) => b.textContent);
    expect(labels.some((l) => l?.includes("Integrations"))).toBe(false);
    expect(labels.some((l) => l?.includes("Activity Log"))).toBe(true);
    expect(labels.some((l) => l?.includes("Security & Access"))).toBe(true);
    unmount(app);
  });

  it("switching to Categories via the nav shows the category sub-tabs", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore() } });
    flushSync();
    const categoriesBtn = [...target.querySelectorAll<HTMLButtonElement>(".nav-item")].find((b) => b.textContent?.includes("Categories"))!;
    categoriesBtn.click();
    flushSync();
    expect(target.textContent).toContain("Cost categories");
    expect(target.textContent).not.toContain("Home");
    unmount(app);
  });

  it("the mobile dropdown lists the same groups as the sidebar", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin") } });
    flushSync();
    const sidebarCount = target.querySelectorAll(".nav-item").length;
    const dropdownCount = target.querySelectorAll(".nav-select option").length;
    expect(dropdownCount).toBe(sidebarCount);
    unmount(app);
  });
});

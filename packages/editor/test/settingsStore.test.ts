import { describe, it, expect, vi, afterEach } from "vitest";
import { createSettingsStore } from "../src/lib/settingsStore.svelte";

afterEach(() => vi.unstubAllGlobals());

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

describe("createSettingsStore — notifications", () => {
  it("loads notification settings from the fetched document", async () => {
    const doc = {
      version: 1, costCategories: [], inventoryCategories: [], workCategories: [],
      contactTypes: [], consumableUnits: [], consumableCategories: [],
      notifications: {
        enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
        haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
      },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
    const store = createSettingsStore(() => "home-1");
    await tick();
    expect(store.notificationSettings.warrantyDaysThreshold).toBe(30);
  });

  it("updateNotificationSettings PUTs to the notifications settings endpoint", async () => {
    const doc = {
      version: 1, costCategories: [], inventoryCategories: [], workCategories: [],
      contactTypes: [], consumableUnits: [], consumableCategories: [],
      notifications: {
        enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
        haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
      },
    };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc });
    vi.stubGlobal("fetch", fetchMock);
    const store = createSettingsStore(() => "home-1");
    await tick();

    fetchMock.mockResolvedValue({ ok: true, status: 204, json: async () => ({}) });
    await store.updateNotificationSettings({ ...store.notificationSettings, warrantyDaysThreshold: 45 });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/homes/home-1/settings/notifications",
      expect.objectContaining({ method: "PUT" }),
    );
  });
});

describe("createSettingsStore — insuranceCategories", () => {
  it("loads insuranceCategories from the fetched document", async () => {
    const doc = {
      version: 1, costCategories: [], inventoryCategories: [], workCategories: [],
      contactTypes: [], consumableUnits: [], consumableCategories: [],
      insuranceCategories: [{ id: "icat-home", name: "Home", emoji: "🏠" }],
      notifications: {
        enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
        haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
      },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
    const store = createSettingsStore(() => "home-1");
    await tick();
    expect(store.insuranceCategories).toEqual([{ id: "icat-home", name: "Home", emoji: "🏠" }]);
  });

  it("updateInsuranceCategories PUTs to the insurance-categories settings endpoint", async () => {
    const doc = {
      version: 1, costCategories: [], inventoryCategories: [], workCategories: [],
      contactTypes: [], consumableUnits: [], consumableCategories: [], insuranceCategories: [],
      notifications: {
        enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
        haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
      },
    };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc });
    vi.stubGlobal("fetch", fetchMock);
    const store = createSettingsStore(() => "home-1");
    await tick();

    fetchMock.mockResolvedValue({ ok: true, status: 204, json: async () => ({}) });
    await store.updateInsuranceCategories([{ id: "icat-pet", name: "Pet", emoji: "🐶" }]);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/homes/home-1/settings/insurance-categories",
      expect.objectContaining({ method: "PUT" }),
    );
  });
});

describe("createSettingsStore — owners/stores", () => {
  it("loads owners and stores from the fetched document", async () => {
    const doc = {
      version: 1, costCategories: [], inventoryCategories: [], workCategories: [],
      contactTypes: [], consumableUnits: [], consumableCategories: [], insuranceCategories: [],
      owners: [{ id: "o1", name: "Alice" }], stores: [{ id: "s1", name: "Ikea" }],
      notifications: {
        enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
        haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
      },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }));
    const store = createSettingsStore(() => "home-1");
    await tick();
    expect(store.owners).toEqual([{ id: "o1", name: "Alice" }]);
    expect(store.stores).toEqual([{ id: "s1", name: "Ikea" }]);
  });

  it("createOwner appends a new owner and PUTs the full list", async () => {
    const doc = {
      version: 1, costCategories: [], inventoryCategories: [], workCategories: [],
      contactTypes: [], consumableUnits: [], consumableCategories: [], insuranceCategories: [],
      owners: [{ id: "o1", name: "Alice" }], stores: [],
      notifications: {
        enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
        haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
      },
    };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc });
    vi.stubGlobal("fetch", fetchMock);
    const store = createSettingsStore(() => "home-1");
    await tick();

    fetchMock.mockResolvedValue({ ok: true, status: 204, json: async () => ({}) });
    const created = await store.createOwner("Bob");
    expect(created.name).toBe("Bob");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/homes/home-1/settings/owners",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify([{ id: "o1", name: "Alice" }, created]),
      }),
    );
  });

  it("createStore appends a new store and PUTs the full list", async () => {
    const doc = {
      version: 1, costCategories: [], inventoryCategories: [], workCategories: [],
      contactTypes: [], consumableUnits: [], consumableCategories: [], insuranceCategories: [],
      owners: [], stores: [],
      notifications: {
        enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
        haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
      },
    };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc });
    vi.stubGlobal("fetch", fetchMock);
    const store = createSettingsStore(() => "home-1");
    await tick();

    fetchMock.mockResolvedValue({ ok: true, status: 204, json: async () => ({}) });
    const created = await store.createStore("Amazon");
    expect(created.name).toBe("Amazon");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/homes/home-1/settings/stores",
      expect.objectContaining({ method: "PUT", body: JSON.stringify([created]) }),
    );
  });
});

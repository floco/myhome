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
      suppliers: [], consumableUnits: [], consumableCategories: [],
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
      suppliers: [], consumableUnits: [], consumableCategories: [],
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

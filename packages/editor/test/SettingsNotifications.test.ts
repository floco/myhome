import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsNotifications from "../src/lib/components/settings/SettingsNotifications.svelte";

function makeStore() {
  return {
    notificationSettings: {
      enabled: true, choresDueSoonThreshold: 0.25, warrantyDaysThreshold: 30,
      haPushEnabled: false, haNotifyService: null, haPushTime: "08:00",
    },
    loaded: true,
    updateNotificationSettings: vi.fn(),
  };
}

describe("SettingsNotifications", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("renders current settings and reflects the enabled toggle", () => {
    const app = mount(SettingsNotifications, { target, props: { store: makeStore() } });
    flushSync();
    const heading = Array.from(target.querySelectorAll("h2")).find((h) => h.textContent === "Notifications");
    expect(heading).toBeDefined();
    expect((target.querySelector(".notif-enable-toggle") as HTMLInputElement).checked).toBe(true);
    unmount(app);
  });

  it("hides push fields until 'Send a daily digest' is checked", () => {
    const app = mount(SettingsNotifications, { target, props: { store: makeStore() } });
    flushSync();
    const labels = Array.from(target.querySelectorAll(".modal-label")).map((el) => el.textContent);
    expect(labels).not.toContain("HA notify service");
    unmount(app);
  });

  it("saves edited settings via store.updateNotificationSettings", async () => {
    const store = makeStore();
    const app = mount(SettingsNotifications, { target, props: { store } });
    flushSync();
    const enableToggle = target.querySelector(".notif-enable-toggle") as HTMLInputElement;
    enableToggle.click();
    enableToggle.click();
    flushSync();
    const saveBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Save"))!;
    (saveBtn as HTMLButtonElement).click();
    await Promise.resolve();
    expect(store.updateNotificationSettings).toHaveBeenCalledWith(
      expect.objectContaining({ enabled: true, warrantyDaysThreshold: 30 }),
    );
    unmount(app);
  });
});

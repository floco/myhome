import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import NotificationBell from "../src/lib/components/NotificationBell.svelte";
import { createNotificationStore } from "../src/lib/notificationStore.svelte";

const sample = [
  { type: "chore", refId: "c1", title: "Sweep", detail: "Due today", severity: "warning" },
  { type: "low_stock", refId: "co1", title: "Salt", detail: "Out of stock", severity: "critical" },
  { type: "warranty", refId: "i1", title: "TV", detail: "Warranty expires in 5d", severity: "info" },
];

afterEach(() => vi.unstubAllGlobals());

async function makeTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

function makeStore() {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => sample }));
  return createNotificationStore(() => "home-1");
}

describe("NotificationBell", () => {
  it("shows a badge with the notification count", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(NotificationBell, { target, props: { store, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".notif-badge")!.textContent).toBe("3");

    unmount(comp);
    target.remove();
  });

  it("opens the dropdown grouped by type on click and calls onnavigate on selection", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(NotificationBell, { target, props: { store, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".notif-bell") as HTMLButtonElement).click();
    await tick();
    flushSync();

    const labels = Array.from(target.querySelectorAll(".notif-group-label")).map((el) => el.textContent);
    expect(labels).toEqual(["Chores", "Low Stock", "Warranty"]);

    (target.querySelector(".notif-item") as HTMLButtonElement).click();
    expect(onnavigate).toHaveBeenCalledWith(sample[0]);
    flushSync();
    expect(target.querySelector(".notif-dropdown")).toBeNull();

    unmount(comp);
    target.remove();
  });

  it("closes the dropdown on outside click", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(NotificationBell, { target, props: { store, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    (target.querySelector(".notif-bell") as HTMLButtonElement).click();
    await tick();
    flushSync();
    expect(target.querySelector(".notif-dropdown")).not.toBeNull();

    document.body.click();
    await tick();
    flushSync();
    expect(target.querySelector(".notif-dropdown")).toBeNull();

    unmount(comp);
    target.remove();
  });
});

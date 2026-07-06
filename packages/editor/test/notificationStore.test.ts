import { describe, it, expect, vi, afterEach } from "vitest";
import { createNotificationStore } from "../src/lib/notificationStore.svelte";

afterEach(() => vi.unstubAllGlobals());

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

describe("createNotificationStore", () => {
  it("fetches notifications for the current home on init", async () => {
    const sample = [
      { type: "chore", refId: "c1", title: "Sweep", detail: "Due today", severity: "warning" },
    ];
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => sample }));
    const store = createNotificationStore(() => "home-1");
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.notifications).toEqual(sample);
    expect(fetch).toHaveBeenCalledWith("/api/homes/home-1/notifications");
  });

  it("returns an empty list without fetching when there is no active home", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    const store = createNotificationStore(() => null);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.notifications).toEqual([]);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("refresh() re-fetches", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);
    const store = createNotificationStore(() => "home-1");
    await tick();
    await store.refresh();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("sets loadError on a failed fetch", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    const store = createNotificationStore(() => "home-1");
    await tick();
    expect(store.loadError).toContain("500");
  });
});

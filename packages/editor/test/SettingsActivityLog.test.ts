import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsActivityLog from "../src/lib/components/settings/SettingsActivityLog.svelte";
import { homesStore } from "../src/lib/homesStore.svelte";

describe("SettingsActivityLog", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    homesStore.setActiveHomeId("home-1");
    fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.startsWith("/api/homes/home-1/activity")) {
        return Promise.resolve({ ok: true, json: async () => ({ entries: [], total: 0 }) });
      }
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    homesStore._reset();
    target.remove();
  });

  it("renders the Activity Log section", async () => {
    const app = mount(SettingsActivityLog, { target });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Activity Log");
    unmount(app);
  });

  it("fetches recent activity on mount", async () => {
    const app = mount(SettingsActivityLog, { target });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/homes/home-1/activity"));
    unmount(app);
  });

  it("renders returned entries with description", async () => {
    fetchMock.mockImplementation((url: string) => {
      if (url.startsWith("/api/homes/home-1/activity")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            entries: [{
              id: "e1", timestamp: "2026-07-08T12:00:00+00:00", userId: "u1", username: "alice",
              module: "works", action: "create", entityLabel: "Fix boiler", refId: null,
              description: "added work 'Fix boiler'",
            }],
            total: 1,
          }),
        });
      }
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    const app = mount(SettingsActivityLog, { target });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("added work 'Fix boiler'");
    unmount(app);
  });

  it("applying a module filter re-fetches with the module query param", async () => {
    const app = mount(SettingsActivityLog, { target });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const moduleSelect = target.querySelector(".activity-module-filter") as HTMLSelectElement;
    moduleSelect.value = "kb";
    moduleSelect.dispatchEvent(new Event("change", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 0));
    const lastCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
    expect(lastCall[0]).toContain("module=kb");
    unmount(app);
  });
});

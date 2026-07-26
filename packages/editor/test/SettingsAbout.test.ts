import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsAbout from "../src/lib/components/settings/SettingsAbout.svelte";

describe("SettingsAbout", () => {
  let target: HTMLDivElement;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  async function mountWith(info: object) {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => info });
    const app = mount(SettingsAbout, { target });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    return app;
  }

  it("shows the version and an up-to-date badge", async () => {
    const app = await mountWith({
      version: "0.8.0", deploymentMode: "standalone", pythonVersion: "3.12.3",
      arch: "x86_64", dbSchemaVersion: 6, homeCount: 1, databaseSizeBytes: 2048,
      uptimeSeconds: 3661,
      updateCheck: { status: "up_to_date", latestVersion: "0.8.0", checkedAt: "2026-07-26T18:00:00Z" },
    });
    expect(target.textContent).toContain("0.8.0");
    expect(target.textContent).toContain("up to date");
    unmount(app);
  });

  it("shows an update-available link with the latest version", async () => {
    const app = await mountWith({
      version: "0.8.0", deploymentMode: "home_assistant", pythonVersion: "3.12.3",
      arch: "aarch64", dbSchemaVersion: 6, homeCount: 2, databaseSizeBytes: 4096,
      uptimeSeconds: 60,
      updateCheck: { status: "update_available", latestVersion: "0.9.0", checkedAt: "2026-07-26T18:00:00Z" },
    });
    expect(target.textContent).toContain("0.9.0");
    unmount(app);
  });

  it("shows a neutral message when the update check is unknown", async () => {
    const app = await mountWith({
      version: "0.8.0", deploymentMode: "standalone", pythonVersion: "3.12.3",
      arch: "x86_64", dbSchemaVersion: 6, homeCount: 0, databaseSizeBytes: 0,
      uptimeSeconds: 5,
      updateCheck: { status: "unknown", latestVersion: null, checkedAt: null },
    });
    expect(target.textContent).toContain("Unable to check for updates");
    unmount(app);
  });
});

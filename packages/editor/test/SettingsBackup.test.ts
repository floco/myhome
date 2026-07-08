import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsBackup from "../src/lib/components/settings/SettingsBackup.svelte";

function mockBoilerplateEndpoints(url: string): { ok: boolean; json: () => Promise<unknown> } | null {
  if (url === "/api/backup/config") {
    return {
      ok: true,
      json: async () => ({ enabled: false, frequency: "daily", time: "03:00", dayOfWeek: 7, dayOfMonth: 1, retentionCount: 7 }),
    };
  }
  if (url === "/api/backup/scheduled") return { ok: true, json: async () => [] };
  return null;
}

describe("SettingsBackup", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    fetchMock = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      return Promise.resolve(new Response(null, { status: 200 }));
    });
    globalThis.fetch = fetchMock;
    globalThis.URL.createObjectURL = vi.fn().mockReturnValue("blob:fake");
    globalThis.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("renders the Backup & Restore card with both buttons", () => {
    const app = mount(SettingsBackup, { target, props: {} });
    flushSync();
    expect(target.textContent).toContain("Backup & Restore");
    expect(target.textContent).toContain("Download Backup");
    expect(target.textContent).toContain("Restore from Backup");
    unmount(app);
  });

  it("calls GET /api/backup/download when Download Backup is clicked", async () => {
    fetchMock = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      return Promise.resolve(new Response("fake-zip-content", {
        status: 200,
        headers: { "Content-Disposition": 'attachment; filename="myhome-backup-2026-06-29.zip"' },
      }));
    });
    globalThis.fetch = fetchMock;
    const app = mount(SettingsBackup, { target, props: {} });
    flushSync();
    const btn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("Download Backup"))!;
    btn.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(fetchMock).toHaveBeenCalledWith("/api/backup/download");
    unmount(app);
  });

  it("shows confirmation modal and posts FormData on confirm", async () => {
    fetchMock = vi.fn().mockImplementation((url: string) => {
      const boiler = mockBoilerplateEndpoints(url);
      if (boiler) return Promise.resolve(boiler);
      return Promise.resolve(new Response(null, { status: 204 }));
    });
    globalThis.fetch = fetchMock;
    const app = mount(SettingsBackup, { target, props: {} });
    flushSync();
    const fileInput = target.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["fake-zip"], "backup.zip", { type: "application/zip" });
    Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
    fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    expect(target.querySelector(".ui-modal")).not.toBeNull();
    const restoreBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Restore")!;
    restoreBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(fetchMock).toHaveBeenCalledWith("/api/backup/restore", expect.objectContaining({ method: "POST" }));
    unmount(app);
  });

  it("renders the Scheduled Backups section with defaults", async () => {
    const app = mount(SettingsBackup, { target, props: {} });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    expect(target.textContent).toContain("Scheduled Backups");
    expect((target.querySelector(".backup-enable-toggle") as HTMLInputElement).checked).toBe(false);
    unmount(app);
  });

  it("Run backup now calls POST /api/backup/scheduled/run", async () => {
    const app = mount(SettingsBackup, { target, props: {} });
    await new Promise((r) => setTimeout(r, 0));
    flushSync();
    const runBtn = Array.from(target.querySelectorAll("button")).find((b) => b.textContent?.includes("Run backup now"))!;
    (runBtn as HTMLButtonElement).click();
    await new Promise((r) => setTimeout(r, 0));
    expect(fetchMock).toHaveBeenCalledWith("/api/backup/scheduled/run", expect.objectContaining({ method: "POST" }));
    unmount(app);
  });
});

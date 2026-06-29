import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsPage from "../src/lib/components/SettingsPage.svelte";

function makeStore() {
  return {
    costCategories: [],
    inventoryCategories: [],
    workCategories: [],
    suppliers: [],
    loaded: true,
    loadError: null,
    updateCostCategories: vi.fn(),
    updateInventoryCategories: vi.fn(),
    updateWorkCategories: vi.fn(),
    updateSuppliers: vi.fn(),
    placeCostCategory: vi.fn(),
  };
}

describe("SettingsPage — Backup & Restore", () => {
  let target: HTMLDivElement;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
    fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 200 }));
    globalThis.fetch = fetchMock;
    globalThis.URL.createObjectURL = vi.fn().mockReturnValue("blob:fake");
    globalThis.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    target.remove();
  });

  it("renders the Backup & Restore card with both buttons", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore() } });
    flushSync();
    expect(target.textContent).toContain("Backup & Restore");
    expect(target.textContent).toContain("Download Backup");
    expect(target.textContent).toContain("Restore from Backup");
    unmount(app);
  });

  it("has a hidden file input that accepts .zip files", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore() } });
    flushSync();
    const fileInput = target.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).not.toBeNull();
    expect(fileInput.accept).toBe(".zip");
    unmount(app);
  });

  it("calls GET /api/backup/download when Download Backup is clicked", async () => {
    fetchMock = vi.fn().mockResolvedValue(
      new Response("fake-zip-content", {
        status: 200,
        headers: { "Content-Disposition": 'attachment; filename="myhome-backup-2026-06-29.zip"' },
      })
    );
    globalThis.fetch = fetchMock;
    const app = mount(SettingsPage, { target, props: { store: makeStore() } });
    flushSync();

    const btn = [...target.querySelectorAll("button")].find(
      (b) => b.textContent?.includes("Download Backup")
    )!;
    btn.click();
    await new Promise((r) => setTimeout(r, 0));

    expect(fetchMock).toHaveBeenCalledWith("/api/backup/download");
    unmount(app);
  });

  it("shows confirmation modal when a zip file is selected for restore", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore() } });
    flushSync();

    const fileInput = target.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["fake-zip"], "backup.zip", { type: "application/zip" });
    Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
    fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    expect(target.querySelector(".ui-modal")).not.toBeNull();
    expect(target.textContent).toContain("This will replace all current data");
    unmount(app);
  });

  it("calls POST /api/backup/restore with FormData when Restore is confirmed", async () => {
    fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    globalThis.fetch = fetchMock;
    const app = mount(SettingsPage, { target, props: { store: makeStore() } });
    flushSync();

    const fileInput = target.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["fake-zip"], "backup.zip", { type: "application/zip" });
    Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
    fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    const restoreBtn = [...target.querySelectorAll("button")].find(
      (b) => b.textContent?.trim() === "Restore"
    )!;
    restoreBtn.click();
    await new Promise((r) => setTimeout(r, 0));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/backup/restore",
      expect.objectContaining({ method: "POST" })
    );
    unmount(app);
  });

  it("dismisses modal when Cancel is clicked without calling fetch", async () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore() } });
    flushSync();

    const fileInput = target.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["fake-zip"], "backup.zip", { type: "application/zip" });
    Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
    fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();

    const cancelBtn = [...target.querySelectorAll("button")].find(
      (b) => b.textContent?.trim() === "Cancel"
    )!;
    cancelBtn.click();
    flushSync();

    expect(target.querySelector(".ui-modal")).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
    unmount(app);
  });
});

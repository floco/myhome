import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SettingsGeneral from "../src/lib/components/settings/SettingsGeneral.svelte";
import { homesStore } from "../src/lib/homesStore.svelte";

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

function seedHome(overrides: Partial<{ id: string; name: string; type: "existing" | "project"; enabledModules: string[] }> = {}) {
  const home = {
    id: "h1", name: "Rue des Lilas", type: "existing" as const,
    enabledModules: ["home", "plan"], createdAt: "2026-01-01T00:00:00Z",
    ...overrides,
  };
  homesStore.homes.push(home);
  homesStore.setActiveHomeId(home.id);
  return home;
}

describe("SettingsGeneral", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    homesStore._reset();
    target.remove();
  });

  it("renders the home name and type", () => {
    seedHome();
    const app = mount(SettingsGeneral, { target, props: {} });
    flushSync();
    expect(target.textContent).toContain("Rue des Lilas");
    expect(target.textContent).toContain("Existing home");
    unmount(app);
  });

  it("renders core module checkboxes reflecting enabledModules", () => {
    seedHome({ enabledModules: ["home", "plan", "chores"] });
    const app = mount(SettingsGeneral, { target, props: {} });
    flushSync();
    const choresRow = [...target.querySelectorAll(".module-row")].find((r) => r.textContent?.includes("Chores"))!;
    expect((choresRow.querySelector("input") as HTMLInputElement).checked).toBe(true);
    const worksRow = [...target.querySelectorAll(".module-row")].find((r) => r.textContent?.includes("Works"))!;
    expect((worksRow.querySelector("input") as HTMLInputElement).checked).toBe(false);
    unmount(app);
  });

  it("toggling a module checkbox calls patchHome with a PATCH request", async () => {
    seedHome({ enabledModules: ["home"] });
    vi.stubGlobal("fetch", makeFetch(200, { id: "h1", name: "Rue des Lilas", type: "existing", enabledModules: ["home", "chores"], createdAt: "2026-01-01T00:00:00Z" }));
    const app = mount(SettingsGeneral, { target, props: {} });
    flushSync();
    const choresRow = [...target.querySelectorAll(".module-row")].find((r) => r.textContent?.includes("Chores"))!;
    (choresRow.querySelector("input") as HTMLInputElement).click();
    await new Promise((r) => setTimeout(r, 0));
    expect(fetch).toHaveBeenCalledWith("/api/homes/h1", expect.objectContaining({ method: "PATCH" }));
    unmount(app);
  });

  it("editing the home name saves via patchHome", async () => {
    seedHome();
    vi.stubGlobal("fetch", makeFetch(200, { id: "h1", name: "New Name", type: "existing", enabledModules: ["home", "plan"], createdAt: "2026-01-01T00:00:00Z" }));
    const app = mount(SettingsGeneral, { target, props: {} });
    flushSync();
    const editBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Edit")!;
    editBtn.click();
    flushSync();
    const input = target.querySelector("input.ui-input") as HTMLInputElement;
    input.value = "New Name";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const saveBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Save")!;
    saveBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(fetch).toHaveBeenCalledWith("/api/homes/h1", expect.objectContaining({ method: "PATCH" }));
    unmount(app);
  });

  it("shows a delete confirmation modal and calls deleteHome on confirm", async () => {
    seedHome();
    homesStore.homes.push({ id: "h2", name: "Second", type: "existing", enabledModules: [], createdAt: "" });
    vi.stubGlobal("fetch", makeFetch(204));
    const app = mount(SettingsGeneral, { target, props: {} });
    flushSync();
    const deleteBtn = [...target.querySelectorAll("button")].find((b) => b.textContent?.includes("Delete this home"))!;
    deleteBtn.click();
    flushSync();
    expect(target.querySelector(".ui-modal")).not.toBeNull();
    const confirmBtn = [...target.querySelectorAll(".ui-modal button")].find((b) => b.textContent?.trim() === "Delete")!;
    confirmBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(fetch).toHaveBeenCalledWith("/api/homes/h1", expect.objectContaining({ method: "DELETE" }));
    unmount(app);
  });
});

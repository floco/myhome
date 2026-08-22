import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import App from "../src/App.svelte";

function stubFetch404() {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    if (url === "/api/auth/me") {
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ id: "u1", username: "admin", role: "admin" }) });
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => undefined });
  }));
}

async function mountAndLoad(target: HTMLElement, route = "#/plan"): Promise<ReturnType<typeof mount>> {
  window.location.hash = route;
  const app = mount(App, { target });
  await tick(); await tick();
  flushSync();
  // The floor plan loads in view mode by default; enter edit mode so the
  // full button set (Picker/Furniture, etc.) is present for these checks.
  const editToggle = target.querySelector('button[title="Switch to edit mode"]') as HTMLButtonElement | null;
  editToggle?.click();
  flushSync();
  return app;
}

describe("App — floating toolbar button order", () => {
  it("keeps the Edit/View toggle button in a fixed slot, before Picker/Furniture", async () => {
    stubFetch404();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = await mountAndLoad(target);

    // mountAndLoad enters edit mode, so Picker/Furniture are both present.
    const toolbar = target.querySelector(".floating-toolbar") as HTMLElement;
    const buttons = Array.from(toolbar.querySelectorAll(":scope > button.ft-btn"));
    const toggleIndex = buttons.findIndex((b) => b.querySelector(".mode-icon") !== null);
    const pickerIndex = buttons.findIndex((b) => (b as HTMLButtonElement).title === "Toggle item picker");
    const furnitureIndex = buttons.findIndex((b) => (b as HTMLButtonElement).title === "Toggle furniture library");

    expect(toggleIndex).toBeGreaterThanOrEqual(0);
    expect(pickerIndex).toBeGreaterThan(toggleIndex);
    expect(furnitureIndex).toBeGreaterThan(toggleIndex);

    unmount(app);
    target.remove();
  });

  it("does not shift the toggle button's index when switching to view mode", async () => {
    stubFetch404();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = await mountAndLoad(target);

    const toolbar = target.querySelector(".floating-toolbar") as HTMLElement;
    const indexOfToggle = () =>
      Array.from(toolbar.querySelectorAll(":scope > button.ft-btn")).findIndex(
        (b) => b.querySelector(".mode-icon") !== null,
      );

    const editModeIndex = indexOfToggle();
    const toggleBtn = Array.from(toolbar.querySelectorAll(":scope > button.ft-btn")).find(
      (b) => b.querySelector(".mode-icon") !== null,
    ) as HTMLButtonElement;
    toggleBtn.click();
    flushSync();

    expect(indexOfToggle()).toBe(editModeIndex);

    unmount(app);
    target.remove();
  });
});
